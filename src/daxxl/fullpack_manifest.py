from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import urlparse
from zipfile import ZipFile

from daxxl.assembler.downloader import get_asset_version_cache_location
from daxxl.assembler.platforms.zip_assembler import ZipAssembler
from daxxl.defs import Side
from daxxl.models.gtnh_version import ExtraAsset, GTNHVersion
from daxxl.models.mod_info import GTNHModInfo
from daxxl.models.versionable import Versionable
from daxxl.utils import atomic_write_text

AssetPathResolver = Callable[[Versionable, GTNHVersion], Path]
InstallationPlan = dict[str, Any]


def fullpack_manifest_path(manifest_path: Path) -> Path:
    return manifest_path.parent / "fullpack" / manifest_path.name


def build_fullpack_manifest(
    assembler: ZipAssembler,
    asset_path: AssetPathResolver = get_asset_version_cache_location,
) -> InstallationPlan:
    """Describe how to install the Java 17+ client from the resolved release."""
    files: list[dict[str, Any]] = []
    for mod, version in assembler.get_mods(Side.CLIENT_JAVA9):
        files.append(_mod_file(mod, version))

        if mod.name == "lwjgl3ify":
            patch = next(asset for asset in version.extra_assets if asset.filename is not None and asset.filename.endswith("forgePatches.jar"))
            launcher = {
                "path": ".gtnh/launcher/lwjgl3ify-forgePatches.jar",
                "url": _extra_asset_url(mod, patch),
            }
            _add_authentication(launcher, mod)
            files.append(launcher)

    config, config_version = assembler.get_config()
    exclusions = list(assembler.exclusions[Side.CLIENT_JAVA9].exclusions)
    exclusions.extend(sorted(assembler.excluded_config_files - set(exclusions)))

    config_archive: dict[str, Any] = {"url": _download_url(config, config_version)}
    if exclusions:
        config_archive["exclude"] = exclusions
    _add_authentication(config_archive, config)

    archives = [config_archive]
    translations = assembler.context.assets.translations
    for version in translations.versions:
        translation_archive: dict[str, Any] = {
            "url": _download_url(translations, version),
            "keepExisting": True,
        }
        _add_authentication(translation_archive, translations)
        archives.append(translation_archive)

    config_path = asset_path(config, config_version)
    with ZipFile(config_path) as config_zip:
        text_files = {
            destination: assembler._modify_config_file(destination, config_zip.read(destination)).decode("utf-8")
            for destination in assembler.modified_config_files
        }

    return {
        "version": 1,
        "files": files,
        "archives": archives,
        "textFiles": text_files,
    }


def write_fullpack_manifest(
    manifest_path: Path,
    assembler: ZipAssembler,
    asset_path: AssetPathResolver = get_asset_version_cache_location,
) -> None:
    path = fullpack_manifest_path(manifest_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(build_fullpack_manifest(assembler, asset_path), indent=2, ensure_ascii=False) + "\n"
    atomic_write_text(path, data)


def _mod_file(mod: GTNHModInfo, version: GTNHVersion) -> dict[str, Any]:
    if version.filename is None:
        raise ValueError(f"Asset {mod.name!r} version {version.version_tag!r} has no filename")

    entry: dict[str, Any] = {
        "path": (PurePosixPath("mods") / version.filename).as_posix(),
        "url": _download_url(mod, version),
    }
    if mod.is_github():
        entry["owner"] = _repository_name(mod)
        if _is_gtnh_repository(mod):
            entry["maven"] = f"com.github.GTNewHorizons:{mod.name}:{version.version_tag}"
    _add_authentication(entry, mod)
    return entry


def _download_url(asset: Versionable, version: GTNHVersion) -> str:
    if isinstance(asset, GTNHModInfo) and not asset.is_github():
        url = version.download_url
    else:
        url = version.download_url if asset.private else version.browser_download_url
    if url is None:
        raise ValueError(f"Asset {asset.name!r} version {version.version_tag!r} has no download URL")
    return url


def _extra_asset_url(mod: GTNHModInfo, asset: ExtraAsset) -> str:
    url = asset.download_url if mod.private else asset.browser_download_url
    if url is None:
        raise ValueError(f"Extra asset for {mod.name!r} has no download URL")
    return url


def _add_authentication(entry: dict[str, Any], asset: Versionable) -> None:
    if asset.private and (not isinstance(asset, GTNHModInfo) or asset.is_github()):
        entry["authentication"] = "github"


def _repository_name(mod: GTNHModInfo) -> str:
    assert mod.repo_url is not None
    return PurePosixPath(urlparse(mod.repo_url).path).name.removesuffix(".git")


def _is_gtnh_repository(mod: GTNHModInfo) -> bool:
    if mod.repo_url is None:
        return False
    url = urlparse(mod.repo_url)
    parts = [part for part in url.path.split("/") if part]
    return url.hostname == "github.com" and len(parts) == 2 and parts[0] == "GTNewHorizons"
