import bisect

from colorama import Fore, Style
from github import UnknownObjectException
from github.GitRelease import GitRelease
from github.Repository import Repository
from packaging.version import LegacyVersion
from pydantic import BaseModel, Field
from structlog import get_logger

from gtnh.defs import VersionableType
from gtnh.models.gtnh_version import GTNHVersion, version_from_release

log = get_logger(__name__)


class Versionable(BaseModel):
    name: str
    latest_version: str

    versions: list[GTNHVersion] = Field(default_factory=list)
    type: VersionableType = Field(default=VersionableType.mod)

    def add_version(self, version: GTNHVersion) -> None:
        bisect.insort_right(self.versions, version, key=version_sort_key)  # type: ignore

    def get_latest_version(self) -> GTNHVersion | None:
        return self.versions[-1] if self.versions else None

    def get_version(self, version: str) -> GTNHVersion | None:
        i = bisect.bisect_left(self.versions, LegacyVersion(version), key=version_sort_key)  # type: ignore
        if i != len(self.versions) and self.versions[i] and self.versions[i].version_tag == version:
            return self.versions[i]
        return None

    def has_version(self, version: str) -> bool:
        return self.get_version(version) is not None


def update_versions_from_repo(asset: Versionable, repo: Repository) -> bool:
    releases = repo.get_releases()
    version_updated = False

    asset.versions = sorted(asset.versions, key=version_sort_key)

    for release in releases:
        version = version_from_release(release, asset.type)
        if not version:
            log.error(f"{Fore.RED}No assets found for mod `{Fore.CYAN}{asset.name}{Fore.RESET}` release " f"`{release.tag_name}, skipping.{Style.RESET_ALL}")
            continue

        if version_is_newer(version.version_tag, asset.latest_version):
            log.info(
                f"Updating latest version for `{Fore.CYAN}{asset.name}{Fore.RESET}` "
                f"{Style.DIM}{Fore.GREEN}{asset.latest_version}{Style.RESET_ALL} -> "
                f"{Fore.GREEN}{version.version_tag}{Style.RESET_ALL}"
            )
            asset.latest_version = version.version_tag

        if asset.has_version(version.version_tag):
            log.info(f"Mod `{Fore.CYAN}{asset.name}{Fore.RESET}` already has version " f"`{Fore.YELLOW}{version.version_tag}{Fore.RESET}` skipping")
        else:
            log.info(f"Adding version {Fore.GREEN}`{version.version_tag}`{Style.RESET_ALL} to mod " f"`{Fore.CYAN}{asset.name}{Fore.RESET}`")
            asset.add_version(version)

        version_updated = True
    return version_updated


def get_latest_github_release(repo: Repository) -> GitRelease | None:
    try:
        latest_release = repo.get_latest_release()
    except UnknownObjectException:
        log.error(f"{Fore.RED}No latest release found for {Fore.CYAN}{repo.name}{Style.RESET_ALL}")
        latest_release = None

    return latest_release


def version_sort_key(version: GTNHVersion) -> LegacyVersion:
    return LegacyVersion(version.version_tag)


def version_is_newer(test_version: str, existing_version: str) -> bool:
    return LegacyVersion(test_version) > LegacyVersion(existing_version)
