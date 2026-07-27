import os
import re
from enum import Enum
from pathlib import Path
from typing import Callable, Optional
from zipfile import ZIP_DEFLATED, ZipFile

from colorama import Fore

from daxxl.app_context import AppContext
from daxxl.assembler.downloader import get_asset_version_cache_location
from daxxl.assembler.platforms.generic_assembler import GenericAssembler
from daxxl.defs import RELEASE_TECHNIC_DIR, Side
from daxxl.gtnh_logger import get_logger
from daxxl.models.gtnh_config import GTNHConfig
from daxxl.models.gtnh_release import GTNHRelease
from daxxl.models.gtnh_version import GTNHVersion
from daxxl.models.mod_info import GTNHModInfo
from daxxl.utils import normalize_archive_permissions

log = get_logger("technic process")


class DifferentialUpdateMode(str, Enum):
    NEW_MODS = "NEW_MODS"
    UPDATED_MODS = "UPDATED_MODS"
    REMOVED_MODS = "REMOVED_MODS"


def technify(string: str) -> str:
    """
    format the given string to be only lower case letters or numbers or dashes.

    :param string: the given string
    :return: the formatted string
    """
    pattern_separators = re.compile("[ _]")
    pattern_strip = re.compile("[^a-z0-9.-]")
    formatted_string = re.sub(pattern_separators, "-", string.lower())
    formatted_string = re.sub(pattern_strip, "", formatted_string)

    return formatted_string


