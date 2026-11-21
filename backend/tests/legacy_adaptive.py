"""Eski adaptive eşik düşürme + eş anlamlı yedek davranışını testlerde açar.

Üretimde ikisi de kapalı (config.allow_lowering=False, SYNONYM_FALLBACK_ENABLED=False);
mekanizmalar ayar olarak durduğu için bu dosyalar onları açıp sınamaya devam eder.
"""

import dataclasses
from unittest.mock import patch

from backend.app import config

_patchers = []
LEGACY_YOLO_WORLD = (0.25, 0.15, 0.10, 0.05)


def start():
    legacy = {key: dataclasses.replace(policy, allow_lowering=True)
              for key, policy in config.ADAPTIVE_THRESHOLDS.items()}
    # Kalibrasyondan önceki kademeli YOLO-World eşikleri (eski davranış).
    legacy["yolo-world"] = dataclasses.replace(legacy["yolo-world"], thresholds=LEGACY_YOLO_WORLD)
    _patchers[:] = [patch.dict(config.ADAPTIVE_THRESHOLDS, legacy),
                    patch.object(config, "SYNONYM_FALLBACK_ENABLED", True)]
    for patcher in _patchers:
        patcher.start()


def stop():
    for patcher in reversed(_patchers):
        patcher.stop()
    _patchers.clear()
