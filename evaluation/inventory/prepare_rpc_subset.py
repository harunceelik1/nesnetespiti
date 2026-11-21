"""Bounded RPC validation subset hazırlama; model/evaluation çalıştırmaz."""

import argparse
from collections import Counter
import hashlib
from io import BytesIO
from itertools import islice
import json
from pathlib import Path
import random
import sys
from tempfile import TemporaryDirectory
from urllib.request import urlopen

if __package__:
    from .category_mapping import parse_category_table, semantic_category, xywh_to_xyxy
    from .config import CATEGORIES, DATASET, REVISION, SOURCE_FILES, SOURCE_FILE_BYTES, SPLIT, PrepareConfig, preparation_plan, shard_budgets
else:
    # python evaluation/inventory/prepare_rpc_subset.py komutunu da destekle.
    from category_mapping import parse_category_table, semantic_category, xywh_to_xyxy
    from config import CATEGORIES, DATASET, REVISION, SOURCE_FILES, SOURCE_FILE_BYTES, SPLIT, PrepareConfig, preparation_plan, shard_budgets


def read_category_names() -> dict[int, str]:
    url = f"https://huggingface.co/datasets/{DATASET}/raw/{REVISION}/categories.csv"
    # Yalnızca küçük metadata: asla sınırsız response.read() çağırma.
    with urlopen(url, timeout=30) as response:
        content = response.read(128 * 1024 + 1)
    if len(content) > 128 * 1024:
        raise ValueError("Kategori tablosu beklenmedik büyüklükte; işlem durduruldu.")
    names = parse_category_table(content.decode("utf-8-sig"))
    if set(names) != set(range(200)):
        raise ValueError("Beklenen 200 dense kategori ID'si bulunamadı; eşleme incelenmeli.")
    return names


def open_stream(*, images: bool, source_file: str):
    if source_file not in SOURCE_FILES:
        raise ValueError("Yalnızca izinli dört validation shard'ı okunabilir.")
    try:
        from datasets import Image as DatasetImage, load_dataset
    except ImportError as exc:
        raise RuntimeError("datasets eksik. evaluation/inventory/requirements.txt bağımlılıklarını kurun.") from exc
    # Her shard ayrı açılır; bir öncekinin scan limiti diğerlerinin havuzunu tüketmez.
    # Streaming başarısızsa offline/eager fallback YOK.
    url = f"https://huggingface.co/datasets/{DATASET}/resolve/{REVISION}/{source_file}"
    columns = ["width", "height", "objects"]
    if images:
        columns.insert(0, "image")
    dataset = load_dataset(
        "parquet", data_files={SPLIT: [url]}, split=SPLIT, streaming=True,
        columns=columns, batch_size=16, storage_options={"block_size": 1024 * 1024},
    )
    # decode=False: yalnızca seçilen satırların görüntüleri Pillow ile açılır.
    return dataset.cast_column("image", DatasetImage(decode=False)) if images else dataset


def annotation_record(row: dict, index: int, names: dict[int, str], source_file: str = SOURCE_FILES[0]) -> dict:
    width, height = int(row["width"]), int(row["height"])
    if width <= 0 or height <= 0:
        raise ValueError("Geçersiz görüntü boyutu.")
    objects = row["objects"]
    boxes, categories = objects["bbox"], objects["category"]
    if len(boxes) != len(categories):
        raise ValueError("bbox ve category sayıları farklı.")
    selected = []
    for bbox, category_id in zip(boxes, categories):
        category_id = int(category_id)
        original_name = names[category_id]  # Bilinmeyen ID sessizce atlanmaz.
        family = semantic_category(original_name)
        if family not in CATEGORIES:
            continue
        xyxy = xywh_to_xyxy(bbox)
        # Kaynak veri clipped olarak yayınlanır; koordinatlar değiştirilmez.
        tolerance = 0.01
        if xyxy[0] < -tolerance or xyxy[1] < -tolerance or xyxy[2] > width + tolerance or xyxy[3] > height + tolerance:
            raise ValueError("bbox görüntü sınırları dışında; koordinatlar incelenmeli.")
        selected.append({
            "original_category_id": category_id, "original_category_name": original_name,
            "evaluation_category": family, "bbox_xywh": list(map(float, bbox)),
            "bbox_xyxy": xyxy,
        })
    # row_index shard içindedir; shard kimliği olmadan farklı dosyalar çakışır.
    shard_index = SOURCE_FILES.index(source_file)
    image_id = f"rpc-validation-{shard_index:05d}-{index:06d}"
    return {
        "image_id": image_id, "file_name": image_id + ".jpg",
        "source_shard": source_file, "source_row_index": index,
        "width": width, "height": height, "objects": selected,
    }


def record_categories(record: dict) -> set[str]:
    return {item["evaluation_category"] for item in record["objects"]}


