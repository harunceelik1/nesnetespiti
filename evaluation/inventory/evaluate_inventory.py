"""Calibration-only, en fazla 5 görüntülük inventory evaluation smoke test."""

import argparse
import csv
from datetime import datetime, timezone
import gc
import hashlib
import json
import os
from pathlib import Path
import random
import sys
import time
import warnings
from time import perf_counter
from uuid import uuid4

if __package__:
    from .grounding_dino_adapter import build_caption, resolve_label
    from .metrics import evaluate_boxes, summarize
    from .prompt_aliases import build_prompt_mapping, normalize_prompt
else:
    # Script doğrudan çalıştırıldığında backend package'i de bulunabilsin.
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from evaluation.inventory.grounding_dino_adapter import build_caption, resolve_label
    from evaluation.inventory.metrics import evaluate_boxes, summarize
    from evaluation.inventory.prompt_aliases import build_prompt_mapping, normalize_prompt


ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
RESULTS = ROOT / "results"
# Önceden belirlenen prompt listesi: test GT'sine/başarıya bakarak değiştirilmez.
CATEGORIES = (
    "puffed food", "dried fruit", "dried food", "instant drink", "instant noodles",
    "dessert", "drink", "alcohol", "milk", "canned food", "chocolate", "gum",
    "candy", "seasoner", "personal hygiene", "tissue", "stationery",
)
OWLVIT_CONFIDENCE_THRESHOLD = 0.05
MODEL_GROUPS = {"both": ("owlvit", "grounding-dino"), "all": ("owlvit", "grounding-dino", "yolo-world")}


