"""Aynı calibration görüntülerinin canonical/alias JSON sonuçlarını karşılaştır; inference yapmaz."""

import argparse
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from uuid import uuid4

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from evaluation.inventory.evaluate_inventory import CATEGORIES, RESULTS
from evaluation.inventory.metrics import precision_recall_f1


def compare_results(canonical: dict, alias: dict, expected_images: int = 5) -> dict:
    """F1, görüntü F1 ortalamasından değil birleştirilmiş TP/FP/FN'den hesaplanır."""
    if not 1 <= expected_images <= 5:
        raise ValueError("Yalnızca 1–5 calibration görüntüsü karşılaştırılabilir.")
    reference = canonical["metadata"]
    for report, mode in ((canonical, "canonical"), (alias, "alias")):
        meta = report["metadata"]
        if meta.get("split") != "calibration" or meta.get("prompt_mode") != mode:
            raise ValueError("Calibration canonical/alias raporları gerekli.")
        for key in ("model", "inference_mode", "seed", "dataset", "revision",
                    "full_annotations_sha256", "manifest_sha256", "categories"):
            if key not in meta or meta[key] != reference.get(key):
                raise ValueError(f"Karşılaştırma ayarları uyuşmuyor veya eksik: {key}")
        if set(meta["categories"]) != set(CATEGORIES):
            raise ValueError("17 canonical kategori gerekli.")

    indexed = []
    for report in (canonical, alias):
        rows = {}
        for row in report["records"]:
            key = (row["image_id"], row["category"])
            if key in rows:
                raise ValueError("Tekrarlanan image/category kaydı.")
            if any(type(row[field]) is not int or row[field] < 0
                   for field in ("TP", "FP", "FN", "ground_truth_count", "predicted_count")):
                raise ValueError("Geçersiz metric sayacı.")
            if row["TP"] + row["FN"] != row["ground_truth_count"] or row["TP"] + row["FP"] != row["predicted_count"]:
                raise ValueError("Metric sayaçları tutarsız.")
            rows[key] = row
        ids = {image_id for image_id, _ in rows}
        if len(ids) != expected_images or set(rows) != {(image_id, category) for image_id in ids for category in CATEGORIES}:
            raise ValueError("Beklenen görüntü sayısı veya kategori kayıtları eksik.")
        indexed.append(rows)
    left, right = indexed
    if set(left) != set(right):
        raise ValueError("Canonical ve alias aynı image_id listesini kullanmalı.")
    for key in left:
        for field in ("ground_truth_count", "threshold", "matching_iou_threshold", "model", "inference_mode"):
            if field not in left[key] or left[key][field] != right[key].get(field):
                raise ValueError(f"Karşılaştırma koşulları uyuşmuyor: {field}")
    comparisons = []
    for category in CATEGORIES:
        row = {"category": category}
        for name, records in (("canonical", left), ("alias", right)):
            totals = {field: sum(record[field] for (_, cat), record in records.items() if cat == category)
                      for field in ("TP", "FP", "FN")}
            row.update({f"{name}_{field}": value for field, value in totals.items()})
            row[f"{name}_F1"] = precision_recall_f1(**{key.lower(): value for key, value in totals.items()})["F1"]
        row["F1_delta"] = row["alias_F1"] - row["canonical_F1"]
        # Toplam iyileşme tek görüntüden mi geliyor, yoksa daha tutarlı mı?
        deltas = [precision_recall_f1(right[key]["TP"], right[key]["FP"], right[key]["FN"])["F1"]
                  - precision_recall_f1(left[key]["TP"], left[key]["FP"], left[key]["FN"])["F1"]
                  for key in sorted(left) if key[1] == category]
        row.update({"improved_images": sum(delta > 0 for delta in deltas),
                    "unchanged_images": sum(delta == 0 for delta in deltas),
                    "worsened_images": sum(delta < 0 for delta in deltas)})
        comparisons.append(row)
    return {"model": reference["model"], "inference_mode": reference["inference_mode"],
            "split": "calibration", "image_ids": sorted({key[0] for key in left}),
            "image_count": expected_images, "records": comparisons}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--canonical", type=Path, required=True)
    parser.add_argument("--alias", type=Path, required=True)
    parser.add_argument("--expected-images", type=int, choices=range(1, 6), default=5)
    parser.add_argument("--output-dir", type=Path, default=RESULTS / "comparisons")
    args = parser.parse_args(argv)
    try:
        result = compare_results(json.loads(args.canonical.read_text(encoding="utf-8")),
                                 json.loads(args.alias.read_text(encoding="utf-8")), args.expected_images)
        result["source_files"] = {"canonical": str(args.canonical.resolve()), "alias": str(args.alias.resolve())}
        print(f"{result['image_count']} calibration images | {result['model']} | {result['inference_mode']}")
        print(f"{'Category':<18} {'Canonical TP/FP/FN/F1':<26} {'Alias TP/FP/FN/F1':<26} {'F1 delta':>9}")
        for row in result["records"]:
            values = [f"{row[m + '_TP']}/{row[m + '_FP']}/{row[m + '_FN']}/{row[m + '_F1']:.4f}" for m in ("canonical", "alias")]
            print(f"{row['category']:<18} {values[0]:<26} {values[1]:<26} {row['F1_delta']:>+9.4f}")
        args.output_dir.mkdir(parents=True, exist_ok=True)
        stem = f"prompt_comparison_{result['model']}_{result['inference_mode']}_{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}_{uuid4().hex[:8]}"
        target = args.output_dir / stem
        target.with_suffix(".json").write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        with target.with_suffix(".csv").open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=list(result["records"][0]))
            writer.writeheader()
            writer.writerows(result["records"])
        print(f"Rapor: {target}.json / .csv")
        return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"Karşılaştırma başarısız: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