def balanced_select(records: list[dict], count: int, seed: int, *, balance_shards: bool = False) -> list[dict]:
    """Az temsil edilen aileyi sırayla seç; eşitlikleri sabit seed ile çöz.

    Multi-label görüntüler bütün aile sayaçlarını artırır. Tam denge/istatistiksel
    temsil garantisi verilmez; yalnızca sınırlı aday havuzunda çeşitlilik sağlar.
    """
    if len(records) < count:
        raise ValueError(f"Hedef {count}, fakat yalnızca {len(records)} uygun görüntü bulundu. Tarama limitini kontrollü artırın.")
    remaining = list(records)
    random.Random(seed).shuffle(remaining)
    counts = Counter()
    shard_counts = Counter()
    quotas = shard_budgets(count)
    if balance_shards:
        availability = Counter(record["source_shard"] for record in records)
        quotas = {source: min(quota, availability[source]) for source, quota in quotas.items()}
        # Bir shard'da yeterli aday yoksa eksik kota diğer uygun shard'lara dağıtılır.
        while sum(quotas.values()) < count:
            for source in SOURCE_FILES:
                if quotas[source] < availability[source] and sum(quotas.values()) < count:
                    quotas[source] += 1
    selected = []
    while len(selected) < count:
        eligible = [i for i, record in enumerate(remaining)
                    if not balance_shards or shard_counts[record["source_shard"]] < quotas[record["source_shard"]]]
        available = set().union(*(record_categories(remaining[i]) for i in eligible))
        family = min(available, key=lambda name: (counts[name], CATEGORIES.index(name)))
        index = next(i for i in eligible if family in record_categories(remaining[i]))
        record = remaining.pop(index)
        selected.append(record)
        counts.update(record_categories(record))
        if balance_shards:
            shard_counts[record["source_shard"]] += 1
    return selected


def split_records(records: list[dict], calibration_count: int, seed: int) -> tuple[list[dict], list[dict]]:
    ids = [record["image_id"] for record in records]
    if len(ids) != len(set(ids)):
        raise ValueError("Tekrarlı image_id: calibration/test leakage riski.")
    hashes = [record["content_sha256"] for record in records if "content_sha256" in record]
    if len(hashes) != len(set(hashes)):
        raise ValueError("Aynı görüntü içeriği birden fazla kayıtta mevcut.")
    calibration = balanced_select(records, calibration_count, seed, balance_shards=True)
    calibration_ids = {record["image_id"] for record in calibration}
    return calibration, [record for record in records if record["image_id"] not in calibration_ids]


def category_counts(records: list[dict]) -> dict:
    images = Counter()
    objects = Counter()
    for record in records:
        images.update(record_categories(record))
        objects.update(item["evaluation_category"] for item in record["objects"])
    return {
        "images": {name: images[name] for name in CATEGORIES},
        "objects": {name: objects[name] for name in CATEGORIES},
    }


def ensure_empty_output(output: Path):
    # Önceki çalışmayı silme/üzerine yazma. Repodaki boş iskelet kabul edilir.
    if output.exists():
        for path in output.rglob("*"):
            if path.is_file() and path.name != ".gitkeep":
                if path.name == "annotations.json" and json.loads(path.read_text(encoding="utf-8")) == []:
                    continue
                if path.name == "manifest.json" and json.loads(path.read_text(encoding="utf-8")).get("status") == "not_prepared":
                    continue
                raise ValueError(f"Çıktı boş değil; üzerine yazılmayacak: {path}")


