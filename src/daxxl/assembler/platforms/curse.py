from collections.abc import Callable
from json import dumps, loads
from pathlib import Path, PurePosixPath
from typing import Any
from zipfile import ZIP_DEFLATED, BadZipFile, ZipFile

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
        self.profile_image = Path("profileImage/636125694388807951.png")
        self.overrides = ROOT_DIR / "overrides.png"
        self.overrideslash = ROOT_DIR / "overrideslash.png"

    def get_archive_path(self, side: Side) -> Path:
        return RELEASE_CURSE_DIR / f"GT_New_Horizons_{self.release.version}.zip"

    def load_lwjgl3ify_files(self, side: Side) -> tuple[dict[str, Any], dict[str, bytes]]:
        """Read the selected version's CurseForge artifact before replacing an existing pack archive."""
        lwjgl3ify = next(((mod, version) for mod, version in self.get_mods(side) if mod.name == "lwjgl3ify"), None)
        if lwjgl3ify is None:
            raise ValueError(f"Cannot assemble CurseForge archive: release {self.release.version} has no client lwjgl3ify mod.")

        mod, version = lwjgl3ify
        try:
            artifact_path = get_asset_version_cache_location(mod, version, "-curse.zip")
        except FileNotFoundError as error:
            raise ValueError(f"Cannot assemble CurseForge archive: lwjgl3ify {version.version_tag} has no CurseForge artifact (*-curse.zip).") from error
        if not artifact_path.is_file():
            raise FileNotFoundError(f"Cannot assemble CurseForge archive: {artifact_path.name} is missing from the cache. Download the release assets first.")

        try:
            with ZipFile(artifact_path) as artifact:
                additions = loads(artifact.read("manifest-additions.json"))
                minecraft = additions.get("minecraft") if isinstance(additions, dict) else None
                if not isinstance(minecraft, dict) or not isinstance(minecraft.get("javaVersion"), int) or not isinstance(minecraft.get("patches"), list):
                    raise ValueError("manifest-additions.json must define minecraft.javaVersion and minecraft.patches")

                overrides: dict[str, bytes] = {}
                for entry in artifact.infolist():
                    if entry.is_dir() or not entry.filename.startswith("overrides/"):
                        continue
                    path = PurePosixPath(entry.filename)
                    if ".." in path.parts or "\\" in entry.filename or ":" in entry.filename or path.as_posix() != entry.filename:
                        raise ValueError(f"Invalid override path: {entry.filename}")
                    if entry.filename in overrides:
                        raise ValueError(f"Duplicate override path: {entry.filename}")
                    overrides[entry.filename] = artifact.read(entry)

                for patch in minecraft["patches"]:
                    if not isinstance(patch, str) or f"overrides/{patch}" not in overrides:
                        raise ValueError(f"Missing patch in artifact: {patch}")
        except (BadZipFile, OSError, KeyError, ValueError) as error:
            raise ValueError(f"Cannot assemble CurseForge archive: invalid {artifact_path.name}: {error}") from error

        return minecraft, overrides

    async def assemble(self, side: Side, verbose: bool = False) -> None:
        if side != Side.CLIENT_JAVA9:
            raise ValueError("Can only assemble CurseForge releases for CLIENT_JAVA9")

        minecraft_additions, lwjgl_overrides = self.load_lwjgl3ify_files(side)

        # +2 override pictures, +2 manifest/profile image and an optional changelog
        self.delta_progress = 100 / (
            len(self.get_override_mods(side))
            + len(lwjgl_overrides)
            + 2
            + self.get_amount_of_files_in_config(side)
            + self.get_amount_of_files_in_locales()
            + 2
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
            archive.write(ROOT_DIR / "icon.png", arcname=self.profile_image)
            if self.task_progress_callback is not None:
                self.task_progress_callback(self.delta_progress, f"adding {self.profile_image} to the archive")
            await self.yield_to_event_loop()
            log.info("Adding manifest.json to the archive")
            self.generate_meta_data(side, archive, minecraft_additions)
            await self.yield_to_event_loop()
            log.info("Adding overrides to the archive")
            await self.add_overrides(side, archive)
            log.info("Adding lwjgl3ify CurseForge files to the archive")
            for name, data in lwjgl_overrides.items():
                archive.writestr(name, data)
                if self.task_progress_callback is not None:
                    self.task_progress_callback(self.delta_progress, f"adding {name} to the archive")
                await self.yield_to_event_loop()
            log.info("Adding locales to the archive")
            await self.add_localisation_files(archive, self.overrides_folder.as_posix())
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

    def generate_meta_data(self, side: Side, archive: ZipFile, minecraft_additions: dict[str, Any]) -> None:
        """
        Generates the manifest.json and places it in the archive.

        :param side: the side of the pack
        :param archive: the zipfile
        :param minecraft_additions: fields supplied by the selected lwjgl3ify CurseForge artifact
        :return: None
        """

        metadata: dict[str, Any] = {
            "minecraft": {
                "version": "1.7.10",
                "modLoaders": [{"id": "forge-10.13.4.1614", "primary": True}],
                "recommendedRam": 4096,
                **minecraft_additions,
            },
            "manifestType": "minecraftModpack",
            "manifestVersion": 1,
            "name": "GT New Horizons",
            "version": self.release.version,
            "author": "DreamMasterXXL",
            "overrides": "overrides",
            "image": self.profile_image.as_posix(),
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
                        "isLocked": False,
                    }
                )

        metadata["files"] = files

        archive.writestr(str(self.manifest_json), dumps(metadata, indent=2))

        if self.task_progress_callback is not None:
            self.task_progress_callback(self.delta_progress, f"adding {self.manifest_json} to the archive")
