import bisect
from functools import cached_property
from typing import Dict, List

from pydantic import Field

from daxxl.defs import Side
from daxxl.exceptions import NoModAssetFound
from daxxl.gtnh_logger import get_logger
from daxxl.models.base import GTNHBaseModel
from daxxl.models.gtnh_config import GTNHConfig
from daxxl.models.gtnh_translations import GTNHTranslations
from daxxl.models.gtnh_version import GTNHVersion
from daxxl.models.mod_info import GTNHModInfo
from daxxl.models.mod_version_info import ModVersionInfo

log = get_logger(__name__)


class AvailableAssets(GTNHBaseModel):
    config: GTNHConfig
    translations: GTNHTranslations
    mods: List[GTNHModInfo] = Field(default_factory=list)
    latest_experimental: int
    latest_successful_experimental: int
    latest_daily: int
    latest_successful_daily: int

    def add_mod(self, mod: GTNHModInfo) -> None:
        log.info(f"Adding {mod.name}")
        bisect.insort_right(self.mods, mod, key=self._mod_sort_key)
        self.refresh_modmap()

    def update_mod(self, mod: GTNHModInfo) -> None:
        # todo: do something better than this
        index: int
        for i in range(len(self.mods)):
            if self.mods[i].name == mod.name:
                index = i
                break
        else:
            raise IndexError(f"mod {mod.name} not found")
        self.mods[index] = mod
        self.refresh_modmap()

    @staticmethod
    def _mod_sort_key(mod: GTNHModInfo) -> str:
        return mod.name.lower()

    def refresh_modmap(self) -> None:
        # This is the correct way to reload a cached_property, but linter doesn't understand it whatsoever
        if hasattr(self, "_modmap"):
            # noinspection PyPropertyAccess
            del self._modmap

    @cached_property
    def _modmap(self) -> Dict[str, GTNHModInfo]:
        return {mod.name: mod for mod in self.mods}

    def has_mod(self, mod_name: str) -> bool:
        return mod_name in self._modmap

    def get_mod(self, mod_name: str) -> GTNHModInfo:
        """
        Get a mod, preferring github mods over external mods
        """
        if self.has_mod(mod_name):
            mod = self._modmap[mod_name]
            if mod.latest_version and mod.latest_version != "<unknown>":
                return mod

        raise NoModAssetFound(f"{mod_name} not found")

    def get_mod_and_version(
        self, mod_name: str, mod_version: ModVersionInfo, valid_sides: set[Side]
    ) -> tuple[GTNHModInfo, GTNHVersion] | None:
        try:
            mod = self.get_mod(mod_name)
        except NoModAssetFound:
            log.warn(f"Mod {mod_name} cannot be found, returning None")
            return None

        side = mod_version.side if mod_version.side else mod.side

        if side not in valid_sides:
            return None

        version = mod.get_version(mod_version.version)
        if not version:
            log.error(f"Cannot find {mod_name}:{version}")
            return None

        return mod, version
