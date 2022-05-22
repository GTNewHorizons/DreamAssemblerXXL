#!/usr/bin/env python3

from typing import Dict

from colorama import Fore, Style, init
from github import Github
from github.Repository import Repository

from gtnh.defs import OTHER, UNKNOWN
from gtnh.mod_info import GTNHModpack, ModInfo
from gtnh.utils import (
    check_for_missing_maven,
    check_for_missing_repos,
    get_all_repos,
    get_latest_release,
    get_license,
    get_maven,
    get_mod_asset,
    get_token,
    load_gtnh_manifest,
    sort_and_write_modpack,
)

init(autoreset=True)


class NoReleasesException(Exception):
    pass


def check_for_updates(all_repos: Dict[str, Repository], gtnh_modpack: GTNHModpack) -> None:
    print("Checking for updates")

    for mod in gtnh_modpack.github_mods:
        check_mod_for_update(all_repos, mod)


def check_mod_for_update(all_repos: Dict[str, Repository], mod: ModInfo) -> None:
    version_updated = False

    print(f"Checking {mod.name}:{mod.version} for updates")
    repo = all_repos.get(mod.name, None)
    if repo is None:
        print(f"{Fore.RED}Couldn't find repo {Style.DIM}{mod.name}")
        return

    latest_release = get_latest_release(repo)

    latest_version = latest_release.tag_name

    if latest_version > mod.version:
        print(f"Update found for {mod.name} {Style.DIM}{Fore.GREEN}{mod.version}{Style.RESET_ALL} -> {Fore.GREEN}{latest_version}")
        mod.version = latest_version
        version_updated = True

    if mod.license in [UNKNOWN, OTHER, None]:
        license = get_license(repo)
        if license is not None:
            mod.license = license

    if mod.repo_url is None:
        mod.repo_url = repo.html_url

    if mod.maven is None:
        mod.maven = get_maven(mod.name)

    if version_updated or mod.download_url is None or mod.filename is None or mod.browser_download_url is None:
        asset = get_mod_asset(latest_release)

        mod.browser_download_url = asset.browser_download_url
        mod.download_url = asset.url
        mod.tagged_at = asset.created_at
        mod.filename = asset.name


if __name__ == "__main__":
    g = Github(get_token())
    o = g.get_organization("GTNewHorizons")

    print("Grabbing all repository information")
    all_repos = get_all_repos(o)
    gtnh = load_gtnh_manifest()

    check_for_updates(all_repos, gtnh)

    sort_and_write_modpack(gtnh)

    missing_repos = check_for_missing_repos(all_repos, gtnh)
    if len(missing_repos):
        print(f"{Fore.RED}****** Missing Mods:{Style.RESET_ALL} {', '.join(sorted(missing_repos))}")

    missing_maven = check_for_missing_maven(gtnh)
    if len(missing_maven):
        print(f"{Fore.RED}****** Missing Maven:{Style.RESET_ALL} {', '.join(sorted(missing_maven))}")
