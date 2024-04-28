import os
import re
import shutil
from pathlib import Path
from typing import Callable, Optional, Tuple, Set, List
from zipfile import ZIP_DEFLATED, ZipFile

from colorama import Fore

from gtnh.assembler.downloader import get_asset_version_cache_location
from gtnh.assembler.generic_assembler import GenericAssembler
from gtnh.defs import RELEASE_TECHNIC_DIR, Side
from gtnh.gtnh_logger import get_logger
from gtnh.models.gtnh_config import GTNHConfig
from gtnh.models.gtnh_release import GTNHRelease
from gtnh.models.gtnh_version import GTNHVersion
from gtnh.models.mod_info import GTNHModInfo
from gtnh.modpack_manager import GTNHModpackManager

log = get_logger("technic process")


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
        gtnh_modpack: GTNHModpackManager,
        release: GTNHRelease,
        task_progress_callback: Optional[Callable[[float, str], None]] = None,
        global_progress_callback: Optional[Callable[[float, str], None]] = None,
        changelog_path: Optional[Path] = None,
    ):
        """
        Constructor of the TechnicAssembler class.

        :param gtnh_modpack: the modpack manager instance
        :param release: the target release object
        :param task_progress_callback: the callback to report the progress of the task
        :param global_progress_callback: the callback to report the global progress
        """
        GenericAssembler.__init__(
            self,
            gtnh_modpack=gtnh_modpack,
            release=release,
            task_progress_callback=task_progress_callback,
            global_progress_callback=global_progress_callback,
            changelog_path=changelog_path,
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

        archive_name: Path = self.get_partial_archive_path()

        # deleting any existing archive
        if os.path.exists(archive_name):
            os.remove(archive_name)
            log.warn(f"Previous archive {Fore.YELLOW}'{archive_name}'{Fore.RESET} deleted")

        log.info(f"Constructing {Fore.YELLOW}{side}{Fore.RESET} archive at {Fore.YELLOW}'{archive_name}'{Fore.RESET}")

        with ZipFile(archive_name, "w", compression=ZIP_DEFLATED) as archive:
            log.info("Adding mods to the archive")
            self.add_mods(side, self.partial_mods(side), archive, verbose=verbose)
            log.info("Adding config to the archive")
            self.add_config(side, self.get_config(), archive, verbose=verbose)
            log.info("Generating the readme for the modpack repo")
            self.generate_readme()
            log.info("Archive created successfully!")

    def partial_mods(self, side)->list[Tuple[GTNHModInfo, GTNHVersion]]:
        valid_sides: Set[Side] = side.valid_mod_sides()

        github_mods: List[Tuple[GTNHModInfo, GTNHVersion]] = self.github_mods(valid_sides)
        github_mods_names = [x[0].name for x in github_mods]

        external_mods: List[Tuple[GTNHModInfo, GTNHVersion]] = self.external_mods(valid_sides)
        external_mods_names = [x[0].name for x in external_mods]

        last_version: GTNHRelease = self.modpack_manager.get_release(self.release.last_version)

        mods: List[Tuple[GTNHModInfo, GTNHVersion]] = []

        for mod_name in self.modpack_manager.get_changed_mods(self.release, last_version):
            if mod_name in github_mods_names:
                mod_index = github_mods_names.index(mod_name)
                mods.append(github_mods[mod_index])
            elif mod_name in external_mods_names:
                mod_index = external_mods_names.index(mod_name)
                mods.append(external_mods[mod_index])
            else:
                log.warn(f"Mod {mod_name} was detected as an updated mod"
                                 ", but is not a github mod nor an external one")

        return mods

    def add_mods(
        self, side: Side, mods: list[tuple[GTNHModInfo, GTNHVersion]], archive: ZipFile, verbose: bool = False
    ) -> None:

        temp_zip_path: Path = Path("./temp.zip")

        for mod, version in mods:
            source_file: Path = get_asset_version_cache_location(mod, version)
            archive_path: Path = Path("mods") / source_file.name

            # set up temp zip
            with ZipFile(temp_zip_path, "w", compression=ZIP_DEFLATED) as temp_zip:
                temp_zip.write(source_file, arcname=archive_path)

            archive.write(
                temp_zip_path,
                arcname=(f"mods/{technify(mod.name)}/{technify(mod.name)}" f"-{technify(version.version_tag)}.zip"),
            )

            if self.task_progress_callback is not None:
                self.task_progress_callback(
                    self.get_progress(), f"adding mod {mod.name} : version {version.version_tag} to the archive"
                )

        # deleting temp zip
        if temp_zip_path is not None:
            temp_zip_path.unlink()

    def add_config(
        self, side: Side, config: Tuple[GTNHConfig, GTNHVersion], archive: ZipFile, verbose: bool = False
    ) -> None:

        modpack_config: GTNHConfig
        config_version: Optional[GTNHVersion]
        modpack_config, config_version = config

        config_file: Path = get_asset_version_cache_location(modpack_config, config_version)

        temp_zip_path: Path = Path("./temp.zip")

        # set up a temp zip
        with ZipFile(Path("./temp.zip"), "w", compression=ZIP_DEFLATED) as temp_zip:

            # reading the config files
            with ZipFile(config_file, "r", compression=ZIP_DEFLATED) as config_zip:

                for item in config_zip.namelist():
                    # excluding files
                    if item in self.exclusions[side]:
                        continue

                    # reading the file
                    with config_zip.open(item) as config_item:

                        # creating a new file in the temp zip
                        with temp_zip.open(item, "w") as target:

                            # copying the file
                            shutil.copyfileobj(config_item, target)

                            if self.task_progress_callback is not None:
                                self.task_progress_callback(self.get_progress(), f"adding {item} to the archive")

            # adding the locales
            self.add_localisation_files(temp_zip)

            self.add_changelog(temp_zip)

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
    def get_partial_archive_path(self) -> Path:
        return RELEASE_TECHNIC_DIR / f"GT_New_Horizons_{self.release.version}_(technic_partial).zip"
    async def assemble(self, side: Side, verbose: bool = False) -> None:
        if side != Side.CLIENT:
            raise ValueError(f"Only valid side is {Side.CLIENT}, got {side}")
        log.info(f"packing technic launcher release for {self.release.version}")
        self.set_progress(
            100
            / (
                len(self.get_mods(side))
                + self.get_amount_of_files_in_config(side)
                + self.get_amount_of_files_in_locales()
                + 1
            )
        )
        await GenericAssembler.assemble(self, side, verbose)

        log.info(f"packing partial technic launcher release for {self.release.version}")
        await self.partial_assemble(side, verbose)
