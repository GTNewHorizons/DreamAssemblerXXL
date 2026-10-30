import asyncio
import io
import json
import os
import re
import shlex
import shutil
from collections.abc import Awaitable, Callable
from copy import copy
from enum import Enum
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from zipfile import ZIP_DEFLATED, ZIP_STORED, ZipFile, ZipInfo

from colorama import Fore

from daxxl.app_context import AppContext
from daxxl.assembler.downloader import get_asset_version_cache_location
from daxxl.assembler.platforms.generic_assembler import GenericAssembler
from daxxl.defs import RELEASE_TECHNIC_DIR, SERVER_ASSETS_DIR, TECHNIC_JAVA_RUNTIME, TECHNIC_JAVA_VERSION, Side
from daxxl.exceptions import ReleaseNotFoundException
from daxxl.gtnh_logger import get_logger
from daxxl.models.gtnh_config import GTNHConfig
from daxxl.models.gtnh_release import GTNHRelease
from daxxl.models.gtnh_version import GTNHVersion
from daxxl.models.mod_info import GTNHModInfo
from daxxl.utils import normalize_archive_entry_permissions, normalize_archive_permissions

log = get_logger("technic process")

TECHNIC_JVM_PATCH_PATH = "patches/gtnh-jvm.json"


def build_java_args_package(args_text: str, version_json: bytes) -> bytes:
    """Bundle the selected lwjgl3ify profile and Java 25 arguments with deterministic ZIP metadata."""
    arguments = shlex.split(args_text, comments=True)
    if not arguments:
        raise ValueError("java9args.txt contains no JVM arguments.")
    arguments = [arg for arg in arguments if arg not in {"-XX:+UseCompactObjectHeaders", "-XX:-UseCompactObjectHeaders"}]
    arguments.append("-XX:+UseCompactObjectHeaders")
    patch = {
        "formatVersion": 1,
        "uid": "gtnh.jvm",
        "name": f"GTNH Java {TECHNIC_JAVA_VERSION} arguments",
        "version": str(TECHNIC_JAVA_VERSION),
        "order": 1000,
        "javaVersion": {"component": TECHNIC_JAVA_RUNTIME, "majorVersion": TECHNIC_JAVA_VERSION},
        "+jvmArgs": arguments,
    }
    with io.BytesIO() as buffer:
        with ZipFile(buffer, "w") as archive:
            for name, data in ((TECHNIC_JVM_PATCH_PATH, json.dumps(patch, indent=2) + "\n"), ("bin/version.json", version_json)):
                entry = ZipInfo(name)  # Fixed timestamp keeps identical inputs byte-identical.
                entry.compress_type = ZIP_DEFLATED
                normalize_archive_entry_permissions(entry)
                archive.writestr(entry, data)
        return buffer.getvalue()


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


def _build_mod_zip(source: Path, destination: Path) -> None:
    with ZipFile(destination, "w", compression=ZIP_DEFLATED) as archive:
        archive.write(source, arcname=Path("mods") / source.name)
        for entry in archive.infolist():
            normalize_archive_entry_permissions(entry)


def _copy_package(source: ZipFile, destination: ZipFile, name: str) -> None:
    entry = copy(source.getinfo(name))
    entry.compress_type = ZIP_STORED
    with source.open(name) as reader, destination.open(entry, "w") as writer:
        shutil.copyfileobj(reader, writer, length=1024 * 1024)


async def _wait_for_zip_io(operation: Awaitable[Any]) -> Any:
    """Keep ZIP handles and temporary files alive until workers finish, even on cancellation."""
    task = asyncio.ensure_future(operation)
    try:
        return await asyncio.shield(task)
    except asyncio.CancelledError:
        await asyncio.gather(task, return_exceptions=True)
        raise


