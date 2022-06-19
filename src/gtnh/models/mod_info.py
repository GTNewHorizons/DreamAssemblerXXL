import bisect
import json
from typing import List, Optional

import requests
from colorama import Fore, Style
from github.GitRelease import GitRelease
from github.GithubException import UnknownObjectException
from github.Repository import Repository

# Using LegacyVersion because we want everything to be comparable
from packaging.version import LegacyVersion
from pydantic import Field
from structlog import get_logger

from gtnh.defs import MAVEN_BASE_URL, OTHER, ROOT_DIR, UNKNOWN, Side
from gtnh.models.base import GTNHBaseModel
from gtnh.models.mod_version import ModVersion, version_from_release

log = get_logger(__name__)


class ModInfo(GTNHBaseModel):
    name: str
    license: Optional[str] = Field(default=UNKNOWN)
    repo_url: Optional[str] = Field(default=None)
    maven: Optional[str] = Field(default=None)
    side: Side = Field(default=Side.BOTH)
    latest_version: str

    private: bool = Field(default=False)
    disabled: bool = Field(default=False)

    versions: List[ModVersion] = Field(default_factory=list)

    def add_version(self, version: ModVersion) -> None:
        bisect.insort_right(self.versions, version, key=version_sort_key)  # type: ignore

    def get_latest_version(self) -> ModVersion | None:
        return self.versions[-1] if self.versions else None

    def get_version(self, version: str) -> ModVersion | None:
        i = bisect.bisect_left(self.versions, LegacyVersion(version), key=version_sort_key)  # type: ignore
        if i != len(self.versions) and self.versions[i] and self.versions[i].version_tag == version:
            return self.versions[i]
        return None

    def has_version(self, version: str) -> bool:
        return self.get_version(version) is not None


def mod_from_repo(repo: Repository, side: Side = Side.BOTH) -> ModInfo:
    try:
        latest_release: GitRelease = repo.get_latest_release()
        latest_version = latest_release.tag_name
    except UnknownObjectException:
        latest_version = "<unknown>"

    mod = ModInfo(
        name=repo.name,
        license=get_license(repo),
        repo_url=repo.html_url,
        maven=get_maven(repo.name),
        side=side,
        latest_version=latest_version,
        private=repo.private,
    )

    update_versions_from_repo(mod, repo)

    mod.latest_version = latest_version

    return mod


def version_sort_key(version: ModVersion) -> LegacyVersion:
    return LegacyVersion(version.version_tag)


def version_is_newer(test_version: str, existing_version: str) -> bool:
    return LegacyVersion(test_version) > LegacyVersion(existing_version)


def update_github_mod_from_repo(mod: ModInfo, repo: Repository) -> bool:
    """
    Attempt to update a github mod from a github repository.
    :param mod: The mod to check for update
    :param repo: The repo corresponding to the mod
    :return: True if the mod, or any releases were updated; False otherwise
    """
    version_updated = False
    mod_updated = False
    log.info(f"Checking {Fore.CYAN}{mod.name}:{Fore.YELLOW}{mod.latest_version}{Fore.RESET} for updates")
    latest_release = get_latest_github_release(repo)

    latest_version = latest_release.tag_name if latest_release else "<unknown>"

    if version_is_newer(latest_version, mod.latest_version):
        # Candidate update found
        version_updated = True

    if mod.license in [UNKNOWN, OTHER]:
        mod_license = get_license(repo)
        if mod_license is not None:
            log.info(f"Updated License: {mod_license}")
            mod.license = mod_license
            mod_updated = True

    if mod.repo_url is None:
        repo_url = repo.html_url
        if repo_url:
            mod.repo_url = repo_url
            log.info(f"Updated Repo URL: {mod.repo_url}")
            mod_updated = True

    if mod.maven is None:
        maven = get_maven(mod.name)
        if maven:
            mod.maven = maven
            log.info(f"Updated Maven: {mod.maven}")
            mod_updated = True

    if mod.private != repo.private:
        mod.private = repo.private
        log.info(f"Updated Private Repo Status: {mod.private}")
        mod_updated = True

    if version_updated or not mod.versions or not mod.versions == sorted(mod.versions, key=version_sort_key):
        mod_updated |= update_versions_from_repo(mod, repo)

    return mod_updated


def update_versions_from_repo(mod: ModInfo, repo: Repository) -> bool:
    releases = repo.get_releases()
    version_updated = False

    mod.versions = sorted(mod.versions, key=version_sort_key)

    for release in releases:
        version = version_from_release(release)
        if not version:
            log.error(f"{Fore.RED}No assets found for mod `{Fore.CYAN}{mod.name}{Fore.RESET}` release " f"`{release.tag_name}, skipping.{Style.RESET_ALL}")
            continue

        if version_is_newer(version.version_tag, mod.latest_version):
            log.info(
                f"Updating latest version for `{Fore.CYAN}{mod.name}{Fore.RESET}` "
                f"{Style.DIM}{Fore.GREEN}{mod.latest_version}{Style.RESET_ALL} -> "
                f"{Fore.GREEN}{version.version_tag}{Style.RESET_ALL}"
            )
            mod.latest_version = version.version_tag

        if mod.has_version(version.version_tag):
            log.info(f"Mod `{Fore.CYAN}{mod.name}{Fore.RESET}` already has version " f"`{Fore.YELLOW}{version.version_tag}{Fore.RESET}` skipping")
        else:
            log.info(f"Adding version {Fore.GREEN}`{version.version_tag}`{Style.RESET_ALL} to mod " f"`{Fore.CYAN}{mod.name}{Fore.RESET}`")
            mod.add_version(version)

        version_updated = True
    return version_updated


def get_latest_github_release(repo: Repository) -> GitRelease | None:
    try:
        latest_release = repo.get_latest_release()
    except UnknownObjectException:
        log.error(f"{Fore.RED}No latest release found for {Fore.CYAN}{repo.name}{Style.RESET_ALL}")
        latest_release = None

    return latest_release


def get_license(repo: Repository) -> str | None:
    """
    Attempt to find a license for a mod, based on the repository; falling back to some manually collected licenses
    :param repo: Github Repository
    :return: License `str`
    """
    mod_license = None
    try:
        repo_license = repo.get_license()
        if repo_license:
            mod_license = repo_license.license.name
            log.info(f"Found license `{Fore.YELLOW}{mod_license}{Fore.RESET}` from repo")
    except Exception:
        log.info("No license found from repo")

    if mod_license in [None, UNKNOWN, OTHER]:
        with open(ROOT_DIR / "licenses_from_boubou.json") as f:
            manual_licenses = json.loads(f.read())
            by_url = {v["url"]: v.get("license", None) for v in manual_licenses.values()}
            mod_license = by_url.get(repo.html_url, None)
            if mod_license:
                log.info(f"Found fallback license {Fore.YELLOW}{mod_license}{Fore.RESET}.")

    if not mod_license:
        log.info("No license found!")

    return mod_license


def get_maven(mod_name: str) -> str | None:
    """
    Get the maven URL for a `mod_name`, ensuring it exists
    :param mod_name: Mod Name
    :return: Maven URL, if found
    """
    maven_url = MAVEN_BASE_URL + mod_name + "/"
    response = requests.head(maven_url, allow_redirects=True)

    if response.status_code == 200:
        return maven_url
    elif response.status_code >= 500:
        raise Exception(f"Maven unreachable status: {response.status_code}")

    return None
