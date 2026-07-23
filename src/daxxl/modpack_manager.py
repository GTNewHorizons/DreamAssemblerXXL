import asyncio
import glob
import json
import os
import re
import shutil
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable, Coroutine, List, Optional, Set, Tuple

from colorama import Fore
from gidgethub.httpx import GitHubAPI
from httpx import AsyncClient

from daxxl.assembler.changelog import ChangelogCollection, ChangelogEntry
from daxxl.assembler.downloader import get_asset_version_cache_location
from daxxl.assembler.exclusions import Exclusions
from daxxl.defs import (
    AVAILABLE_ASSETS_FILE,
    BLACKLISTED_REPOS_FILE,
    GTNH_MODPACK_FILE,
    INPLACE_PINNED_FILE,
    LOCAL_EXCLUDES_FILE,
    RED_CROSS,
    ROOT_DIR,
    DevRelease,
    ModSource,
    Side,
)
from daxxl.exceptions import (
    InvalidReleaseException,
    ReleaseNotFoundException,
)

from daxxl.gtnh_logger import get_logger
from daxxl.models.available_assets import AvailableAssets

from daxxl.models.gtnh_modpack import GTNHModpack
from daxxl.models.gtnh_release import GTNHRelease
from daxxl.models.gtnh_version import GTNHVersion
from daxxl.models.mod_info import GTNHModInfo
from daxxl.models.mod_version_info import ModVersionInfo
from daxxl.models.versionable import Versionable
from daxxl.services.asset_service import AssetService
from daxxl.services.counter_service import CounterService
from daxxl.services.download_service import DownloadService
from daxxl.services.github_client import GitHubClient
from daxxl.services.release_service import ReleaseService
from daxxl.utils import AttributeDict, atomic_write_text, get_github_token

log = get_logger(__name__)

# Up Next - GT-New-Horizons-Modpack config/scripts handling


