#!/usr/bin/env python3

import os
from pathlib import Path
from typing import List

import requests
from github import Github
from github.GitRelease import GitRelease
from github.Organization import Organization
from retry import retry

from gtnh.mod_info import GTNHModpack, ModInfo
from gtnh.utils import get_token, load_gtnh_manifest

CACHE_DIR = "cache"


def get_latest_releases(gtnh_modpack: GTNHModpack) -> None:
    g = Github(get_token())
    o = g.get_organization("GTNewHorizons")

    for mod in gtnh_modpack.github_mods:
        download_mod(g, o, mod)


@retry(delay=5, tries=3)
def download_mod(g: Github, o: Organization, mod: ModInfo) -> List[Path]:
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
        if not asset.name.endswith(".jar") or asset.name.endswith("dev.jar") or asset.name.endswith("sources.jar") or asset.name.endswith("api.jar"):
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


def ensure_cache_dir() -> Path:
    cache_dir = Path(os.getcwd()) / CACHE_DIR
    os.makedirs(cache_dir / "mods", exist_ok=True)

    return cache_dir


if __name__ == "__main__":
    github_mods = load_gtnh_manifest()
    get_latest_releases(github_mods)
