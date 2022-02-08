import json
import os
from functools import cache
from typing import Dict, Optional, Set

import requests
from defs import BLACKLISTED_REPOS_FILE, GTNH_MODPACK_FILE, MAVEN_BASE_URL, OTHER, UNKNOWN
from github.GitRelease import GitRelease
from github.GitReleaseAsset import GitReleaseAsset
from github.GithubException import UnknownObjectException
from github.Organization import Organization
from github.Repository import Repository
from mod_info import GTNHModpack


class LatestReleaseNotFound(Exception):
    pass


@cache
def get_token():
    if os.getenv("GITHUB_TOKEN", None) is None:
        token_file = os.path.expanduser("~/.github_personal_token")
        if os.path.exists(token_file):
            with open(token_file) as f:
                token = f.readline()[:-1]
                os.environ["GITHUB_TOKEN"] = token
        else:
            raise Exception("No token ENV and no token file")

    return os.getenv("GITHUB_TOKEN")


@cache
def get_all_repos(o: Organization):
    return {r.name: r for r in o.get_repos()}


def modpack_manifest() -> str:
    return os.path.abspath(os.path.dirname(__file__)) + "/../../" + GTNH_MODPACK_FILE


def get_blacklisted_repos() -> Set[str]:
    with open(os.path.abspath(os.path.dirname(__file__)) + "/../../" + BLACKLISTED_REPOS_FILE) as f:
        return set(json.loads(f.read()))


def load_gtnh_manifest() -> GTNHModpack:
    with open(modpack_manifest()) as f:
        gtnh_modpack = GTNHModpack.parse_raw(f.read())

    return gtnh_modpack


def sort_and_write_modpack(gtnh: GTNHModpack):
    gtnh.github_mods.sort(key=lambda m: m.name.lower())
    with open(modpack_manifest(), "w+") as f:
        f.write(gtnh.json(indent=2, exclude={"_github_modmap"}))


def get_license(repo: Repository) -> Optional[str]:
    mod_license = None
    try:
        repo_license = repo.get_license()
        if repo_license:
            mod_license = repo_license.license.name
    except Exception:
        pass

    if mod_license in [None, UNKNOWN, OTHER]:
        with open(os.path.abspath(os.path.dirname(__file__)) + "/../../licenses_from_boubou.json") as f:
            manual_licenses = json.loads(f.read())
            by_url = {v["url"]: v.get("license", None) for v in manual_licenses.values()}
            mod_license = by_url.get(repo.html_url, None)

    return mod_license


def get_latest_release(repo: Repository) -> GitRelease:
    try:
        latest_release: GitRelease = repo.get_latest_release()
    except UnknownObjectException:
        raise LatestReleaseNotFound(f"*** No latest release found for {repo.name}")

    return latest_release


def get_mod_asset(release: GitRelease) -> GitReleaseAsset:
    release_assets = release.get_assets()
    for asset in release_assets:
        if (
            not asset.name.endswith(".jar")
            or asset.name.endswith("dev.jar")
            or asset.name.endswith("sources.jar")
            or asset.name.endswith("api.jar")
        ):
            continue

        return asset


def get_maven(mod_name: str) -> Optional[str]:
    maven_url = MAVEN_BASE_URL + mod_name + "/"
    response = requests.head(maven_url, allow_redirects=True)

    if response.status_code == 200:
        return maven_url
    elif response.status_code >= 500:
        raise Exception(f"Maven unreachable status: {response.status_code}")

    return None


def check_for_missing_repos(all_repos: Dict[str, Repository], gtnh_modpack: GTNHModpack) -> Set[str]:
    all_repo_names = set(all_repos.keys())
    all_modpack_names = set(gtnh_modpack._github_modmap.keys())
    blacklisted_repos = get_blacklisted_repos()

    return all_repo_names - all_modpack_names - blacklisted_repos


def check_for_missing_maven(gtnh_modpack: GTNHModpack) -> Set[str]:
    all_modpack_names = set(k for k, v in gtnh_modpack._github_modmap.items() if v.maven is None)

    return all_modpack_names
