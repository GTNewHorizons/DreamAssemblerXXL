import os
from datetime import datetime
from enum import Enum
from functools import cached_property
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

GTNH_MODPACK_FILE = "gtnh-modpack.json"
UNKNOWN = "Unknown"
OTHER = "Other"


class Side(str, Enum):
    SERVER = "SERVER"
    CLIENT = "CLIENT"
    BOTH = "BOTH"
    NONE = "NONE"


class ModInfo(BaseModel):
    name: str
    version: str
    tagged_at: Optional[datetime] = Field(default=None)
    repo_url: Optional[str] = Field(default=None)
    filename: Optional[str] = Field(default=None)
    download_url: Optional[str] = Field(default=None)
    browser_download_url: Optional[str] = Field(default=None)
    license: str = Field(default=UNKNOWN)
    side: Side = Field(default=Side.BOTH)



class GTNHModpack(BaseModel):
    github_mods: List[ModInfo]

    @cached_property
    def _github_modmap(self) -> Dict[str, ModInfo]:
        return {mod.name: mod for mod in self.github_mods}

    def has_github_mod(self, mod_name: str):
        return mod_name in self._github_modmap

    def get_github_mod(self, mod_name: str):
        return self._github_modmap.get(mod_name)


def load_gtnh_manifest() -> GTNHModpack:
    latest_version_filename = os.path.abspath(os.path.dirname(__file__)) + "/../../" + GTNH_MODPACK_FILE
    print(f"Loading mod info from `{latest_version_filename}`")
    with open(latest_version_filename) as f:
        gtnh_modpack = GTNHModpack.parse_raw(f.read())

    return gtnh_modpack
