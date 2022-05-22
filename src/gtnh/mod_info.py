from datetime import datetime
from functools import cached_property
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from gtnh.defs import UNKNOWN, Side


class ModInfo(BaseModel):
    name: str
    version: str
    tagged_at: Optional[datetime] = Field(default=None)
    repo_url: Optional[str] = Field(default=None)
    filename: Optional[str] = Field(default=None)
    download_url: Optional[str] = Field(default=None)
    browser_download_url: Optional[str] = Field(default=None)
    license: Optional[str] = Field(default=UNKNOWN)
    side: Side = Field(default=Side.BOTH)
    maven: Optional[str] = Field(default=None)


class GTNHModpack(BaseModel):
    github_mods: List[ModInfo]
    external_mods: List[ModInfo] = Field(default_factory=list)
    modpack_version: str = Field(default="nightly")
    server_exclusions: List[str] = Field(default_factory=list)
    client_exclusions: List[str] = Field(default_factory=list)

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
