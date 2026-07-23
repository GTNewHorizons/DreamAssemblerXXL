from typing import Awaitable, Callable, Optional

from colorama import Fore

from daxxl.defs import DevRelease
from daxxl.exceptions import InvalidReleaseException, ReleaseNotFoundException
from daxxl.gtnh_logger import get_logger
from daxxl.models.available_assets import AvailableAssets
from daxxl.models.gtnh_release import GTNHRelease
from daxxl.models.mod_info import GTNHModInfo
from daxxl.models.mod_version_info import ModVersionInfo
from daxxl.services.release_service import ReleaseService

log = get_logger(__name__)


class UpdateService:
    def __init__(
        self,
        assets: AvailableAssets,
        release_service: ReleaseService,
        update_all_callback: Callable[..., Awaitable[list[str]]],
        save_modpack_callback: Callable[[], None],
    ) -> None:
        self.assets = assets
        self.release_service = release_service
        self._update_all = update_all_callback
        self._save_modpack = save_modpack_callback

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
            update_errors = await self._update_all(
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

        existing_release = self.release_service.get_release(release_type)
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
        self.release_service.add_release(release, update=True)

        existing_release.version = previous_release_name
        self.release_service.add_release(existing_release, update=True)
        self._save_modpack()
        return release, update_errors