def write_json(path: Path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(content, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def prepare(config: PrepareConfig) -> dict:
    ensure_empty_output(config.output)
    names = read_category_names()
    # İki geçiş: ilkinde image kolonu hiç okunmaz; shuffle buffer'da JPEG tutulmaz.
    candidates = []
    scanned_by_shard = dict.fromkeys(SOURCE_FILES, 0)
    for source_file, limit in shard_budgets(config.max_scan_rows).items():
        for index, row in enumerate(islice(open_stream(images=False, source_file=source_file), limit)):
            scanned_by_shard[source_file] += 1
            record = annotation_record(row, index, names, source_file)
            if record["objects"]:
                candidates.append(record)
    chosen = balanced_select(candidates, config.total, config.seed, balance_shards=True)
    from PIL import Image
    config.output.parent.mkdir(parents=True, exist_ok=True)
    # Hata olursa yarım subset yayımlama; yalnızca bize ait geçici klasör temizlenir.
    with TemporaryDirectory(prefix=".rpc-subset-", dir=config.output.parent) as temporary:
        staging = Path(temporary)
        seen_hashes = set()
        saved_bytes = 0
        written = 0
        image_rows_by_shard = dict.fromkeys(SOURCE_FILES, 0)
        for source_file in SOURCE_FILES:
            wanted = {record["source_row_index"]: record for record in chosen if record["source_shard"] == source_file}
            if not wanted:
                continue
            for index, row in enumerate(islice(open_stream(images=True, source_file=source_file), max(wanted) + 1)):
                image_rows_by_shard[source_file] += 1
                if index not in wanted:
                    continue
                record = wanted[index]
                if annotation_record(row, index, names, source_file) != record:
                    raise ValueError("İki stream geçişinin satır/annotation sırası uyuşmuyor.")
                payload = row["image"].get("bytes")
                if not isinstance(payload, bytes) or not payload:
                    raise ValueError("Embedded image bytes bulunamadı; harici image indirmeye geçilmeyecek.")
                with Image.open(BytesIO(payload)) as source:
                    if source.size != (record["width"], record["height"]):
                        raise ValueError("Piksel boyutu annotation ile uyuşmuyor.")
                    with source.convert("RGB") as rgb:
                        digest = hashlib.sha256(f"{rgb.width}x{rgb.height}:".encode() + rgb.tobytes()).hexdigest()
                        if digest in seen_hashes:
                            raise ValueError("Seçilen görüntülerde aynı piksel içeriği bulundu. Farklı seed ile tekrar seçin; çıktı yayımlanmadı.")
                        seen_hashes.add(digest)
                        record["content_sha256"] = digest
                        if source.format != "JPEG":
                            with BytesIO() as buffer:
                                rgb.save(buffer, format="JPEG", quality=95)
                                payload = buffer.getvalue()
                saved_bytes += len(payload)
                if saved_bytes > config.max_saved_bytes:
                    raise ValueError("Yerel JPEG byte limiti aşıldı; çıktı yayımlanmadı.")
                (staging / record["file_name"]).write_bytes(payload)
                written += 1
        if written != config.total:
            raise ValueError("Image stream seçilen bütün satırları döndürmedi; çıktı yayımlanmadı.")
        calibration, test = split_records(chosen, config.calibration_count, config.seed + 1)
        counts = category_counts(chosen)
        manifest = {
            "status": "prepared", "dataset": DATASET, "split": SPLIT, "revision": REVISION,
            "random_seed": config.seed, "source_files": list(SOURCE_FILES),
            "source_file_bytes": SOURCE_FILE_BYTES, "scanned_rows": sum(scanned_by_shard.values()),
            "scanned_rows_per_shard": scanned_by_shard,
            "image_stream_rows_per_shard": image_rows_by_shard,
            "stream_rows_read_total": sum(scanned_by_shard.values()) + sum(image_rows_by_shard.values()),
            "selected_images_per_shard": {source: sum(r["source_shard"] == source for r in chosen) for source in SOURCE_FILES},
            "per_split_shard_counts": {
                split: {source: sum(r["source_shard"] == source for r in records) for source in SOURCE_FILES}
                for split, records in (("calibration", calibration), ("test", test))
            },
            "candidate_images": len(candidates), "total_images": len(chosen),
            "calibration_images": len(calibration), "test_images": len(test),
            "category_image_counts": counts["images"], "category_object_counts": counts["objects"],
            "per_split_counts": {"calibration": category_counts(calibration), "test": category_counts(test)},
            "saved_image_bytes": saved_bytes, "config": preparation_plan(config),
            "coverage_missing_categories": [name for name, count in counts["images"].items() if not count],
            "selection_note": "Near-equal shard quotas and greedy family coverage within bounded pools from all four validation shards; not uniform sampling of all rows.",
            "category_mapping": {str(key): {"original_name": name, "evaluation_category": semantic_category(name)} for key, name in names.items()},
            "split_image_ids": {"calibration": [r["image_id"] for r in calibration], "test": [r["image_id"] for r in test]},
        }
        ensure_empty_output(config.output)
        for split_name, records in (("calibration", calibration), ("test", test)):
            image_dir = config.output / split_name / "images"
            image_dir.mkdir(parents=True, exist_ok=True)
            for record in records:
                (staging / record["file_name"]).replace(image_dir / record["file_name"])
            write_json(image_dir.parent / "annotations.json", records)
        # Manifest son yazılır; prepared durumu yalnızca bütün çıktı hazırsa oluşur.
        write_json(config.output / "manifest.json", manifest)
    return manifest


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Yalnızca yerel planı göster; ağ/dosya yazma yok.")
    parser.add_argument("--calibration-count", type=int, default=50)
    parser.add_argument("--test-count", type=int, default=200)
    parser.add_argument("--max-scan-rows", type=int, default=2000, help="Dört shard'a bölünen toplam metadata satır limiti (en fazla 3000).")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=Path, default=PrepareConfig().output)
    args = parser.parse_args(argv)
    try:
        config = PrepareConfig(calibration_count=args.calibration_count, test_count=args.test_count,
                               seed=args.seed, max_scan_rows=args.max_scan_rows, output=args.output)
        print(json.dumps(preparation_plan(config), ensure_ascii=False, indent=2))
        if args.dry_run:
            return 0
        manifest = prepare(config)
        print(f"Hazır: {manifest['total_images']} görüntü; {manifest['saved_image_bytes'] / 1024**2:.1f} MiB JPEG.")
        if manifest["coverage_missing_categories"]:
            print("Bu havuzda temsil edilmeyen aileler: " + ", ".join(manifest["coverage_missing_categories"]))
        return 0
    except (ValueError, RuntimeError, OSError, KeyError, ImportError) as exc:
        print(f"Hazırlama durduruldu: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
