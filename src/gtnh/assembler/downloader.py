#!/usr/bin/env python3
import os
import re
from pathlib import Path

from structlog import get_logger

from gtnh.defs import CACHE_DIR
from gtnh.models.gtnh_version import GTNHVersion, ExtraAsset
from gtnh.models.versionable import Versionable

log = get_logger(__name__)

# this regex filtering will make it safe to use on windows,
# see https://gist.github.com/doctaphred/d01d05291546186941e1b7ddc02034d3
# '\' is excluded because it's used when stringifying a Path object

forbidden_chars = re.compile(r'[<>:"\/|\?\*]')


def sanitize(to_sanitize: str) -> str:
    return re.sub(forbidden_chars, "_", to_sanitize)


def ensure_cache_dir(asset: Versionable | None = None) -> Path:
    os.makedirs(CACHE_DIR, exist_ok=True)
    if asset is not None:
        path: Path = CACHE_DIR / sanitize(asset.type.value) / sanitize(asset.name)

        os.makedirs(path, exist_ok=True)

    return CACHE_DIR


def get_asset_version_cache_location(asset: Versionable, version: GTNHVersion, extra_asset_suffix: str | None = None) -> Path:
    cache_dir = ensure_cache_dir(asset)

    subasset: GTNHVersion | ExtraAsset = version
    if extra_asset_suffix is not None:
        for extra_asset in version.extra_assets:
            if extra_asset.filename.endswith(extra_asset_suffix):
                subasset = extra_asset
                break
        if subasset is version:
            raise FileNotFoundError(f"Could not find an asset with suffix {extra_asset_suffix} for {version.filename}")
    return cache_dir / sanitize(asset.type.value) / sanitize(asset.name) / sanitize(str(subasset.filename))
