"""Module providing a class for availiable assets."""
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
from gtnh.models.mod_info import GTNHModInfo
from gtnh.models.mod_version_info import ModVersionInfo

log = get_logger(__name__)


class AvailableAssets(GTNHBaseModel):
    """Class representing all the availiable assets to assemble pack versions."""

    config: GTNHConfig
    mods: List[GTNHModInfo] = Field(default_factory=list)

    def add_mod(self, mod: GTNHModInfo) -> None:
        """
        Add a mod to the availiable mods.

        Parameters
        ----------
        mod: GTNHModInfo
            The new mod.

        Returns
        -------
        None.
        """
        log.info(f"Adding {mod.name}")
        bisect.insort_right(self.mods, mod, key=self._mod_sort_key)  # type: ignore
        self.refresh_modmap()

    @staticmethod
    def _mod_sort_key(mod: GTNHModInfo) -> str:
        """
        Get the name of the provided mod object.

        This is used as sorting criteria for mod insertion.

        Parameters
        ----------
        mod: GTNHModInfo
            The provided mod object.

        Returns
        -------
        The name of the mod object.
        """
        return mod.name.lower()

    def refresh_modmap(self) -> None:
        """
        Refresh the modmap.

        Returns
        -------
        None.
        """
        # This is the correct way to reload a cached_property, but linter doesn't understand it whatsoever
        if hasattr(self, "_modmap"):
            # noinspection PyPropertyAccess
            del self._modmap

    @cached_property
    def _modmap(self) -> Dict[str, GTNHModInfo]:
        """
        Get the internal modmap.

        Returns
        -------
        A Dict[str, GTNHModInfo] representing the modmap.
        """
        return {mod.name: mod for mod in self.mods}

    def has_mod(self, mod_name: str) -> bool:
        """
        Check if a mod name is in the modmap.

        Parameters
        ----------
        mod_name: str
            The mod name to check.

        Returns
        -------
        True if the mod name is in the modmap.
        """
        return mod_name in self._modmap

    def get_mod(self, mod_name: str) -> GTNHModInfo:
        """
        Get the mod object in the modmap corresponding to the given mod name.

        Parameters
        ----------
        mod_name: str
            The name of the mod to get.

        Returns
        -------
        The corresponding GTNHModInfo from the modmap.
        """
        if self.has_mod(mod_name):
            mod = self._modmap[mod_name]
            if mod.latest_version and mod.latest_version != "<unknown>":
                return mod

        raise NoModAssetFound(f"{mod_name} not found")

    def get_mod_and_version(
        self, mod_name: str, mod_version: ModVersionInfo, valid_sides: set[Side], source: ModSource
    ) -> tuple[GTNHModInfo, GTNHVersion] | None:
        """
        Get the tuple[GTNHModInfo, GTNHVersion] corresponding to the given mod name and version.

        Parameters
        ----------
        mod_name: str
            The given mod name.

        mod_version: str
            The associated mod version.

        valid_sides: set[Side]
            A set of sides declared as only valid sides.

        source: ModSource
            The source of the mod to retrieve.

        Returns
        -------
        The tuple[GTNHModInfo, GTNHVersion] from the given mod name and mod version. Return None if nothing is found.
        Return None if the side of the mod is not in the provided valid sides.
        """
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
