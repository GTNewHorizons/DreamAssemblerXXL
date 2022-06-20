#!/usr/bin/env python3

import os
from pathlib import Path
from typing import Callable

import requests
from colorama import Fore
from retry import retry
from structlog import get_logger

from gtnh.defs import CACHE_DIR, GREEN_CHECK, MODS_CACHE_DIR, RED_CROSS
from gtnh.mod_manager import GTNHModManager
from gtnh.models.gtnh_release import GTNHRelease
from gtnh.models.mod_info import ModInfo
from gtnh.models.mod_version import ModVersion
from gtnh.utils import get_token

log = get_logger(__name__)


def ensure_cache_dir(mod_name: str | None = None) -> Path:
    os.makedirs(MODS_CACHE_DIR, exist_ok=True)
    if mod_name is not None:
        os.makedirs(MODS_CACHE_DIR / mod_name, exist_ok=True)

    return CACHE_DIR


def get_mod_version_cache_location(mod_name: str, version: ModVersion) -> Path:
    cache_dir = ensure_cache_dir(mod_name)
    return cache_dir / "mods" / mod_name / str(version.filename)


@retry(delay=5, tries=3)
def download_github_mod(mod: ModInfo, mod_version: str | None = None) -> Path | None:
    if mod_version is None:
        mod_version = mod.latest_version

    version = mod.get_version(mod_version)
    if not version or not version.filename or not version.download_url:
        log.error(
            f"{RED_CROSS} {Fore.RED}Version `{Fore.YELLOW}{mod_version}{Fore.RED}` not found for Github Mod " f"`{Fore.CYAN}{mod.name}{Fore.RED}`{Fore.RESET}"
        )
        return None

    private_repo = f" {Fore.MAGENTA}<PRIVATE REPO>{Fore.RESET}" if mod.private else ""
    log.info(f"Downloading Github Mod `{Fore.CYAN}{mod.name}:{Fore.YELLOW}{mod_version}{Fore.RESET}` from {version.browser_download_url}{private_repo}")

    mod_filename = get_mod_version_cache_location(mod.name, version)

    if os.path.exists(mod_filename):
        log.info(f"{Fore.YELLOW}Skipping re-redownload of {mod_filename}{Fore.RESET}")
        return mod_filename

    headers = {"Authorization": f"token {get_token()}", "Accept": "application/octet-stream"}

    with requests.get(version.download_url, stream=True, headers=headers) as r:
        r.raise_for_status()
        with open(mod_filename, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    log.info(f"{GREEN_CHECK} Download successful `{mod_filename}`")

    return mod_filename


def download_external_mod(mod: ModInfo, mod_version: str | None = None) -> Path | None:
    if mod_version is None:
        mod_version = mod.latest_version

    version = mod.get_version(mod_version)
    if not version or not version.filename:
        log.error(
            f"{RED_CROSS} {Fore.RED}Version `{Fore.YELLOW}{mod_version}{Fore.RED}` not found for External Mod " f"`{Fore.CYAN}{mod.name}{Fore.RED}`{Fore.RESET}"
        )
        return None

    log.info(f"Downloading External Mod `{Fore.CYAN}{mod.name}:{Fore.YELLOW}{mod_version}{Fore.RESET}` from {version.browser_download_url}")

    mod_filename = get_mod_version_cache_location(mod.name, version)

    if os.path.exists(mod_filename):
        log.info(f"{Fore.YELLOW}Skipping re-redownload of {mod_filename}{Fore.RESET}")
        return mod_filename

    headers = {"Accept": "application/octet-stream"}

    with requests.get(str(version.download_url), stream=True, headers=headers) as r:
        r.raise_for_status()
        with open(mod_filename, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    log.info(f"{GREEN_CHECK} Download successful `{mod_filename}`")

    return mod_filename


def download_release(
    mod_manager: GTNHModManager,
    release: GTNHRelease,
    callback: Callable[[float, str], None] | None = None,
) -> list[Path]:
    """
    method to download all the mods required for a release of the pack

    :param mod_manager: The Modpack Manager
    :param release: Release to download
    :param callback: Callable that takes a float and a string in parameters. (mainly the method to update the
                progress bar that takes a progress step per call and the label used to display infos to the user)
    :return: a list holding all the paths to the clientside mods and a list holding all the paths to the serverside
            mod.
    """

    log.info(f"Downloading mods for Release `{Fore.LIGHTRED_EX}{release.version}{Fore.RESET}`")

    # computation of the progress per mod for the progressbar
    delta_progress = 100 / (len(release.github_mods) + len(release.external_mods))

    downloaded: list[Path] = []

    log.info(f"Downloading {Fore.GREEN}{len(release.github_mods)}{Fore.RESET} Github Mod(s)")
    # download of the github mods
    for mod_name, mod_version in release.github_mods.items():
        mod = mod_manager.mods.get_github_mod(mod_name)

        if callback is not None:
            callback(delta_progress, f"downloading github mods. current mod: {mod.name} Progress: {{0}}%")

        path = download_github_mod(mod, mod_version)
        if path:
            downloaded.append(path)

    for mod_name, mod_version in release.external_mods.items():
        mod = mod_manager.mods.get_external_mod(mod_name)
        if callback is not None:
            callback(delta_progress, f"downloading external mods. current mod: {mod.name} Progress: {{0}}%")

        # do the actual work
        path = download_external_mod(mod, mod_version)
        if path:
            downloaded.append(path)

    return downloaded


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
