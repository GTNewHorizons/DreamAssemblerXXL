import json
from functools import cache
from pathlib import Path

from colorama import Fore
from github import Github
from github.Repository import Repository
from structlog import get_logger

from gtnh.defs import AVAILABLE_MODS_FILE, BLACKLISTED_REPOS_FILE, GTNH_MODPACK_FILE, ROOT_DIR
from gtnh.exceptions import RepoNotFoundException
from gtnh.models.available_mods import AvailableMods
from gtnh.models.gtnh_modpack import GTNHModpack
from gtnh.models.gtnh_release import GTNHRelease, load_release, save_release
from gtnh.models.mod_info import ModInfo, mod_from_repo, update_github_mod_from_repo
from gtnh.utils import get_token

log = get_logger(__name__)


class GTNHModManager:
    """
    The GTNH Mod Manager - Tracks all of the available mods
    """

    def __init__(self) -> None:
        self.mods: AvailableMods = self.load_mods()
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

    def update_available_mods(self, mods_to_update: list[str] | None = None) -> bool:
        all_repos = self.get_all_repos()
        updated = False

        for mod in self.mods.github_mods:
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

        if updated:
            self.save_mods()

        return updated

    def generate_release(self, version: str, update_available: bool = True, overrides: dict[str, str] | None = None) -> GTNHRelease:
        if update_available:
            log.info("Updating available mods")
            self.update_available_mods()

        log.info(f"Assembling release: `{Fore.GREEN}{version}{Fore.RESET}`")
        if overrides:
            log.info(f"Using overrides: `{Fore.GREEN}{overrides}{Fore.RESET}`")

        github_mods: dict[str, str] = {}
        for mod in self.mods.github_mods:
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

    def add_github_mod(self, name: str) -> ModInfo | None:
        """
        Attempts to add a mod from a github repo
        :param name: Name of the github repo
        :return: The ModInfo, if any, that was created
        """
        log.info(f"Trying to add `{name}`.")

        new_repo = self.get_repo(name)
        if self.mods.has_github_mod(new_repo.name):
            log.info(f"Mod `{name}` already exists.")
            return None

        new_mod = mod_from_repo(new_repo)
        self.mods.add_github_mod(new_mod)

        del self.mods._github_modmap

        log.info(f"Successfully added {name}!")
        return new_mod

    def update_github_mod(self, name: str) -> ModInfo | None:
        """
        Attempts to update a mod from a github repo; specifically pulling in any new releases and updating the latest release
        :param name: Name of the github repo/mod
        :return: The ModInfo, if any, that was updated
        """
        log.info(f"Trying to update `{name}`.")
        mod = self.mods.get_github_mod(name)
        if not mod:
            log.info(f"Mod `{name} not found!")
            return None

        repo = self.organization.get_repo(name)
        if not repo:
            log.info(f"Mod `{name}` was found, but not a Github Repository!?")
            return None

        update_github_mod_from_repo(mod, repo)
        return mod

    def load_mods(self) -> AvailableMods:
        """
        Load the Available Mods manifest
        """
        log.info(f"Loading mods from {self.mod_manifest_path}")
        with open(self.mod_manifest_path, encoding="utf-8") as f:
            return AvailableMods.parse_raw(f.read())

    def load_modpack(self) -> GTNHModpack:
        """
        Load the GTNH Modpack manifest
        """
        log.info(f"Loading GTNH Modpack from {self.mod_pack_manifest_path}")
        with open(self.mod_pack_manifest_path, encoding="utf-8") as f:
            return GTNHModpack.parse_raw(f.read())

    def save_mods(self) -> None:
        """
        Saves the Available Mods Manifest
        """
        log.info(f"Saving mods to from {self.mod_manifest_path}")
        dumped = self.mods.json(exclude={"_github_modmap", "_external_modmap"})
        if dumped:
            with open(self.mod_manifest_path, "w", encoding="utf-8") as f:
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
        all_github_mod_names = set(self.mods._github_modmap.keys())

        return all_repo_names - all_github_mod_names - self.blacklisted_repos

    def get_missing_mavens(self) -> set[str]:
        """
        Return the list of github mods that are missing a maven
        :return: Set of repo anmes missing mavens
        """
        all_github_mod_names = set(k for k, v in self.mods._github_modmap.items() if v.maven is None)

        return all_github_mod_names

    @property
    def mod_manifest_path(self) -> Path:
        """
        Helper property for the available mods manifest file location
        """
        return ROOT_DIR / AVAILABLE_MODS_FILE

    @property
    def mod_pack_manifest_path(self) -> Path:
        return ROOT_DIR / GTNH_MODPACK_FILE

    @property
    def repo_blacklist_path(self) -> Path:
        """
        Helper property for the blacklisted repo file location
        """
        return ROOT_DIR / BLACKLISTED_REPOS_FILE
