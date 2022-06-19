import bisect
from functools import cached_property
from typing import Any, Callable, Dict, List

import orjson
from pydantic import BaseModel, Field

from gtnh.models.mod_info import ModInfo


def orjson_dumps(v: Any, *, default: Callable[..., Any]) -> str:
    # orjson.dumps returns bytes, to match standard json.dumps we need to decode
    return orjson.dumps(v, default=default, option=orjson.OPT_INDENT_2).decode()


class AvailableMods(BaseModel):
    github_mods: List[ModInfo]
    external_mods: List[ModInfo] = Field(default_factory=list)

    def add_github_mod(self, mod: ModInfo) -> None:
        bisect.insort_right(self.github_mods, mod, key=self._mod_sort_key)  # type: ignore

    @staticmethod
    def _mod_sort_key(mod: ModInfo) -> str:
        return mod.name.lower()

    @cached_property
    def _github_modmap(self) -> Dict[str, ModInfo]:
        return {mod.name: mod for mod in self.github_mods}

    @cached_property
    def _external_modmap(self) -> Dict[str, ModInfo]:
        return {mod.name: mod for mod in self.external_mods}

    def has_github_mod(self, mod_name: str) -> bool:
        return mod_name in self._github_modmap

    def has_external_mod(self, mod_name: str) -> bool:
        return mod_name in self._external_modmap

    def get_github_mod(self, mod_name: str) -> ModInfo:
        return self._github_modmap[mod_name]

    def get_external_mod(self, mod_name: str) -> ModInfo:
        return self._external_modmap[mod_name]

    class Config:
        json_loads = orjson.loads
        json_dumps = orjson_dumps
