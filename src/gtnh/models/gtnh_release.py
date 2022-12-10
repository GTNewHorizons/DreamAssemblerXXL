from datetime import datetime
from typing import Dict

from colorama import Fore
from pydantic import Field, ValidationError
from structlog import get_logger

from gtnh.defs import GREEN_CHECK, RED_CROSS, RELEASE_MANIFEST_DIR
from gtnh.models.available_assets import AvailableAssets
from gtnh.models.base import GTNHBaseModel
from gtnh.models.mod_version_info import ModVersionInfo

log = get_logger(__name__)


class GTNHRelease(GTNHBaseModel):
    version: str = Field(default="nightly")
    last_version: str | None = Field(default=None)
    last_updated: datetime = Field(default_factory=datetime.utcnow)

    # ModName, Version
    config: str
    github_mods: dict[str, ModVersionInfo]
    external_mods: dict[str, ModVersionInfo]

    def validate_release(self, available_assets: AvailableAssets) -> bool:
        """
        Validate's a release against `available_mods`
        :param available_assets: A list of available github and external mods
        :return: Validity as a boolean
        """

        for mod_name, mod_version in self.github_mods.items():
            mod = available_assets.get_mod(mod_name)
            if mod is None:
                log.error(
                    f"{RED_CROSS} {Fore.RED}Github Mod "
                    f"`{Fore.CYAN}{mod_name}:{Fore.YELLOW}{mod_version}{Fore.RED}` not found!{Fore.RESET}"
                )
                return False

            version = mod.get_version(mod_version.version)
            if version is None:
                log.error(
                    f"{RED_CROSS} {Fore.RED}Version `{Fore.YELLOW}{mod_version}{Fore.RED}` not found for Github Mod "
                    f"`{Fore.CYAN}{mod_name}{Fore.RED}`{Fore.RESET}"
                )
                return False

            log.info(
                f"{GREEN_CHECK} Validated Github Mod `{Fore.CYAN}{mod_name}:{Fore.YELLOW}{mod_version}{Fore.RESET}`"
            )

        return True


class __GTNHReleaseV1(GTNHBaseModel):
    version: str = Field(default="nightly")
    last_version: str | None = Field(default=None)
    last_updated: datetime = Field(default_factory=datetime.utcnow)

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
        with open(release_file, "w", encoding="utf-8") as f:
            f.write(dumped)
        log.info(f"Saved release file `{Fore.GREEN}{release_file}{Fore.RESET}`")
        return True
    else:
        log.error("Save aborted, empty save result")
        return False
