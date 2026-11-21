"""Mevcut subset'in tam RPC annotation'larını geri al; görüntü/subset üretme."""

import argparse
from itertools import islice
import json
from pathlib import Path
import sys
from tempfile import NamedTemporaryFile

if __package__:
    from .category_mapping import semantic_category, xywh_to_xyxy
    from .config import CATEGORIES, DEFAULT_OUTPUT, DATASET, REVISION, SOURCE_FILES
    from .prepare_rpc_subset import open_stream
else:
    from category_mapping import semantic_category, xywh_to_xyxy
    from config import CATEGORIES, DEFAULT_OUTPUT, DATASET, REVISION, SOURCE_FILES
    from prepare_rpc_subset import open_stream


def recovery_inputs(data: Path) -> tuple[dict, list[dict]]:
    manifest = json.loads((data / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("status") != "prepared" or manifest.get("dataset") != DATASET or manifest.get("split") != "validation" or manifest.get("revision") != REVISION:
        raise ValueError("Manifest hazır RPC validation subset'ine ve desteklenen sabit revision'a ait olmalıdır.")
    records = []
    all_ids = set()
    source_rows = set()
    for split in ("calibration", "test"):
        items = json.loads((data / split / "annotations.json").read_text(encoding="utf-8"))
        expected = manifest["split_image_ids"][split]
        ids = [item["image_id"] for item in items]
        if len(ids) != len(set(ids)) or len(expected) != len(set(expected)) or set(ids) != set(expected):
            raise ValueError(f"{split}: mevcut image_id listesi manifest ile uyuşmuyor.")
        for item in items:
            key = (item["source_shard"], item["source_row_index"])
            if (key[0] not in SOURCE_FILES or type(key[1]) is not int or not 0 <= key[1] < 1500
                    or item["image_id"] in all_ids or key in source_rows):
                raise ValueError("Tekrarlı veya geçersiz image_id/source row bulundu.")
            all_ids.add(item["image_id"])
            source_rows.add(key)
            records.append({**item, "subset": split})
    if len(records) != manifest["total_images"] or len(records) > 250:
        raise ValueError("Manifest toplamı ile mevcut kayıtlar uyuşmuyor veya 250 sınırı aşılıyor.")
    return manifest, records


def recovery_plan(data: Path) -> dict:
    _, records = recovery_inputs(data)
    limits = {source: max((r["source_row_index"] + 1 for r in records if r["source_shard"] == source), default=0) for source in SOURCE_FILES}
    return {
        "dataset": DATASET, "split": "validation", "revision": REVISION,
        "image_count": len(records), "columns": ["width", "height", "objects"],
        "streaming": True, "source_files": list(SOURCE_FILES),
        "scan_rows_per_shard": limits, "max_rows_read": sum(limits.values()),
        "output": str(data / "full_annotations.json"),
        "network_estimate": "Birkaç MB–onlarca MB tahmini; Parquet range/read-ahead nedeniyle kesin kota değildir. Dört kaynak shard toplamı yaklaşık 1.23 GiB; image kolonu istenmez.",
        "dry_run_note": "Yalnızca yerel manifest ve annotation okunur. Ağ erişimi veya dosya yazımı yapılmaz.",
    }


def recover(data: Path) -> dict:
    manifest, records = recovery_inputs(data)
    output = data / "full_annotations.json"
    if output.exists():
        raise ValueError("full_annotations.json zaten var; üzerine yazılmayacak.")
    mapping = manifest["category_mapping"]
    recovered = {}
    scanned = dict.fromkeys(SOURCE_FILES, 0)
    for source in SOURCE_FILES:
        wanted = {record["source_row_index"]: record for record in records if record["source_shard"] == source}
        if not wanted:
            continue
        # Annotation projection: image kolonunu hiçbir zaman isteme/decode etme.
        for index, row in enumerate(islice(open_stream(images=False, source_file=source), max(wanted) + 1)):
            scanned[source] += 1
            if index not in wanted:
                continue
            record = wanted[index]
            if (row["width"], row["height"]) != (record["width"], record["height"]):
                raise ValueError("Kaynak boyutları mevcut subset kaydıyla uyuşmuyor.")
            boxes, categories = row["objects"]["bbox"], row["objects"]["category"]
            if len(boxes) != len(categories):
                raise ValueError("Kaynak bbox/category sayıları uyuşmuyor.")
            objects = []
            for bbox, category_id in zip(boxes, categories):
                original_name = mapping[str(int(category_id))]["original_name"]
                family = semantic_category(original_name)
                objects.append({
                    "original_category_id": int(category_id), "original_category_name": original_name,
                    "evaluation_category": family, "bbox_xywh": list(map(float, bbox)),
                    "bbox_xyxy": xywh_to_xyxy(bbox), "is_evaluation_category": family in CATEGORIES,
                })
            # Yanlış row/revision eşleşmesini mevcut seçili nesnelerden de denetle.
            selected = [{key: value for key, value in obj.items() if key != "is_evaluation_category"}
                        for obj in objects if obj["is_evaluation_category"]]
            if selected != record["objects"]:
                raise ValueError("Geri alınan selected nesneler mevcut annotation ile uyuşmuyor; çıktı yazılmadı.")
            recovered[record["image_id"]] = {**record, "objects": objects}
    if len(recovered) != len(records):
        raise ValueError("Mevcut ID listesindeki bütün görüntülerin annotation'ları bulunamadı.")
    result = {
        "dataset": DATASET, "split": "validation", "revision": REVISION,
        "complete": True, "image_count": len(records), "source_files": list(SOURCE_FILES),
        "scanned_rows_per_shard": scanned, "scanned_rows": sum(scanned.values()),
        "images": [recovered[record["image_id"]] for record in records],
    }
    # Yalnızca yeni dosya yazılır; hata halinde yarım full annotation bırakılmaz.
    temporary = None
    try:
        with NamedTemporaryFile(mode="w", encoding="utf-8", dir=data, prefix=".full-annotations-", suffix=".tmp", delete=False) as file:
            temporary = Path(file.name)
            json.dump(result, file, ensure_ascii=False, indent=2, allow_nan=False)
            file.write("\n")
        if output.exists():
            raise ValueError("full_annotations.json bu sırada oluştu; üzerine yazılmayacak.")
        temporary.rename(output)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()
    return result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    try:
        print(json.dumps(recovery_plan(DEFAULT_OUTPUT), ensure_ascii=False, indent=2))
        if not args.dry_run:
            result = recover(DEFAULT_OUTPUT)
            print(f"Tam annotation hazır: {result['image_count']} mevcut görüntü. JPEG'ler ve split dosyaları değiştirilmedi.")
        return 0
    except (OSError, ValueError, RuntimeError, KeyError, ImportError) as exc:
        print(f"Annotation recovery durduruldu: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
