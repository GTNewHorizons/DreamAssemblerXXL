from collections.abc import Callable
from json import dumps
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from colorama import Fore

from daxxl.app_context import AppContext
from daxxl.assembler.downloader import get_asset_version_cache_location
from daxxl.assembler.platforms.generic_assembler import GenericAssembler
from daxxl.defs import RELEASE_CURSE_DIR, ROOT_DIR, Side
from daxxl.gtnh_logger import get_logger
from daxxl.models.gtnh_release import GTNHRelease
from daxxl.models.gtnh_version import GTNHVersion
from daxxl.models.mod_info import GTNHModInfo
from daxxl.utils import normalize_archive_permissions

log = get_logger(__name__)


def is_valid_curse_mod(mod: GTNHModInfo, version: GTNHVersion) -> bool:
    """
     Returns whether or not a given mod is a valid curse mod or not.

    :param mod: the given mod object
    :param version: its corresponding version
    :return: true if it is a valid curse mod
    """
    # If we don't have curse file info, it's not a valid curse file
    if version.curse_file is None:
        return False

    # If we don't have a file no, or a project no, it's not a valid curse file
    if not version.curse_file.file_no or not version.curse_file.project_no:
        return False

    return True


class CurseAssembler(GenericAssembler):
    """
    Curse assembler class. Allows for the assembling of curse archives.
    """

    excluded_config_files = frozenset({"config/dependencies.json"})

    def __init__(
        self,
        context: AppContext,
        release: GTNHRelease,
        task_progress_callback: Callable[[float, str], None] | None = None,
        global_progress_callback: Callable[[float, str], None] | None = None,
        changelog_path: Path | None = None,
    ):
        """
        Constructor of the CurseAssembler class.

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

        self.overrides_folder = Path("overrides")
        self.manifest_json = Path("manifest.json")
        self.overrides = ROOT_DIR / "overrides.png"
        self.overrideslash = ROOT_DIR / "overrideslash.png"

    def get_archive_path(self, side: Side) -> Path:
        return RELEASE_CURSE_DIR / f"GT_New_Horizons_{self.release.version}.zip"

    async def assemble(self, side: Side, verbose: bool = False) -> None:
        if side not in {Side.CLIENT}:
            raise Exception("Can only assemble release for CLIENT")

        # +2 override pictures, +1 manifest.json and an optional changelog
        self.delta_progress = 100 / (
            len(self.get_override_mods(side))
            + 2
            + self.get_amount_of_files_in_config(side)
            + self.get_amount_of_files_in_locales()
            + 1
            + int(self.changelog_path is not None)
        )

        archive_name: Path = self.get_archive_path(side)

        # deleting any existing archive
        if archive_name.exists():
            archive_name.unlink()
            log.warn(f"Previous archive {Fore.YELLOW}'{archive_name}'{Fore.RESET} deleted")

        log.info(f"Constructing {Fore.YELLOW}{side}{Fore.RESET} archive at {Fore.YELLOW}'{archive_name}'{Fore.RESET}")

        with ZipFile(self.get_archive_path(side), "w", compression=ZIP_DEFLATED) as archive:
            log.info("Adding config to the archive")
            await self.add_config(side, self.get_config(), archive, verbose=verbose)
            await self.yield_to_event_loop()
            log.info("Adding manifest.json to the archive")
            self.generate_meta_data(side, archive)
            await self.yield_to_event_loop()
            log.info("Adding overrides to the archive")
            await self.add_overrides(side, archive)
            log.info("Adding locales to the archive")
            await self.add_localisation_files(archive, str(self.overrides_folder))
            await self.yield_to_event_loop()
            await normalize_archive_permissions(archive)
            log.info("Archive created successfully!")

    def get_override_mods(self, side: Side) -> list[tuple[GTNHModInfo, GTNHVersion]]:
        return [(mod, version) for mod, version in self.get_mods(side) if not is_valid_curse_mod(mod, version)]

    async def add_overrides(self, side: Side, archive: ZipFile) -> None:
        """
        Method to add the overrides to the curse archive.

        :param side: client side
        :param archive: curse archive
        :return: None
        """
        for image in (self.overrides, self.overrideslash):
            archive_path = self.overrides_folder / image.name
            archive.write(image, arcname=archive_path)
            if self.task_progress_callback is not None:
                self.task_progress_callback(self.delta_progress, f"adding {archive_path} to the archive")
            await self.yield_to_event_loop()

        for mod, version in self.get_override_mods(side):
            source_file = get_asset_version_cache_location(mod, version)
            archive_path = self.overrides_folder / "mods" / source_file.name
            archive.write(source_file, arcname=archive_path)
            if self.task_progress_callback is not None:
                self.task_progress_callback(self.delta_progress, f"adding mod {mod.name} : version {version.version_tag} to the archive")
            await self.yield_to_event_loop()

    @property
    def config_root(self) -> Path | None:
        return self.overrides_folder

    def generate_meta_data(self, side: Side, archive: ZipFile) -> None:
        """
        Generates the manifest.json and places it in the archive.

        :param side: the side of the pack
        :param archive: the zipfile
        :return: None
        """

        metadata: dict[
            str,
            dict[str, str | list[dict[str, str | bool | int]]] | list[dict[str, str | bool | int]] | str | int,
        ] = {
            "minecraft": {"version": "1.7.10", "modLoaders": [{"id": "forge-10.13.4.1614", "primary": True}]},
            "manifestType": "minecraftModpack",
            "manifestVersion": 1,
            "name": "GT New Horizons",
            "version": f"{self.release.version}-1.7.10",
            "author": "DreamMasterXXL",
            "overrides": "overrides",
        }

        mod: GTNHModInfo
        version: GTNHVersion
        files: list[dict[str, str | int | bool]] = []
        for mod, version in self.get_mods(side):
            if is_valid_curse_mod(mod, version):
                assert version.curse_file  # make mypy happy
                # ignoring mypy errors here because it's all good in the check above
                files.append(
                    {
                        "projectID": int(version.curse_file.project_no),
                        "fileID": int(version.curse_file.file_no),
                        "required": True,
                    }
                )

        metadata["files"] = files

        archive.writestr(str(self.manifest_json), dumps(metadata, indent=2))

        if self.task_progress_callback is not None:
            self.task_progress_callback(self.delta_progress, f"adding {self.manifest_json} to the archive")
