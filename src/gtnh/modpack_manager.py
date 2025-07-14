import asyncio
import glob
import json
import os
import re
import shutil
from collections import defaultdict
from pathlib import Path
from typing import Callable, List, Optional, Set, Tuple

from cache import AsyncLRU
from colorama import Fore, Style
from gidgethub import BadRequest
from gidgethub.httpx import GitHubAPI
from httpx import AsyncClient, HTTPStatusError

from gtnh.assembler.changelog import ChangelogCollection, ChangelogEntry

try:
    from packaging.version import LegacyVersion  # type: ignore
except ImportError:
    from packaging_legacy.version import LegacyVersion

from retry import retry

from gtnh.assembler.downloader import get_asset_version_cache_location
from gtnh.assembler.exclusions import Exclusions
from gtnh.defs import (
    AVAILABLE_ASSETS_FILE,
    BLACKLISTED_REPOS_FILE,
    GREEN_CHECK,
    GTNH_MODPACK_FILE,
    INPLACE_PINNED_FILE,
    LOCAL_EXCLUDES_FILE,
    MAVEN_BASE_URL,
    OTHER,
    RED_CROSS,
    RELEASE_MANIFEST_DIR,
    ROOT_DIR,
    UNKNOWN,
    ModSource,
    Side,
)
from gtnh.exceptions import (
    InvalidDailyIdException,
    InvalidExperimentalIdException,
    InvalidReleaseException,
    RepoNotFoundException,
)
from gtnh.github.uri import latest_release_uri, org_repos_uri, repo_releases_uri, repo_uri
from gtnh.gtnh_logger import get_logger
from gtnh.models.available_assets import AvailableAssets
from gtnh.models.gtnh_config import CONFIG_REPO_NAME
from gtnh.models.gtnh_modpack import GTNHModpack
from gtnh.models.gtnh_release import GTNHRelease, load_release, save_release
from gtnh.models.gtnh_version import GTNHVersion, version_from_release
from gtnh.models.mod_info import GTNHModInfo
from gtnh.models.mod_version_info import ModVersionInfo
from gtnh.models.versionable import Versionable, version_is_newer, version_is_older, version_sort_key
from gtnh.utils import AttributeDict, get_github_token, index

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

    @AsyncLRU(maxsize=None)  # type: ignore
    async def get_all_repos(self) -> dict[str, AttributeDict]:
        return {r["name"]: AttributeDict(r) async for r in self.gh.getiter(org_repos_uri(self.org))}

    @AsyncLRU(maxsize=None)  # type: ignore
    async def get_repo(self, name: str) -> AttributeDict:
        try:
            return AttributeDict(await self.gh.getitem(repo_uri(self.org, name)))
        except Exception:
            raise RepoNotFoundException(f"Repo not Found {name}")

    def add_release(self, release: GTNHRelease, update: bool = False) -> bool:
        log.info(f"Adding Release `{Fore.GREEN}{release.version}{Fore.RESET}`")
        if not update and release.version in self.mod_pack.releases:
            log.error(f"Release `{Fore.RED}{release.version}{Fore.RESET} already exists, and update was not specified!")
            return False
        self.mod_pack.releases.add(release.version)
        return save_release(release, update=update)

    def get_release(self, release_name: str) -> GTNHRelease | None:
        if release_name in self.mod_pack.releases:
            return load_release(release_name)

        return None

    async def update_all(
        self,
        mods_to_update: list[str] | None = None,
        progress_callback: Optional[Callable[[float, str], None]] = None,
        global_progress_callback: Optional[Callable[[str], None]] = None,
        releaseVersion: str | None = None,
    ) -> None:
        if await self.update_available_assets(
            mods_to_update,
            progress_callback=progress_callback,
            global_progress_callback=global_progress_callback,
            releaseVersion=releaseVersion,
        ):
            self.save_assets()

    async def update_available_assets(
        self,
        assets_to_update: list[str] | None = None,
        progress_callback: Optional[Callable[[float, str], None]] = None,
        global_progress_callback: Optional[Callable[[str], None]] = None,
        releaseVersion: str | None = None,
    ) -> bool:

        if global_progress_callback is not None:
            global_progress_callback("Downloading data from Github")

        all_repos = await self.get_all_repos()

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
            tasks.append(self.update_versionable_from_repo(asset, repo, releaseVersion))

        # update translation manually because version check cannot work on this repo given the nature of the releases
        self.assets.translations.versions = []
        self.assets.translations.latest_version = ""
        tasks.append(
            self.update_translations_from_repo(self.assets.translations, all_repos.get(self.assets.translations.name))
        )

        gathered = await asyncio.gather(*tasks, return_exceptions=True)
        return any([r for r in gathered])

    async def update_curse_assets(self, assets_to_update: list[str] | None = None) -> bool:
        # curseforge_assets = [m for m in self.assets.external_mods if m.source == ModSource.curse]
        #
        # to_update = []
        # for asset in curseforge_assets:
        #     if (assets_to_update and asset.name not in assets_to_update) or (asset.source != ModSource.curse):
        #         continue
        #     to_update.append(asset)
        #
        # return await self.update_assets_from_curse(to_update)

        raise NotImplementedError("Not currently implemented")

    async def update_assets_from_curse(self, assets: list[GTNHModInfo]) -> bool:
        # return False
        raise NotImplementedError("Not currently implemented")

    async def update_versionable_from_repo(
        self, versionable: Versionable, repo: AttributeDict, releaseVersion: str | None = None
    ) -> bool:
        """
        Attempt to update a versionable asset from a github repository.
        :param versionable: The asset to check for update
        :param repo: The repo corresponding to the asset
        :return: True if the asset, or any releases were updated; False otherwise
        """
        version_updated = False
        versionable_updated = False
        version_outdated = False
        log.debug(
            f"Checking {Fore.CYAN}{versionable.name}:{Fore.YELLOW}{versionable.latest_version}{Fore.RESET} for updates"
        )

        if releaseVersion == "daily":
            if isinstance(versionable, GTNHModInfo):
                await self.update_github_mod_from_repo(versionable, repo)
            await self.update_versions_from_repo(versionable, repo, releaseVersion=releaseVersion)

            compareVersions = versionable.versions.copy()

            versionable.latest_version = next(
                (
                    version.version_tag
                    for version in sorted(compareVersions, key=version_sort_key, reverse=True)
                    if not version.version_tag.endswith("-pre")
                ),
                "<unknown>",
            )

            return True

        latest_release = await self.get_latest_github_release(repo)

        latest_version = latest_release.tag_name if latest_release else "<unknown>"

        if version_is_newer(latest_version, versionable.latest_version):
            # Candidate update found
            version_updated = True
            log.debug(
                f"Found candidate newer version for mod {Fore.CYAN}{versionable.name}:{Fore.YELLOW}{latest_version}"
                f"{Fore.RESET}"
            )
        elif version_is_older(latest_version, versionable.latest_version):
            log.warn(
                f"Latest release by date for mod {Fore.CYAN}{versionable.name}:{Fore.RED}{latest_version}"
                f"{Fore.RESET} is LOWER than the current latest release per DreamAssembler: "
                f"{Fore.RED}{versionable.latest_version}{Fore.RESET}"
            )
            version_outdated = True
            versionable.needs_attention = True

        if isinstance(versionable, GTNHModInfo):
            versionable_updated |= await self.update_github_mod_from_repo(versionable, repo)

        # Versionable
        if version_updated or not versionable.versions:
            versionable_updated |= await self.update_versions_from_repo(
                versionable, repo, releaseVersion=releaseVersion
            )

        if versionable_updated:
            self.needs_attention = False
            log.debug(f"Updated {Fore.CYAN}{versionable.name}{Fore.RESET}!")

        return versionable_updated or version_outdated  # If outdated we've flagged it and want to save the asset

    async def update_github_mod_from_repo(self, mod: GTNHModInfo, repo: AttributeDict) -> bool:
        """
        Additional updates only applicable to a mod
        :param mod: The mod to check for update
        :param repo: The repo corresonding to the mod
        :return: True if the mod, or any releases were updated
        """
        mod_updated = False
        if mod.license in [UNKNOWN, OTHER]:
            mod_license = await self.get_license_from_repo(repo)
            if mod_license is not None:
                log.info(f"Updated License: {mod_license}")
                mod.license = mod_license
                mod_updated = True

        if mod.repo_url is None:
            repo_url = repo.get("html_url")
            if repo_url:
                mod.repo_url = repo_url
                log.info(f"Updated Repo URL: {mod.repo_url}")
                mod_updated = True

        if mod.maven is None:
            maven = await self.get_maven(mod.name)
            if maven:
                mod.maven = maven
                log.debug(f"Updated Maven: {mod.maven}")
                mod_updated = True

        if mod.private != repo.get("private"):
            mod.private = bool(repo.get("private"))
            log.info(f"Updated Private Repo Status: {mod.private}")
            mod_updated = True

        return mod_updated

    async def update_translations_from_repo(self, versionable: Versionable, repo: AttributeDict) -> bool:
        log.debug(f"Checking {Fore.CYAN}{versionable.name}{Fore.RESET} for updates")

        await self.update_versions_from_repo(versionable, repo, for_translation=True)

        self.needs_attention = False
        log.debug(f"Updated {Fore.CYAN}{versionable.name}{Fore.RESET}!")

        return True

    async def get_latest_github_release(self, repo: AttributeDict | str) -> AttributeDict | None:
        if isinstance(repo, str):
            try:
                latest_release = AttributeDict(await self.gh.getitem(latest_release_uri(self.org, repo)))
            except BadRequest:
                log.error(f"{Fore.RED}No latest release found for {Fore.CYAN}{repo}{Style.RESET_ALL}")
                latest_release = None
        else:
            try:
                latest_release = AttributeDict(await self.gh.getitem(latest_release_uri(self.org, repo.name)))
            except BadRequest:
                log.error(f"{Fore.RED}No latest release found for {Fore.CYAN}{repo.get('name')}{Style.RESET_ALL}")
                latest_release = None

        return latest_release

    async def update_versions_from_repo(
        self, asset: Versionable, repo: AttributeDict, for_translation: bool = False, releaseVersion: str | None = None
    ) -> bool:
        releases = [AttributeDict(r) async for r in self.gh.getiter(repo_releases_uri(self.org, repo.name))]
        if for_translation:
            releases = [r for r in releases if r.tag_name.endswith("-latest")]

        if releaseVersion == "daily":
            releases = [r for r in releases if not r.tag_name.endswith("-pre")]
            # if latest version is a -pre release, nuke it and start from scratch
            if asset.latest_version.endswith("-pre"):
                log.info("-pre latest version detected in daily run, reseting it to get latest")
                asset.latest_version = "0.0.0-pre"

        old_latest_version = asset.latest_version
        # Sorted releases, newest version first
        sorted_releases: List[AttributeDict] = sorted(releases, key=lambda r: LegacyVersion(r.tag_name), reverse=True)  # type: ignore
        version_updated = False

        asset.versions = sorted(asset.versions, key=version_sort_key)

        for release in sorted_releases:
            if asset.has_version(release.tag_name):
                if for_translation:
                    # Just skip it if we find a duplicate translation release, don't bail entirely
                    continue
                if release.tag_name == old_latest_version:
                    # Hit the old latest version, no more newer releases
                    break

            version = version_from_release(release, asset.type)
            if not version:
                continue

            if for_translation:
                log.info(
                    f"Updating version for `{Fore.CYAN}{asset.name}{Fore.RESET}` -> "
                    f"{Fore.GREEN}{version.version_tag}{Style.RESET_ALL}"
                )
                asset.latest_version = version.version_tag
            elif version_is_newer(version.version_tag, asset.latest_version):
                log.info(
                    f"Updating latest version for `{Fore.CYAN}{asset.name}{Fore.RESET}` "
                    f"{Style.DIM}{Fore.GREEN}{asset.latest_version}{Style.RESET_ALL} -> "
                    f"{Fore.GREEN}{version.version_tag}{Style.RESET_ALL}"
                )
                asset.latest_version = version.version_tag

            if not asset.has_version(release.tag_name):
                log.debug(
                    f"Adding version {Fore.GREEN}`{version.version_tag}`{Style.RESET_ALL} for asset "
                    f"`{Fore.CYAN}{asset.name}{Fore.RESET}`"
                )
                asset.add_version(version)

            version_updated = True

        return version_updated

    async def get_license_from_repo(self, repo: AttributeDict, allow_fallback: bool = True) -> str | None:
        """
        Attempt to find a license for a mod, based on the repository; falling back to some manually collected licenses
        :param repo: Github Repository
        :return: License `str`
        """
        mod_license = None
        try:
            repo_license = repo.license
            if repo_license:
                mod_license = repo_license.name
                log.info(f"Found license `{Fore.YELLOW}{mod_license}{Fore.RESET}` from repo")
        except BadRequest:
            log.warn("No license found from repo")

        if mod_license in [None, UNKNOWN, OTHER] and allow_fallback:
            with open(ROOT_DIR / "licenses_from_boubou.json") as f:
                manual_licenses = json.loads(f.read())
                by_url = {v["url"]: v.get("license", None) for v in manual_licenses.values()}
                mod_license = by_url.get(repo.html_url, None)
                if mod_license:
                    log.info(f"Found fallback license {Fore.YELLOW}{mod_license}{Fore.RESET}.")

        if not mod_license:
            log.warn("No license found!")
            mod_license = "All Rights Reserved (fallback)"

        return mod_license

    async def get_maven(self, mod_name: str) -> str | None:
        """
        Get the maven URL for a `mod_name`, ensuring it exists
        :param mod_name: Mod Name
        :return: Maven URL, if found
        """
        maven_url = MAVEN_BASE_URL + mod_name + "/"
        response = await self.client.head(maven_url, follow_redirects=True)

        if response.status_code == 200:
            return maven_url
        elif response.status_code >= 500:
            raise Exception(f"Maven unreachable status: {response.status_code}")
        return None

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
    ) -> GTNHRelease:
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

        :return: The generated release
        """
        if update_available:
            log.info("Updating assets")
            await self.update_all(
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

                override = overrides and overrides.get(mod.name)
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

        return GTNHRelease(
            version=version,
            config=config,
            github_mods=github_mods,
            external_mods=external_mods,
            last_version=last_version or existing_release.last_version,
        )

    def delete_release(self, release_name: str) -> None:
        release = self.get_release(release_name)
        if release:
            manifest_path = RELEASE_MANIFEST_DIR / (release.version + ".json")
            manifest_path.unlink(missing_ok=True)  # file deletion
            self.mod_pack.releases.remove(release_name)
            self.save_modpack()

    async def add_github_mod(self, name: str) -> GTNHModInfo | None:
        """
        Attempts to add a mod from a github repo
        :param name: Name of the github repo
        :return: The ModInfo, if any, that was created
        """
        log.info(f"Trying to add `{name}`.")

        new_repo = await self.get_repo(name)
        if self.assets.has_mod(new_repo.name):
            log.debug(f"Mod `{name}` already exists.")
            return None

        new_mod = await self.mod_from_repo(new_repo)
        self.assets.add_mod(new_mod)

        log.info(f"Successfully added {name}!")
        self.save_assets()
        return new_mod

    async def delete_mod(self, name: str) -> bool:
        """
        Attempts to delete a mod from the assets.

        :param name: the name of the repository/mod
        :return: true if the repo has been deleted from assets
        """
        log.info(f"Trying to delete `{name}`.")

        if not self.assets.has_mod(name):
            log.warn(f"Mod `{name}` is not present in the assets.")
            return False

        mod_index: int = 0

        for i, mod in enumerate(self.assets.mods):
            if mod.name == name:
                mod_index = i
                break

        del self.assets.mods[mod_index]
        self.assets.refresh_modmap()
        self.save_assets()

        log.info(f"Successfully deleted {name}!")
        return True

    async def regen_github_assets(self, callback: Optional[Callable[[float, str], None]] = None) -> None:
        log.debug("refreshing all the github mods")
        repo_names = [mod.name for mod in self.assets.mods if mod.source == ModSource.github]
        delta_progress: float = 100 / len(repo_names)
        for repo_name in repo_names:
            await self.regen_github_repo_asset(repo_name, callback=callback, delta_progress=delta_progress)

    async def regen_github_repo_asset(
        self,
        repo_name: str,
        callback: Optional[Callable[[float, str], None]] = None,
        delta_progress: Optional[float] = None,
    ) -> None:

        if callback is not None and delta_progress is not None:
            callback(delta_progress, f"regenerating assets for {repo_name}")
        side: Side
        try:
            side = self.assets.get_mod(repo_name).side
        except Exception:
            side = Side.BOTH

        await self.delete_mod(repo_name)
        await self.add_github_mod(repo_name)
        if side != Side.BOTH:  # by default the side is set to BOTH
            self.set_mod_side(repo_name, side)
        self.save_assets()

    async def regen_config_assets(self) -> None:
        self.assets.config.versions = []
        self.assets.config.latest_version = "0.0.0"
        await self.update_versionable_from_repo(self.assets.config, await self.get_repo(self.assets.config.name))
        self.save_assets()

    async def regen_translation_assets(self) -> None:
        self.assets.translations.versions = []
        self.assets.translations.latest_version = ""
        await self.update_translations_from_repo(
            self.assets.translations, await self.get_repo(self.assets.translations.name)
        )
        self.save_assets()

    async def mod_from_repo(self, repo: AttributeDict, side: Side = Side.BOTH) -> GTNHModInfo:
        try:
            latest_release = await self.get_latest_github_release(repo)
            latest_version = latest_release.tag_name if latest_release else "<unknown>"
        except Exception:
            latest_version = "<unknown>"

        mod = GTNHModInfo(
            name=repo.name,
            license=await self.get_license_from_repo(repo),
            repo_url=repo.html_url,
            maven=await self.get_maven(repo.name),
            side=side,
            latest_version=latest_version,
            private=repo.private,
        )

        await self.update_versions_from_repo(mod, repo)

        mod.latest_version = latest_version

        return mod

    def load_assets(self) -> AvailableAssets:
        """
        Load the Available Mods manifest
        """
        log.debug(f"Loading mods from {self.gtnh_asset_manifest_path}")
        with open(self.gtnh_asset_manifest_path, encoding="utf-8") as f:
            return AvailableAssets.parse_raw(f.read())

    def get_experimental_count(self) -> int:
        """
        Return the current experimental count.

        Returns
        -------
        int: The current experimental count.
        """
        return self.assets.latest_experimental

    def set_experimental_id(self, id: int) -> None:
        """
        Set the experimental id to a specific number. Has to be greater than the last experimental id.

        Returns
        -------
        None
        """
        latest_id = self.assets.latest_experimental
        if id > latest_id:
            self.assets.latest_experimental = id
        else:
            raise InvalidExperimentalIdException(
                f"Cannot set new experimental id to {id}, needs to be greater than latest experimental count {latest_id}"
            )

    def increment_experimental_count(self) -> None:
        """
        Increment the experimental count.

        Returns
        -------
        None
        """
        self.assets.latest_experimental += 1
        self.save_assets()

    def set_last_successful_experimental_id(self, id: int) -> None:
        """
        Set the last successful experimental id.

        Parameters
        ----------
        id: int
            The last successful experimental id.

        Returns
        -------
        None
        """
        self.assets.latest_successful_experimental = id
        self.save_assets()
        log.info(f"last successful build set to {id}")

    def get_last_successful_experimental(self) -> int:
        """
        get the last successful experimental id.

        Returns
        -------
        int
            The last successful experimental id.
        """
        return self.assets.latest_successful_experimental

    def get_daily_count(self) -> int:
        """
        Return the current daily count.

        Returns
        -------
        int: The current daily count.
        """
        return self.assets.latest_daily

    def set_daily_id(self, id: int) -> None:
        """
        Set the daily id to a specific number. Has to be greater than the last daily id.

        Returns
        -------
        None
        """
        latest_id = self.assets.latest_daily
        if id > latest_id:
            self.assets.latest_daily = id
        else:
            raise InvalidDailyIdException(
                f"Cannot set new daily id to {id}, needs to be greater than latest daily count {latest_id}"
            )

    def increment_daily_count(self) -> None:
        """
        Increment the daily count.

        Returns
        -------
        None
        """
        self.assets.latest_daily += 1
        self.save_assets()

    def set_last_successful_daily_id(self, id: int) -> None:
        """
        Set the last successful daily id.

        Parameters
        ----------
        id: int
            The last successful daily id.

        Returns
        -------
        None
        """
        self.assets.latest_successful_daily = id
        self.save_assets()
        log.info(f"last successful build set to {id}")

    def get_last_successful_daily(self) -> int:
        """
        get the last successful daily id.

        Returns
        -------
        int
            The last successful daily id.
        """
        return self.assets.latest_successful_daily

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
            with open(self.modpack_manifest_path, "w", encoding="utf-8") as f:
                f.write(dumped)
        else:
            log.error("Save aborted, empty save result")

    def save_assets(self) -> None:
        """
        Saves the Available Mods Manifest
        """
        log.debug(f"Saving assets to from {self.gtnh_asset_manifest_path}")
        dumped = self.assets.json(exclude={"_modmap"}, exclude_unset=True, exclude_none=True)
        if dumped:
            with open(self.gtnh_asset_manifest_path, "w", encoding="utf-8") as f:
                f.write(dumped)
        else:
            log.error("Save aborted, empty save result")

    def load_blacklisted_repos(self) -> set[str]:
        with open(self.repo_blacklist_path) as f:
            return set(json.loads(f.read()))

    async def get_missing_repos(self) -> set[str]:
        """
        Return the list of mod repositories that are on github, not blacklisted, and not included in github_mods
        :param all_repos: A dictionary of [repo_name, Repository]
        :return: Set of repo names missing
        """
        all_repo_names = set((await self.get_all_repos()).keys())
        all_github_mod_names = set(self.assets._modmap.keys())
        config_repo = CONFIG_REPO_NAME
        return all_repo_names - all_github_mod_names - self.blacklisted_repos - {config_repo}

    def get_missing_mavens(self) -> set[str]:
        """
        Return the list of github mods that are missing a maven
        :return: Set of repo anmes missing mavens
        """
        all_github_mod_names = set(k for k, v in self.assets._modmap.items() if v.maven is None)

        return all_github_mod_names

    @property
    def gtnh_asset_manifest_path(self) -> Path:
        """
        Helper property for the available mods manifest file location
        """
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

    @retry(delay=5, tries=3)
    async def download_asset(
        self,
        asset: Versionable,
        asset_version: str | None = None,
        is_github: bool = False,
        download_callback: Optional[Callable[[str], None]] = None,
        error_callback: Optional[Callable[[str], None]] = None,
        force_redownload: bool = False,
    ) -> Path | None:
        if asset_version is None:
            asset_version = asset.latest_version

        type = "Github" if is_github else "External"
        version = asset.get_version(asset_version)
        if not version or not version.filename or not version.download_url:
            log.error(
                f"{RED_CROSS} {Fore.RED}Version `{Fore.YELLOW}{asset_version}{Fore.RED}` not found for {type} Asset "
                f"`{Fore.CYAN}{asset.name}{Fore.RED}`{Fore.RESET}"
            )
            if error_callback:
                error_callback(f"Version `{asset_version}` not found for {type} Asset `{asset.name}`")
            return None

        private_repo = f" {Fore.MAGENTA}<PRIVATE REPO>{Fore.RESET}" if asset.private else ""

        log.debug(
            f"Downloading {type} Asset `{Fore.CYAN}{asset.name}:{Fore.YELLOW}{asset_version}{Fore.RESET}` from "
            f"{version.browser_download_url}{private_repo}"
        )

        files_to_download = [(get_asset_version_cache_location(asset, version), version.download_url)]
        for extra_asset in version.extra_assets:
            if extra_asset.download_url is not None:
                files_to_download.append(
                    (get_asset_version_cache_location(asset, version, extra_asset.filename), extra_asset.download_url)
                )

        for mod_filename, download_url in files_to_download:
            if os.path.exists(mod_filename) and not force_redownload:
                log.debug(f"{Fore.YELLOW}Skipping re-redownload of {mod_filename}{Fore.RESET}")
                if download_callback:
                    download_callback(str(mod_filename.name))
                continue

            headers = {"Accept": "application/octet-stream"}
            if is_github:
                headers |= {"Authorization": f"token {get_github_token()}"}

            async with self.client.stream(url=download_url, headers=headers, method="GET", follow_redirects=True) as r:
                try:
                    r.raise_for_status()
                    with open(mod_filename, "wb") as f:
                        async for chunk in r.aiter_bytes(chunk_size=8192):
                            f.write(chunk)
                    log.info(f"{GREEN_CHECK} Download successful `{mod_filename}`")
                except HTTPStatusError as e:
                    log.error(
                        f"{RED_CROSS} {Fore.RED}The following HTTP error while downloading`{Fore.YELLOW}{asset_version}"
                        f"{Fore.RED}` while downloading {Fore.CYAN}{mod_filename.name}{Fore.RED} ({type} asset): {e}{Fore.RESET}"
                    )
                    if error_callback:
                        error_callback(
                            f"The following HTTP error while downloading`{asset_version}` while downloading{mod_filename.name}"
                            f"({type} asset): {e}"
                        )
                    return None

            if download_callback:
                download_callback(str(mod_filename.name))

        return mod_filename

    async def download_release(
        self,
        release: GTNHRelease,
        download_callback: Optional[Callable[[float, str], None]] = None,
        error_callback: Optional[Callable[[str], None]] = None,
        ignore_translations: bool = False,
    ) -> list[Path]:
        """
        method to download all the mods required for a release of the pack

        :param release: Release to download
        :param download_callback: Callable that takes a float and a string in parameters. (mainly the method to update
                                  the progress bar that takes a progress step per call and the label used to display
                                  infos to the user)
        :param error_callback: Callable that takes a string in parameters indicating error messages
        :return: a list holding all the paths to the clientside mods and a list holding all the paths to the serverside
                mod.
        """

        log.debug(f"Downloading mods for Release `{Fore.LIGHTYELLOW_EX}{release.version}{Fore.RESET}`")
        # computation of the progress per mod for the progressbar
        delta_progress = 100 / (
            len(release.github_mods) + len(release.external_mods) + len(self.assets.translations.versions) + 1
        )  # +1 for the config

        # Download Mods
        log.debug(f"Downloading {Fore.GREEN}{len(release.github_mods)}{Fore.RESET} Mod(s)")
        downloaders = []
        for is_github, mods in [(True, release.github_mods), (False, release.external_mods)]:
            for mod_name, mod_version in mods.items():
                mod = self.assets.get_mod(mod_name)
                mod_callback = (
                    lambda name: download_callback(delta_progress, f"mod {name} downloaded!")
                    if download_callback
                    else None
                )  # noqa, type: ignore
                downloaders.append(
                    self.download_asset(
                        mod,
                        mod_version.version,
                        is_github=is_github,
                        download_callback=mod_callback,
                        error_callback=error_callback,
                    )
                )

        # download the modpack configs
        config_callback = (
            lambda name: download_callback(delta_progress, f"config for release {release.version} downloaded!")
            if download_callback
            else None
        )  # noqa, type: ignore

        downloaders.append(
            self.download_asset(
                self.assets.config,
                release.config,
                is_github=True,
                download_callback=config_callback,
                error_callback=error_callback,
            )
        )

        if not ignore_translations:
            # download the translations for the pack
            translation_callback = (
                lambda name: download_callback(
                    delta_progress, f"localisation for {release.version.replace('-latest', '')} downloaded!"
                )
                if download_callback
                else None
            )  # noqa, type: ignore

            for language in self.assets.translations.versions:
                downloaders.append(
                    self.download_asset(
                        asset=self.assets.translations,
                        asset_version=language.version_tag,
                        is_github=True,
                        download_callback=translation_callback,
                        error_callback=error_callback,
                        force_redownload=True,
                    )
                )

        downloaded: list[Path] = [d for d in await asyncio.gather(*downloaders) if d is not None]

        return downloaded

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

    def get_removed_mods(self, release: GTNHRelease, previous_release: GTNHRelease) -> Set[str]:
        """
        Generate the list of removed mods between two releases.

        :returns: set[str]
        """
        removed_mods = set()
        new_mods = set()

        removed_mods |= set(previous_release.github_mods.keys() - release.github_mods.keys())
        removed_mods |= set(previous_release.external_mods.keys() - release.external_mods.keys())

        new_mods |= set(release.github_mods.keys() - previous_release.github_mods.keys())
        new_mods |= set(release.external_mods.keys() - previous_release.external_mods.keys())

        self.remove_false_positive_in_mod_removed(removed_mods, new_mods)
        return removed_mods

    def get_new_mods(self, release: GTNHRelease, previous_release: GTNHRelease) -> Set[str]:
        """
        Generate the list of new mods between two releases.

        :returns: set[str]
        """
        removed_mods = set()
        new_mods = set()

        removed_mods |= set(previous_release.github_mods.keys() - release.github_mods.keys())
        removed_mods |= set(previous_release.external_mods.keys() - release.external_mods.keys())

        new_mods |= set(release.github_mods.keys() - previous_release.github_mods.keys())
        new_mods |= set(release.external_mods.keys() - previous_release.external_mods.keys())

        self.remove_false_positive_in_mod_removed(removed_mods, new_mods)
        return new_mods

    def get_changed_mods(self, release: GTNHRelease, previous_release: GTNHRelease) -> Set[str]:
        """
        Generate the list of updated/added mods between two releases. If the `previous_release` is None, generate
        it for all history.

        :returns: set[str]
        """
        removed_mods = set()
        new_mods = set()

        removed_mods |= set(previous_release.github_mods.keys() - release.github_mods.keys())
        removed_mods |= set(previous_release.external_mods.keys() - release.external_mods.keys())

        new_mods |= set(release.github_mods.keys() - previous_release.github_mods.keys())
        new_mods |= set(release.external_mods.keys() - previous_release.external_mods.keys())

        self.remove_false_positive_in_mod_removed(removed_mods, new_mods)

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
            removed_mods |= set(previous_release.github_mods.keys() - release.github_mods.keys())
            removed_mods |= set(previous_release.external_mods.keys() - release.external_mods.keys())

            new_mods |= set(release.github_mods.keys() - previous_release.github_mods.keys())
            new_mods |= set(release.external_mods.keys() - previous_release.external_mods.keys())

            self.remove_false_positive_in_mod_removed(removed_mods, new_mods)

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
                oldest_side=None if is_new_mod else old_version.side,  # type: ignore
                newest_side=new_version.side,  # type: ignore
                new_mod=is_new_mod,
            )

            changes.append(mod_changelog.generate_mod_changelog())
            contributors |= mod_changelog.contributors

        changelog["credits"].append("# Credits")
        changelog["credits"].append(
            f"Special thanks to {', '.join(sorted(list(contributors), key=str.casefold))}, "
            "for their code contributions listed above, and to everyone else who helped, "
            "including all of our beta testers! <3"
        )

        return changelog

    def set_mod_side(self, mod_name: str, side: str) -> bool:
        if self.assets.has_mod(mod_name):
            mod: GTNHModInfo = self.assets.get_mod(mod_name)
        else:
            log.error(f"Release `{Fore.RED}{mod_name} is not a github mod{Fore.RESET}")
            return False

        if mod.side == side:
            log.warn(f"{Fore.YELLOW}{mod.name}'s side is already set to {side}{Fore.RESET}")
            return False

        mod.side = Side[side]
        self.save_assets()

        log.info(f"{Fore.GREEN}Side of {mod.name} has been set to {mod.side}{Fore.RESET}")
        return True

    def add_exclusion(self, side: str, exclusion: str) -> bool:
        if side == "client":
            if exclusion in self.mod_pack.client_exclusions:
                log.warn(f"{Fore.YELLOW}{exclusion} is already in {side} side exclusions{Fore.RESET}")
                return False
            else:
                self.mod_pack.client_exclusions.append(exclusion)
                log.info(f"{Fore.GREEN}{exclusion} has been added to {side} side exclusions{Fore.RESET}")
                return True

        if side == "server":
            if exclusion in self.mod_pack.server_exclusions:
                log.warn(f"{Fore.YELLOW}{exclusion} is already in {side} side exclusions{Fore.RESET}")
                return False
            else:
                self.mod_pack.server_exclusions.append(exclusion)
                log.info(f"{Fore.GREEN}{exclusion} has been added to {side} side exclusions{Fore.RESET}")
                return True
        else:
            raise ValueError(f"{side} isn't a valid side")

    def delete_exclusion(self, side: str, exclusion: str) -> bool:
        if side == "client":
            self.mod_pack.client_exclusions.sort()
            if exclusion not in self.mod_pack.client_exclusions:
                log.warn(f"{Fore.YELLOW}{exclusion} is not in {side} side exclusions{Fore.RESET}")
                return False
            else:
                position = index(self.mod_pack.client_exclusions, exclusion)
                del self.mod_pack.client_exclusions[position]
                log.info(f"{Fore.GREEN}{exclusion} has been removed from {side} side exclusions{Fore.RESET}")
                return True

        if side == "server":
            self.mod_pack.server_exclusions.sort()
            if exclusion not in self.mod_pack.server_exclusions:
                log.warn(f"{Fore.YELLOW}{exclusion} is not in {side} side exclusions{Fore.RESET}")
                return False
            else:
                position = index(self.mod_pack.server_exclusions, exclusion)
                del self.mod_pack.server_exclusions[position]
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
            mod_ver = self.assets.get_mod_and_version(mod_dict[0], mod_dict[1], side.valid_mod_sides(), mod.source)
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
