import json
import os
from functools import cache
from pathlib import Path
from shutil import copy, rmtree
from typing import Dict, List, Optional, Set
from urllib import parse

import requests
from github.GitRelease import GitRelease
from github.GitReleaseAsset import GitReleaseAsset
from github.GithubException import UnknownObjectException
from github.Organization import Organization
from github.Repository import Repository

from gtnh.defs import BLACKLISTED_REPOS_FILE, GTNH_MODPACK_FILE, MAVEN_BASE_URL, OTHER, UNKNOWN
from gtnh.exceptions import LatestReleaseNotFound, NoModAssetFound
from gtnh.mod_info import GTNHModpack

CACHE_DIR = "cache"


@cache
def get_token() -> Optional[str]:
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
def get_all_repos(o: Organization) -> Dict[str, Repository]:
    return {r.name: r for r in o.get_repos()}


def modpack_manifest() -> Path:
    return (Path(__file__).parent.parent.parent / GTNH_MODPACK_FILE).absolute()


def get_blacklisted_repos() -> Set[str]:
    with open((Path(__file__).parent.parent.parent / BLACKLISTED_REPOS_FILE).absolute()) as f:
        return set(json.loads(f.read()))


def load_gtnh_manifest() -> GTNHModpack:
    with open(modpack_manifest()) as f:
        gtnh_modpack = GTNHModpack.parse_raw(f.read())

    return gtnh_modpack


def save_gtnh_manifest(gtnh_modpack: GTNHModpack) -> None:
    with open(modpack_manifest(), "w") as f:
        f.write(gtnh_modpack.json(indent=2, exclude={"_github_modmap", "_external_modmap"}))


def sort_and_write_modpack(gtnh: GTNHModpack) -> None:
    gtnh.github_mods.sort(key=lambda m: m.name.lower())
    with open(modpack_manifest(), "w+") as f:
        f.write(gtnh.json(indent=2, exclude={"_github_modmap", "_external_modmap"}))


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
        if not asset.name.endswith(".jar") or any(asset.name.endswith(s) for s in ["dev.jar", "sources.jar", "api.jar", "api2.jar"]):
            continue

        return asset

    raise NoModAssetFound()


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


def copy_file_to_folder(path_list: List[Path], source_root: Path, destination_root: Path) -> None:
    """
    Function used to move files from the source folder to the destination folder, while keeping the relative path.

    :param path_list: the list of files to move.
    :param source_root: the root folder of the files to move. It is assumed that path_list has files comming from the
                        same root folder.
    :param destination_root: the root folder for the destination.
    :return: None
    """
    for file in path_list:
        dst = destination_root / file.relative_to(source_root)
        if not dst.parent.is_dir():
            os.makedirs(dst.parent)
        copy(file, dst)


def crawl(path: Path) -> List[Path]:
    """
    Function that will recursively list all the files of a folder.

    :param path: The folder to scan
    :return: The list of all the files contained in that folder
    """
    files = [x for x in path.iterdir() if x.is_file()]
    for folder in [x for x in path.iterdir() if x.is_dir()]:
        files.extend(crawl(folder))
    return files


def ensure_cache_dir() -> Path:
    cache_dir = Path(os.getcwd()) / CACHE_DIR
    os.makedirs(cache_dir / "mods", exist_ok=True)

    return cache_dir


def move_mods(client_paths: List[Path], server_paths: List[Path]) -> None:
    """
    Method used to move the mods in their correct archive folder after they have been downloaded.

    :param client_paths: the paths for the mods clientside
    :param server_paths: the paths for the mods serverside
    :return: None
    """
    cache_dir = ensure_cache_dir()
    client_folder = cache_dir / "client_archive"
    server_folder = cache_dir / "server_archive"
    source_root = cache_dir

    if client_folder.exists():
        rmtree(client_folder)
        os.makedirs(client_folder)

    if server_folder.exists():
        rmtree(server_folder)
        os.makedirs(server_folder)

    copy_file_to_folder(client_paths, source_root, client_folder)
    copy_file_to_folder(server_paths, source_root, server_folder)


def verify_url(url: str) -> bool:
    """
    Url validator.

    :param url: the url to be checked
    :return: if yes or no it's valid
    """
    parse_result = parse.urlparse(url)
    return parse_result.scheme in ["https", "http"] and parse_result.netloc != ""
