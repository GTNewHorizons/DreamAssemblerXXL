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
from gtnh.models.mod_version_info import ModVersionInfo

log = get_logger(__name__)


class AvailableAssets(GTNHBaseModel):
    config: GTNHConfig
    mods: List[GTNHModInfo] = Field(default_factory=list)

    def add_mod(self, mod: GTNHModInfo) -> None:
        log.info(f"Adding {mod.name}")
        bisect.insort_right(self.mods, mod, key=self._mod_sort_key)  # type: ignore
        if hasattr(self, "_modmap"):
            del self._modmap

    @staticmethod
    def _mod_sort_key(mod: GTNHModInfo) -> str:
        return mod.name.lower()

    @cached_property
    def _modmap(self) -> Dict[str, GTNHModInfo]:
        return {mod.name: mod for mod in self.mods}

    def has_mod(self, mod_name: str) -> bool:
        return mod_name in self._modmap

    def get_mod(self, mod_name: str) -> GTNHModInfo | ExternalModInfo:
        """
        Get a mod, preferring github mods over external mods
        """
        if self.has_mod(mod_name):
            mod = self._modmap[mod_name]
            if mod.latest_version and mod.latest_version != "<unknown>":
                return mod

        raise NoModAssetFound(f"{mod_name} not found")

    def get_mod_and_version(
        self, mod_name: str, mod_version: ModVersionInfo, valid_sides: set[Side], source: ModSource
    ) -> tuple[GTNHModInfo | ExternalModInfo, GTNHVersion] | None:
        try:
            mod = self.get_mod(mod_name)
        except KeyError:
            log.warn(f"Mod {mod_name} in {source} cannot be found, returning None")
            return None

        side = mod_version.side if mod_version.side else mod.side

        if side not in valid_sides:
            return None

        version = mod.get_version(mod_version.version)
        if not version:
            log.error(f"Cannot find {mod_name}:{version}")
            return None

        return mod, version
