"""Yerel TR→EN çeviri modellerini nesne sorguları üzerinde karşılaştırır.

Adaylar: Marian (opus-mt-tr-en, şu an backend'de), opus-mt-tc-big-tr-en, NLLB-200-distilled-600M.
Her aday iki biçimde denenir:
  düz      : sorgu tek başına çevrilir ("kumanda")
  bağlamla : sorgu sabit bir cümle içinde çevrilir ("Fotoğrafta kumanda var.") ve nesne
             adı İngilizce cümleden çıkarılır. Cümle, modele kelimenin nesne olduğunu söyler.
Referans olarak şimdiki sistem (elle yazılmış sözlük + Marian) da ölçülür.

Puanlama (tr_en_test.tsv'deki kabul listesine göre):
  doğru   : çıktı kabul edilen karşılıklardan biri (küçük harf, artikel ve çoğul eki farkı yok sayılır)
  eklemeli: kabul edilen karşılık çıktının içinde geçiyor ama fazladan sözcük var
  yanlış  : ikisi de değil

Çalıştırma (proje kökünden):
  .venv\\Scripts\\python.exe -m evaluation.translation.compare_translators
"""

from __future__ import annotations

import re
import sys
import time
from collections import defaultdict
from pathlib import Path

import torch
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from backend.app.services import object_lexicon  # noqa: E402
# Bağlam cümlesi ve nesne çıkarma backend ile aynı koddur (ölçülen = çalışan).
from backend.app.services.translation_service import CONTEXT_TEMPLATE, extract_object  # noqa: E402

CACHE = ROOT / ".cache" / "translation"
TEST_FILE = Path(__file__).with_name("tr_en_test.tsv")
OUT_DIR = ROOT / "outputs" / "ceviri"

MODELS = {
    "marian": "Helsinki-NLP/opus-mt-tr-en",
    "opus-big": "Helsinki-NLP/opus-mt-tc-big-tr-en",
    "nllb": "facebook/nllb-200-distilled-600M",
}
_ARTICLES = re.compile(r"^(?:a|an|the|some|one)\s+", re.I)


def read_test_set() -> list[dict]:
    rows = []
    lines = [line for line in TEST_FILE.read_text(encoding="utf-8").splitlines() if line and not line.startswith("#")]
    for line in lines[1:]:
        turkish, accepted, group = line.split("\t")
        rows.append({"tr": turkish, "accepted": [a.strip() for a in accepted.split("|")], "group": group})
    return rows


def normalize(text: str) -> str:
    text = re.sub(r"[^\w\s-]", " ", text.casefold())
    text = _ARTICLES.sub("", " ".join(text.split()))
    return text


def singular_forms(text: str) -> set[str]:
    """Son sözcüğün olası tekil biçimleri: bottles → bottle, boxes → box, batteries → battery."""
    words = text.split()
    if not words:
        return {text}
    forms = {text}
    last = words[-1]
    for suffix, repl in (("ies", "y"), ("es", ""), ("s", "")):
        if last.endswith(suffix) and len(last) > len(suffix) + 2:
            forms.add(" ".join([*words[:-1], last[: -len(suffix)] + repl]))
    return forms


def score(output: str, accepted: list[str]) -> str:
    out = normalize(output)
    forms = {normalize(a) for a in accepted}
    forms |= {s for f in forms for s in singular_forms(f)}
    if singular_forms(out) & forms:
        return "doğru"
    padded = f" {out} "
    if any(f" {form} " in padded or f" {form}s " in padded or f" {form}es " in padded for form in forms):
        return "eklemeli"
    return "yanlış"


class Translator:
    def __init__(self, key: str):
        self.key = key
        repo = MODELS[key]
        kwargs = {"src_lang": "tur_Latn"} if key == "nllb" else {}
        self.tokenizer = AutoTokenizer.from_pretrained(repo, cache_dir=CACHE, **kwargs)
        self.model = AutoModelForSeq2SeqLM.from_pretrained(repo, cache_dir=CACHE).eval()
        self.generate_kwargs = {"max_new_tokens": 64, "num_beams": 4, "do_sample": False}
        if key == "nllb":
            self.generate_kwargs["forced_bos_token_id"] = self.tokenizer.convert_tokens_to_ids("eng_Latn")

    @torch.inference_mode()
    def translate(self, texts: list[str]) -> list[str]:
        inputs = self.tokenizer(texts, return_tensors="pt", padding=True)
        tokens = self.model.generate(**inputs, **self.generate_kwargs)
        return [" ".join(t.split()) for t in self.tokenizer.batch_decode(tokens, skip_special_tokens=True)]


def run_variant(translator: Translator, rows: list[dict], context: bool) -> tuple[list[dict], float, int]:
    sources = [CONTEXT_TEMPLATE.format(query=r["tr"]) if context else r["tr"] for r in rows]
    started = time.perf_counter()
    outputs = []
    for i in range(0, len(sources), 16):
        outputs.extend(translator.translate(sources[i:i + 16]))
    elapsed = (time.perf_counter() - started) * 1000 / len(rows)
    results, fallbacks = [], 0
    plain_cache: dict[str, str] = {}
    for row, raw in zip(rows, outputs):
        candidate = raw
        if context:
            extracted = extract_object(raw)
            if extracted is None:
                # Cümle beklenen kalıpta değilse düz çeviriye düşülür; sayısı raporlanır.
                fallbacks += 1
                if row["tr"] not in plain_cache:
                    plain_cache[row["tr"]] = translator.translate([row["tr"]])[0]
                candidate = plain_cache[row["tr"]]
            else:
                candidate = extracted
        results.append({**row, "raw": raw, "output": candidate, "result": score(candidate, row["accepted"])})
    return results, elapsed, fallbacks


