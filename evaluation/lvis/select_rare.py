"""LVIS v1 val'den "nadir" (frequency = r) nesne içeren 50 görsellik alt küme seçer.

LVIS her kategoriyi eğitim kümesindeki görsel sayısına göre işaretler:
  f (frequent) > 100 görsel · c (common) 11–100 · r (rare) <= 10.
OWLv2, Grounding DINO ve YOLO-World makaleleri "görülmemiş nesne" başarısını
LVIS'in nadir (r) kategorileriyle raporlar; bu alt küme aynı ölçütü kullanır.

Seçim (sabit tohum):
  - görselde en az bir nadir kategori tam etiketli (not_exhaustive değil) olmalı,
  - en az 3 "kesinlikle yok" kategori olmalı,
  - olabildiğince çok farklı nadir kategori kapsansın diye, yeni nadir kategori
    getiren görseller önce seçilir.
Ayrıca tüm LVIS kategorilerinin sıklık sınıfı category_frequency.json'a yazılır
(rapor her sorguyu f / c / r diye ayırır).

Kullanım (proje kökünden):
  .venv\\Scripts\\python.exe -m evaluation.lvis.select_rare --download
"""

from __future__ import annotations

import argparse
import json
import random
from collections import Counter, defaultdict
from pathlib import Path

from evaluation.lvis.select_subset import ANNOTATIONS, IMAGE_DIR, download

SUBSET_FILE = Path(__file__).with_name("subset_nadir_50.json")
FREQUENCY_FILE = Path(__file__).with_name("category_frequency.json")
COUNT = 50
SEED = 42


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--download", action="store_true")
    args = parser.parse_args()
    data = json.loads(ANNOTATIONS.read_text(encoding="utf-8"))
    frequency = {c["name"]: c["frequency"] for c in data["categories"]}
    FREQUENCY_FILE.write_text(json.dumps(dict(sorted(frequency.items())), ensure_ascii=False, indent=0), encoding="utf-8")
    subset, candidates, covered = rare_subset(data, COUNT)
    SUBSET_FILE.write_text(json.dumps(subset, ensure_ascii=False, indent=1), encoding="utf-8")
    rare_pairs = sum(len(i["focus"]) for i in subset)
    print(f"{candidates} aday görsel · {len(subset)} seçildi · {len(covered)} farklı nadir kategori · "
          f"{rare_pairs} nadir 'var' sorusu")
    print("Nadir kategoriler:", ", ".join(sorted(covered)))
    print("Yok-sorusu sıklık dağılımı (ilk 4):", Counter(frequency[n] for i in subset for n in i["negatives"][:4]))
    if args.download:
        download(subset)
        print(f"Görseller: {IMAGE_DIR}")


def rare_subset(data: dict, count: int | None) -> tuple[list[dict], int, set[str]]:
    """Nadir küme seçimi. count=None: koşulu sağlayan tüm havuz (select_main.py).
    Dönüş: (küme, aday görsel sayısı, kapsanan nadir kategoriler)."""
    names = {c["id"]: c["name"] for c in data["categories"]}
    frequency = {c["name"]: c["frequency"] for c in data["categories"]}
    anns = defaultdict(list)
    for ann in data["annotations"]:
        anns[ann["image_id"]].append(ann)

    candidates = []
    for image in data["images"]:
        not_exhaustive = {names[c] for c in image.get("not_exhaustive_category_ids", [])}
        present = {names[a["category_id"]] for a in anns[image["id"]]}
        rare = sorted(n for n in present if frequency[n] == "r" and n not in not_exhaustive)
        if rare and len(image.get("neg_category_ids", [])) >= 3:
            candidates.append((image, rare))
    rng = random.Random(SEED)
    rng.shuffle(candidates)
    count = len(candidates) if count is None else count
    # Önce yeni nadir kategori getirenler; sonra kalan yer rastgele sırayla dolar.
    chosen, covered = [], set()
    for image, rare in candidates:
        if len(chosen) < count and set(rare) - covered:
            chosen.append((image, rare)); covered |= set(rare)
    chosen_ids = {c[0]["id"] for c in chosen}
    for image, rare in candidates:
        if len(chosen) < count and image["id"] not in chosen_ids:
            chosen.append((image, rare)); chosen_ids.add(image["id"]); covered |= set(rare)

    subset = []
    for image, rare in chosen:
        positives = defaultdict(list)
        for a in anns[image["id"]]:
            positives[names[a["category_id"]]].append([round(v, 1) for v in a["bbox"]])
        negatives = [names[c] for c in image["neg_category_ids"]]
        # "Yok" sorularında da önce nadir kategoriler: görülmemiş nesne adıyla uydurma kutu ölçülür.
        negatives.sort(key=lambda n: (frequency[n] != "r", frequency[n] != "c", n))
        subset.append({
            "image_id": image["id"], "group": "nadir", "coco_url": image["coco_url"],
            "file_name": image["coco_url"].rsplit("/", 1)[-1], "focus": rare,
            "width": image["width"], "height": image["height"],
            "positives": dict(sorted(positives.items())), "negatives": negatives,
            "not_exhaustive": sorted(names[c] for c in image.get("not_exhaustive_category_ids", [])),
        })
    return subset, len(candidates), covered


if __name__ == "__main__":
    main()
