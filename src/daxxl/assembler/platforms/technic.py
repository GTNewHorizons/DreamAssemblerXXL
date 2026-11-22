import asyncio
import hashlib
import io
import json
import re
import shlex
from collections.abc import Awaitable
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from zipfile import ZIP_DEFLATED, ZIP_STORED, ZipFile, ZipInfo

from colorama import Fore

from daxxl.assembler.downloader import get_asset_version_cache_location
from daxxl.assembler.platforms.generic_assembler import GenericAssembler
from daxxl.defs import RELEASE_TECHNIC_DIR, SERVER_ASSETS_DIR, TECHNIC_JAVA_RUNTIME, TECHNIC_JAVA_VERSION, Side, technic_archive_name
from daxxl.exceptions import ReleaseNotFoundException
from daxxl.gtnh_logger import get_logger
from daxxl.models.gtnh_config import GTNHConfig
from daxxl.models.gtnh_release import GTNHRelease
from daxxl.models.gtnh_version import GTNHVersion
from daxxl.models.mod_info import GTNHModInfo
from daxxl.utils import normalize_archive_entry_permissions, normalize_archive_permissions

log = get_logger("technic process")

TECHNIC_JVM_PATCH_PATH = "patches/gtnh-jvm.json"
JAVA_ARGS_PACKAGE = "gtnh-java-args"
TECHNIC_SELECTION_PATH = "technic-selection.json"


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


def _package_path(name: str, version: str) -> str:
    slug = technify(name)
    return f"mods/{slug}/{slug}-{technify(version)}.zip"


def java_args_version(release: str, md5: str) -> str:
    # Corrected args can be registered without overwriting the version used by another build.
    return f"{technify(release)}-{md5[:12]}"


def _build_mod_zip(source: Path, destination: Path) -> None:
    with ZipFile(destination, "w", compression=ZIP_DEFLATED) as archive:
        archive.write(source, arcname=Path("mods") / source.name)
        for entry in archive.infolist():
            normalize_archive_entry_permissions(entry)


async def _wait_for_zip_io(operation: Awaitable[Any]) -> Any:
    """Keep ZIP handles and temporary files alive until workers finish, even on cancellation."""
    task = asyncio.ensure_future(operation)
    try:
        return await asyncio.shield(task)
    except asyncio.CancelledError:
        await asyncio.gather(task, return_exceptions=True)
        raise


class TechnicAssembler(GenericAssembler):
    """Assemble the packages to upload for a Technic release."""

    def get_mods(self, side: Side) -> list[tuple[GTNHModInfo, GTNHVersion]]:
        """Technic includes client/both mods for both Java 8 and Java 9+."""
        return super().get_mods(Side.CLIENT_JAVA9 if side == Side.CLIENT else side)

    def get_package_versions(self, side: Side) -> dict[str, str]:
        """Select Technic mod and config versions without opening ZIPs."""
        config, config_version = self.get_config()
        packages = [(mod.name, version.version_tag) for mod, version in self.get_mods(side)]
        packages.append((config.name, config_version.version_tag))
        versions: dict[str, str] = {}
        for name, tag in packages:
            slug = technify(name)
            if slug == JAVA_ARGS_PACKAGE or slug in versions:
                raise ValueError(f"Duplicate Technic package: {slug}")
            versions[slug] = technify(tag)
        return versions

    def _previous_release(self) -> GTNHRelease | None:
        if self.release.last_version is None:
            return None
        previous = self.context.release_service.get_release(self.release.last_version)
        if previous is None:
            raise ReleaseNotFoundException(f"Cannot assemble Technic update: previous release {self.release.last_version!r} could not be loaded.")
        return previous

    async def add_mods(self, side: Side, mods: list[tuple[GTNHModInfo, GTNHVersion]], archive: ZipFile, verbose: bool = False) -> None:

        # Bound CPU work and temporary disk usage to four packages; only one writer touches the outer ZIP.
        with TemporaryDirectory() as staging_dir:
            for start in range(0, len(mods), 4):
                batch = mods[start : start + 4]
                paths = [Path(staging_dir) / f"{index}.zip" for index in range(len(batch))]
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
                    name = _package_path(mod.name, version.version_tag)
                    await _wait_for_zip_io(asyncio.to_thread(archive.write, path, arcname=name, compress_type=ZIP_STORED))
                    path.unlink()
                    if self.task_progress_callback is not None:
                        self.task_progress_callback(self.delta_progress, f"adding mod {mod.name} : version {version.version_tag} to the archive")
                    await self.yield_to_event_loop()

    async def add_config(self, side: Side, config: tuple[GTNHConfig, GTNHVersion], archive: ZipFile, verbose: bool = False) -> None:

        modpack_config, config_version = config
        name = _package_path(modpack_config.name, config_version.version_tag)
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

    def get_archive_path(self, side: Side) -> Path:
        return RELEASE_TECHNIC_DIR / technic_archive_name(self.release.version)

    async def assemble(self, side: Side, verbose: bool = False) -> None:
        if side != Side.CLIENT:
            raise ValueError(f"Only valid side is {Side.CLIENT}, got {side}")
        selection = self.get_package_versions(side)
        previous = self._previous_release()
        previous_versions = {}
        if previous is not None:
            valid_sides = Side.CLIENT_JAVA9.valid_mod_sides()
            previous_mods = self.github_mods(valid_sides, release=previous) + self.external_mods(valid_sides, release=previous)
            previous_versions = {technify(mod.name): technify(version.version_tag) for mod, version in previous_mods}
        mods = [(mod, version) for mod, version in self.get_mods(side) if previous_versions.get(technify(mod.name)) != technify(version.version_tag)]
        config_changed = previous is None or technify(previous.config) != technify(self.release.config)
        java_args = build_java_args_package(
            (SERVER_ASSETS_DIR / "forge" / "java9args.txt").read_text(encoding="utf-8-sig"),
            await self.load_lwjgl3ify_version_json(),
        )
        java_version = java_args_version(self.release.version, hashlib.md5(java_args, usedforsecurity=False).hexdigest())
        steps = len(mods) + 1  # JVM argument package
        if config_changed:
            steps += self.get_amount_of_files_in_config(side) + self.get_amount_of_files_in_locales() + (self.changelog_path is not None)
        self.delta_progress = 100 / steps

        path = self.get_archive_path(side)
        log.info(f"Constructing Technic update at {Fore.YELLOW}{path}{Fore.RESET}")
        with TemporaryDirectory(dir=path.parent) as staging_dir:
            staged_path = Path(staging_dir) / path.name
            with ZipFile(staged_path, "w", compression=ZIP_DEFLATED) as archive:
                await self.add_mods(side, mods, archive, verbose)
                if config_changed:
                    await self.add_config(side, self.get_config(), archive, verbose)
                archive.writestr(_package_path(JAVA_ARGS_PACKAGE, java_version), java_args, compress_type=ZIP_STORED)
                archive.writestr(TECHNIC_SELECTION_PATH, json.dumps(selection, sort_keys=True))
                if self.task_progress_callback is not None:
                    self.task_progress_callback(self.delta_progress, f"Adding Java {TECHNIC_JAVA_VERSION} JVM argument package")
                await normalize_archive_permissions(archive)
            staged_path.replace(path)
