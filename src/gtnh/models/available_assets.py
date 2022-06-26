import bisect
from functools import cached_property
from typing import Dict, List

from pydantic import Field

from gtnh.models.base import GTNHBaseModel
from gtnh.models.gtnh_config import GTNHConfig
from gtnh.models.gtnh_mod_info import GTNHModInfo


class AvailableAssets(GTNHBaseModel):
    config: GTNHConfig
    github_mods: List[GTNHModInfo] = Field(default_factory=list)
    external_mods: List[GTNHModInfo] = Field(default_factory=list)

    def add_github_mod(self, mod: GTNHModInfo) -> None:
        bisect.insort_right(self.github_mods, mod, key=self._mod_sort_key)  # type: ignore

    @staticmethod
    def _mod_sort_key(mod: GTNHModInfo) -> str:
        return mod.name.lower()

    @cached_property
    def _github_modmap(self) -> Dict[str, GTNHModInfo]:
        return {mod.name: mod for mod in self.github_mods}

    @cached_property
    def _external_modmap(self) -> Dict[str, GTNHModInfo]:
        return {mod.name: mod for mod in self.external_mods}

    def has_github_mod(self, mod_name: str) -> bool:
        return mod_name in self._github_modmap

    def has_external_mod(self, mod_name: str) -> bool:
        return mod_name in self._external_modmap

    def get_github_mod(self, mod_name: str) -> GTNHModInfo:
        return self._github_modmap[mod_name]

    def get_external_mod(self, mod_name: str) -> GTNHModInfo:
        return self._external_modmap[mod_name]
