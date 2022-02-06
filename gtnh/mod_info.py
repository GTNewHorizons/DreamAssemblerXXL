import json
import os
from enum import Enum

from pydantic import BaseModel, Field

GTNH_MOD_INFO_FILE = "gtnh-mods.json"


class Side(str, Enum):
    SERVER = "SERVER"
    CLIENT = "CLIENT"
    BOTH = "BOTH"
    NONE = "NONE"


class ModInfo(BaseModel):
    mod_name: str
    latest_version: str
    side: Side = Field(default=Side.BOTH)


class GTNHMods(BaseModel):
    mods: dict[str, ModInfo]

    def has_mod(self, mod_name):
        return mod_name in self.mods

    def get_mod(self, mod_name):
        return self.mods.get(mod_name)


def load_gtnh_mod_info() -> GTNHMods:
    latest_version_filename = (
        os.path.abspath(os.path.dirname(__file__)) + "/" + GTNH_MOD_INFO_FILE
    )
    print(f"Loading mod info from `{latest_version_filename}`")
    with open(latest_version_filename) as f:
        mods_json = json.loads(f.read())
        mods_info = GTNHMods(mods={
            k: ModInfo.parse_obj(v | {"mod_name": k}) for k, v in mods_json.items()
        })

    return mods_info
