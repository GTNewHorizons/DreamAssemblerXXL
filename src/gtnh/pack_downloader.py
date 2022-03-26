#!/usr/bin/env python3

import os
from pathlib import Path
from typing import Callable, List, Optional, Tuple

import requests
from github import Github
from github.GitRelease import GitRelease
from github.Organization import Organization
from retry import retry

from gtnh.add_mod import get_repo, new_mod_from_repo
from gtnh.exceptions import LatestReleaseNotFound
from gtnh.mod_info import GTNHModpack, ModInfo
from gtnh.utils import get_latest_release, get_token, load_gtnh_manifest, save_gtnh_manifest

CACHE_DIR = "cache"


def get_releases(gtnh_modpack: GTNHModpack) -> None:
    g = Github(get_token())
    o = g.get_organization("GTNewHorizons")

    for mod in gtnh_modpack.github_mods:
        download_github_mod(g, o, mod)


@retry(delay=5, tries=3)
def download_github_mod(g: Github, o: Organization, mod: ModInfo) -> List[Path]:
    print("***********************************************************")
    print(f"Downloading {mod.name}:{mod.version}")
    paths = []
    repo = o.get_repo(mod.name)
    release: GitRelease = repo.get_release(mod.version)

    if not release:
        print(f"*** No release found for {mod.name}:{mod.version}")
        return []

    release_assets = release.get_assets()
    for asset in release_assets:
        if (
            not asset.name.endswith(".jar")
            or asset.name.endswith("dev.jar")
            or asset.name.endswith("sources.jar")
            or asset.name.endswith("api.jar")
            or asset.name.endswith("api2.jar")
        ):
            continue

        print(f"Found Release at {asset.browser_download_url}")
        cache_dir = ensure_cache_dir()
        mod_filename = cache_dir / "mods" / asset.name
        if os.path.exists(mod_filename):
            print(f"Skipping re-redownload of {asset.name}")
            paths.append(mod_filename)
            continue

        print(f"Downloading {asset.name} to {mod_filename}")

        headers = {"Authorization": f"token {get_token()}", "Accept": "application/octet-stream"}

        if repo.private:
            print("Private Repo!")

        with requests.get(asset.url, stream=True, headers=headers) as r:
            r.raise_for_status()
            with open(mod_filename, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        print("Download successful")
        paths.append(mod_filename)
    return paths


def download_external_mod(mod: ModInfo) -> List[Path]:
    cache_dir = ensure_cache_dir()
    mod_filename = cache_dir / "mods" / str(mod.filename)
    if os.path.exists(mod_filename):
        print(f"Skipping re-redownload of {mod.filename}")
        return [mod_filename]

    print(f"Downloading {mod.filename} to {mod_filename}")

    headers = {"Accept": "application/octet-stream"}

    with requests.get(str(mod.download_url), stream=True, headers=headers) as r:
        r.raise_for_status()
        with open(mod_filename, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    print("Download successful")
    return [mod_filename]


def download_mods(
    gtnh_modpack: GTNHModpack,
    github: Github,
    organization: Organization,
    callback: Optional[Callable[[float, str], None]] = None,
) -> Tuple[List[Path], List[Path]]:
    """
    method to download all the mods required for the pack.

    :param gtnh_modpack: GTNHModpack object. Represents the metadata of the modpack.
    :param github: Github object.
    :param organization: Organization object. Represent the GTNH organization.
    :param callback: Callable that takes a float and a string in parameters. (mainly the method to update the
                progress bar that takes a progress step per call and the label used to display infos to the user)
    :return: a list holding all the paths to the clientside mods and a list holding all the paths to the serverside
            mod.
    """
    # computation of the progress per mod for the progressbar
    delta_progress = 100 / (len(gtnh_modpack.github_mods) + len(gtnh_modpack.external_mods))

    # lists holding the paths to the mods
    client_paths = []
    server_paths = []

    # download of the github mods
    for mod in gtnh_modpack.github_mods:
        if callback is not None:
            callback(delta_progress, f"downloading github mods. current mod: {mod.name} Progress: {{0}}%")

        # do the actual work
        paths = download_github_mod(github, organization, mod)
        if mod.side == "BOTH":
            client_paths.extend(paths)
            server_paths.extend(paths)
        elif mod.side == "CLIENT":
            client_paths.extend(paths)
        elif mod.side == "SERVER":
            server_paths.extend(paths)

    for mod in gtnh_modpack.external_mods:
        if callback is not None:
            callback(delta_progress, f"downloading external mods. current mod: {mod.name} Progress: {{0}}%")

        # do the actual work
        paths = download_external_mod(mod)
        if mod.side == "BOTH":
            client_paths.extend(paths)
            server_paths.extend(paths)
        elif mod.side == "CLIENT":
            client_paths.extend(paths)
        elif mod.side == "SERVER":
            server_paths.extend(paths)

    return client_paths, server_paths


def download_pack_archive() -> Path:
    """
    Method used to download the latest gtnh modpack archive.

    :return: the path of the downloaded archive. None is returned if somehow it wasn't able to download any release.
    """
    gtnh_modpack_repo = get_repo("GT-New-Horizons-Modpack")

    gtnh_archive_release = get_latest_release(gtnh_modpack_repo)
    print("***********************************************************")
    print(f"Downloading {'GT-New-Horizons-Modpack'}:{gtnh_archive_release.title}")

    if not gtnh_archive_release:
        print(f"*** No release found for {'GT-New-Horizons-Modpack'}:{gtnh_archive_release.title}")
        raise LatestReleaseNotFound

    release_assets = gtnh_archive_release.get_assets()
    for asset in release_assets:
        if not asset.name.endswith(".zip"):
            continue

        print(f"Found Release at {asset.browser_download_url}")
        cache_dir = ensure_cache_dir()
        gtnh_archive_path = cache_dir / asset.name

        if os.path.exists(gtnh_archive_path):
            print(f"Skipping re-redownload of {asset.name}")
            continue

        print(f"Downloading {asset.name} to {gtnh_archive_path}")

        headers = {"Authorization": f"token {get_token()}", "Accept": "application/octet-stream"}

        with requests.get(asset.url, stream=True, headers=headers) as r:
            r.raise_for_status()
            with open(gtnh_archive_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        print("Download successful")
    return gtnh_archive_path


def ensure_cache_dir() -> Path:
    cache_dir = Path(os.getcwd()) / CACHE_DIR
    os.makedirs(cache_dir / "mods", exist_ok=True)

    return cache_dir


def update_releases(callback: Optional[Callable] = None) -> None:
    """
    Method to update the github mods to latest releases.

    :param callback: Optional callback called for each mod updated
    :return: None
    """
    gtnh_modpack = load_gtnh_manifest()
    github_mods = gtnh_modpack.github_mods
    gtnh_modpack.github_mods = []
    delta_progress = 100/len(github_mods)

    for i, mod in enumerate(github_mods):
        text = f"updating {mod.name} ({i+1}/{len(github_mods)})"
        print(text)
        if callback is not None:
            callback(delta_progress, text)
        try:
            curr_mod = new_mod_from_repo(get_repo(mod.name))
        except BaseException as e:
            print(e)
            curr_mod = [x for x in github_mods if x.name == mod.name][0]
        curr_mod.side = mod.side
        gtnh_modpack.github_mods.append(curr_mod)

    save_gtnh_manifest(gtnh_modpack)


if __name__ == "__main__":
    update_releases()