def load_calibration(limit: int, seed: int = 42, data: Path = DATA) -> tuple[list[dict], dict]:
    if not 1 <= limit <= 5:
        raise ValueError("Bu smoke test yalnızca 1–5 calibration görüntüsünü destekler.")
    full_path, manifest_path = data / "full_annotations.json", data / "manifest.json"
    full = json.loads(full_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if (full.get("complete") is not True or full.get("revision") != manifest.get("revision")
            or full.get("image_count") != len(full.get("images", []))):
        raise ValueError("Tam annotation eksik veya revision manifest ile uyuşmuyor.")
    calibration_ids = manifest["split_image_ids"]["calibration"]
    if len(calibration_ids) != len(set(calibration_ids)) or set(calibration_ids) & set(manifest["split_image_ids"]["test"]):
        raise ValueError("Manifest ID'lerinde tekrar veya calibration/test çakışması var.")
    if len(calibration_ids) < limit:
        raise ValueError("Yeterli calibration görüntüsü yok.")
    selected = random.Random(seed).sample(sorted(calibration_ids), limit)
    # Test kutuları prompt/threshold seçmek veya metrik hesaplamak için kullanılmaz.
    lookup = {}
    for record in full["images"]:
        if record["image_id"] in selected:
            if record["image_id"] in lookup or record.get("subset") != "calibration":
                raise ValueError("Calibration annotation üyeliği geçersiz.")
            lookup[record["image_id"]] = record
    if set(lookup) != set(selected):
        raise ValueError("Seçili calibration ID'leri full annotation içinde bulunamadı.")
    for record in lookup.values():
        name = record["file_name"]
        if not isinstance(name, str) or not name or any(char in name for char in ("/", "\\", ":", "\x00")):
            raise ValueError("Geçersiz calibration dosya adı.")
        image = (data / "calibration/images" / name).resolve()
        if image.parent != (data / "calibration/images").resolve() or not image.is_file():
            raise ValueError("Calibration görüntüsü eksik veya images klasörü dışında.")
        for obj in record["objects"]:
            if obj["evaluation_category"] not in CATEGORIES:
                raise ValueError("Full annotation desteklenmeyen semantic aile içeriyor; sessizce atlanmayacak.")
    return [lookup[image_id] for image_id in selected], {
        "dataset": full["dataset"], "revision": full["revision"], "split": "calibration", "seed": seed,
        "full_annotations_sha256": hashlib.sha256(full_path.read_bytes()).hexdigest(),
        "manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
    }


def make_detector(model_id: str):
    # Sadece evaluation CLI süreci: ağırlıklar cache'te yoksa indirilmeyecek.
    # Production ortamına/servis koduna kalıcı değişiklik yapılmaz.
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    if model_id == "owlvit":
        from backend.app.models.owlvit_service import OwlViTService
        return OwlViTService()
    if model_id == "grounding-dino":
        from backend.app.models.grounding_dino_service import GroundingDinoService
        return GroundingDinoService()
    if model_id == "yolo-world":
        from backend.app.models.yoloworld_service import YoloWorldService, yolo_world_weights_cached
        # HF offline bayrakları Ultralytics'i kapsamaz; indirme olmaması için önce kontrol.
        if not yolo_world_weights_cached():
            raise FileNotFoundError("YOLO-World ağırlıkları önbellekte yok. Önce backend'i bir kez başlatıp "
                                    "YOLO-World'ün yüklenmesini bekleyin; evaluation indirme başlatmaz.")
        return YoloWorldService()
    raise ValueError("Geçersiz model.")


def threshold_settings(model_id: str) -> dict:
    if model_id == "owlvit":
        return {"strategy": "fixed_smoke_baseline", "confidence_threshold": OWLVIT_CONFIDENCE_THRESHOLD}
    if model_id == "grounding-dino":
        from backend.app.config import GROUNDING_DINO
        return {"strategy": "fixed_smoke_baseline", "box_threshold": GROUNDING_DINO.box_threshold,
                "text_threshold": GROUNDING_DINO.text_threshold}
    if model_id == "yolo-world":
        # Production adaptive listesinin ilk değeri; veri başarısına bakılarak seçilmedi.
        from backend.app.config import ADAPTIVE_THRESHOLDS
        return {"strategy": "fixed_smoke_baseline",
                "confidence_threshold": ADAPTIVE_THRESHOLDS["yolo-world"].thresholds[0]}
    raise ValueError("Geçersiz model.")


def infer_categories(detector, image, thresholds: dict, *, prompt_mode: str = "canonical", prompt_mapping: dict | None = None, unresolved: list | None = None) -> tuple[list[dict], float]:
    # BaseDetector.detect_result, tüm label'ları original_query'ye dönüştürür.
    # Bu nedenle hazır çoklu İngilizce prompt için infer_queries sözleşmesi kullanılır.
    from backend.app.utils.nms import class_aware_nms
    mapping = build_prompt_mapping(CATEGORIES, prompt_mode) if prompt_mapping is None else prompt_mapping
    reverse = {normalize_prompt(prompt): category for category, prompt in mapping.items()}
    grounding_multi = detector.model_id == "grounding-dino" and len(mapping) > 1
    if grounding_multi:
        # Servis text=[queries] kullanır; kurulu HF processor candidate listesini
        # '. ' ile birleştirir. Önceden birleştirilmiş caption'ı nested listeye
        # koymak batch boyutunu bozabilir; desteklenen candidate-list API korunur.
        build_caption(list(mapping.values()))
    threshold = thresholds.get("confidence_threshold", thresholds.get("box_threshold"))
    started = perf_counter()
    raw = detector.infer_queries(image, list(mapping.values()), threshold, thresholds.get("text_threshold"))
    elapsed_ms = (perf_counter() - started) * 1000
    canonical = []
    for detection in raw:
        label = normalize_prompt(detection["label"])
        if grounding_multi:
            resolved = resolve_label(detection["label"], mapping)
            if resolved is None:
                entry = {"prediction": dict(detection), "raw_model_label": detection["label"],
                         "reason": "no_unique_safe_prompt_match", "prompt_mode": prompt_mode,
                         "sent_model_prompts": list(mapping.values())}
                if unresolved is not None:
                    unresolved.append(entry)
                warnings.warn(f"Unresolved Grounding DINO model label: {detection['label']!r}; prediction rapora ayrıldı.", RuntimeWarning)
                continue
            category, _ = resolved
        else:
            # OWL-ViT ve single-query için önceki strict sözleşme korunur.
            # GT'ye göre fuzzy matching veya sessiz label atlama yapılmaz.
            if label not in reverse:
                raise ValueError(f"Model etiketi gönderilen prompt'lardan biriyle tam eşleşmiyor: {detection['label']!r}")
            category = reverse[label]
        # NMS ve metric matching daima canonical semantic label kullanır.
        canonical.append({**detection, "label": category, "category": category,
                          "raw_model_label": detection["label"], "model_prompt": mapping[category],
                          "prompt_mode": prompt_mode})
    return class_aware_nms(canonical), elapsed_ms


def infer_image(detector, image, thresholds: dict, mapping: dict, prompt_mode: str, inference_mode: str, *, unresolved: list | None = None) -> tuple[list[dict], float, dict, int]:
    """Tek ortak forward veya her kategori için bağımsız forward; eşikler aynıdır."""
    if inference_mode == "multi-label":
        detections, elapsed = infer_categories(detector, image, thresholds, prompt_mode=prompt_mode, prompt_mapping=mapping, unresolved=unresolved)
        # Ortak forward süresi kategorilere bölünerek sahte kategori süresi üretilmez.
        return detections, elapsed, dict.fromkeys(mapping), 1
    if inference_mode != "single-query":
        raise ValueError("Geçersiz inference mode.")
    detections, category_times = [], {}
    for category, prompt in mapping.items():
        found, elapsed = infer_categories(detector, image, thresholds, prompt_mode=prompt_mode,
                                          prompt_mapping={category: prompt})
        # Tek prompt reverse mapping'i başka bir kategoriye prediction atayamaz.
        detections.extend(found)
        category_times[category] = elapsed
    return detections, sum(category_times.values()), category_times, len(mapping)


def evaluate_model(detector, selected: list[dict], iou_threshold: float, data: Path = DATA, *, prompt_mode: str = "canonical", inference_mode: str = "multi-label") -> dict:
    started = time.perf_counter()
    if not 1 <= len(selected) <= 5 or not 0 < iou_threshold <= 1:
        raise ValueError("Yalnızca 1–5 calibration görüntüsü ve geçerli IoU eşiği desteklenir.")
    if any(record.get("subset") != "calibration" for record in selected):
        raise ValueError("Test split evaluation bu smoke testte desteklenmiyor.")
    from PIL import Image
    thresholds = threshold_settings(detector.model_id)
    prompt_mapping = build_prompt_mapping(CATEGORIES, prompt_mode)
    rows, image_runs = [], []
    for record in selected:
        unresolved = []
        path = data / "calibration/images" / record["file_name"]
        with Image.open(path) as source, source.convert("RGB") as image:
            if image.size != (record["width"], record["height"]):
                raise ValueError("Görüntü boyutu annotation ile uyuşmuyor; resize uygulanmayacak.")
            detections, elapsed_ms, category_times, calls = infer_image(
                detector, image, thresholds, prompt_mapping, prompt_mode, inference_mode, unresolved=unresolved)
        image_runs.append({"image_id": record["image_id"], "inference_time_ms": elapsed_ms,
                           "model": detector.model_id, "device": detector.device,
                           "threshold": thresholds, "detections": detections, "prompt_mode": prompt_mode,
                           "category_prompt_mapping": prompt_mapping, "inference_mode": inference_mode,
                           "forward_call_count": calls, "category_inference_time_ms": category_times})
        if detector.model_id == "grounding-dino" and inference_mode == "multi-label":
            image_runs[-1].update({"unresolved_model_labels": unresolved,
                                   "unresolved_model_label_count": len(unresolved),
                                   "model_caption": build_caption(list(prompt_mapping.values()))})
        # Olmayan kategoriler de sorgulanır: bu sınıflardaki FP'ler kaybolmaz.
        for category in CATEGORIES:
            gt = [obj["bbox_xyxy"] for obj in record["objects"] if obj["evaluation_category"] == category]
            predictions = [d for d in detections if d["label"] == category]
            metrics = evaluate_boxes(predictions, gt, iou_threshold)
            rows.append({"image_id": record["image_id"], "category": category,
                         "model_prompt": prompt_mapping[category], "prompt_mode": prompt_mode, **metrics,
                         "inference_mode": inference_mode, "category_inference_time_ms": category_times[category],
                         "inference_time_ms": category_times[category] if inference_mode == "single-query" else elapsed_ms,
                         "inference_time_scope": "category" if inference_mode == "single-query" else "image_all_17_categories",
                         "model": detector.model_id, "threshold": thresholds, "matching_iou_threshold": iou_threshold})
    summary = {**summarize(rows, CATEGORIES, image_runs), "prompt_mode": prompt_mode,
               "category_prompt_mapping": prompt_mapping, "inference_mode": inference_mode,
               "total_forward_calls": sum(run["forward_call_count"] for run in image_runs),
               "category_inference_time_ms": {
                   category: sum(run["category_inference_time_ms"][category] for run in image_runs)
                   if inference_mode == "single-query" else None for category in CATEGORIES},
               "total_evaluation_time_ms": (time.perf_counter() - started) * 1000,
               "evaluation_time_scope": "image_loading_inference_nms_metrics_excludes_model_loading_and_exports"}
    result = {"records": rows, "image_runs": image_runs, "summary": summary}
    if detector.model_id == "grounding-dino" and inference_mode == "multi-label":
        result["unresolved_model_labels"] = [
            {"image_id": run["image_id"], **entry} for run in image_runs
            for entry in run["unresolved_model_labels"]]
        summary["unresolved_model_label_count"] = len(result["unresolved_model_labels"])
        summary["label_resolution_complete"] = not result["unresolved_model_labels"]
        summary["prediction_metric_scope"] = "resolved_predictions_only_unresolved_preserved_separately"
    return result


def save_results(result: dict, model: str, metadata: dict, output: Path = RESULTS) -> tuple[Path, Path]:
    output.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    prompt_mode = result["summary"].get("prompt_mode", "canonical")
    mapping = result["summary"].get("category_prompt_mapping", build_prompt_mapping(CATEGORIES, prompt_mode))
    inference_mode = result["summary"].get("inference_mode", "multi-label")
    stem = f"calibration_{model}_{prompt_mode}_{inference_mode}_{stamp}_{uuid4().hex[:8]}"
    json_path, csv_path = output / (stem + ".json"), output / (stem + ".csv")
    report = {"metadata": {**metadata, "model": model, "categories": list(CATEGORIES),
                           "inference_mode": inference_mode,
                           "prompt_mode": prompt_mode, "category_prompt_mapping": mapping,
                           "production_adaptive_threshold_used": False}, **result}
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    fields = [key for key in result["records"][0] if key != "matches"]
    with csv_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        for row in result["records"]:
            writer.writerow({key: json.dumps(row[key], sort_keys=True) if key == "threshold" else row[key] for key in fields})
    return json_path, csv_path


def save_debug_images(result: dict, selected: list[dict], report_path: Path, data: Path = DATA) -> list[Path]:
    """Kaydedilen evaluation sonucunu çiz; detector veya metric fonksiyonu çağırma."""
    from PIL import Image
    from evaluation.inventory.debug_visualization import render_debug_image
    records = {record["image_id"]: record for record in selected}
    output = report_path.parent / "debug"
    output.mkdir(parents=True, exist_ok=True)
    files = []
    for run in result["image_runs"]:
        record = records[run["image_id"]]
        if record.get("subset") != "calibration":
            raise ValueError("Debug görseli yalnızca calibration görüntülerinden üretilebilir.")
        source_path = (data / "calibration/images" / record["file_name"]).resolve()
        if source_path.parent != (data / "calibration/images").resolve():
            raise ValueError("Debug kaynak görüntüsü calibration/images dışında.")
        filename = f"{report_path.stem}_{Path(record['file_name']).stem}_debug.png"
        with Image.open(source_path) as source:
            with render_debug_image(source, record["objects"], run["detections"],
                                    model=run["model"] + (" / " + run["prompt_mode"] if "prompt_mode" in run else ""), image_id=run["image_id"]) as debug:
                debug.save(output / filename, format="PNG")
        files.append(output / filename)
    return files


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split", choices=("calibration",), default="calibration")
    parser.add_argument("--limit", type=int, choices=range(1, 6), default=5)
    parser.add_argument("--model", choices=("owlvit", "grounding-dino", "yolo-world", "both", "all"), default="owlvit",
                        help="both: OWL-ViT + Grounding DINO; all: üç model.")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--prompt-mode", choices=("canonical", "alias"), default="canonical")
    parser.add_argument("--inference-mode", choices=("multi-label", "single-query"), default="multi-label")
    parser.add_argument("--iou-threshold", type=float, default=0.5)
    parser.add_argument("--dry-run", action="store_true", help="Yerel plan; model yükleme/inference yok.")
    parser.add_argument("--save-debug-images", action="store_true", help="Aynı evaluation sonucunun GT/prediction panellerini results/debug/ altına kaydet.")
    args = parser.parse_args(argv)
    try:
        if not 0 < args.iou_threshold <= 1:
            raise ValueError("IoU threshold (0, 1] aralığında olmalıdır.")
        selected, metadata = load_calibration(args.limit, args.seed)
        prompt_mapping = build_prompt_mapping(CATEGORIES, args.prompt_mode)
        models = MODEL_GROUPS.get(args.model, (args.model,))
        print(json.dumps({"split": "calibration", "image_ids": [r["image_id"] for r in selected],
                          "categories": list(CATEGORIES), "model_thresholds": {m: threshold_settings(m) for m in models},
                          "prompt_mode": args.prompt_mode, "category_prompt_mapping": prompt_mapping,
                          "inference_mode": args.inference_mode,
                          "grounding_dino_caption": build_caption(list(prompt_mapping.values()))
                          if "grounding-dino" in models and args.inference_mode == "multi-label" else None,
                          "max_forward_calls": len(selected) * len(models) * (len(CATEGORIES) if args.inference_mode == "single-query" else 1), "offline_models_only": True,
                          "matching_iou_threshold": args.iou_threshold}, ensure_ascii=False, indent=2))
        if args.dry_run:
            return 0
        for model in models:
            detector = make_detector(model)
            result = evaluate_model(detector, selected, args.iou_threshold, prompt_mode=args.prompt_mode, inference_mode=args.inference_mode)
            paths = save_results(result, model, metadata)
            print(json.dumps(result["summary"], ensure_ascii=False, indent=2))
            print("Sonuçlar: " + ", ".join(str(path) for path in paths))
            if args.save_debug_images:
                try:
                    files = save_debug_images(result, selected, paths[0])
                    print("Debug görselleri: " + ", ".join(str(path) for path in files))
                except (OSError, ValueError, KeyError, TypeError) as exc:
                    # Görselleştirme hatası tamamlanmış metric raporlarını etkilemez.
                    print(f"WARNING: Metric raporları kaydedildi, debug görseli oluşturulamadı: {exc}", file=sys.stderr)
            del detector
            gc.collect()
        return 0
    except Exception as exc:
        print(f"Calibration smoke test başarısız: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
