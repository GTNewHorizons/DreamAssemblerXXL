import asyncio
from pathlib import Path
from typing import Any, Callable, Coroutine, Optional

from colorama import Fore
from gidgethub.httpx import GitHubAPI
from httpx import AsyncClient

from daxxl.defs import (
    AVAILABLE_ASSETS_FILE,
    BLACKLISTED_REPOS_FILE,
    GTNH_MODPACK_FILE,
    INPLACE_PINNED_FILE,
    LOCAL_EXCLUDES_FILE,
    RED_CROSS,
    ROOT_DIR,
    ModSource,
    Side,
)
from daxxl.gtnh_logger import get_logger
from daxxl.models.available_assets import AvailableAssets
from daxxl.models.gtnh_modpack import GTNHModpack
from daxxl.models.versionable import Versionable
from daxxl.services.asset_service import AssetService
from daxxl.services.comparison_service import ComparisonService
from daxxl.services.counter_service import CounterService
from daxxl.services.download_service import DownloadService
from daxxl.services.github_client import GitHubClient
from daxxl.services.release_service import ReleaseService
from daxxl.services.update_service import UpdateService
from daxxl.utils import atomic_write_text, get_github_token

log = get_logger(__name__)

# Up Next - GT-New-Horizons-Modpack config/scripts handling


class GTNHModpackManager:
    """
    The GTNH ModPack Manager - Manages the GTNH Modpack
    """

    def __init__(self, client: AsyncClient) -> None:
        self.org = "GTNewHorizons"
        self.client = client
        self.gh = GitHubAPI(self.client, "DreamAssemblerXXL", oauth_token=get_github_token())
        self.gh_client = GitHubClient(self.client, self.org)
        self.asset_service = AssetService(self.gh_client, self.gh, self.org)
        self.mod_pack: GTNHModpack = self.load_modpack()
        self.blacklisted_repos = self.asset_service.load_blacklisted_repos()
        self.counter = CounterService(self.assets, self.asset_service.save_assets)
        self.downloader = DownloadService(self.client, self.assets)
        self.release_service = ReleaseService(self.mod_pack)
        self.comparison = ComparisonService(self.assets)
        self.update_service = UpdateService(self.assets, self.release_service, self.update_all, self.save_modpack)

    @property
    def assets(self) -> AvailableAssets:
        """
        The AvailableAssets instance, owned by the AssetService.
        """
        return self.asset_service.assets

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
                self._run_safely(
                    asset.name, self.asset_service.update_versionable_from_repo(asset, repo, releaseVersion), errors
                )
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

    def delete_release(self, release_name: str) -> None:
        self.release_service.delete_release(release_name)
        self.save_modpack()

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