class TechnicAssembler(GenericAssembler):
    """
    Technic assembler class. Allows for the assembling of technic archives.
    """

    def __init__(
        self,
        context: AppContext,
        release: GTNHRelease,
        task_progress_callback: Optional[Callable[[float, str], None]] = None,
        global_progress_callback: Optional[Callable[[float, str], None]] = None,
        changelog_path: Optional[Path] = None,
        current_task_reset_callback: Optional[Callable[[], None]] = None,
    ):
        """
        Constructor of the TechnicAssembler class.

        :param context: the context instance
        :param release: the target release object
        :param task_progress_callback: the callback to report the progress of the task
        :param global_progress_callback: the callback to report the global progress
        :param current_task_reset_callback: the callback to reset the progress bar for the current task
        """
        GenericAssembler.__init__(
            self,
            context=context,
            release=release,
            task_progress_callback=task_progress_callback,
            global_progress_callback=global_progress_callback,
            changelog_path=changelog_path,
            current_task_reset_callback=current_task_reset_callback,
        )

    async def partial_assemble(self, side: Side, verbose: bool = False) -> None:
        """
        Method to assemble only the changed mods of the release.

        :param side: target side
        :param verbose: flag to enable the verbose mode
        :return: None
        """
        if side not in {Side.CLIENT, Side.CLIENT_JAVA9}:
            raise Exception(f"Can only assemble release for CLIENT or SERVER, not {side}")

        updated_mods_archive_name: Path = self.get_updated_mods_archive_path()
        new_mods_archive_name: Path = self.get_new_mods_archive_path()
        removed_modlist_name: Path = self.get_removed_modlist_path()

        # deleting any existing archive
        if os.path.exists(updated_mods_archive_name):
            os.remove(updated_mods_archive_name)
            log.warn(f"Previous archive {Fore.YELLOW}'{updated_mods_archive_name}'{Fore.RESET} deleted")

        if os.path.exists(new_mods_archive_name):
            os.remove(new_mods_archive_name)
            log.warn(f"Previous archive {Fore.YELLOW}'{new_mods_archive_name}'{Fore.RESET} deleted")

        if os.path.exists(removed_modlist_name):
            os.remove(removed_modlist_name)
            log.warn(f"Previous modlist {Fore.YELLOW}'{removed_modlist_name}'{Fore.RESET} deleted")

        log.info(
            f"Constructing {Fore.YELLOW}{side}{Fore.RESET} archive at {Fore.YELLOW}'{updated_mods_archive_name}'{Fore.RESET}"
        )

        with ZipFile(updated_mods_archive_name, "w", compression=ZIP_DEFLATED) as archive:
            log.info("Adding mods to the archive")
            await self.add_mods(
                side, self.differential_update(side, DifferentialUpdateMode.UPDATED_MODS), archive, verbose=verbose
            )
            await self.yield_to_event_loop()
            log.info("Adding config to the archive")
            await self.add_config(side, self.get_config(), archive, verbose=verbose)
            await self.yield_to_event_loop()
            log.info("Generating the readme for the modpack repo")
            self.generate_readme()
            await self.yield_to_event_loop()
            await normalize_archive_permissions(archive)
            log.info("Archive created successfully!")

        log.info(
            f"Constructing {Fore.YELLOW}{side}{Fore.RESET} archive at {Fore.YELLOW}'{new_mods_archive_name}'{Fore.RESET}"
        )

        with ZipFile(new_mods_archive_name, "w", compression=ZIP_DEFLATED) as archive:
            log.info("Adding mods to the archive")
            await self.add_mods(
                side, self.differential_update(side, DifferentialUpdateMode.NEW_MODS), archive, verbose=verbose
            )
            await self.yield_to_event_loop()
            await normalize_archive_permissions(archive)
            log.info("Archive created successfully!")

        with open(removed_modlist_name, "w") as f:
            log.info("generating removed modlist")
            removed_modlist: list[tuple[GTNHModInfo, GTNHVersion]] = self.differential_update(
                side, DifferentialUpdateMode.REMOVED_MODS
            )
            f.write("\n".join([f"{mod.name}: {version.version_tag}" for (mod, version) in removed_modlist]))
            log.info("modlist created successfully!")

    def differential_update(
        self, side: Side, update_mode: DifferentialUpdateMode
    ) -> list[tuple[GTNHModInfo, GTNHVersion]]:
        update_source: Callable[[GTNHRelease, GTNHRelease], set[str]]

        if update_mode == DifferentialUpdateMode.NEW_MODS:
            update_source = self.context.comparison.get_new_mods
        elif update_mode == DifferentialUpdateMode.UPDATED_MODS:
            update_source = self.context.comparison.get_changed_mods
        else:
            update_source = self.context.comparison.get_removed_mods

        last_release: GTNHRelease = self.context.release_service.get_release(self.release.last_version)  # type: ignore
        process_release: GTNHRelease = (
            last_release if update_mode == DifferentialUpdateMode.REMOVED_MODS else self.release
        )

        valid_sides: set[Side] = side.valid_mod_sides()
        j9_sides: set[Side] = {Side.CLIENT_JAVA9, Side.BOTH_JAVA9}

        github_mods: list[tuple[GTNHModInfo, GTNHVersion]] = self.github_mods(valid_sides, release=process_release)
        github_mods_names = [x[0].name for x in github_mods]
        github_mods_j9: list[tuple[GTNHModInfo, GTNHVersion]] = self.github_mods(j9_sides, release=process_release)
        github_mods_names_j9 = [x[0].name for x in github_mods_j9]

        external_mods: list[tuple[GTNHModInfo, GTNHVersion]] = self.external_mods(valid_sides, release=process_release)
        external_mods_names = [x[0].name for x in external_mods]
        external_mods_j9: list[tuple[GTNHModInfo, GTNHVersion]] = self.external_mods(j9_sides, release=process_release)
        external_mods_names_j9 = [x[0].name for x in external_mods_j9]

        mods: list[tuple[GTNHModInfo, GTNHVersion]] = []
        for mod_name in update_source(self.release, last_release):
            if mod_name in github_mods_names:
                mod_index = github_mods_names.index(mod_name)
                mods.append(github_mods[mod_index])
            elif mod_name in external_mods_names:
                mod_index = external_mods_names.index(mod_name)
                mods.append(external_mods[mod_index])
            else:
                if side == Side.CLIENT and (mod_name in github_mods_names_j9 or mod_name in external_mods_names_j9):
                    log.warn(f"Mod {mod_name} is a java 9+ mod but currently packing only java 8 mods. Skipping it.")
                else:
                    log.warn(
                        f"Mod {mod_name} was detected as an updated mod, but is not a github mod nor an external one"
                    )

        return mods

    async def add_mods(
        self, side: Side, mods: list[tuple[GTNHModInfo, GTNHVersion]], archive: ZipFile, verbose: bool = False
    ) -> None:

        temp_zip_path: Path = RELEASE_TECHNIC_DIR / "temp.zip"

        for mod, version in mods:
            source_file: Path = get_asset_version_cache_location(mod, version)
            archive_path: Path = Path("mods") / source_file.name

            # set up temp zip
            with ZipFile(temp_zip_path, "w", compression=ZIP_DEFLATED) as temp_zip:
                temp_zip.write(source_file, arcname=archive_path)
                await normalize_archive_permissions(temp_zip)

            archive.write(
                temp_zip_path,
                arcname=(f"mods/{technify(mod.name)}/{technify(mod.name)}-{technify(version.version_tag)}.zip"),
            )

            if self.task_progress_callback is not None:
                self.task_progress_callback(
                    self.progress, f"adding mod {mod.name} : version {version.version_tag} to the archive"
                )
            await self.yield_to_event_loop()

        # deleting temp zip
        if temp_zip_path.exists():
            temp_zip_path.unlink()

    async def add_config(
        self, side: Side, config: tuple[GTNHConfig, GTNHVersion], archive: ZipFile, verbose: bool = False
    ) -> None:

        modpack_config: GTNHConfig
        config_version: Optional[GTNHVersion]
        modpack_config, config_version = config

        config_file: Path = get_asset_version_cache_location(modpack_config, config_version)

        temp_zip_path: Path = Path("./temp.zip")

        # technic wants the config as a single nested zip rather than as loose files in the archive
        with ZipFile(temp_zip_path, "w", compression=ZIP_DEFLATED) as temp_zip:
            await self._add_config_files(side, config_file, temp_zip)

            # adding the locales
            await self.add_localisation_files(temp_zip)

            self.add_changelog(temp_zip)

            await normalize_archive_permissions(temp_zip)

        # writing the config zip in the technic archive
        archive.write(
            temp_zip_path,
            arcname=(
                f"mods/{technify(modpack_config.name)}/{technify(modpack_config.name)}"
                f"-{technify(config_version.version_tag)}.zip"
            ),
        )

        # deleting temp zip
        temp_zip_path.unlink()

    def get_archive_path(self, side: Side) -> Path:
        return RELEASE_TECHNIC_DIR / f"GT_New_Horizons_{self.release.version}_(technic).zip"

    def get_updated_mods_archive_path(self) -> Path:
        return RELEASE_TECHNIC_DIR / f"GT_New_Horizons_{self.release.version}_(updated mods).zip"

    def get_new_mods_archive_path(self) -> Path:
        return RELEASE_TECHNIC_DIR / f"GT_New_Horizons_{self.release.version}_(new mods).zip"

    def get_removed_modlist_path(self) -> Path:
        return RELEASE_TECHNIC_DIR / f"GT_New_Horizons_{self.release.version}_(removed mods).txt"

    async def assemble(
        self,
        side: Side,
        verbose: bool = False,
        global_step_callback: Optional[Callable[[str], None]] = None,
    ) -> None:
        if side != Side.CLIENT:
            raise ValueError(f"Only valid side is {Side.CLIENT}, got {side}")
        log.info(f"packing technic launcher release for {self.release.version}")
        self.progress = 100 / (
            len(self.get_mods(side))
            + self.get_amount_of_files_in_config(side)
            + self.get_amount_of_files_in_locales()
            + 1
        )
        await GenericAssembler.assemble(self, side, verbose)

        log.info(f"packing partial technic launcher release for {self.release.version}")
        if global_step_callback is not None:
            global_step_callback("Assembling partial Technic archive")
        if self.current_task_reset_callback is not None:
            self.current_task_reset_callback()
        self.progress = 100 / (
            len(self.differential_update(side, DifferentialUpdateMode.UPDATED_MODS))
            + self.get_amount_of_files_in_config(side)
            + self.get_amount_of_files_in_locales()
            + 1  # changelog
            + len(self.differential_update(side, DifferentialUpdateMode.NEW_MODS))
        )
        await self.partial_assemble(side, verbose)
