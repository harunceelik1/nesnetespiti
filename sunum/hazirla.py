"""Sunum örneklerini çalıştırır ve sonuç görsellerini kaydeder (backend gerekmez).

Uygulama yalnızca OWLv2 large ile çalışır; sunumdaki karşılaştırma için diğer modeller de
burada, uygulamanın /detect akışının aynısıyla çalıştırılır: çeviri (process_query) →
run_detection → Dengeli hassasiyet politikası → aynı kutu çizimi. Böylece görseller
uygulamada canlı alınan sonuçla birebir aynıdır (OWLv2 large için).

Modeller (dosya adındaki son ek):
  owlv2-large    uygulamanın modeli
  owlv2-base     aynı ailenin küçük modeli (LVIS nadirde large ile berabere; dürüstlük için)
  grounding-dino Grounding DINO tiny
  yolo-world     YOLO-World s

sonuclar/ozet.json SENARYO.md'deki sayıların kaynağıdır.

Kullanım (proje kökünden):
  .venv\\Scripts\\python.exe sunum\\hazirla.py      # hepsi
  .venv\\Scripts\\python.exe sunum\\hazirla.py 7    # yalnızca 7. adım; ozet.json'daki diğerleri korunur
"""

from __future__ import annotations

import json
import os
import sys
import warnings
from pathlib import Path

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
warnings.filterwarnings("ignore")

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from PIL import Image  # noqa: E402

from backend.app.services import sensitivity as sensitivity_levels  # noqa: E402
from backend.app.services.exemplar_search import search_by_example  # noqa: E402
from backend.app.services.inference_orchestrator import run_detection  # noqa: E402
from backend.app.services.query_processor import process_query  # noqa: E402
from backend.app.services.translation_service import TranslationService  # noqa: E402
from backend.app.utils.visualization import annotate_image  # noqa: E402

IMAGES = HERE / "gorseller"
OUT = HERE / "sonuclar"
LEVEL = "balanced"  # sunumda her adım Dengeli (uygulamanın varsayılanı)
APP = "owlv2-large"
ALL = (APP, "owlv2-base", "grounding-dino", "yolo-world")
ONLY_APP = (APP,)

# (no, kısa ad, görsel, sorgu, modeller, düzeltilmiş İngilizce ifade)
CASES = [
    (1, "makas", "masa_12.jpeg", "makas", ALL, None),
    (2, "envanter", "market_12.jpg", "sakız, şişe", ONLY_APP, None),
    (4, "alkollu_icecek", "market_05.jpg", "alkollü içecek", ALL, None),
    (5, "sac_spreyi", "masa_12.jpeg", "saç spreyi", ALL, None),
    (6, "olmayan_kedi", "masa_12.jpeg", "kedi", ALL, None),
    (7, "nadir_kibrit_kutusu", "nadir_kibrit_kutusu.jpg", "matchbox", ALL, None),
    (7, "nadir_bozuk_para", "nadir_bozuk_para.jpg", "penny", ALL, None),
    (7, "nadir_kelepce", "nadir_kelepce.jpg", "handcuff", ALL, None),
    (7, "nadir_omlet", "nadir_omlet.jpg", "omelet", ALL, None),
    (7, "nadir_kibrit_kutusu_tr", "nadir_kibrit_kutusu.jpg", "kibrit kutusu", ALL, None),
    (7, "nadir_bozuk_para_tr", "nadir_bozuk_para.jpg", "bozuk para", ALL, None),
    (7, "nadir_kelepce_tr", "nadir_kelepce.jpg", "kelepçe", ALL, None),
    (7, "nadir_omlet_tr", "nadir_omlet.jpg", "omlet", ALL, None),
    (8, "tv_unitesi", "otel_odasi_lvis.jpg", "televizyon ünitesi", ALL, None),
    (8, "tv_unitesi_duzeltilmis", "otel_odasi_lvis.jpg", "televizyon ünitesi", ALL, "tv stand"),
    (9, "pil", "masa_9.jpeg", "pil", ALL, None),
]


def load_detectors(needed: set[str]) -> dict:
    from backend.app.models.detector_registry import DetectorRegistry
    from backend.app.models.owlv2_service import Owlv2LargeService, Owlv2Service
    factories = {APP: Owlv2LargeService, "owlv2-base": Owlv2Service}
    detectors = {}
    for model in ALL:
        if model in needed:
            detectors[model] = (factories[model]() if model in factories
                                else DetectorRegistry(model_ids=(model,)).get(model))
    return detectors


def save(result: dict, image: Image.Image, name: str) -> dict:
    with annotate_image(image, result["detections"]) as annotated:
        annotated.save(OUT / f"{name}.jpg", format="JPEG")
    return {
        "aranan_ifade": result.get("primary_query"),
        "kaynak": result.get("translation_source"),
        "kutu": len(result["detections"]),
        "emin_degil": sum(bool(d.get("uncertain")) for d in result["detections"]),
        "guven": sorted((round(d["confidence"], 2) for d in result["detections"]), reverse=True),
        "sure_ms": round(result.get("inference_time_ms", 0)),
        "cihaz": result.get("device"),
    }


def open_image(name: str) -> Image.Image:
    with Image.open(IMAGES / name) as source:
        return source.convert("RGB")


def main() -> None:
    OUT.mkdir(exist_ok=True)
    only = {int(arg) for arg in sys.argv[1:]}
    cases = [c for c in CASES if not only or c[0] in only]
    needed = {m for c in cases for m in c[4]} | ({APP} if not only or 3 in only else set())
    detectors = load_detectors(needed)
    translation = TranslationService()

    summary_file = OUT / "ozet.json"
    summary: dict[str, dict] = json.loads(summary_file.read_text(encoding="utf-8")) if only and summary_file.exists() else {}
    for number, name, image_name, query, models, english in cases:
        image = open_image(image_name)
        plan = process_query(query, translation, english)
        for model in models:
            detector = detectors[model]
            result = run_detection(detector, image, plan, sensitivity_levels.detection_policy(detector, LEVEL))
            key = f"{number:02d}_{name}_{model}"
            summary[key] = save(result, image, key)
            print(key, summary[key], flush=True)

    if not only or 3 in only:
        # 3: örnekle arama. Örnek kutu, "sakız" aramasındaki en güvenli kutudur (elle çizmenin yerine).
        detector = detectors[APP]
        image = open_image("market_12.jpg")
        gum = run_detection(detector, image, process_query("sakız", translation, None),
                            sensitivity_levels.detection_policy(detector, LEVEL))
        best = max(gum["detections"], key=lambda d: d["confidence"])["box"]
        box = {k: round(v, 1) for k, v in best.items()}
        result = search_by_example(detector, image, box, "sakız", sensitivity_levels.exemplar_settings(LEVEL))
        key = f"03_ornekle_arama_{APP}"
        summary[key] = {**save(result, image, key), "ornek_kutu": {k: round(v) for k, v in best.items()}}
        print(key, summary[key], flush=True)

    summary_file.write_text(json.dumps(dict(sorted(summary.items())), ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Kaydedildi: {OUT}")


if __name__ == "__main__":
    main()
