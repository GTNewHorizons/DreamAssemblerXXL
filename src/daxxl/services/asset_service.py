import json
from collections.abc import Callable
from pathlib import Path

from colorama import Fore, Style
from gidgethub.httpx import GitHubAPI

from daxxl.defs import DevRelease

try:
    from packaging.version import LegacyVersion
except ImportError:
    from packaging_legacy.version import LegacyVersion

from daxxl.defs import (
    AVAILABLE_ASSETS_FILE,
    BLACKLISTED_REPOS_FILE,
    OTHER,
    ROOT_DIR,
    UNKNOWN,
    ModSource,
    Side,
)
from daxxl.github.uri import GitHubURI
from daxxl.gtnh_logger import get_logger
from daxxl.models.available_assets import AvailableAssets
from daxxl.models.gtnh_version import version_from_release
from daxxl.models.mod_info import GTNHModInfo
from daxxl.models.versionable import Versionable, full_version_refresh, version_is_newer, version_is_older, version_sort_key
from daxxl.services.github_client import GitHubClient
from daxxl.utils import AttributeDict, atomic_write_text

log = get_logger(__name__)


class AssetService:
    def __init__(self, gh_client: GitHubClient, gh: GitHubAPI, org: str) -> None:
        self.gh_client = gh_client
        self.gh = gh
        self.org = org
        self.uri = GitHubURI(org)
        self.assets = self.load_assets()

    @property
    def gtnh_asset_manifest_path(self) -> Path:
        return ROOT_DIR / AVAILABLE_ASSETS_FILE

    @property
    def repo_blacklist_path(self) -> Path:
        return ROOT_DIR / BLACKLISTED_REPOS_FILE

    def load_assets(self) -> AvailableAssets:
        """
        Load the Available Mods manifest
        """
        log.debug(f"Loading mods from {self.gtnh_asset_manifest_path}")
        with open(self.gtnh_asset_manifest_path, encoding="utf-8") as f:
            return AvailableAssets.parse_raw(f.read())

    def save_assets(self) -> None:
        """
        Saves the Available Mods Manifest
        """
        log.debug(f"Saving assets to {self.gtnh_asset_manifest_path}")
        dumped = self.assets.json(by_alias=True, exclude={"_modmap"}, exclude_unset=True, exclude_none=True)
        if dumped:
            atomic_write_text(self.gtnh_asset_manifest_path, dumped)
        else:
            log.error("Save aborted, empty save result")

    def load_blacklisted_repos(self) -> set[str]:
        with open(self.repo_blacklist_path) as f:
            return set(json.loads(f.read()))

    async def add_github_mod(self, name: str) -> GTNHModInfo | None:
        """
        Attempts to add a mod from a github repo
        :param name: Name of the github repo
        :return: The ModInfo, if any, that was created
        """
        log.info(f"Trying to add `{name}`.")

        new_repo = await self.gh_client.get_repo(name)
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

    async def regen_github_assets(self, callback: Callable[[float, str], None] | None = None) -> None:
        log.debug("refreshing all the github mods")
        repo_names = [mod.name for mod in self.assets.mods if mod.source == ModSource.github]
        delta_progress: float = 100 / len(repo_names)
        for repo_name in repo_names:
            await self.regen_github_repo_asset(repo_name, callback=callback, delta_progress=delta_progress)

    async def regen_github_repo_asset(
        self,
        repo_name: str,
        callback: Callable[[float, str], None] | None = None,
        delta_progress: float | None = None,
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
        with full_version_refresh(self.assets.config, latest_version_floor="0.0.0"):
            await self.update_versionable_from_repo(self.assets.config, await self.gh_client.get_repo(self.assets.config.name))
        self.save_assets()

    async def regen_translation_assets(self) -> None:
        with full_version_refresh(self.assets.translations):
            await self.update_translations_from_repo(self.assets.translations, await self.gh_client.get_repo(self.assets.translations.name))
        self.save_assets()

    async def mod_from_repo(self, repo: AttributeDict, side: Side = Side.BOTH) -> GTNHModInfo:
        try:
            latest_release = await self.gh_client.get_latest_github_release(repo)
            latest_version = latest_release.tag_name if latest_release else "<unknown>"
        except Exception:
            latest_version = "<unknown>"

        mod = GTNHModInfo(
            name=repo.name,
            license=await self.gh_client.get_license_from_repo(repo),
            repo_url=repo.html_url,
            maven=await self.gh_client.get_maven(repo.name),
            side=side,
            latest_version=latest_version,
            private=repo.private,
        )

        # update_versions_from_repo settles latest_version from the tags it discovers, the same way
        # the regular update path does. Forcing github's "latest release" back over it here used to
        # undo that, and pinned the mod to "<unknown>" whenever the latest release lookup failed.
        await self.update_versions_from_repo(mod, repo)

        return mod

    async def update_versionable_from_repo(self, versionable: Versionable, repo: AttributeDict, release_version: str | None = None) -> bool:
        """
        Attempt to update a versionable asset from a github repository.
        :param versionable: The asset to check for update
        :param repo: The repo corresponding to the asset
        :return: True if the asset, or any releases were updated; False otherwise
        """
        version_updated = False
        versionable_updated = False
        version_outdated = False
        log.debug(f"Checking {Fore.CYAN}{versionable.name}:{Fore.YELLOW}{versionable.latest_version}{Fore.RESET} for updates")

        if release_version == DevRelease.DAILY.value:
            if isinstance(versionable, GTNHModInfo):
                await self.update_github_mod_from_repo(versionable, repo)
            await self.update_versions_from_repo(versionable, repo, release_version=release_version)

            compare_versions = versionable.versions.copy()

            versionable.latest_version = next(
                (version.version_tag for version in sorted(compare_versions, key=version_sort_key, reverse=True) if not version.version_tag.endswith("-pre")),
                "<unknown>",
            )

            return True

        latest_release = await self.gh_client.get_latest_github_release(repo)

        latest_version = latest_release.tag_name if latest_release else "<unknown>"

        if version_is_newer(latest_version, versionable.latest_version):
            # Candidate update found
            version_updated = True
            log.debug(f"Found candidate newer version for mod {Fore.CYAN}{versionable.name}:{Fore.YELLOW}{latest_version}{Fore.RESET}")
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
            versionable_updated |= await self.update_versions_from_repo(versionable, repo, release_version=release_version)

        if versionable_updated:
            versionable.needs_attention = False
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
            mod_license = await self.gh_client.get_license_from_repo(repo)
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
            maven = await self.gh_client.get_maven(mod.name)
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

        versionable.needs_attention = False
        log.debug(f"Updated {Fore.CYAN}{versionable.name}{Fore.RESET}!")

        return True

    async def update_versions_from_repo(
        self, asset: Versionable, repo: AttributeDict, for_translation: bool = False, release_version: str | None = None
    ) -> bool:
        # dont update mods with a side of NONE
        if isinstance(asset, GTNHModInfo):
            if asset.side == Side.NONE:
                return False

        releases = [AttributeDict(r) async for r in self.gh.getiter(self.uri.releases(repo.name))]
        if for_translation:
            releases = [r for r in releases if r.tag_name.endswith("-latest")]

        # Sorted releases, newest version first
        sorted_releases: list[AttributeDict] = sorted(releases, key=lambda r: LegacyVersion(r.tag_name), reverse=True)

        if release_version == DevRelease.DAILY.value:
            sorted_releases = [r for r in sorted_releases if not r.tag_name.endswith("-pre")]
            # if latest version is a -pre release, reset to latest valid release
            if asset.latest_version.endswith("-pre"):
                if sorted_releases:
                    asset.latest_version = sorted_releases[0].tag_name
                else:
                    asset.latest_version = "0.0.0-pre"

        old_latest_version = asset.latest_version
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

            version = version_from_release(release, asset.versionable_type)
            if not version:
                continue

            if for_translation:
                log.info(f"Updating version for `{Fore.CYAN}{asset.name}{Fore.RESET}` -> {Fore.GREEN}{version.version_tag}{Style.RESET_ALL}")
                asset.latest_version = version.version_tag
            elif version_is_newer(version.version_tag, asset.latest_version):
                log.info(
                    f"Updating latest version for `{Fore.CYAN}{asset.name}{Fore.RESET}` "
                    f"{Style.DIM}{Fore.GREEN}{asset.latest_version}{Style.RESET_ALL} -> "
                    f"{Fore.GREEN}{version.version_tag}{Style.RESET_ALL}"
                )
                asset.latest_version = version.version_tag

            if not asset.has_version(release.tag_name):
                log.debug(f"Adding version {Fore.GREEN}`{version.version_tag}`{Style.RESET_ALL} for asset `{Fore.CYAN}{asset.name}{Fore.RESET}`")
                asset.add_version(version)

            version_updated = True

        return version_updated

    def set_mod_side(self, mod_name: str, side: Side) -> bool:
        if self.assets.has_mod(mod_name):
            mod: GTNHModInfo = self.assets.get_mod(mod_name)
        else:
            log.error(f"Release `{Fore.RED}{mod_name} is not a github mod{Fore.RESET}")
            return False

        if mod.side == side:
            log.warn(f"{Fore.YELLOW}{mod.name}'s side is already set to {side}{Fore.RESET}")
            return False

        mod.side = side
        self.save_assets()

        log.info(f"{Fore.GREEN}Side of {mod.name} has been set to {mod.side}{Fore.RESET}")
        return True

    async def get_missing_repos(self, blacklisted_repos: set[str]) -> set[str]:
        """
        Return the list of mod repositories that are on github, not blacklisted, and not included in github_mods
        :param all_repos: A dictionary of [repo_name, Repository]
        :return: Set of repo names missing
        """
        all_repo_names = set((await self.gh_client.get_all_repos()).keys())
        all_github_mod_names = set(self.assets._modmap.keys())
        return all_repo_names - all_github_mod_names - blacklisted_repos

    def get_missing_mavens(self) -> set[str]:
        """
        Return the list of github mods that are missing a maven
        :return: Set of repo anmes missing mavens
        """
        all_github_mod_names = set(k for k, v in self.assets._modmap.items() if v.maven is None)
        return all_github_mod_names
