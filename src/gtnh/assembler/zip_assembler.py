import shutil
from pathlib import Path
from typing import Callable, Optional, Tuple
from zipfile import ZIP_DEFLATED, ZipFile

from gtnh.assembler.downloader import get_asset_version_cache_location
from gtnh.assembler.generic_assembler import GenericAssembler
from gtnh.defs import RELEASE_ZIP_DIR, Side
from gtnh.models.gtnh_config import GTNHConfig
from gtnh.models.gtnh_release import GTNHRelease
from gtnh.models.gtnh_version import GTNHVersion
from gtnh.models.mod_info import ExternalModInfo, GTNHModInfo
from gtnh.modpack_manager import GTNHModpackManager


class ZipAssembler(GenericAssembler):
    """
    Zip assembler class. Allows for the assembling of zip archives.
    """

    def __init__(
        self,
        gtnh_modpack: GTNHModpackManager,
        release: GTNHRelease,
        task_progress_callback: Optional[Callable[[float, str], None]] = None,
        global_progress_callback: Optional[Callable[[float, str], None]] = None,
    ):
        """
        Constructor of the ZipAssembler class.

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
        )

    def add_mods(
        self,
        side: Side,
        mods: list[tuple[GTNHModInfo | ExternalModInfo, GTNHVersion]],
        archive: ZipFile,
        verbose: bool = False,
    ) -> None:

        for mod, version in mods:
            source_file: Path = get_asset_version_cache_location(mod, version)
            archive_path: Path = Path("mods") / source_file.name
            archive.write(source_file, arcname=archive_path)
            if self.task_progress_callback is not None:
                self.task_progress_callback(
                    self.get_progress(), f"adding mod {mod.name} : version {version.version_tag} to the archive"
                )

    def add_config(
        self, side: Side, config: Tuple[GTNHConfig, GTNHVersion], archive: ZipFile, verbose: bool = False
    ) -> None:
        modpack_config: GTNHConfig
        config_version: Optional[GTNHVersion]
        modpack_config, config_version = config

        config_file: Path = get_asset_version_cache_location(modpack_config, config_version)

        with ZipFile(config_file, "r", compression=ZIP_DEFLATED) as config_zip:

            for item in config_zip.namelist():
                if item in self.exclusions[side]:
                    continue
                with config_zip.open(item) as config_item:
                    with archive.open(item, "w") as target:
                        shutil.copyfileobj(config_item, target)
                        if self.task_progress_callback is not None:
                            self.task_progress_callback(self.get_progress(), f"adding {item} to the archive")

    def get_archive_path(self, side: Side) -> Path:
        return RELEASE_ZIP_DIR / f"GTNewHorizons-{side}-{self.release.version}.zip"

    def assemble(self, side: Side, verbose: bool = False) -> None:
        self.set_progress(100 / (len(self.get_mods(side)) + self.get_amount_of_files_in_config(side)))
        GenericAssembler.assemble(self, side, verbose)
