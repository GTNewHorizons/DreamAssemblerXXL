from datetime import datetime

from colorama import Fore
from pydantic import Field
from structlog import get_logger

from gtnh.defs import GREEN_CHECK, RED_CROSS, RELEASE_MANIFEST_DIR
from gtnh.models.available_assets import AvailableAssets
from gtnh.models.base import GTNHBaseModel

log = get_logger(__name__)


class GTNHRelease(GTNHBaseModel):
    version: str = Field(default="nightly")
    last_version: str | None = Field(default=None)
    last_updated: datetime = Field(default_factory=datetime.utcnow)

    # ModName, Version
    config: str
    github_mods: dict[str, str]
    external_mods: dict[str, str]

    def validate_release(self, available_assets: AvailableAssets) -> bool:
        """
        Validate's a release against `available_mods`
        :param available_assets: A list of available github and external mods
        :return: Validity as a boolean
        """

        for mod_name, mod_version in self.github_mods.items():
            mod = available_assets.get_github_mod(mod_name)
            if mod is None:
                log.error(
                    f"{RED_CROSS} {Fore.RED}Github Mod "
                    f"`{Fore.CYAN}{mod_name}:{Fore.YELLOW}{mod_version}{Fore.RED}` not found!{Fore.RESET}"
                )
                return False

            version = mod.get_version(mod_version)
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


def load_release(release: str) -> GTNHRelease | None:
    release_file = RELEASE_MANIFEST_DIR / (release + ".json")
    if not release_file.exists():
        log.error(f"Release `{Fore.LIGHTRED_EX}{release_file}{Fore.RESET}` not found!")
        return None

    with open(release_file, encoding="utf-8") as f:
        return GTNHRelease.parse_raw(f.read())


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
