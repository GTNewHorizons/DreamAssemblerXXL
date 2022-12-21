#!/usr/bin/env python3
"""Module providing helper functions about cached assets."""
import os
import re
from pathlib import Path

from structlog import get_logger

from gtnh.defs import CACHE_DIR
from gtnh.models.gtnh_version import GTNHVersion
from gtnh.models.versionable import Versionable

log = get_logger(__name__)

# this regex filtering will make it safe to use on windows,
# see https://gist.github.com/doctaphred/d01d05291546186941e1b7ddc02034d3
# '\' is excluded because it's used when stringifying a Path object

forbidden_chars = re.compile(r'[<>:"\/|\?\*]')


def sanitize(to_sanitize: str) -> str:
    """
    Replace forbidden characters with _.

    Parameters
    ----------
    to_sanitize: str
        The string to sanitize.

    Returns
    -------
    A string corresponding to the sanitized version of the string.
    """
    return re.sub(forbidden_chars, "_", to_sanitize)


def ensure_cache_dir(asset: Versionable | None = None) -> Path:
    """
    Ensure the cache dir(s) exist before returning the path of the asset.

    Parameters
    ----------
    asset: Versionable
        The asset in the cache.

    Returns
    -------
    A Path pointing to the emplacement of the asset in the cache.
    """
    os.makedirs(CACHE_DIR, exist_ok=True)
    if asset is not None:
        path: Path = CACHE_DIR / sanitize(asset.type.value) / sanitize(asset.name)

        os.makedirs(path, exist_ok=True)

    return CACHE_DIR


def get_asset_version_cache_location(asset: Versionable, version: GTNHVersion) -> Path:
    """
    Get the location for a specific version of the given asset.

    Parameters
    ----------
    asset: Versionable
        The asset to check.
    version: GTNHVersion
        The associated version.

    Returns
    -------
    A Path object corresponding to the asset's version's location in the cache.
    """
    cache_dir = ensure_cache_dir(asset)

    return cache_dir / sanitize(asset.type.value) / sanitize(asset.name) / sanitize(str(version.filename))
