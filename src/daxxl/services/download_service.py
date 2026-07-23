import asyncio
import os
from typing import Callable
from pathlib import Path
from typing import Optional

import retry
from colorama import Fore, Style
from httpx import AsyncClient, HTTPStatusError

from daxxl.assembler.downloader import get_asset_version_cache_location
from daxxl.defs import GREEN_CHECK, RED_CROSS
from daxxl.gtnh_logger import get_logger
from daxxl.models.available_assets import AvailableAssets
from daxxl.models.gtnh_release import GTNHRelease
from daxxl.models.versionable import Versionable
from daxxl.exceptions import NoModAssetFound
from daxxl.utils import get_github_token

log = get_logger(__name__)


class DownloadService:
    def __init__(self, client: AsyncClient, assets: AvailableAssets) -> None:
        self.client = client
        self.assets = assets

    @retry.retry(delay=5, tries=3)
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

            temporary = mod_filename.with_name(f"{mod_filename.name}.part")
            try:
                async with self.client.stream(
                    url=download_url, headers=headers, method="GET", follow_redirects=True
                ) as r:
                    r.raise_for_status()
                    with open(temporary, "wb") as f:
                        async for chunk in r.aiter_bytes(chunk_size=8192):
                            f.write(chunk)
                temporary.replace(mod_filename)
                log.info(f"{GREEN_CHECK} Download successful `{mod_filename}`")
            except HTTPStatusError as e:
                log.error(
                    f"{RED_CROSS} {Fore.RED}The following HTTP error while downloading`{Fore.YELLOW}{asset_version}"
                    f"{Fore.RED}` while downloading {Fore.CYAN}{mod_filename.name}{Fore.RED} ({type} asset): {e}{Fore.RESET}"
                )
                if error_callback:
                    error_callback(
                        f"The following HTTP error while downloading `{asset_version}` while downloading "
                        f"{mod_filename.name} ({type} asset): {e}"
                    )
                return None
            finally:
                temporary.unlink(missing_ok=True)

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
        release.validate_release(self.assets)
        log.debug(f"Downloading mods for Release `{Fore.LIGHTYELLOW_EX}{release.version}{Fore.RESET}`")
        errors: list[str] = []

        def report_error(message: str) -> None:
            errors.append(message)
            if error_callback:
                error_callback(message)

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

                def mod_callback(name):
                    return download_callback(delta_progress, f"mod {name} downloaded!") if download_callback else None

                downloaders.append(
                    self.download_asset(
                        mod,
                        mod_version.version,
                        is_github=is_github,
                        download_callback=mod_callback,
                        error_callback=report_error,
                    )
                )

        def config_callback(name):
            return (
                download_callback(delta_progress, f"config for release {release.version} downloaded!")
                if download_callback
                else None
            )

        # download the modpack configs
        downloaders.append(
            self.download_asset(
                self.assets.config,
                release.config,
                is_github=True,
                download_callback=config_callback,
                error_callback=report_error,
            )
        )

        if not ignore_translations:
            # download the translations for the pack
            def translation_callback(name):
                return (
                    download_callback(
                        delta_progress, f"localisation for {release.version.replace('-latest', '')} downloaded!"
                    )
                    if download_callback
                    else None
                )

            for language in self.assets.translations.versions:
                downloaders.append(
                    self.download_asset(
                        asset=self.assets.translations,
                        asset_version=language.version_tag,
                        is_github=True,
                        download_callback=translation_callback,
                        error_callback=report_error,
                        force_redownload=True,
                    )
                )

        downloaded: list[Path] = [d for d in await asyncio.gather(*downloaders) if d is not None]

        if errors:
            raise NoModAssetFound("Asset download failed:\n- " + "\n- ".join(errors))

        return downloaded
