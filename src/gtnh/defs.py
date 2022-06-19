from enum import Enum
from pathlib import Path

# Root is two levels up
ROOT_DIR = Path(__file__).parent.parent.parent
CACHE_DIR = ROOT_DIR / "cache"
MODS_CACHE_DIR = CACHE_DIR / "mods"
CONFIG_CACHE_DIR = CACHE_DIR / "config"
WORKING_DIR = ROOT_DIR / "working"
CLIENT_WORKING_DIR = WORKING_DIR / "client"
SERVER_WORKING_DIR = WORKING_DIR / "server"
RELEASE_DIR = ROOT_DIR / "releases"


AVAILABLE_MODS_FILE = "gtnh-mods.json"
GTNH_MODPACK_FILE = "gtnh-modpack.json"
BLACKLISTED_REPOS_FILE = "repo-blacklist.json"
UNKNOWN = "Unknown"
OTHER = "Other"
MAVEN_BASE_URL = "http://jenkins.usrv.eu:8081/nexus/content/repositories/releases/com/github/GTNewHorizons/"

GREEN_CHECK = "\N{white heavy check mark}"
RED_CROSS = "\N{cross mark}"


class Side(str, Enum):
    SERVER = "SERVER"
    CLIENT = "CLIENT"
    BOTH = "BOTH"
    NONE = "NONE"
