import json
import os
from functools import cache
from typing import Optional

from github.GitRelease import GitRelease
from github.GitReleaseAsset import GitReleaseAsset
from github.Organization import Organization
from github.Repository import Repository
from github.GithubException import UnknownObjectException
from defs import GTNH_MODPACK_FILE, UNKNOWN, OTHER
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


def load_gtnh_manifest() -> GTNHModpack:
    with open(modpack_manifest()) as f:
        gtnh_modpack = GTNHModpack.parse_raw(f.read())

    return gtnh_modpack


def sort_and_write_modpack(gtnh: GTNHModpack):
    gtnh.github_mods.sort(key=lambda m: m.name.lower())
    with open(modpack_manifest(), 'w+') as f:
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
