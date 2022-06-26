import json
from functools import cache
from pathlib import Path

from colorama import Fore
from github import Github
from github.Repository import Repository
from structlog import get_logger

from gtnh.defs import AVAILABLE_ASSETS_FILE, BLACKLISTED_REPOS_FILE, GTNH_MODPACK_FILE, ROOT_DIR
from gtnh.exceptions import RepoNotFoundException
from gtnh.models.available_assets import AvailableAssets
from gtnh.models.gtnh_config import CONFIG_REPO_NAME
from gtnh.models.gtnh_mod_info import GTNHModInfo, mod_from_repo, update_github_mod_from_repo
from gtnh.models.gtnh_modpack import GTNHModpack
from gtnh.models.gtnh_release import GTNHRelease, load_release, save_release
from gtnh.models.versionable import update_versions_from_repo, version_sort_key
from gtnh.utils import get_token

log = get_logger(__name__)

# Up Next - GT-New-Horizons-Modpack config/scripts handling


class GTNHModpackManager:
    """
    The GTNH Mod Pack Manager - Manages the GTNH Modpack
    """

    def __init__(self) -> None:
        self.assets: AvailableAssets = self.load_assets()
        self.mod_pack: GTNHModpack = self.load_modpack()
        self.blacklisted_repos = self.load_blacklisted_repos()
        self.github = Github(get_token())
        self.organization = self.github.get_organization("GTNewHorizons")

    @cache
    def get_all_repos(self) -> dict[str, Repository]:
        return {r.name: r for r in self.organization.get_repos()}

    @cache
    def get_repo(self, name: str) -> Repository:
        try:
            return self.organization.get_repo(name)
        except Exception:
            raise RepoNotFoundException(f"Repo not Found {name}")

    def add_release(self, release: GTNHRelease, update: bool = False) -> bool:
        log.info(f"Adding Release `{Fore.GREEN}{release.version}{Fore.RESET}`")
        if not update and release.version in self.mod_pack.releases:
            log.error(f"Release `{Fore.RED}{release.version}{Fore.RESET} already exists, and update was not specified!")
            return False

        self.mod_pack.releases |= {release.version}
        return save_release(release, update=update)

    def get_release(self, release_name: str) -> GTNHRelease | None:
        if release_name in self.mod_pack.releases:
            return load_release(release_name)

        log.error(f"Release `{Fore.LIGHTRED_EX}{release_name}{Fore.RESET}` not found!")
        return None

    def update_all(self, mods_to_update: list[str] | None = None) -> None:
        updated = False
        updated |= self.update_available_mods(mods_to_update)
        updated |= self.update_config()

        if updated:
            self.save_assets()

    def update_available_mods(self, mods_to_update: list[str] | None = None) -> bool:
        all_repos = self.get_all_repos()
        updated = False

        for mod in self.assets.github_mods:
            if mods_to_update and mod.name not in mods_to_update:
                continue

            repo = all_repos.get(mod.name)
            if not repo:
                log.error(f"{Fore.RED}Missing repo for {Fore.CYAN}{mod.name}{Fore.RED}, skipping update check.{Fore.RESET}")
                continue
            mod_updated = update_github_mod_from_repo(mod, repo)
            if mod_updated:
                log.info(f"Updated {Fore.CYAN}{mod.name}{Fore.RESET}!")
            updated |= mod_updated

        return updated

    def update_config(self) -> bool:
        all_repo = self.get_all_repos()
        repo = all_repo.get(self.assets.config.name)
        if not repo:
            raise Exception("GTNH Modpack Config repo not found")
        config = self.assets.config
        if not config.versions or not config.versions == sorted(config.versions, key=version_sort_key):
            update_versions_from_repo(config, repo)

        return True

    def generate_release(self, version: str, update_available: bool = True, overrides: dict[str, str] | None = None) -> GTNHRelease:
        if update_available:
            log.info("Updating assets")
            self.update_all()

        log.info(f"Assembling release: `{Fore.GREEN}{version}{Fore.RESET}`")
        if overrides:
            log.info(f"Using overrides: `{Fore.GREEN}{overrides}{Fore.RESET}`")

        github_mods: dict[str, str] = {}
        for mod in self.assets.github_mods:
            if mod.disabled:
                log.warn(f"Mod `{Fore.CYAN}{mod.name}{Fore.RESET}` is disabled, skipping")
                continue

            override = overrides and overrides.get(mod.name)
            mod_version = override if override else mod.latest_version

            if not mod.has_version(mod_version):
                log.warn(f"Version `{Fore.YELLOW}{mod_version}{Fore.RESET} not found for Mod `{Fore.CYAN}{mod.name}{Fore.RESET}`, skipping")
                continue

            overide_str = f"{Fore.RED} ** OVERRIDE **{Fore.RESET}" if override else ""
            log.info(f"Using `{Fore.CYAN}{mod.name}{Fore.RESET}:{Fore.YELLOW}{mod_version}{Fore.RESET}{overide_str}")
            github_mods[mod.name] = mod.latest_version
        external_mods: dict[str, str] = {}

        return GTNHRelease(version=version, github_mods=github_mods, external_mods=external_mods)

    def add_github_mod(self, name: str) -> GTNHModInfo | None:
        """
        Attempts to add a mod from a github repo
        :param name: Name of the github repo
        :return: The ModInfo, if any, that was created
        """
        log.info(f"Trying to add `{name}`.")

        new_repo = self.get_repo(name)
        if self.assets.has_github_mod(new_repo.name):
            log.info(f"Mod `{name}` already exists.")
            return None

        new_mod = mod_from_repo(new_repo)
        self.assets.add_github_mod(new_mod)

        del self.assets._github_modmap

        log.info(f"Successfully added {name}!")
        return new_mod

    def update_github_mod(self, name: str) -> GTNHModInfo | None:
        """
        Attempts to update a mod from a github repo; specifically pulling in any new releases and updating the latest release
        :param name: Name of the github repo/mod
        :return: The ModInfo, if any, that was updated
        """
        log.info(f"Trying to update `{name}`.")
        mod = self.assets.get_github_mod(name)
        if not mod:
            log.info(f"Mod `{name} not found!")
            return None

        repo = self.organization.get_repo(name)
        if not repo:
            log.info(f"Mod `{name}` was found, but not a Github Repository!?")
            return None

        update_github_mod_from_repo(mod, repo)
        return mod

    def load_assets(self) -> AvailableAssets:
        """
        Load the Available Mods manifest
        """
        log.info(f"Loading mods from {self.gtnh_asset_manifest_path}")
        with open(self.gtnh_asset_manifest_path, encoding="utf-8") as f:
            return AvailableAssets.parse_raw(f.read())

    def load_modpack(self) -> GTNHModpack:
        """
        Load the GTNH Modpack manifest
        """
        log.info(f"Loading GTNH Modpack from {self.modpack_manifest_path}")
        with open(self.modpack_manifest_path, encoding="utf-8") as f:
            return GTNHModpack.parse_raw(f.read())

    def save_assets(self) -> None:
        """
        Saves the Available Mods Manifest
        """
        log.info(f"Saving assets to from {self.gtnh_asset_manifest_path}")
        dumped = self.assets.json(exclude={"_github_modmap", "_external_modmap"})
        if dumped:
            with open(self.gtnh_asset_manifest_path, "w", encoding="utf-8") as f:
                f.write(dumped)
        else:
            log.error("Save aborted, empty save result")

    def load_blacklisted_repos(self) -> set[str]:
        with open(self.repo_blacklist_path) as f:
            return set(json.loads(f.read()))

    def get_missing_repos(self, all_repos: dict[str, Repository]) -> set[str]:
        """
        Return the list of mod repositories that are on github, not blacklisted, and not included in github_mods
        :param all_repos: A dictionary of [repo_name, Repository]
        :return: Set of repo names missing
        """
        all_repo_names = set(all_repos.keys())
        all_github_mod_names = set(self.assets._github_modmap.keys())
        config_repo = CONFIG_REPO_NAME
        return all_repo_names - all_github_mod_names - self.blacklisted_repos - {config_repo}

    def get_missing_mavens(self) -> set[str]:
        """
        Return the list of github mods that are missing a maven
        :return: Set of repo anmes missing mavens
        """
        all_github_mod_names = set(k for k, v in self.assets._github_modmap.items() if v.maven is None)

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
