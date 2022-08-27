#!/usr/bin/env python3
import os
from pathlib import Path

from structlog import get_logger

from gtnh.defs import CACHE_DIR
from gtnh.models.gtnh_version import GTNHVersion
from gtnh.models.versionable import Versionable
import re

log = get_logger(__name__)

# this regex filtering will make it safe to use on windows,
# see https://gist.github.com/doctaphred/d01d05291546186941e1b7ddc02034d3
# '\' is excluded because it's used when stringifying a Path object

forbidden_chars = re.compile(r'[<>:"\/|\?\*]')

def ensure_cache_dir(asset: Versionable | None = None) -> Path:
    os.makedirs(CACHE_DIR, exist_ok=True)
    if asset is not None:
        path: Path = CACHE_DIR / Path(re.sub(forbidden_chars, "", str(Path(asset.type.value) / asset.name)))

        os.makedirs(path, exist_ok=True)

    return CACHE_DIR


def get_asset_version_cache_location(asset: Versionable, version: GTNHVersion) -> Path:
    cache_dir = ensure_cache_dir(asset)

    path: Path = cache_dir / Path(re.sub(forbidden_chars, "", str(Path(asset.type.value) / asset.name / str(version.filename))))
    print(f"raw path: {path}\nsafe path:{path}")
    return path
