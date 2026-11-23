"""Sunum örneklerini çalışan backend'de (127.0.0.1:8000) çalıştırır ve sonuç görsellerini kaydeder.

Sunumdan önce bir kez çalıştır: canlı demo yavaş kalırsa sonuclar/ altındaki görselleri gösterirsin,
sonuclar/ozet.json da SENARYO.md'deki sayıların kaynağıdır.

Kullanım (proje kökünden, backend açıkken):
  .venv\\Scripts\\python.exe sunum\\hazirla.py      # hepsi
  .venv\\Scripts\\python.exe sunum\\hazirla.py 7    # yalnızca 7. adım; ozet.json'daki diğerleri korunur
"""

from __future__ import annotations

import base64
import json
import sys
import urllib.request
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
IMAGES = HERE / "gorseller"
OUT = HERE / "sonuclar"
API = "http://127.0.0.1:8000"
ALL = ("owlvit", "grounding-dino", "yolo-world")

# (no, kısa ad, görsel, sorgu, modeller, ek form alanları)
CASES = [
    (1, "makas", "masa_12.jpeg", "makas", ALL, {}),
    (2, "envanter", "market_12.jpg", "sakız, şişe", ("owlvit",), {}),
    (4, "alkollu_icecek", "market_05.jpg", "alkollü içecek", ALL, {}),
    (5, "sac_spreyi", "masa_12.jpeg", "saç spreyi", ALL, {}),
    (6, "olmayan_kedi", "masa_12.jpeg", "kedi", ALL, {}),
    (7, "nadir_kibrit_kutusu", "nadir_kibrit_kutusu.jpg", "matchbox", ALL, {}),
    (7, "nadir_bozuk_para", "nadir_bozuk_para.jpg", "penny", ALL, {}),
    (7, "nadir_kelepce", "nadir_kelepce.jpg", "handcuff", ALL, {}),
    (7, "nadir_omlet", "nadir_omlet.jpg", "omelet", ALL, {}),
    (7, "nadir_kibrit_kutusu_tr", "nadir_kibrit_kutusu.jpg", "kibrit kutusu", ALL, {}),
    (7, "nadir_bozuk_para_tr", "nadir_bozuk_para.jpg", "bozuk para", ALL, {}),
    (7, "nadir_kelepce_tr", "nadir_kelepce.jpg", "kelepçe", ALL, {}),
    (7, "nadir_omlet_tr", "nadir_omlet.jpg", "omlet", ALL, {}),
    (8, "tv_unitesi", "otel_odasi_lvis.jpg", "televizyon ünitesi", ALL, {}),
    (8, "tv_unitesi_duzeltilmis", "otel_odasi_lvis.jpg", "televizyon ünitesi", ALL, {"english_query": "tv stand"}),
    (9, "pil", "masa_9.jpeg", "pil", ALL, {}),
]


def post(path: str, image: Path, fields: dict) -> dict:
    boundary = uuid.uuid4().hex
    body = []
    for key, value in {**fields, "include_image": "true"}.items():
        body.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{key}\"\r\n\r\n{value}\r\n".encode())
    body.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"image\"; filename=\"{image.name}\"\r\n"
                f"Content-Type: image/jpeg\r\n\r\n".encode() + image.read_bytes() + b"\r\n")
    body.append(f"--{boundary}--\r\n".encode())
    request = urllib.request.Request(API + path, data=b"".join(body),
                                     headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    with urllib.request.urlopen(request, timeout=900) as response:
        return json.loads(response.read())


def save(result: dict, name: str) -> dict:
    (OUT / f"{name}.jpg").write_bytes(base64.b64decode(result["annotated_image"]["data_base64"]))
    return {
        "aranan_ifade": result.get("primary_query"),
        "kaynak": result.get("translation_source"),
        "kutu": len(result["detections"]),
        "guven": sorted((round(d["confidence"], 2) for d in result["detections"]), reverse=True),
        "sure_ms": round(result.get("inference_time_ms", 0)),
    }


def main() -> None:
    OUT.mkdir(exist_ok=True)
    only = {int(arg) for arg in sys.argv[1:]}
    summary_file = OUT / "ozet.json"
    summary: dict[str, dict] = json.loads(summary_file.read_text(encoding="utf-8")) if only and summary_file.exists() else {}
    for number, name, image, query, models, extra in CASES:
        if only and number not in only:
            continue
        for model in models:
            key = f"{number:02d}_{name}_{model}"
            result = post("/detect", IMAGES / image, {"query": query, "model": model, **extra})
            summary[key] = save(result, key)
            print(key, summary[key], flush=True)

    if only and 3 not in only:
        summary_file.write_text(json.dumps(dict(sorted(summary.items())), ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"Kaydedildi: {OUT}")
        return

    # 3: örnekle arama. Örnek kutu, "sakız" aramasındaki en güvenli kutudur (elle çizmenin yerine).
    gum = post("/detect", IMAGES / "market_12.jpg", {"query": "sakız", "model": "owlvit"})
    best = max(gum["detections"], key=lambda d: d["confidence"])["box"]
    result = post("/detect-by-example", IMAGES / "market_12.jpg",
                  {**{k: round(v, 1) for k, v in best.items()}, "label": "sakız", "model": "owlvit"})
    key = "03_ornekle_arama_owlvit"
    summary[key] = {**save(result, key), "ornek_kutu": {k: round(v) for k, v in best.items()}}
    print(key, summary[key], flush=True)

    summary_file.write_text(json.dumps(dict(sorted(summary.items())), ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Kaydedildi: {OUT}")


if __name__ == "__main__":
    main()
