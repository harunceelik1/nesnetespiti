"""Hassasiyet seviyesi → model eşiği. Varsayılan ("balanced") kalibre edilmiş politikadır."""

import dataclasses

from .. import config
from ..models.base_detector import DetectorError

DEFAULT = "balanced"


def validate(level: str | None) -> str:
    level = (level or DEFAULT).strip().lower()
    if level not in config.SENSITIVITY_LEVELS:
        raise DetectorError("Hassasiyet strict, balanced veya loose olmalıdır.", 422)
    return level


def detection_policy(detector, level: str) -> config.AdaptiveThresholdSettings:
    """Seçilen seviye için tek, sabit eşikli politika (eşik düşürme yok)."""
    key = detector.policy_key or detector.model_id
    base = config.ADAPTIVE_THRESHOLDS[key]
    if level == DEFAULT:
        return base
    levels = config.SENSITIVITY_THRESHOLDS.get(key)
    if not levels:
        raise DetectorError(f"{detector.name} için hassasiyet seviyeleri tanımlı değil.", 422)
    return dataclasses.replace(base, thresholds=(levels[level],), allow_lowering=False)


def exemplar_settings(level: str) -> config.ExemplarSearchSettings:
    if level == DEFAULT:
        return config.EXEMPLAR_SEARCH
    return dataclasses.replace(config.EXEMPLAR_SEARCH, similarity_threshold=config.EXEMPLAR_SENSITIVITY[level])
