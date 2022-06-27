#!/usr/bin/env python3
import os
from pathlib import Path

from structlog import get_logger

from gtnh.defs import CACHE_DIR, MODS_CACHE_DIR
from gtnh.models.gtnh_version import GTNHVersion

log = get_logger(__name__)


def ensure_cache_dir(mod_name: str | None = None) -> Path:
    os.makedirs(MODS_CACHE_DIR, exist_ok=True)
    if mod_name is not None:
        os.makedirs(MODS_CACHE_DIR / mod_name, exist_ok=True)

    return CACHE_DIR


def get_mod_version_cache_location(mod_name: str, version: GTNHVersion) -> Path:
    cache_dir = ensure_cache_dir(mod_name)
    return cache_dir / "mods" / mod_name / str(version.filename)


#
# def download_pack_archive() -> Path:
#     """
#     Method used to download the latest gtnh modpack archive.
#
#     :return: the path of the downloaded archive. None is returned if somehow it wasn't able to download any release.
#     """
#     gtnh_modpack_repo = get_repo("GT-New-Horizons-Modpack")
#
#     gtnh_archive_release = get_latest_release(gtnh_modpack_repo)
#     print("***********************************************************")
#     print(f"Downloading {'GT-New-Horizons-Modpack'}:{gtnh_archive_release.title}")
#
#     if not gtnh_archive_release:
#         print(f"*** No release found for {'GT-New-Horizons-Modpack'}:{gtnh_archive_release.title}")
#         raise LatestReleaseNotFound
#
#     release_assets = gtnh_archive_release.get_assets()
#     for asset in release_assets:
#         if not asset.name.endswith(".zip"):
#             continue
#
#         print(f"Found Release at {asset.browser_download_url}")
#         cache_dir = ensure_cache_dir()
#         gtnh_archive_path = cache_dir / asset.name
#
#         if os.path.exists(gtnh_archive_path):
#             print(f"Skipping re-redownload of {asset.name}")
#             continue
#
#         print(f"Downloading {asset.name} to {gtnh_archive_path}")
#
#         headers = {"Authorization": f"token {get_token()}", "Accept": "application/octet-stream"}
#
#         with requests.get(asset.url, stream=True, headers=headers) as r:
#             r.raise_for_status()
#             with open(gtnh_archive_path, "wb") as f:
#                 for chunk in r.iter_content(chunk_size=8192):
#                     f.write(chunk)
#         print("Download successful")
#     return gtnh_archive_path
#
#
#
#
# def update_releases(callback: Optional[Callable[[float, str], None]] = None) -> None:
#     """
#     Method to update the github mods with the list of releases
#
#     :param callback: Optional callback called for each mod updated
#     :return: None
#     """
#     gtnh_mods = load_gtnh_manifest()
#     github_mods = gtnh_mods.github_mods
#     gtnh_mods.github_mods = []
#     delta_progress = 100 / len(github_mods)
#
#     for i, mod in enumerate(github_mods):
#         text = f"updating {mod.name} ({i+1}/{len(github_mods)})"
#         print(text)
#         if callback is not None:
#             callback(delta_progress, text)
#         try:
#             curr_mod = new_mod_from_repo(get_repo(mod.name))
#         except BaseException as e:
#             print(e)
#             curr_mod = [x for x in github_mods if x.name == mod.name][0]
#         curr_mod.side = mod.side
#         gtnh_mods.github_mods.append(curr_mod)
#
#     save_gtnh_manifest(gtnh_mods)
#
#
# if __name__ == "__main__":
#     update_releases()