class TechnicAssembler(GenericAssembler):
    """
    Technic assembler class. Allows for the assembling of technic archives.
    """

    def __init__(
        self,
        context: AppContext,
        release: GTNHRelease,
        task_progress_callback: Callable[[float, str], None] | None = None,
        global_progress_callback: Callable[[float, str], None] | None = None,
        changelog_path: Path | None = None,
        current_task_reset_callback: Callable[[], None] | None = None,
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
        self._reuse_archive: ZipFile | None = None
        self._java_args_name: str | None = None

    def get_mods(self, side: Side) -> list[tuple[GTNHModInfo, GTNHVersion]]:
        """Technic includes client/both mods for both Java 8 and Java 9+."""
        return super().get_mods(Side.CLIENT_JAVA9 if side == Side.CLIENT else side)

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

        log.info(f"Constructing {Fore.YELLOW}{side}{Fore.RESET} archive at {Fore.YELLOW}'{updated_mods_archive_name}'{Fore.RESET}")

        with ZipFile(updated_mods_archive_name, "w", compression=ZIP_DEFLATED) as archive:
            log.info("Adding mods to the archive")
            await self.add_mods(side, self.differential_update(side, DifferentialUpdateMode.UPDATED_MODS), archive, verbose=verbose)
            await self.yield_to_event_loop()
            log.info("Adding config to the archive")
            await self.add_config(side, self.get_config(), archive, verbose=verbose)
            await self.yield_to_event_loop()
            log.info("Generating the readme for the modpack repo")
            self.generate_readme()
            await self.yield_to_event_loop()
            await normalize_archive_permissions(archive)
            log.info("Archive created successfully!")

        log.info(f"Constructing {Fore.YELLOW}{side}{Fore.RESET} archive at {Fore.YELLOW}'{new_mods_archive_name}'{Fore.RESET}")

        with ZipFile(new_mods_archive_name, "w", compression=ZIP_DEFLATED) as archive:
            log.info("Adding mods to the archive")
            await self.add_mods(side, self.differential_update(side, DifferentialUpdateMode.NEW_MODS), archive, verbose=verbose)
            await self.yield_to_event_loop()
            await normalize_archive_permissions(archive)
            log.info("Archive created successfully!")

        with open(removed_modlist_name, "w") as f:
            log.info("generating removed modlist")
            removed_modlist: list[tuple[GTNHModInfo, GTNHVersion]] = self.differential_update(side, DifferentialUpdateMode.REMOVED_MODS)
            f.write("\n".join([f"{mod.name}: {version.version_tag}" for (mod, version) in removed_modlist]))
            log.info("modlist created successfully!")

    def differential_update(self, side: Side, update_mode: DifferentialUpdateMode) -> list[tuple[GTNHModInfo, GTNHVersion]]:
        """
        List the mods that changed between this release and the one before it.

        :param side: the targeted side
        :param update_mode: which side of the comparison to report
        :raises ReleaseNotFoundException: if the release has no previous release to compare against
        :return: a list of couples of the mod info object and its targeted version
        """
        update_source: Callable[[GTNHRelease, GTNHRelease], set[str]]

        if update_mode == DifferentialUpdateMode.NEW_MODS:
            update_source = self.context.comparison.get_new_mods
        elif update_mode == DifferentialUpdateMode.UPDATED_MODS:
            update_source = self.context.comparison.get_changed_mods
        else:
            update_source = self.context.comparison.get_removed_mods

        last_version = self.release.last_version
        last_release = self.context.release_service.get_release(last_version) if last_version is not None else None
        if last_release is None:
            raise ReleaseNotFoundException(
                f"the partial technic archive for {self.release.version} is built against its previous release {last_version!r}, which could not be loaded"
            )

        process_release: GTNHRelease = last_release if update_mode == DifferentialUpdateMode.REMOVED_MODS else self.release

        valid_sides: set[Side] = (Side.CLIENT_JAVA9 if side == Side.CLIENT else side).valid_mod_sides()

        github_mods: list[tuple[GTNHModInfo, GTNHVersion]] = self.github_mods(valid_sides, release=process_release)
        github_mods_names = [x[0].name for x in github_mods]

        external_mods: list[tuple[GTNHModInfo, GTNHVersion]] = self.external_mods(valid_sides, release=process_release)
        external_mods_names = [x[0].name for x in external_mods]

        mods: list[tuple[GTNHModInfo, GTNHVersion]] = []
        for mod_name in update_source(self.release, last_release):
            if mod_name in github_mods_names:
                mod_index = github_mods_names.index(mod_name)
                mods.append(github_mods[mod_index])
            elif mod_name in external_mods_names:
                mod_index = external_mods_names.index(mod_name)
                mods.append(external_mods[mod_index])
            else:
                log.warn(f"Mod {mod_name} changed but is not included in the Technic {side.value} mod selection")

        return mods

    async def add_mods(self, side: Side, mods: list[tuple[GTNHModInfo, GTNHVersion]], archive: ZipFile, verbose: bool = False) -> None:

        # Bound CPU work and temporary disk usage to four packages; only one writer touches the outer ZIP.
        with TemporaryDirectory() as staging_dir:
            for start in range(0, len(mods), 4):
                batch = mods[start : start + 4]
                paths = [Path(staging_dir) / f"{index}.zip" for index in range(len(batch))]
                if self._reuse_archive is None:
                    sources = [get_asset_version_cache_location(mod, version) for mod, version in batch]
                    results = await _wait_for_zip_io(
                        asyncio.gather(
                            *(asyncio.to_thread(_build_mod_zip, source, path) for source, path in zip(sources, paths)),
                            return_exceptions=True,
                        )
                    )
                    for result in results:
                        if isinstance(result, BaseException):
                            raise result
                for (mod, version), path in zip(batch, paths):
                    name = f"mods/{technify(mod.name)}/{technify(mod.name)}-{technify(version.version_tag)}.zip"
                    if self._reuse_archive is not None:
                        await _wait_for_zip_io(asyncio.to_thread(_copy_package, self._reuse_archive, archive, name))
                    else:
                        await _wait_for_zip_io(asyncio.to_thread(archive.write, path, arcname=name, compress_type=ZIP_STORED))
                        path.unlink()
                    if self.task_progress_callback is not None:
                        self.task_progress_callback(self.delta_progress, f"adding mod {mod.name} : version {version.version_tag} to the archive")
                    await self.yield_to_event_loop()

    async def add_config(self, side: Side, config: tuple[GTNHConfig, GTNHVersion], archive: ZipFile, verbose: bool = False) -> None:

        modpack_config: GTNHConfig
        config_version: GTNHVersion | None
        modpack_config, config_version = config

        name = f"mods/{technify(modpack_config.name)}/{technify(modpack_config.name)}-{technify(config_version.version_tag)}.zip"
        if self._reuse_archive is not None:
            await _wait_for_zip_io(asyncio.to_thread(_copy_package, self._reuse_archive, archive, name))
            if self.task_progress_callback is not None:
                steps = self.get_amount_of_files_in_config(side) + self.get_amount_of_files_in_locales() + 1
                self.task_progress_callback(self.delta_progress * steps, "Reusing config package from full Technic archive")
            await self.add_java_args(archive)
            return

        config_file: Path = get_asset_version_cache_location(modpack_config, config_version)

        with TemporaryDirectory() as staging_dir:
            temp_zip_path: Path = Path(staging_dir) / "temp.zip"

            # technic wants the config as a single nested zip rather than as loose files in the archive
            with ZipFile(temp_zip_path, "w", compression=ZIP_DEFLATED) as temp_zip:
                await self._add_config_files(side, config_file, temp_zip)

                # adding the locales
                await self.add_localisation_files(temp_zip)

                self.add_changelog(temp_zip)

                await normalize_archive_permissions(temp_zip)

            # writing the config zip in the technic archive
            await _wait_for_zip_io(asyncio.to_thread(archive.write, temp_zip_path, arcname=name, compress_type=ZIP_STORED))
        await self.add_java_args(archive)

    async def load_lwjgl3ify_version_json(self) -> bytes:
        selected = next(((mod, version) for mod, version in self.get_mods(Side.CLIENT) if mod.name == "lwjgl3ify"), None)
        if selected is None:
            raise ValueError(f"Cannot assemble Technic archive: release {self.release.version} has no client lwjgl3ify mod.")
        mod, version = selected
        path = await self.context.downloader.download_version_json(mod, version)
        data = path.read_bytes()
        try:
            profile = json.loads(data)
        except (ValueError, UnicodeError):
            raise ValueError(f"lwjgl3ify {version.version_tag} has an invalid release asset version.json.") from None
        if (
            not isinstance(profile, dict)
            or not isinstance(profile.get("id"), str)
            or not profile["id"].endswith(f"-lwjgl3ify-{version.version_tag}")
            or not isinstance(profile.get("libraries"), list)
            or not isinstance(profile.get("mainClass"), str)
            or not profile["mainClass"]
        ):
            raise ValueError(f"lwjgl3ify {version.version_tag} has an incomplete or mismatched release asset version.json.")
        return data

    async def add_java_args(self, archive: ZipFile) -> None:
        if self._reuse_archive is not None:
            if self._java_args_name is None:
                raise ValueError("The current full Technic archive has no generated JVM argument package.")
            await _wait_for_zip_io(asyncio.to_thread(_copy_package, self._reuse_archive, archive, self._java_args_name))
        else:
            data = build_java_args_package(
                (SERVER_ASSETS_DIR / "forge" / "java9args.txt").read_text(encoding="utf-8-sig"),
                await self.load_lwjgl3ify_version_json(),
            )
            version = technify(self.release.version)
            self._java_args_name = f"mods/gtnh-java-args/gtnh-java-args-{version}.zip"
            archive.writestr(self._java_args_name, data, compress_type=ZIP_STORED)
        if self.task_progress_callback is not None:
            self.task_progress_callback(self.delta_progress, f"Adding Java {TECHNIC_JAVA_VERSION} JVM argument package")

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
        global_step_callback: Callable[[str], None] | None = None,
    ) -> None:
        if side != Side.CLIENT:
            raise ValueError(f"Only valid side is {Side.CLIENT}, got {side}")
        await self.load_lwjgl3ify_version_json()  # Fail before replacing existing archives if the required profile is unavailable.
        log.info(f"packing technic launcher release for {self.release.version}")
        self.delta_progress = 100 / (len(self.get_mods(side)) + self.get_amount_of_files_in_config(side) + self.get_amount_of_files_in_locales() + 2)
        await GenericAssembler.assemble(self, side, verbose)

        log.info(f"packing partial technic launcher release for {self.release.version}")
        if global_step_callback is not None:
            global_step_callback("Assembling partial Technic archive")
        if self.current_task_reset_callback is not None:
            self.current_task_reset_callback()
        self.delta_progress = 100 / (
            len(self.differential_update(side, DifferentialUpdateMode.UPDATED_MODS))
            + self.get_amount_of_files_in_config(side)
            + self.get_amount_of_files_in_locales()
            + 2  # changelog and JVM argument package
            + len(self.differential_update(side, DifferentialUpdateMode.NEW_MODS))
        )
        # Reuse only the full archive just built in this run, never a stale archive from disk.
        with ZipFile(self.get_archive_path(side)) as full_archive:
            self._reuse_archive = full_archive
            try:
                await self.partial_assemble(side, verbose)
            finally:
                self._reuse_archive = None
