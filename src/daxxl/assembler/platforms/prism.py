import shutil
from pathlib import Path
from typing import Callable, Optional
from zipfile import ZIP_DEFLATED, ZipFile

from daxxl.app_context import AppContext
from daxxl.assembler.downloader import get_asset_version_cache_location
from daxxl.assembler.platforms.generic_assembler import GenericAssembler
from daxxl.defs import (
    JAVA_9_ARCHIVE_SUFFIX,
    MMC_PACK_JSON,
    PRISM_ASSETS_DIR,
    PRISM_PACK_INSTANCE,
    RELEASE_PRISM_DIR,
    Side,
)
from daxxl.models.gtnh_release import GTNHRelease
from daxxl.models.gtnh_version import GTNHVersion
from daxxl.models.mod_info import GTNHModInfo
from daxxl.utils import normalize_archive_permissions


class PrismAssembler(GenericAssembler):
    """
    Prism assembler class. Allows for the assembling of Prism archives.
    """

    def __init__(
        self,
        context: AppContext,
        release: GTNHRelease,
        task_progress_callback: Optional[Callable[[float, str], None]] = None,
        global_progress_callback: Optional[Callable[[float, str], None]] = None,
        changelog_path: Optional[Path] = None,
    ):
        """
        Constructor of the PrismAssembler class.

        :param context: the context instance
        :param release: the target release object
        :param task_progress_callback: the callback to report the progress of the task
        :param global_progress_callback: the callback to report the global progress
        """
        GenericAssembler.__init__(
            self,
            context=context,
            release=release,
            task_progress_callback=task_progress_callback,
            global_progress_callback=global_progress_callback,
            changelog_path=changelog_path,
        )
        self.prism_archive_root: Path = Path(f"GT New Horizons {self.release.version}")
        self.prism_modpack_files: Path = self.prism_archive_root / ".minecraft"
        self.prism_modpack_mods: Path = self.prism_modpack_files / "mods"

    async def add_mods(
        self,
        side: Side,
        mods: list[tuple[GTNHModInfo, GTNHVersion]],
        archive: ZipFile,
        verbose: bool = False,
    ) -> None:

        for mod, version in mods:
            source_file: Path = get_asset_version_cache_location(mod, version)
            archive_path: Path = self.prism_modpack_mods / source_file.name
            archive.write(source_file, arcname=archive_path)
            for extra_asset in version.extra_assets:
                if extra_asset.filename is not None and extra_asset.filename.endswith("multimc.zip"):
                    extra_asset_path: Path = get_asset_version_cache_location(mod, version, extra_asset.filename)
                    with ZipFile(extra_asset_path, "r", compression=ZIP_DEFLATED) as prism_patches_zip:
                        for item in prism_patches_zip.namelist():
                            with prism_patches_zip.open(item, "r") as prism_patch:
                                with archive.open(str(self.prism_archive_root) + "/" + item, "w") as target:
                                    shutil.copyfileobj(prism_patch, target)
            if self.task_progress_callback is not None:
                self.task_progress_callback(
                    self.progress, f"adding mod {mod.name} : version {version.version_tag} to the archive"
                )
            await self.yield_to_event_loop()

    @property
    def config_root(self) -> Optional[Path]:
        return self.prism_modpack_files

    def get_archive_path(self, side: Side) -> Path:
        suffix = "_Java_8" if not side.is_java9() else f"_{JAVA_9_ARCHIVE_SUFFIX}"

        return RELEASE_PRISM_DIR / f"GT_New_Horizons_{self.release.version}{suffix}.zip"

    async def assemble(self, side: Side, verbose: bool = False) -> None:
        if side not in {Side.CLIENT, Side.CLIENT_JAVA9}:
            raise ValueError(f"Only valid sides are {Side.CLIENT.value}, got {side.value}")

        # +1 for the metadata file
        self.progress = 100 / (
            len(self.get_mods(side))
            + self.get_amount_of_files_in_config(side)
            + self.get_amount_of_files_in_locales()
            + 1
        )
        await GenericAssembler.assemble(self, side, verbose)

        with ZipFile(self.get_archive_path(side), "a", compression=ZIP_DEFLATED) as archive:
            await self.add_localisation_files(
                archive, str(self.prism_modpack_files.as_posix())
            )  # otherwise file check fails
            # on windows
            await normalize_archive_permissions(archive)

        await self.add_prism_meta_data(side)

    async def add_prism_meta_data(self, side: Side) -> None:
        """
        Method used to add additional meta data to the prism archive.

        :param side: client side
        :return: None
        """

        with ZipFile(self.get_archive_path(side), "a", compression=ZIP_DEFLATED) as archive:
            if self.task_progress_callback is not None:
                self.task_progress_callback(self.progress, "adding archive's metadata to the archive")
            if not side.is_java9():
                archive.writestr(str(self.prism_archive_root) + "/mmc-pack.json", MMC_PACK_JSON)
            archive.writestr(
                str(self.prism_archive_root) + "/instance.cfg",
                PRISM_PACK_INSTANCE.format(f"GTNH {self.release.version}"),
            )
            with archive.open(str(self.prism_archive_root) + "/gtnh_icon.png", "w") as target:
                with open(PRISM_ASSETS_DIR / "gtnh_icon.png", "rb") as icon:
                    shutil.copyfileobj(icon, target)
            await normalize_archive_permissions(archive)
