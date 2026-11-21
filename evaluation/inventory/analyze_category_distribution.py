"""Yerel full_annotations.json için semantic family dağılımı; ağ/model işlemi yok."""

from collections import Counter
import json
from pathlib import Path
import sys


DATA = Path(__file__).resolve().parent / "data"


def analyze_distribution(payload: dict, split_image_ids: dict) -> dict:
    if payload.get("complete") is not True or not isinstance(payload.get("images"), list):
        raise ValueError("Tamamlanmış full_annotations.json gerekli.")
    records = payload["images"]
    if payload.get("image_count") != len(records):
        raise ValueError("image_count ile annotation kayıt sayısı uyuşmuyor.")
    membership = {}
    for split in ("calibration", "test"):
        for image_id in split_image_ids[split]:
            if image_id in membership:
                raise ValueError("Manifest ID listelerinde tekrar veya split çakışması var.")
            membership[image_id] = split
    object_counts = Counter()
    image_counts = Counter()
    split_counts = {"calibration": Counter(), "test": Counter()}
    seen = set()
    for record in records:
        image_id = record["image_id"]
        if image_id in seen or image_id not in membership:
            raise ValueError("Tekrarlı image_id veya manifest dışı görüntü var.")
        seen.add(image_id)
        split = membership[image_id]
        if record.get("subset", split) != split:
            raise ValueError("Full annotation subset alanı manifest ile uyuşmuyor.")
        if not isinstance(record.get("objects"), list):
            raise ValueError("objects bir liste olmalıdır.")
        categories = set()
        for obj in record["objects"]:
            category = obj.get("evaluation_category") if isinstance(obj, dict) else None
            if not isinstance(category, str) or not category.strip():
                raise ValueError("Semantic family adı eksik/geçersiz.")
            category = " ".join(category.casefold().split())
            # is_evaluation_category filtresi uygulanmaz: bütün RPC aileleri dahil.
            object_counts[category] += 1
            categories.add(category)
        image_counts.update(categories)
        split_counts[split].update(categories)
    if seen != set(membership):
        raise ValueError("Manifest'teki bütün görüntüler full annotation içinde bulunamadı.")
    total_objects = sum(object_counts.values())
    return {
        "dataset": payload.get("dataset"), "source_split": payload.get("split"),
        "revision": payload.get("revision"), "source": "full_annotations.json",
        "categories": [
            {"semantic_category": category, "image_count": image_counts[category],
             "object_count": object_counts[category],
             "calibration_image_count": split_counts["calibration"][category],
             "test_image_count": split_counts["test"][category]}
            for category in sorted(object_counts)
        ],
        "summary": {
            "total_images": len(records), "calibration_images": len(split_image_ids["calibration"]),
            "test_images": len(split_image_ids["test"]), "total_semantic_categories": len(object_counts),
            "total_objects": total_objects,
            "average_objects_per_annotation": total_objects / len(records) if records else 0.0,
        },
    }


def print_report(report: dict):
    headers = ["Semantic category", "Images", "Objects", "Calibration", "Test"]
    rows = [[r["semantic_category"], str(r["image_count"]), str(r["object_count"]),
             str(r["calibration_image_count"]), str(r["test_image_count"])] for r in report["categories"]]
    widths = [max(len(row[i]) for row in [headers, *rows]) for i in range(len(headers))]
    for row in [headers, ["-" * width for width in widths], *rows]:
        print(" | ".join(value.ljust(widths[i]) if i == 0 else value.rjust(widths[i]) for i, value in enumerate(row)))
    summary = report["summary"]
    print(f"\nTotal semantic categories: {summary['total_semantic_categories']}")
    print(f"Total objects: {summary['total_objects']}")
    print(f"Objects per annotation: {summary['average_objects_per_annotation']:.3f}")
    print(f"Images: {summary['total_images']} (calibration: {summary['calibration_images']}, test: {summary['test_images']})")


def main() -> int:
    try:
        payload = json.loads((DATA / "full_annotations.json").read_text(encoding="utf-8"))
        manifest = json.loads((DATA / "manifest.json").read_text(encoding="utf-8"))
        report = analyze_distribution(payload, manifest["split_image_ids"])
        output = DATA / "category_distribution.json"
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        print_report(report)
        print(f"\nReport: {output}")
        return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"Dağılım analizi başarısız: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
