#!/usr/bin/env python3

import sys

import click
from github import Github
from github.Repository import Repository

from gtnh.exceptions import RepoNotFoundException
from gtnh.mod_info import ModInfo
from gtnh.utils import (
    get_latest_release,
    get_license,
    get_maven,
    get_mod_asset,
    get_token,
    load_gtnh_manifest,
    sort_and_write_modpack,
)


@click.command()
@click.argument("name")
def add_mod(name: str) -> None:
    print(f"Trying to add {name}")

    new_repo = get_repo(name)
    gtnh = load_gtnh_manifest()
    if gtnh.has_github_mod(new_repo.name):
        print(f"Mod already added {name}")
        sys.exit()

    new_mod = new_mod_from_repo(new_repo)

    gtnh.github_mods.append(new_mod)

    sort_and_write_modpack(gtnh)
    print("Success!")


def get_repo(name: str) -> Repository:
    g = Github(get_token())
    o = g.get_organization("GTNewHorizons")
    try:
        return o.get_repo(name)
    except Exception:
        raise RepoNotFoundException(f"Repo not Found {name}")


def new_mod_from_repo(repo: Repository) -> ModInfo:
    license = get_license(repo)
    repo_url = repo.html_url

    latest_release = get_latest_release(repo)
    version = latest_release.tag_name
    asset = get_mod_asset(latest_release)
    maven = get_maven(repo.name)

    return ModInfo(
        name=repo.name,
        repo_url=repo_url,
        license=license,
        version=version,
        browser_download_url=asset.browser_download_url,
        download_url=asset.url,
        tagged_at=asset.created_at,
        filename=asset.name,
        maven=maven,
    )


if __name__ == "__main__":
    add_mod()
