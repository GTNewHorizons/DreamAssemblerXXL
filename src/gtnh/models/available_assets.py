import bisect
from functools import cached_property
from typing import Dict, List

from pydantic import Field
from structlog import get_logger

from gtnh.defs import ModSource, Side
from gtnh.exceptions import NoModAssetFound
from gtnh.models.base import GTNHBaseModel
from gtnh.models.gtnh_config import GTNHConfig
from gtnh.models.gtnh_version import GTNHVersion
from gtnh.models.mod_info import ExternalModInfo, GTNHModInfo

log = get_logger(__name__)


class AvailableAssets(GTNHBaseModel):
    config: GTNHConfig
    github_mods: List[GTNHModInfo] = Field(default_factory=list)
    external_mods: List[ExternalModInfo] = Field(default_factory=list)

    def add_github_mod(self, mod: GTNHModInfo) -> None:
        bisect.insort_right(self.github_mods, mod, key=self._mod_sort_key)  # type: ignore

    @staticmethod
    def _mod_sort_key(mod: GTNHModInfo) -> str:
        return mod.name.lower()

    @cached_property
    def _github_modmap(self) -> Dict[str, GTNHModInfo]:
        return {mod.name: mod for mod in self.github_mods}

    @cached_property
    def _external_modmap(self) -> Dict[str, ExternalModInfo]:
        return {mod.name: mod for mod in self.external_mods}

    def has_github_mod(self, mod_name: str) -> bool:
        return mod_name in self._github_modmap

    def has_external_mod(self, mod_name: str) -> bool:
        return mod_name in self._external_modmap

    def get_mod(self, mod_name: str) -> GTNHModInfo:
        """
        Get a mod, preferring github mods over external mods
        """
        if self.has_github_mod(mod_name):
            mod = self.get_github_mod(mod_name)
            if mod.latest_version and mod.latest_version != "<unknown>":
                return mod

        if self.has_external_mod(mod_name):
            mod = self.get_external_mod(mod_name)
            if mod.latest_version and mod.latest_version != "<unknown>":
                return mod

        raise NoModAssetFound(f"{mod_name} not found")

    def get_github_mod(self, mod_name: str) -> GTNHModInfo:
        return self._github_modmap[mod_name]

    def get_external_mod(self, mod_name: str) -> ExternalModInfo:
        return self._external_modmap[mod_name]

    def get_mod_and_version(
        self, mod_name: str, mod_version: str, valid_sides: set[Side], source: ModSource
    ) -> tuple[GTNHModInfo | ExternalModInfo, GTNHVersion] | None:
        mod = self.get_github_mod(mod_name) if source == ModSource.github else self.get_external_mod(mod_name)

        if mod.side not in valid_sides:
            return None

        version = mod.get_version(mod_version)
        if not version:
            log.error(f"Cannot find {mod_name}:{version}")
            return None

        return mod, version
