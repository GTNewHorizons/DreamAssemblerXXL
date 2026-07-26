import asyncio
from typing import Any, Callable, Coroutine, Optional

from colorama import Fore

from daxxl.defs import RED_CROSS, ModSource
from daxxl.gtnh_logger import get_logger
from daxxl.models.available_assets import AvailableAssets
from daxxl.models.versionable import Versionable
from daxxl.services.asset_service import AssetService
from daxxl.services.github_client import GitHubClient

log = get_logger(__name__)


class AssetUpdateOrchestrator:
    def __init__(self, gh_client: GitHubClient, asset_service: AssetService, assets: AvailableAssets) -> None:
        self.gh_client = gh_client
        self.asset_service = asset_service
        self.assets = assets

    @staticmethod
    async def _run_safely(name: str, coro: "Coroutine[Any, Any, bool]", errors: list[str]) -> bool:
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
        release_version: str | None = None,
    ) -> list[str]:
        """
        :return: error messages for assets that failed to update, empty if all succeeded
        """
        updated, errors = await self.update_available_assets(
            mods_to_update,
            progress_callback=progress_callback,
            global_progress_callback=global_progress_callback,
            release_version=release_version,
        )
        if updated:
            self.asset_service.save_assets()
        return errors

    async def update_available_assets(
        self,
        assets_to_update: list[str] | None = None,
        progress_callback: Optional[Callable[[float, str], None]] = None,
        global_progress_callback: Optional[Callable[[str], None]] = None,
        release_version: str | None = None,
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
                    progress_callback(delta_progress, "")
                continue # skipped mod is part of the process so we update the progress

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
                    asset.name, self.asset_service.update_versionable_from_repo(asset, repo, release_version), errors
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
