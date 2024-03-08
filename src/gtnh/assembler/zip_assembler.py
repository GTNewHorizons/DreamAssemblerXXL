import shutil
from pathlib import Path
from typing import Callable, List, Optional, Tuple
from zipfile import ZIP_DEFLATED, ZipFile

from gtnh.assembler.downloader import get_asset_version_cache_location
from gtnh.assembler.generic_assembler import GenericAssembler
from gtnh.defs import RELEASE_ZIP_DIR, SERVER_ASSETS_DIR, ServerBrand, Side
from gtnh.gtnh_logger import get_logger
from gtnh.models.gtnh_config import GTNHConfig
from gtnh.models.gtnh_release import GTNHRelease
from gtnh.models.gtnh_version import GTNHVersion
from gtnh.models.mod_info import GTNHModInfo
from gtnh.modpack_manager import GTNHModpackManager

log = get_logger(__name__)


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
        changelog_path: Optional[Path] = None,
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
            changelog_path=changelog_path,
        )

    def add_mods(
        self,
        side: Side,
        mods: list[tuple[GTNHModInfo, GTNHVersion]],
        archive: ZipFile,
        verbose: bool = False,
    ) -> None:

        for mod, version in mods:
            source_file: Path = get_asset_version_cache_location(mod, version)
            archive_path: Path = Path("mods") / source_file.name
            archive.write(source_file, arcname=archive_path)
            if side.is_server():
                for extra_asset in version.extra_assets:
                    if extra_asset.filename is not None:
                        if extra_asset.filename.endswith("forgePatches.jar"):
                            extra_asset_path: Path = get_asset_version_cache_location(
                                mod, version, extra_asset.filename
                            )
                            archive.write(extra_asset_path, arcname=f"{mod.name}-forgePatches.jar")
            if self.task_progress_callback is not None:
                self.task_progress_callback(
                    self.get_progress(), f"adding mod {mod.name} : version {version.version_tag} to the archive"
                )

    def add_server_assets(self, archive: ZipFile, server_brand: ServerBrand, side: Side) -> None:
        assets = self.get_server_assets(server_brand, side)

        for asset in assets:
            archive.write(asset, arcname=asset.relative_to(SERVER_ASSETS_DIR / server_brand.value))
            if self.task_progress_callback is not None:
                self.task_progress_callback(self.get_progress(), f"adding server asset {asset.name} to the archive")

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

        self.add_changelog(archive)

    def get_archive_path(self, side: Side) -> Path:
        return RELEASE_ZIP_DIR / f"GT_New_Horizons_{self.release.version}_{side.archive_name()}.zip"

    async def assemble(self, side: Side, verbose: bool = False, server_brand: ServerBrand = ServerBrand.forge) -> None:
        """
        Method to assemble the release.

        :param side: target side
        :param verbose: flag to enable the verbose mode
        :param server_brand: server brand used to create the archive if it's a server one
        :return: None
        """
        # +1 for the changelog
        amount_of_files: int = len(self.get_mods(side)) + self.get_amount_of_files_in_config(side) + 1

        if side.is_server():
            amount_of_files += len(self.get_server_assets(server_brand, side))

        if side.is_client():
            amount_of_files += self.get_amount_of_files_in_locales()

        self.set_progress(100 / amount_of_files)
        await GenericAssembler.assemble(self, side, verbose)

        if side.is_server():
            log.info("Adding server assets to the server release.")
            with ZipFile(self.get_archive_path(side), "a", compression=ZIP_DEFLATED) as archive:
                self.add_server_assets(archive, server_brand, side)
        if side.is_client():
            log.info("Adding locales to client release.")
            with ZipFile(self.get_archive_path(side), "a", compression=ZIP_DEFLATED) as archive:
                self.add_localisation_files(archive)

    def get_server_assets(self, server_brand: ServerBrand, side: Side) -> List[Path]:
        """
        return the list of Path objects corresponding to the server brand's assets.

        :param server_brand: the server brand to fetch assets for
        :return: a list of Path objects
        """
        assets_root: Path = SERVER_ASSETS_DIR / server_brand.value
        path_objects: List[Path] = [path_object for path_object in assets_root.iterdir()]

        assets: List[Path] = []
        folders: List[Path]

        while len(path_objects) > 0:
            assets.extend(
                [
                    file
                    for file in path_objects
                    if file.is_file() and str(file.relative_to(assets_root)) not in self.exclusions[side]
                ]
            )

            folders = [
                folder
                for folder in path_objects
                if folder.is_dir() and str(folder.relative_to(assets_root)) not in self.exclusions[side]
            ]
            path_objects = []
            for folder in folders:
                path_objects.extend([path for path in folder.iterdir()])

        return assets
