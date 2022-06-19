import json
from functools import cache
from pathlib import Path

from github import Github
from github.Repository import Repository
from structlog import get_logger

from gtnh.defs import AVAILABLE_MODS_FILE, BLACKLISTED_REPOS_FILE, ROOT_DIR
from gtnh.exceptions import RepoNotFoundException
from gtnh.models.available_mods import AvailableMods
from gtnh.models.mod_info import ModInfo, mod_from_repo, update_github_mod_from_repo
from gtnh.utils import get_token

log = get_logger(__name__)


class GTNHModManager:
    """
    The GTNH Mod Manager - Tracks all of the available mods
    """

    def __init__(self) -> None:
        self.mods: AvailableMods = self.load_mods()
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
        with open(self.mod_manifest_path) as f:
            return AvailableMods.parse_raw(f.read())

    def save_mods(self) -> None:
        """
        Saves the Available Mods Manifest
        """
        log.info(f"Saving mods to from {self.mod_manifest_path}")
        dumped = self.mods.json(exclude={"_github_modmap", "_external_modmap"})
        if dumped:
            with open(self.mod_manifest_path, "w") as f:
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
    def repo_blacklist_path(self) -> Path:
        """
        Helper property for the blacklisted repo file location
        """
        return ROOT_DIR / BLACKLISTED_REPOS_FILE