def run_current_system(marian: Translator, rows: list[dict]) -> list[dict]:
    """Şimdiki backend davranışı: sözlükte varsa sözlük, yoksa Marian düz çeviri."""
    results = []
    for row in rows:
        lexicon = object_lexicon.lookup(row["tr"])
        output = lexicon if lexicon is not None else marian.translate([row["tr"]])[0]
        results.append({**row, "raw": output, "output": output, "result": score(output, row["accepted"]),
                        "in_lexicon": lexicon is not None})
    return results


def summarize(results: list[dict]) -> dict:
    counts = defaultdict(int)
    for r in results:
        counts[r["result"]] += 1
    n = len(results)
    return {"n": n, **{k: counts[k] for k in ("doğru", "eklemeli", "yanlış")}, "oran": counts["doğru"] / n if n else 0.0}


def pct(x: float) -> str:
    return f"%{x * 100:.0f}"


def main() -> None:
    torch.manual_seed(0)
    rows = read_test_set()
    groups = sorted({r["group"] for r in rows})
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    all_results: dict[str, list[dict]] = {}
    timings: dict[str, float] = {}
    fallback_counts: dict[str, int] = {}
    translators = {}
    for key in MODELS:
        print(f"Yükleniyor: {MODELS[key]}", flush=True)
        translators[key] = Translator(key)
        for context in (False, True):
            name = f"{key} · {'bağlamla' if context else 'düz'}"
            results, ms, fallbacks = run_variant(translators[key], rows, context)
            all_results[name], timings[name], fallback_counts[name] = results, ms, fallbacks
            s = summarize(results)
            print(f"  {name:22s} doğru {s['doğru']}/{s['n']} ({pct(s['oran'])}) · eklemeli {s['eklemeli']} · {ms:.0f} ms/sorgu", flush=True)
    current = run_current_system(translators["marian"], rows)

    lines = ["# TR→EN çeviri karşılaştırması (nesne sorguları)", "",
             f"Test seti: {len(rows)} sorgu ({', '.join(f'{g} {sum(r['group'] == g for r in rows)}' for g in groups)}).",
             f"Bağlam cümlesi: \"{CONTEXT_TEMPLATE}\". CPU, num_beams=4, sabit (deterministik) çözümleme.", "",
             "## Genel sonuç", "",
             "| Aday | Doğru | Eklemeli | Yanlış | Doğru oranı | Süre (ms/sorgu, toplu) | Kalıp dışı cümle |",
             "|---|---|---|---|---|---|---|"]
    for name, results in all_results.items():
        s = summarize(results)
        fb = fallback_counts[name] if "bağlamla" in name else "—"
        lines.append(f"| {name} | {s['doğru']} | {s['eklemeli']} | {s['yanlış']} | {pct(s['oran'])} | {timings[name]:.0f} | {fb} |")
    s = summarize(current)
    lines.append(f"| şimdiki sistem (sözlük + Marian) | {s['doğru']} | {s['eklemeli']} | {s['yanlış']} | {pct(s['oran'])} | — | — |")
    in_lex = [r for r in current if r["in_lexicon"]]
    out_lex = [r for r in current if not r["in_lexicon"]]
    lines += ["", f"Şimdiki sistemde {len(in_lex)} sorgu sözlükten geldi (doğru {pct(summarize(in_lex)['oran'])}); "
              f"sözlükte olmayan {len(out_lex)} sorguda Marian'a düştü (doğru {pct(summarize(out_lex)['oran'])}). "
              "Sözlük bu test setinin bir kısmı için elle yazıldığından o satır tavan değeri gibi okunmalı, adil bir rakip değildir.", "",
              "## Gruplara göre doğru oranı", "",
              "| Aday | " + " | ".join(groups) + " |", "|---|" + "---|" * len(groups)]
    for name, results in [*all_results.items(), ("şimdiki sistem", current)]:
        cells = []
        for g in groups:
            sub = [r for r in results if r["group"] == g]
            cells.append(f"{summarize(sub)['doğru']}/{len(sub)}")
        lines.append(f"| {name} | " + " | ".join(cells) + " |")

    lines += ["", "## Sorgu bazında çıktılar", "",
              "✓ doğru · + eklemeli · ✗ yanlış", "",
              "| Türkçe | grup | kabul | " + " | ".join(all_results) + " | şimdiki |",
              "|---|---|---|" + "---|" * (len(all_results) + 1)]
    mark = {"doğru": "✓", "eklemeli": "+", "yanlış": "✗"}
    for i, row in enumerate(rows):
        cells = [f"{mark[res[i]['result']]} {res[i]['output']}" for res in all_results.values()]
        cells.append(f"{mark[current[i]['result']]} {current[i]['output']}")
        lines.append(f"| {row['tr']} | {row['group']} | {' / '.join(row['accepted'][:3])} | " + " | ".join(cells) + " |")
    report = OUT_DIR / "karsilastirma.md"
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Rapor: {report}")


if __name__ == "__main__":
    main()
