"""RPC hazırlama ayarları; detection backend'inden tamamen bağımsızdır."""

from dataclasses import dataclass
from pathlib import Path


DATASET = "finedet/rpc"
SPLIT = "validation"
# 2026-10-20'de doğrulanan immutable HF commit; seçim row sırasına da bağlıdır.
REVISION = "d60ce8389c5108c0f59bb01fcb470419c69ccee8"
# Yalnızca bu dört validation shard'ı izinlidir; train/test keşfedilmez.
SOURCE_FILES = tuple(f"data/validation-{index:05d}-of-00004.parquet" for index in range(4))
SOURCE_FILE_SIZES = dict(zip(SOURCE_FILES, (230_833_570, 339_481_527, 411_169_510, 338_952_322)))
SOURCE_FILE_BYTES = sum(SOURCE_FILE_SIZES.values())
CATEGORIES = (
    "puffed food", "dried fruit", "dried food", "instant drink", "instant noodles",
    "dessert", "drink", "milk", "canned food", "chocolate", "personal hygiene",
    "tissue", "stationery",
)
DEFAULT_OUTPUT = Path(__file__).resolve().parent / "data"


@dataclass(frozen=True)
class PrepareConfig:
    calibration_count: int = 50
    test_count: int = 200
    seed: int = 42
    max_scan_rows: int = 2000
    max_saved_bytes: int = 256 * 1024 * 1024
    output: Path = DEFAULT_OUTPUT

    @property
    def total(self) -> int:
        return self.calibration_count + self.test_count

    def __post_init__(self):
        if self.calibration_count < 1 or self.test_count < 1 or self.total > 250:
            raise ValueError("İki split pozitif olmalı; toplam en fazla 250 görüntü olabilir.")
        if not max(self.total, len(SOURCE_FILES)) <= self.max_scan_rows <= 3000:
            raise ValueError("Toplam tarama limiti hedef toplam (en az 4) ile 3000 arasında olmalıdır.")
        if not 0 < self.max_saved_bytes <= 256 * 1024 * 1024:
            raise ValueError("Yerel JPEG limiti en fazla 256 MiB olabilir.")


def shard_budgets(total: int) -> dict[str, int]:
    """Kalan satır/görüntü bütçesini de dağıtarak toplamı tam korur."""
    base, remainder = divmod(total, len(SOURCE_FILES))
    return {source: base + (index < remainder) for index, source in enumerate(SOURCE_FILES)}


def preparation_plan(config: PrepareConfig) -> dict:
    """Ağ erişimi veya datasets import'u olmadan dry-run açıklaması."""
    return {
        "dataset": DATASET, "split": SPLIT, "revision": REVISION,
        "source_files": list(SOURCE_FILES), "source_file_bytes": SOURCE_FILE_BYTES,
        "source_file_sizes": SOURCE_FILE_SIZES,
        "streaming": True, "seed": config.seed,
        "target_images": config.total,
        "calibration_images": config.calibration_count, "test_images": config.test_count,
        "max_scan_rows": config.max_scan_rows, "max_saved_bytes": config.max_saved_bytes,
        "max_scan_rows_per_shard": shard_budgets(config.max_scan_rows),
        "max_stream_rows_both_passes": 2 * config.max_scan_rows,
        "target_images_per_shard": shard_budgets(config.total),
        "categories": list(CATEGORIES), "output": str(config.output.resolve()),
        "passes": ["bounded annotation-only scan", "bounded image stream; save selected rows only"],
        "network_note": "Dört validation shard toplamı yaklaşık 1.23 GiB. Her shard bounded streaming ile okunur. Row-group/read-ahead/retry nedeniyle ağ aktarımı JPEG toplamından büyük olabilir; bu bir HTTP byte kotası değildir.",
        "dry_run_note": "Dry-run ağ erişimi kurmaz, dosya yazmaz ve görüntü indirmez.",
    }
