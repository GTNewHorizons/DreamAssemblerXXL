import re
import shutil
from collections.abc import Callable
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from daxxl.app_context import AppContext
from daxxl.assembler.downloader import get_asset_version_cache_location
from daxxl.assembler.platforms.generic_assembler import GenericAssembler
from daxxl.defs import (
    Side, RELEASE_MOBILE_DIR, MRPACK_METADATA, LWJGL3IFY_SHARED_CONTEXT_ENTRY, LWJGL3IFY_LINUX_CREATE_DESKTOP_ENTRY,
)
from daxxl.models.gtnh_release import GTNHRelease
from daxxl.models.gtnh_version import GTNHVersion
from daxxl.models.mod_info import GTNHModInfo
from daxxl.utils import normalize_archive_permissions


class MobileAssembler(GenericAssembler):
    """
    Mobile assembler class. Allows for the assembling of Mobile archives.
    """

    def __init__(
        self,
        context: AppContext,
        release: GTNHRelease,
        task_progress_callback: Callable[[float, str], None] | None = None,
        global_progress_callback: Callable[[float, str], None] | None = None,
        changelog_path: Path | None = None,
    ):
        """
        Constructor of the MobileAssembler class.

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
        self.excluded_mod_names: list[str] = ["Craft-Presence", "BetterLoadingScreen"]
        self.mobile_modpack_files: Path = Path(f"overrides")
        self.mobile_modpack_mods: Path = self.mobile_modpack_files / "mods"

        self.modified_config_files["config/lwjgl3ify.cfg"] = self._modify_lwjgl3ify_config


    async def add_mods(
        self,
        side: Side,
        mods: list[tuple[GTNHModInfo, GTNHVersion]],
        archive: ZipFile,
        verbose: bool = False,
    ) -> None:
        for mod, version in mods:
            if mod.name in self.excluded_mod_names:
                continue
            source_file: Path = get_asset_version_cache_location(mod, version)
            archive_path: Path = self.mobile_modpack_mods / source_file.name
            archive.write(source_file, arcname=archive_path)

            if self.task_progress_callback is not None:
                self.task_progress_callback(self.delta_progress, f"adding mod {mod.name} : version {version.version_tag} to the archive")
            await self.yield_to_event_loop()

    @property
    def config_root(self) -> Path | None:
        return self.mobile_modpack_files

    def get_archive_path(self, side: Side) -> Path:
        return RELEASE_MOBILE_DIR / f"GT_New_Horizons_{self.release.version}.mrpack"

    async def assemble(self, side: Side, verbose: bool = False) -> None:
        if side is not Side.CLIENT_JAVA9:
            raise ValueError(f"Only valid sides are {Side.CLIENT.value}, got {side.value}")

        # +1 for the metadata file
        self.delta_progress = 100 / (len(self.get_mods(side)) + self.get_amount_of_files_in_config(side) + self.get_amount_of_files_in_locales() + 1)

        # moving this from last step to first step because right now amethyst has a huge perf issue finding the mrpack
        # json if it's not in the first zip entry
        await self.add_mobile_meta_data(side)

        await GenericAssembler.assemble(self, side, verbose)

        with ZipFile(self.get_archive_path(side), "a", compression=ZIP_DEFLATED) as archive:
            await self.add_localisation_files(archive, str(self.mobile_modpack_files.as_posix()))  # otherwise file check fails
            # on windows
            await normalize_archive_permissions(archive)

    async def add_mobile_meta_data(self, side: Side) -> None:
        """
        Method used to add additional meta data to the mobile archive.

        :param side: client side
        :return: None
        """

        with ZipFile(self.get_archive_path(side), "a", compression=ZIP_DEFLATED) as archive:
            if self.task_progress_callback is not None:
                self.task_progress_callback(self.delta_progress, "adding archive's metadata to the archive")

            version_id = self.release.get_display_version(self.context.counter, with_date=False)
            name = f"GT:NH {version_id}" # the version is also added in the name as amethyst does not show
            archive.writestr("modrinth.index.json", MRPACK_METADATA.format(name, version_id))

            await normalize_archive_permissions(archive)

    def _modify_lwjgl3ify_config(self, file_entry:str, data:bytes)->bytes:
        data = self._change_forge_entry_or_raise(data=data, forge_key=LWJGL3IFY_SHARED_CONTEXT_ENTRY, replacement="false", file_entry=file_entry)
        data = self._change_forge_entry_or_raise(data=data, forge_key=LWJGL3IFY_LINUX_CREATE_DESKTOP_ENTRY, replacement="false", file_entry=file_entry)

        return data
