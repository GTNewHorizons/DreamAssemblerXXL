import shutil
from pathlib import Path
from typing import Optional, Callable, Tuple
from zipfile import ZipFile, ZIP_DEFLATED

from generic_assembler import GenericAssembler
from gtnh.assembler.downloader import get_asset_version_cache_location
from gtnh.defs import Side, RELEASE_ZIP_DIR
from gtnh.models.gtnh_config import GTNHConfig
from gtnh.models.gtnh_release import GTNHRelease
from gtnh.models.gtnh_version import GTNHVersion
from gtnh.models.mod_info import GTNHModInfo
from gtnh.modpack_manager import GTNHModpackManager


class ZipAssembler(GenericAssembler):

    def __init__(self, gtnh_modpack: GTNHModpackManager, release: GTNHRelease,
                 progress_callback: Optional[Callable[[str, int], None]] = None):
        GenericAssembler.__init__(self, gtnh_modpack=gtnh_modpack, release=release, progress_callback=progress_callback)

    def add_mods(
            self, side: Side, mods: list[tuple[GTNHModInfo, GTNHVersion]], archive: ZipFile, verbose: bool = False
    ) -> None:

        for mod, version in mods:
            source_file: Path = get_asset_version_cache_location(mod, version)
            self.update_progress(side, source_file, verbose=verbose)
            archive_path: Path = Path("mods") / source_file.name
            archive.write(source_file, arcname=archive_path)

    def add_config(self, side: Side, config: Tuple[GTNHConfig, GTNHVersion], archive: ZipFile,
                   verbose: bool = False) -> None:
        modpack_config: GTNHConfig
        config_version: Optional[GTNHVersion]
        modpack_config, config_version = config

        config_file: Path = get_asset_version_cache_location(modpack_config, config_version)

        with ZipFile(config_file, "r", compression=ZIP_DEFLATED) as config_zip:
            self.update_progress(side, config_file, verbose=verbose)

            for item in config_zip.namelist():
                if item in self.exclusions[side]:
                    continue
                with config_zip.open(item) as config_item:
                    with archive.open(item, "w") as target:
                        shutil.copyfileobj(config_item, target)

    def get_archive_path(self, side: Side) -> Path:
        return RELEASE_ZIP_DIR / f"GTNewHorizons-{side}-{self.release.version}.zip"
