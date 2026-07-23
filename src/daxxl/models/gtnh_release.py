from datetime import datetime, timezone
from typing import Dict

from colorama import Fore
from pydantic import Field, ValidationError

from daxxl.defs import RELEASE_MANIFEST_DIR, ModSource
from daxxl.exceptions import InvalidReleaseException, NoModAssetFound
from daxxl.gtnh_logger import get_logger
from daxxl.models.available_assets import AvailableAssets
from daxxl.models.base import GTNHBaseModel
from daxxl.models.mod_version_info import ModVersionInfo
from daxxl.utils import atomic_write_text

log = get_logger(__name__)


class GTNHRelease(GTNHBaseModel):
    version: str = Field(default="experimental")
    last_version: str | None = Field(default=None)
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # ModName, Version
    config: str
    github_mods: dict[str, ModVersionInfo]
    external_mods: dict[str, ModVersionInfo]

    def validate_release(self, available_assets: AvailableAssets) -> None:
        """
        Validate's a release against `available_mods`
        :param available_assets: A list of available github and external mods
        :raises InvalidReleaseException: if the release references missing or misclassified assets
        """
        errors: list[str] = []

        if not available_assets.config.has_version(self.config):
            errors.append(f"config version {self.config!r} not found")

        duplicate_mods = self.github_mods.keys() & self.external_mods.keys()
        if duplicate_mods:
            errors.append(f"mods listed as both GitHub and external: {', '.join(sorted(duplicate_mods))}")

        for expected_source, mods in (
            (ModSource.github, self.github_mods),
            (ModSource.other, self.external_mods),
        ):
            for mod_name, mod_version in mods.items():
                try:
                    mod = available_assets.get_mod(mod_name)
                except NoModAssetFound:
                    errors.append(f"mod {mod_name!r} not found")
                    continue

                if expected_source == ModSource.github and mod.source != ModSource.github:
                    errors.append(f"mod {mod_name!r} is listed as GitHub but has source {mod.source.value!r}")
                elif expected_source != ModSource.github and mod.source == ModSource.github:
                    errors.append(f"mod {mod_name!r} is listed as external but has source 'github'")

                if not mod.has_version(mod_version.version):
                    errors.append(f"version {mod_version.version!r} not found for mod {mod_name!r}")

        if errors:
            raise InvalidReleaseException(f"Invalid release {self.version!r}:\n- " + "\n- ".join(errors))


class __GTNHReleaseV1(GTNHBaseModel):
    version: str = Field(default="experimental")
    last_version: str | None = Field(default=None)
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # ModName, Version
    config: str
    github_mods: dict[str, str]
    external_mods: dict[str, str]


def __process_mod_list(data: dict[str, str]) -> Dict[str, ModVersionInfo]:
    return {k: ModVersionInfo(version=v) for k, v in data.items()}


def load_release(release: str) -> GTNHRelease | None:
    release_file = RELEASE_MANIFEST_DIR / (release + ".json")
    if not release_file.exists():
        log.error(f"Release `{Fore.LIGHTRED_EX}{release_file}{Fore.RESET}` not found!")
        return None

    with open(release_file, encoding="utf-8") as f:
        data = f.read()

    # a bit inefficient, but pydantic does not seem to offer a way to convert string to model that doesn't
    # inherit from str
    try:
        return GTNHRelease.parse_raw(data)
    except ValidationError:
        v1obj = __GTNHReleaseV1.parse_raw(data)
        log.info(f"Manifest file for release {release} is in V1 format. It will be converted to V2 format in memory.")
        return GTNHRelease(
            version=v1obj.version,
            last_version=v1obj.last_version,
            last_updated=v1obj.last_updated,
            config=v1obj.config,
            external_mods=__process_mod_list(v1obj.external_mods),
            github_mods=__process_mod_list(v1obj.github_mods),
        )


def save_release(release: GTNHRelease, update: bool = False) -> bool:
    release_file = RELEASE_MANIFEST_DIR / (release.version + ".json")
    if not update and release_file.exists():
        log.error(f"Release `{Fore.LIGHTRED_EX}{release_file}{Fore.RESET}` already exists and update not specified!")
        return False

    dumped = release.json()
    if dumped:
        atomic_write_text(release_file, dumped)
        log.info(f"Saved release file `{Fore.GREEN}{release_file}{Fore.RESET}`")
        return True
    else:
        log.error("Save aborted, empty save result")
        return False
