from enum import Enum
from pathlib import Path

# Root is two levels up
ROOT_DIR = Path(__file__).parent.parent.parent
CACHE_DIR = ROOT_DIR / "cache"
TECHNIC_CACHE_DIR = CACHE_DIR / "technic"
CONFIG_CACHE_DIR = CACHE_DIR / "config"
WORKING_DIR = ROOT_DIR / "working"
CLIENT_WORKING_DIR = WORKING_DIR / "client"
SERVER_WORKING_DIR = WORKING_DIR / "server"

RELEASE_DIR = ROOT_DIR / "releases"
RELEASE_MANIFEST_DIR = RELEASE_DIR / "manifests"
RELEASE_ZIP_DIR = RELEASE_DIR / "zip"

AVAILABLE_ASSETS_FILE = "gtnh-assets.json"
GTNH_MODPACK_FILE = "gtnh-modpack.json"
BLACKLISTED_REPOS_FILE = "repo-blacklist.json"
UNKNOWN = "Unknown"
OTHER = "Other"
MAVEN_BASE_URL = "http://jenkins.usrv.eu:8081/nexus/content/repositories/releases/com/github/GTNewHorizons/"

GREEN_CHECK = "\N{white heavy check mark}"
RED_CROSS = "\N{cross mark}"


CURSE_BASE_URL = "https://api.curseforge.com"

CURSE_MINECRAFT_ID = 432
CURSE_FORGE_MODLOADER_ID = 1
CURSE_GAME_VERSION_TYPE_ID = 5


class Side(str, Enum):
    SERVER = "SERVER"
    CLIENT = "CLIENT"
    BOTH = "BOTH"
    NONE = "NONE"


class VersionableType(str, Enum):
    mod = "mod"
    config = "config"


class ModSource(str, Enum):
    curse = "curse"
    modrinth = "modrinth"
    other = "other"
