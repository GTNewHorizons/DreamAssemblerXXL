#!/usr/bin/env python3
import os
from pathlib import Path

from structlog import get_logger

from gtnh.defs import CACHE_DIR
from gtnh.models.gtnh_version import GTNHVersion
from gtnh.models.versionable import Versionable

log = get_logger(__name__)


def ensure_cache_dir(asset: Versionable | None = None) -> Path:
    os.makedirs(CACHE_DIR, exist_ok=True)
    if asset is not None:
        os.makedirs(CACHE_DIR / asset.type.value / asset.name, exist_ok=True)

    return CACHE_DIR


def get_asset_version_cache_location(asset: Versionable, version: GTNHVersion) -> Path:
    cache_dir = ensure_cache_dir(asset)

    return cache_dir / asset.type.value / asset.name / str(version.filename)
