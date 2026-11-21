"""Var/yok nesne kontrol vakaları: üretim akışıyla (çeviri → karşıt sorgu → eşik) çalışır.

- PRESENT: nesne görselde var → en az 1 kutu beklenir (kutu yeri sonuç görsellerinden kontrol edilir).
- ABSENT: nesne görselde yok → 0 kutu beklenir; her kutu sahte tespittir.

Kullanım (proje kökünden):
    .\\.venv\\Scripts\\python.exe evaluation/sanity_cases.py --models owlvit,grounding-dino
Sonuç görselleri: outputs/sanity/<model>/<görsel>_<sorgu>.jpg
"""

import argparse
import os
import sys
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IMAGES = ROOT / "images"
DESK = ROOT / "veri_toplama" / "fotograflar" / "00_ornek_masa.jpg"

CASES = (
    [("PRESENT", IMAGES / "two_people.jpg", q) for q in ["kravat", "kemer", "ceket", "el", "yüz", "adam", "insan"]]
    + [("PRESENT", IMAGES / "test.jpg", q) for q in ["güneş gözlüğü", "ayakkabı", "tekerlek", "araba", "insan"]]
    + [("PRESENT", IMAGES / "2074754.jpg", "insan")]
    + [("PRESENT", DESK, q) for q in ["laptop", "fare", "ilaç kutusu", "gözlük kutusu", "şarj aleti"]]
    + [("ABSENT", IMAGES / "test.jpg", q) for q in ["köpek", "uçak", "çanta", "şemsiye", "şişe"]]
    + [("ABSENT", IMAGES / "2074754.jpg", q) for q in ["köpek", "çanta", "kedi"]]
    + [("ABSENT", IMAGES / "two_people.jpg", q) for q in ["köpek", "araba", "şişe", "fare", "bardak"]]
    + [("ABSENT", DESK, q) for q in ["köpek", "şemsiye", "makas"]]
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--models", default="owlvit,grounding-dino")
    args = parser.parse_args()
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    warnings.filterwarnings("ignore")
    sys.path.insert(0, str(ROOT))
    from PIL import Image
    from backend.app.models.detector_registry import DetectorRegistry
    from backend.app.services.inference_orchestrator import run_detection
    from backend.app.services.query_processor import process_query
    from backend.app.services.translation_service import TranslationService
    from backend.app.utils.visualization import annotate_image

    translation = TranslationService()
    registry = DetectorRegistry()
    detectors = {name: registry.get(name) for name in args.models.split(",")}
    score = {name: {"PRESENT": [0, 0], "ABSENT": [0, 0]} for name in detectors}
    images = {}
    for kind, path, query in CASES:
        if not path.is_file():
            print(f"ATLANDI (görsel yok): {path}", flush=True)
            continue
        image = images.setdefault(path, Image.open(path).convert("RGB"))
        plan = process_query(query, translation)
        parts = []
        for name, detector in detectors.items():
            result = run_detection(detector, image, plan)
            found = result["detections"]
            ok = bool(found) if kind == "PRESENT" else not found
            score[name][kind][0] += ok
            score[name][kind][1] += 1
            out_dir = ROOT / "outputs" / "sanity" / name
            out_dir.mkdir(parents=True, exist_ok=True)
            with annotate_image(image, found) as annotated:
                annotated.save(out_dir / f"{path.stem}_{plan['primary_query'].replace(' ', '-')}.jpg")
            parts.append(f"{name} {'✓' if ok else '✗'} n={len(found)} {[round(d['confidence'], 2) for d in found]}")
        print(f"{kind:7} {path.stem[:14]:14} {query}->{plan['primary_query']:<16} " + " | ".join(parts), flush=True)
    for name, kinds in score.items():
        print(f"TOPLAM {name}: var olan {kinds['PRESENT'][0]}/{kinds['PRESENT'][1]} bulundu, "
              f"olmayan {kinds['ABSENT'][0]}/{kinds['ABSENT'][1]} doğru boş", flush=True)


if __name__ == "__main__":
    main()