class GTNHModpackManager:
    """
    The GTNH ModPack Manager - Manages the GTNH Modpack
    """

    def __init__(self, client: AsyncClient) -> None:
        self.assets: AvailableAssets = self.load_assets()
        self.mod_pack: GTNHModpack = self.load_modpack()
        self.blacklisted_repos = self.load_blacklisted_repos()
        self.org = "GTNewHorizons"
        self.client = client
        self.gh = GitHubAPI(self.client, "DreamAssemblerXXL", oauth_token=get_github_token())
        self.gh_client = GitHubClient(self.client, self.org)
        self.asset_service = AssetService(self.gh_client, self.gh, self.org, self.assets)
        self.counter = CounterService(self.assets, self.asset_service.save_assets)
        self.downloader = DownloadService(self.client, self.assets)
        self.release_service = ReleaseService(self.mod_pack)

    async def get_all_repos(self) -> dict[str, AttributeDict]:
        return await self.gh_client.get_all_repos()

    async def get_repo(self, name: str) -> AttributeDict:
        return await self.gh_client.get_repo(name)

    def add_release(self, release: GTNHRelease, update: bool = False) -> bool:
        return self.release_service.add_release(release, update)

    def get_release(self, release_name: str) -> GTNHRelease | None:
        return self.release_service.get_release(release_name)

    async def _run_safely(self, name: str, coro: "Coroutine[Any, Any, bool]", errors: list[str]) -> bool:
        """
        Await `coro`, recording an error message tagged with `name` in `errors` instead of
        letting the exception propagate out of the batch of concurrently-checked assets.

        :param name: asset name
        :param coro: the update coroutine to run
        :param errors: shared list error messages are appended to
        :return: the coroutine's result, or False if it raised
        """
        try:
            return await coro
        except Exception as error:
            message = f"Failed to update {name}: {error}"
            log.error(f"{RED_CROSS} {Fore.RED}{message}{Fore.RESET}")
            errors.append(message)
            return False

    async def update_all(
        self,
        mods_to_update: list[str] | None = None,
        progress_callback: Optional[Callable[[float, str], None]] = None,
        global_progress_callback: Optional[Callable[[str], None]] = None,
        releaseVersion: str | None = None,
    ) -> list[str]:
        """
        :return: error messages for assets that failed to update, empty if all succeeded
        """
        updated, errors = await self.update_available_assets(
            mods_to_update,
            progress_callback=progress_callback,
            global_progress_callback=global_progress_callback,
            releaseVersion=releaseVersion,
        )
        if updated:
            self.asset_service.save_assets()
        return errors

    async def update_available_assets(
        self,
        assets_to_update: list[str] | None = None,
        progress_callback: Optional[Callable[[float, str], None]] = None,
        global_progress_callback: Optional[Callable[[str], None]] = None,
        releaseVersion: str | None = None,
    ) -> tuple[bool, list[str]]:

        if global_progress_callback is not None:
            global_progress_callback("Downloading data from Github")

        all_repos = await self.gh_client.get_all_repos()

        errors: list[str] = []
        tasks = []
        to_update_from_repos: list[Versionable] = [mod for mod in self.assets.mods if mod.source == ModSource.github]
        to_update_from_repos.append(self.assets.config)

        delta_progress: float = 100 / len(to_update_from_repos)
        if global_progress_callback is not None:
            global_progress_callback("Updating assets")

        for asset in to_update_from_repos:
            if assets_to_update and asset.name not in assets_to_update:
                if progress_callback is not None:
                    progress_callback(
                        delta_progress, ""
                    )  # skipped mod is part of the process so we update the progress
                continue

            repo = all_repos.get(asset.name)

            if progress_callback is not None:
                progress_callback(delta_progress, f"updating {asset.name}")

            if not repo:
                log.error(
                    f"{Fore.RED}Missing repo for {Fore.CYAN}{asset.name}{Fore.RED}, skipping update check.{Fore.RESET}"
                )
                continue
            tasks.append(
                self._run_safely(asset.name, self.asset_service.update_versionable_from_repo(asset, repo, releaseVersion), errors)
            )

        # update translation manually because version check cannot work on this repo given the nature of the releases
        self.assets.translations.versions = []
        self.assets.translations.latest_version = ""
        tasks.append(
            self._run_safely(
                self.assets.translations.name,
                self.asset_service.update_translations_from_repo(
                    self.assets.translations, all_repos.get(self.assets.translations.name)
                ),
                errors,
            )
        )

        gathered = await asyncio.gather(*tasks, return_exceptions=True)
        return any(gathered), errors

    async def update_versionable_from_repo(
        self, versionable: Versionable, repo: AttributeDict, releaseVersion: str | None = None
    ) -> bool:
        return await self.asset_service.update_versionable_from_repo(versionable, repo, releaseVersion)

    async def update_github_mod_from_repo(self, mod: GTNHModInfo, repo: AttributeDict) -> bool:
        return await self.asset_service.update_github_mod_from_repo(mod, repo)

    async def update_translations_from_repo(self, versionable: Versionable, repo: AttributeDict) -> bool:
        return await self.asset_service.update_translations_from_repo(versionable, repo)

    async def update_versions_from_repo(
        self, asset: Versionable, repo: AttributeDict, for_translation: bool = False, releaseVersion: str | None = None
    ) -> bool:
        return await self.asset_service.update_versions_from_repo(asset, repo, for_translation, releaseVersion)

    async def get_license_from_repo(self, repo: AttributeDict, allow_fallback: bool = True) -> str | None:
        return await self.gh_client.get_license_from_repo(repo, allow_fallback=allow_fallback)

    async def get_maven(self, mod_name: str) -> str | None:
        return await self.gh_client.get_maven(mod_name)

    async def update_release(
        self,
        version: str,
        existing_release: GTNHRelease,
        update_available: bool = True,
        overrides: dict[str, str] | None = None,
        exclude: set[str] | None = None,
        new_mods: set[str] | None = None,
        last_version: str | None = None,
        progress_callback: Optional[Callable[[float, str], None]] = None,
        reset_progress_callback: Optional[Callable[[], None]] = None,
        global_progress_callback: Optional[Callable[[str], None]] = None,
    ) -> tuple[GTNHRelease, list[str]]:
        """
        Updates a release
        :param version: Version of the release we're updating to
        :param existing_release: Existing release we're updating from
        :param update_available: Should we update assets first?
        :param overrides: Overrides for (mod_name, version) instead of pulling latest
        :param exclude: List of mod names to exclude from update checks -- keep the existing version
        :param new_mods: New mods to be included in this release
        :param last_version: Optional last version - used generally when rolling a experimental forward after a new modpack release
        :param progress_callback: Optional callback to update the progress bar for the current task in the gui
        :param reset_progress_callback: Optional callback to reset the progress bar for the current task in the gui
        :param global_progress_callback: Optional callback to update the global progress bar in the gui

        :return: a tuple of (the generated release, error messages for assets that failed to update)
        """
        update_errors: list[str] = []
        if update_available:
            log.info("Updating assets")
            update_errors = await self.update_all(
                progress_callback=progress_callback,
                global_progress_callback=global_progress_callback,
                releaseVersion=version,
            )
            if reset_progress_callback is not None:
                reset_progress_callback()

            if global_progress_callback is not None:
                global_progress_callback(f"Updating `{version}` build")

        log.info(f"Assembling release: `{Fore.GREEN}{version}{Fore.RESET}`")
        if overrides:
            log.debug(f"Using overrides: `{Fore.GREEN}{overrides}{Fore.RESET}`")

        exclude = exclude or set()

        if exclude:
            log.info(f"Excluding update checks for `{Fore.GREEN}{exclude}{Fore.RESET}`")

        delta_progress: float = 100 / (1 + len(existing_release.github_mods) + len(existing_release.external_mods))

        config = self.assets.config.latest_version

        if progress_callback is not None:
            progress_callback(delta_progress, "Updating config to last version")

        github_mods: dict[str, ModVersionInfo] = {}
        external_mods: dict[str, ModVersionInfo] = {}

        def _add_mod(mod: GTNHModInfo) -> None:
            modmap = github_mods if mod.is_github() else external_mods
            modmap[mod.name] = ModVersionInfo.create(mod=mod)

        for is_github, existing_mods in [(True, existing_release.github_mods), (False, existing_release.external_mods)]:
            for mod_name, previous_version in existing_mods.items():
                if mod_name in exclude:
                    source_str = "[ Github Mod ]" if is_github else "[External Mod]"
                    log.warn(
                        f"{source_str} Mod `{Fore.CYAN}{mod_name}{Fore.RESET}` is excluded from update check, "
                        f"keeping existing version {Fore.YELLOW}{previous_version}{Fore.RESET}"
                    )
                    modmap = github_mods if is_github else external_mods
                    modmap[mod_name] = previous_version

                    if progress_callback is not None:
                        progress_callback(delta_progress, "")  # to stay synced with the progress
                    continue

                mod = self.assets.get_mod(mod_name)
                source_str = "[ Github Mod ]" if mod.is_github() else "[External Mod]"
                if mod.disabled:
                    log.warn(f"{source_str} Mod `{Fore.CYAN}{mod.name}{Fore.RESET}` is disabled, skipping")

                    if progress_callback is not None:
                        progress_callback(delta_progress, "")  # to stay synced with the progress

                    continue

                override = overrides.get(mod.name) if overrides else None
                mod_version = override if override else mod.latest_version

                if not mod.has_version(mod_version):
                    log.warn(
                        f"{source_str} Version `{Fore.YELLOW}{mod_version}{Fore.RESET} not found for Mod `{Fore.CYAN}{mod.name}"
                        f"{Fore.RESET}`, skipping"
                    )

                    if progress_callback is not None:
                        progress_callback(delta_progress, "")  # to stay synced with the progress
                    continue

                overide_str = f"{Fore.RED} ** OVERRIDE **{Fore.RESET}" if override else ""
                log.debug(
                    f"{source_str} Using `{Fore.CYAN}{mod.name}{Fore.RESET}:{Fore.YELLOW}{mod_version}{Fore.RESET}{overide_str}"
                )

                if progress_callback is not None:
                    progress_callback(delta_progress, f"Updating {mod.name}")

                _add_mod(mod)

        for mod_name in new_mods or []:
            mod = self.assets.get_mod(mod_name)
            _add_mod(mod)

        duplicate_mods = github_mods.keys() & external_mods.keys()

        if duplicate_mods:
            raise InvalidReleaseException(f"Duplicate Mods: {duplicate_mods}")

        release = GTNHRelease(
            version=version,
            config=config,
            github_mods=github_mods,
            external_mods=external_mods,
            last_version=last_version or existing_release.last_version,
        )
        return release, update_errors

    async def update_rolling_release(
        self,
        release_type: str,
        update_available: bool = True,
        progress_callback: Optional[Callable[[float, str], None]] = None,
        reset_progress_callback: Optional[Callable[[], None]] = None,
        global_progress_callback: Optional[Callable[[str], None]] = None,
    ) -> tuple[GTNHRelease, list[str]]:
        """
        :return: a tuple of (the generated release, error messages for assets that failed to update)
        """
        if release_type not in DevRelease.__members__.values():
            raise ValueError(f"Unsupported rolling release {release_type!r}")

        existing_release = self.get_release(release_type)
        if existing_release is None:
            raise ReleaseNotFoundException(f"{release_type.capitalize()} release not found")

        previous_release_name = f"previous_{release_type}"
        release, update_errors = await self.update_release(
            release_type,
            existing_release=existing_release,
            update_available=update_available,
            progress_callback=progress_callback,
            reset_progress_callback=reset_progress_callback,
            global_progress_callback=global_progress_callback,
            last_version=previous_release_name,
        )
        self.add_release(release, update=True)

        existing_release.version = previous_release_name
        self.add_release(existing_release, update=True)
        self.save_modpack()
        return release, update_errors

    def delete_release(self, release_name: str) -> None:
        self.release_service.delete_release(release_name)
        self.save_modpack()

    async def add_github_mod(self, name: str) -> GTNHModInfo | None:
        return await self.asset_service.add_github_mod(name)

    async def delete_mod(self, name: str) -> bool:
        return await self.asset_service.delete_mod(name)

    async def regen_github_assets(self, callback: Optional[Callable[[float, str], None]] = None) -> None:
        await self.asset_service.regen_github_assets(callback)

    async def regen_github_repo_asset(
        self,
        repo_name: str,
        callback: Optional[Callable[[float, str], None]] = None,
        delta_progress: Optional[float] = None,
    ) -> None:
        await self.asset_service.regen_github_repo_asset(repo_name, callback, delta_progress)

    async def regen_config_assets(self) -> None:
        await self.asset_service.regen_config_assets()

    async def regen_translation_assets(self) -> None:
        await self.asset_service.regen_translation_assets()

    async def mod_from_repo(self, repo: AttributeDict, side: Side = Side.BOTH) -> GTNHModInfo:
        return await self.asset_service.mod_from_repo(repo, side)

    def load_assets(self) -> AvailableAssets:
        return self.asset_service.load_assets()

    def get_experimental_count(self) -> int:
        return self.counter.get_experimental_count()

    def set_experimental_id(self, id: int) -> None:
        self.counter.set_experimental_id(id)

    def increment_experimental_count(self) -> None:
        self.counter.increment_experimental_count()

    def set_last_successful_experimental_id(self, id: int) -> None:
        self.counter.set_last_successful_experimental_id(id)

    def get_last_successful_experimental(self) -> int:
        return self.counter.get_last_successful_experimental()

    def get_daily_count(self) -> int:
        return self.counter.get_daily_count()

    def set_daily_id(self, id: int) -> None:
        self.counter.set_daily_id(id)

    def increment_daily_count(self) -> None:
        self.counter.increment_daily_count()

    def set_last_successful_daily_id(self, id: int) -> None:
        self.counter.set_last_successful_daily_id(id)

    def get_last_successful_daily(self) -> int:
        return self.counter.get_last_successful_daily()

    def load_modpack(self) -> GTNHModpack:
        """
        Load the GTNH Modpack manifest
        """
        log.debug(f"Loading GTNH Modpack from {self.modpack_manifest_path}")
        with open(self.modpack_manifest_path, encoding="utf-8") as f:
            return GTNHModpack.parse_raw(f.read())

    def save_modpack(self) -> None:
        """
        Save the GTNH Modpack manifest
        """
        log.debug(f"Saving modpack asset to from {self.modpack_manifest_path}")
        dumped = self.mod_pack.json(exclude_unset=True, exclude_none=True, exclude_defaults=True)
        if dumped:
            atomic_write_text(self.modpack_manifest_path, dumped)
        else:
            log.error("Save aborted, empty save result")

    def save_assets(self) -> None:
        self.asset_service.save_assets()

    def load_blacklisted_repos(self) -> set[str]:
        return self.asset_service.load_blacklisted_repos()

    async def get_missing_repos(self) -> set[str]:
        return await self.asset_service.get_missing_repos(self.blacklisted_repos)

    def get_missing_mavens(self) -> set[str]:
        return self.asset_service.get_missing_mavens()

    @property
    def gtnh_asset_manifest_path(self) -> Path:
        return ROOT_DIR / AVAILABLE_ASSETS_FILE

    @property
    def modpack_manifest_path(self) -> Path:
        return ROOT_DIR / GTNH_MODPACK_FILE

    @property
    def repo_blacklist_path(self) -> Path:
        """
        Helper property for the blacklisted repo file location
        """
        return ROOT_DIR / BLACKLISTED_REPOS_FILE

    @property
    def local_exclusions_path(self) -> Path:
        """
        Helper property for the local exclusions file location
        """
        return ROOT_DIR / LOCAL_EXCLUDES_FILE

    @property
    def inplace_pinned_mods(self) -> Path:
        """
        Helper property for the pinned file location
        """
        return ROOT_DIR / INPLACE_PINNED_FILE

    async def download_asset(
        self,
        asset: Versionable,
        asset_version: str | None = None,
        is_github: bool = False,
        download_callback: Optional[Callable[[str], None]] = None,
        error_callback: Optional[Callable[[str], None]] = None,
        force_redownload: bool = False,
    ) -> Path | None:
        return await self.downloader.download_asset(asset, asset_version, is_github, download_callback, error_callback, force_redownload)

    async def download_release(
        self,
        release: GTNHRelease,
        download_callback: Optional[Callable[[float, str], None]] = None,
        error_callback: Optional[Callable[[str], None]] = None,
        ignore_translations: bool = False,
    ) -> list[Path]:
        return await self.downloader.download_release(release, download_callback, error_callback, ignore_translations)

    @classmethod
    def remove_false_positive_in_mod_removed(cls, removed_mods: Set[str], added_mods: Set[str]) -> None:
        false_removed_mods: List[str] = []
        false_added_mods: List[str] = []
        for removed_mod in removed_mods:
            for added_mod in added_mods:
                stripped_removed_mod = "".join(filter(str.isalnum, removed_mod))
                stripped_added_mod = "".join(filter(str.isalnum, added_mod))
                if stripped_added_mod == stripped_removed_mod:
                    false_removed_mods.append(removed_mod)
                    false_added_mods.append(added_mod)
                    break
        for false_positive in false_removed_mods:
            removed_mods.remove(false_positive)

        for false_positive in false_added_mods:
            added_mods.remove(false_positive)

    @classmethod
    def _mod_additions_and_removals(
        cls, release: GTNHRelease, previous_release: GTNHRelease
    ) -> tuple[Set[str], Set[str]]:
        removed_mods = set(previous_release.github_mods) - set(release.github_mods)
        removed_mods |= set(previous_release.external_mods) - set(release.external_mods)
        new_mods = set(release.github_mods) - set(previous_release.github_mods)
        new_mods |= set(release.external_mods) - set(previous_release.external_mods)
        cls.remove_false_positive_in_mod_removed(removed_mods, new_mods)
        return removed_mods, new_mods

    def get_removed_mods(self, release: GTNHRelease, previous_release: GTNHRelease) -> Set[str]:
        """
        Generate the list of removed mods between two releases.

        :returns: set[str]
        """
        removed_mods, _ = self._mod_additions_and_removals(release, previous_release)
        return removed_mods

    def get_new_mods(self, release: GTNHRelease, previous_release: GTNHRelease) -> Set[str]:
        """
        Generate the list of new mods between two releases.

        :returns: set[str]
        """
        _, new_mods = self._mod_additions_and_removals(release, previous_release)
        return new_mods

    def get_changed_mods(self, release: GTNHRelease, previous_release: GTNHRelease) -> Set[str]:
        """
        Generate the list of updated/added mods between two releases. If the `previous_release` is None, generate
        it for all history.

        :returns: set[str]
        """
        removed_mods, new_mods = self._mod_additions_and_removals(release, previous_release)

        current_releases_github = set(release.github_mods.keys())

        current_releases_external = set(release.external_mods.keys())

        common_github_mods = current_releases_github - removed_mods - new_mods
        common_external_mods = current_releases_external - removed_mods - new_mods

        changed_github_mods = {
            x
            for x in common_github_mods
            if x in release.github_mods
            and x in previous_release.github_mods
            and release.github_mods[x].version != previous_release.github_mods[x].version
        }
        changed_external_mods = {
            x
            for x in common_external_mods
            if x in release.external_mods
            and x in previous_release.external_mods
            and release.external_mods[x].version != previous_release.external_mods[x].version
        }

        return changed_github_mods | changed_external_mods

    def generate_changelog(
        self, release: GTNHRelease, previous_release: GTNHRelease | None = None
    ) -> dict[str, list[str]]:
        """
        Generate a changelog between two releases.  If the `previous_release` is None, generate it for all of history
        :returns: dict[mod_name, list[version_changes]]
        """

        removed_mods = set()
        new_mods = set()
        version_changes: dict[str, Tuple[Optional[ModVersionInfo], ModVersionInfo]] = {}

        changelog: dict[str, list[str]] = defaultdict(list)

        contributors: Set[str] = set()
        if previous_release is not None:
            removed_mods, new_mods = self._mod_additions_and_removals(release, previous_release)

            changed_github_mods = set(release.github_mods.keys() & previous_release.github_mods.keys())
            changed_external_mods = set(release.external_mods.keys() & previous_release.external_mods.keys())

            for mod_name in changed_github_mods | changed_external_mods | new_mods:
                # looks like here there are some shenanigans happening, so i'm just going to check for mod presence before anything
                # i don't quite get what's happenning here.

                previous_source = (
                    previous_release.github_mods if mod_name in release.github_mods else previous_release.external_mods
                )
                current_source = release.github_mods if mod_name in release.github_mods else release.external_mods

                version_changes[mod_name] = (previous_source.get(mod_name, None), current_source[mod_name])
        else:
            changed_github_mods = set(release.github_mods.keys())
            changed_external_mods = set(release.external_mods.keys())

            for mod_name in changed_github_mods:
                version_changes[mod_name] = (None, release.github_mods[mod_name])

            for mod_name in changed_external_mods:
                version_changes[mod_name] = (None, release.external_mods[mod_name])

        if new_mods:
            changelog["new_mods"].append("# New Mods: ")
            changelog["new_mods"].extend([f"> * {mod_name}" for mod_name in sorted(new_mods)])

        if removed_mods:
            changelog["removed_mods"].append("# Mods Removed: ")
            changelog["removed_mods"].extend([f"> * {mod_name}" for mod_name in sorted(removed_mods)])

        # Changes
        for mod_name in sorted(version_changes.keys()):
            (old_version, new_version) = version_changes[mod_name]
            if old_version == new_version:
                continue

            mod = self.assets.get_mod(mod_name)
            mod_versions: List[GTNHVersion] = mod.get_versions(
                left=old_version.version if old_version else None, right=new_version.version
            )

            # Something bad happens if we have empty mod_versions, but better to have an improper changelog than a crash
            if not len(mod_versions):
                continue

            changes = changelog[mod_name]

            mod_version_changelogs = [
                ChangelogEntry(version=v.version_tag, changelog_str=v.changelog, prerelease=v.prerelease)
                for v in mod_versions
            ]
            is_new_mod = old_version is None
            mod_changelog = ChangelogCollection(
                pack_release_version=release.version,
                mod_name=mod_name,
                changelog_entries=mod_version_changelogs,
                oldest_side=None if is_new_mod else old_version.side,
                newest_side=new_version.side,  # type: ignore
                new_mod=is_new_mod,
            )

            changes.append(mod_changelog.generate_mod_changelog())
            contributors |= mod_changelog.contributors

        if len(contributors) > 0:
            changelog["credits"].append("# Credits")
            changelog["credits"].append(
                f"Special thanks to {', '.join(sorted(list(contributors), key=str.casefold))}, "
                "for their code contributions listed above, and to everyone else who helped, "
                "including all of our beta testers! <3"
            )

        return changelog

    def set_mod_side(self, mod_name: str, side: str) -> bool:
        return self.asset_service.set_mod_side(mod_name, side)

    def add_exclusion(self, side: Side, exclusion: str) -> bool:
        if side == Side.CLIENT:
            if exclusion in self.mod_pack.client_exclusions:
                log.warn(f"{Fore.YELLOW}{exclusion} is already in {side} side exclusions{Fore.RESET}")
                return False
            else:
                self.mod_pack.client_exclusions.append(exclusion)
                log.info(f"{Fore.GREEN}{exclusion} has been added to {side} side exclusions{Fore.RESET}")
                return True

        if side == Side.SERVER:
            if exclusion in self.mod_pack.server_exclusions:
                log.warn(f"{Fore.YELLOW}{exclusion} is already in {side} side exclusions{Fore.RESET}")
                return False
            else:
                self.mod_pack.server_exclusions.append(exclusion)
                log.info(f"{Fore.GREEN}{exclusion} has been added to {side} side exclusions{Fore.RESET}")
                return True
        else:
            raise ValueError(f"{side} isn't a valid side")

    def delete_exclusion(self, side: Side, exclusion: str) -> bool:
        if side == Side.CLIENT:
            self.mod_pack.client_exclusions.sort()
            if exclusion not in self.mod_pack.client_exclusions:
                log.warn(f"{Fore.YELLOW}{exclusion} is not in {side} side exclusions{Fore.RESET}")
                return False
            else:
                self.mod_pack.client_exclusions.remove(exclusion)
                log.info(f"{Fore.GREEN}{exclusion} has been removed from {side} side exclusions{Fore.RESET}")
                return True

        if side == Side.SERVER:
            self.mod_pack.server_exclusions.sort()
            if exclusion not in self.mod_pack.server_exclusions:
                log.warn(f"{Fore.YELLOW}{exclusion} is not in {side} side exclusions{Fore.RESET}")
                return False
            else:
                self.mod_pack.server_exclusions.remove(exclusion)
                log.info(f"{Fore.GREEN}{exclusion} has been removed from {side} side exclusions{Fore.RESET}")
                return True
        else:
            raise ValueError(f"{side} isn't a valid side")

    async def update_pack_inplace(
        self, release: GTNHRelease, side: Side, minecraft_dir: str, use_symlink: bool = False
    ) -> None:

        if not os.path.exists(minecraft_dir):
            log.error(f"{Fore.RED}Minecraft directory `{minecraft_dir}` does not exist{Fore.RESET}")
            return

        mods_dir = os.path.join(minecraft_dir, "mods")
        if not os.path.exists(mods_dir):
            log.error(f"{Fore.RED}Mods directory `{mods_dir}` does not exist{Fore.RESET}")
            return

        log.info(
            f"Updating {Fore.GREEN}{side.name}{Fore.RESET} side mods in place at {Fore.CYAN}{mods_dir}{Fore.RESET}"
        )

        exclusions = {
            Side.CLIENT: Exclusions(self.mod_pack.client_exclusions + self.mod_pack.client_java8_exclusions),
            Side.SERVER: Exclusions(self.mod_pack.server_exclusions + self.mod_pack.server_java8_exclusions),
            Side.CLIENT_JAVA9: Exclusions(self.mod_pack.client_exclusions + self.mod_pack.client_java9_exclusions),
            Side.SERVER_JAVA9: Exclusions(self.mod_pack.server_exclusions + self.mod_pack.server_java9_exclusions),
        }[side]

        if os.path.exists(self.local_exclusions_path):
            with open(self.local_exclusions_path, "r") as f:
                local_exclusions = f.read().splitlines()
        else:
            local_exclusions = []

        if os.path.exists(self.inplace_pinned_mods):
            with open(self.inplace_pinned_mods, "r") as f:
                pinned_mods = f.read().splitlines()
        else:
            pinned_mods = []

        # cache all active mods
        active_mods = glob.glob("*.jar", root_dir=mods_dir) + glob.glob("1.7.10/*.jar", root_dir=mods_dir)
        kept_mods = set()

        side_none_mods = [mod for mod in self.assets.mods if mod.side == Side.NONE]
        for mod in side_none_mods:
            for old_version in mod.versions:
                to_remove = os.path.basename(get_asset_version_cache_location(mod, old_version))
                for file in active_mods:
                    file_base = os.path.basename(file)
                    if file_base == to_remove and file_base not in kept_mods:
                        log.info(
                            f"Deleting mod with a side of NONE [{Fore.CYAN}{mod.name} - {os.path.basename(file)}{Fore.RESET}]"
                        )
                        os.remove(os.path.join(mods_dir, file))
                        active_mods.remove(file)

        for mod_dict in (release.github_mods | release.external_mods).items().__reversed__():
            mod_ver = self.assets.get_mod_and_version(mod_dict[0], mod_dict[1], side.valid_mod_sides())
            if not mod_ver:
                continue

            mod = mod_ver[0]
            version = mod_ver[1]

            if mod.name in pinned_mods:
                log.debug(f"{Fore.YELLOW}{mod.name}{Fore.RESET} is pinned, skipping")
                continue

            if mod.name in exclusions:
                log.debug(f"{Fore.YELLOW}{mod.name}{Fore.RESET} is excluded from the {side.name} side, skipping")
                continue

            # ignore mods that are excluded in the target mods directory
            if mod.name in local_exclusions:
                log.debug(f"{Fore.YELLOW}{mod.name}{Fore.RESET} is locally excluded, skipping")
                continue

            mod_cache = get_asset_version_cache_location(mod, version)
            if not mod_cache.exists():
                log.error(f"{Fore.RED}{mod_cache}{Fore.RESET} does not exist after downloading, skipping")
                continue

            # delete older versions
            for old_version in mod.versions:
                if old_version.version_tag == version.version_tag:
                    continue
                to_remove = os.path.basename(get_asset_version_cache_location(mod, old_version))
                for file in active_mods:
                    file_base = os.path.basename(file)
                    if file_base == to_remove and file_base not in kept_mods:
                        log.info(f"Deleting old version [{Fore.CYAN}{mod.name} - {os.path.basename(file)}{Fore.RESET}]")
                        os.remove(os.path.join(mods_dir, file))
                        active_mods.remove(file)

            file_name = mod_cache.name
            mod_dest = os.path.join(mods_dir, file_name)

            # delete non-matching versions to handle local builds (usually -pre, but not name changes)
            version_pattern = re.escape(file_name).replace(re.escape(version.version_tag), ".*")

            for file in active_mods:
                file_base = os.path.basename(file)
                if file_base != file_name and re.match(version_pattern, file_base) and file_base not in kept_mods:
                    log.info(f"Deleting unmatched version [{Fore.CYAN}{mod.name} - {file}{Fore.RESET}]")
                    os.remove(os.path.join(mods_dir, file))
                    active_mods.remove(file)

            kept_mods.add(file_name)

            if any(file_name == os.path.basename(file) for file in active_mods):
                log.debug(f"{Fore.YELLOW}{mod.name}{Fore.RESET} already exists in the mods directory, skipping")
                continue

            # use symlink if set and on unix, otherwise copy
            if use_symlink and os.name == "posix":
                log.info(
                    f"Symlinking [{Fore.CYAN}{mod.name}:{version.version_tag}{Fore.RESET}] to {Fore.CYAN}{mod_dest}{Fore.RESET}"
                )
                os.symlink(mod_cache, mod_dest)
            else:
                log.info(
                    f"Copying [{Fore.CYAN}{mod.name}:{version.version_tag}{Fore.RESET}] to {Fore.CYAN}{mod_dest}{Fore.RESET}"
                )
                shutil.copy(mod_cache, mod_dest)

            active_mods.append(file_name)

        log.info("Cleaning up the mods directory of excluded mods")
        # delete excluded mods from target mods directory
        for excluded_mod in local_exclusions if local_exclusions else []:
            mod = self.assets.get_mod(excluded_mod)
            if mod:
                for ver in mod.versions:
                    mod_cache = get_asset_version_cache_location(mod, ver)
                    for file in active_mods:
                        file_base = os.path.basename(file)
                        if file_base == mod_cache.name and file_base not in kept_mods:
                            log.info(f"Deleting excluded mod [{Fore.CYAN}{mod.name} - {file}{Fore.RESET}]")
                            os.remove(os.path.join(mods_dir, file))
                            active_mods.remove(file)
