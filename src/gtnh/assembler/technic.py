import logging
import shutil
from pathlib import Path
from typing import Callable, Optional, Tuple
from zipfile import ZIP_DEFLATED, ZipFile

from gtnh.assembler.downloader import get_asset_version_cache_location
from gtnh.assembler.generic_assembler import GenericAssembler
from gtnh.defs import RELEASE_TECHNIC_DIR, Side
from gtnh.models.gtnh_config import GTNHConfig
from gtnh.models.gtnh_release import GTNHRelease
from gtnh.models.gtnh_version import GTNHVersion
from gtnh.models.mod_info import GTNHModInfo
from gtnh.modpack_manager import GTNHModpackManager

log = logging.getLogger("technic process")
log.setLevel(logging.INFO)


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

    def add_mods(
        self, side: Side, mods: list[tuple[GTNHModInfo, GTNHVersion]], archive: ZipFile, verbose: bool = False
    ) -> None:

        temp_zip_path: Path = Path("./temp.zip")

        for mod, version in mods:
            source_file: Path = get_asset_version_cache_location(mod, version)
            archive_path: Path = Path("mods") / source_file.name

            # set up temp zip
            with ZipFile(temp_zip_path, "w") as temp_zip:
                temp_zip.write(source_file, arcname=archive_path)

            archive.write(temp_zip_path, arcname=f"mods/{mod.name}/{mod.name}-{version.version_tag}.zip")

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
        with ZipFile(Path("./temp.zip"), "w") as temp_zip:

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

            self.add_changelog(temp_zip)

        # writing the config zip in the technic archive
        archive.write(
            temp_zip_path,
            arcname=f"mods/{modpack_config.name}/{modpack_config.name}-{config_version.version_tag}.zip",
        )

        # deleting temp zip
        temp_zip_path.unlink()

    def get_archive_path(self, side: Side) -> Path:
        return RELEASE_TECHNIC_DIR / f"GT New Horizons {self.release.version} (technic).zip"

    def assemble(self, side: Side, verbose: bool = False) -> None:
        if side != Side.CLIENT:
            raise ValueError(f"Only valid side is {Side.CLIENT}, got {side}")

        self.set_progress(100 / (len(self.get_mods(side)) + self.get_amount_of_files_in_config(side) + 1))
        GenericAssembler.assemble(self, side, verbose)
