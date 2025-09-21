from __future__ import annotations

from enum import Enum
from pathlib import Path

# Root is two levels up
from typing import List, Set

ROOT_DIR = Path(__file__).parent.parent.parent
CACHE_DIR = ROOT_DIR / "cache"
CURSEFORGE_CACHE_DIR = CACHE_DIR / "curseforge"
TECHNIC_CACHE_DIR = CACHE_DIR / "technic"
CONFIG_CACHE_DIR = CACHE_DIR / "config"
WORKING_DIR = ROOT_DIR / "working"
CLIENT_WORKING_DIR = WORKING_DIR / "client"
SERVER_WORKING_DIR = WORKING_DIR / "server"

RELEASE_DIR = ROOT_DIR / "releases"
RELEASE_MANIFEST_DIR = RELEASE_DIR / "manifests"
RELEASE_ZIP_DIR = RELEASE_DIR / "zip"
RELEASE_MMC_DIR = RELEASE_DIR / "multi_poly"
RELEASE_TECHNIC_DIR = RELEASE_DIR / "technic"
RELEASE_CURSE_DIR = RELEASE_DIR / "curse"
RELEASE_MODRINTH_DIR = RELEASE_DIR / "modrinth"
RELEASE_CHANGELOG_DIR = RELEASE_DIR / "changelogs"
RELEASE_CHANGELOG_EXPERIMENTAL_BUILDS_DIR = RELEASE_CHANGELOG_DIR / "experimental builds"
RELEASE_CHANGELOG_DAILY_BUILDS_DIR = RELEASE_CHANGELOG_DIR / "daily builds"
RELEASE_README_DIR = RELEASE_DIR / "readmes"

SERVER_ASSETS_DIR = ROOT_DIR / "server_assets"
CLIENT_ASSETS_DIR = ROOT_DIR / "client_assets"

MMC_ASSETS_DIR = CLIENT_ASSETS_DIR / "multi_poly"

TRANSLATION_DIR = ROOT_DIR / "translations"

README_TEMPLATE = ROOT_DIR / "readme_template.md"


class Archive(str, Enum):
    MMC = "MMC"
    TECHNIC = "Technic"
    ZIP = "zip"
    CURSEFORGE = "CurseForge"
    MODRINTH = "Modrinth"


AVAILABLE_ASSETS_FILE = "gtnh-assets.json"
GTNH_MODPACK_FILE = "gtnh-modpack.json"
BLACKLISTED_REPOS_FILE = "repo-blacklist.json"
LOCAL_EXCLUDES_FILE = ".inplace_mod_exclusions"
INPLACE_PINNED_FILE = ".inplace_pinned_mods"
UNKNOWN = "Unknown"
OTHER = "Other"
MAVEN_BASE_URL = "https://nexus.gtnewhorizons.com/repository/releases/com/github/GTNewHorizons/"

GREEN_CHECK = "\N{white heavy check mark}"
RED_CROSS = "\N{cross mark}"


CURSE_BASE_URL = "https://api.curseforge.com"

CURSE_MINECRAFT_ID = 432
CURSE_FORGE_MODLOADER_ID = 1
CURSE_GAME_VERSION_TYPE_ID = 5

MMC_PACK_JSON = """{
    "components": [
        {
            "dependencyOnly": true,
            "uid": "org.lwjgl",
            "version": "2.9.4-nightly-20150209"
        },
        {
            "important": true,
            "uid": "net.minecraft",
            "version": "1.7.10"
        },
        {
            "uid": "net.minecraftforge",
            "version": "10.13.4.1614"
        }
    ],
    "formatVersion": 1
}
"""

MMC_PACK_INSTANCE = """InstanceType=OneSix
JoinServerOnLaunch=false
OverrideCommands=false
OverrideConsole=false
OverrideGameTime=false
OverrideJavaArgs=false
OverrideJavaLocation=false
OverrideMemory=false
OverrideNativeWorkarounds=false
OverrideWindow=false
iconKey=gtnh_icon
name={}
notes=
"""

SERVER_PROPERTIES_FILE = """generator-settings=
op-permission-level=2
allow-nether=true
level-name=World
enable-query=false
allow-flight=true
announce-player-achievements=true
server-port=25565
level-type=rwg
enable-rcon=false
force-gamemode=false
level-seed=
server-ip=
max-build-height=256
spawn-npcs=true
white-list=true
spawn-animals=true
hardcore=false
snooper-enabled=true
texture-pack=
online-mode=true
server-id=unnamed
resource-pack=
pvp=true
difficulty=3
server-name=
enable-command-block=true
gamemode=0
player-idle-timeout=0
max-players=20
spawn-monsters=true
generate-structures=true
view-distance=8
spawn-protection=1
motd=GT:New Horizons {0}"""

JAVA_9_ARCHIVE_SUFFIX = "Java_17-25"


class Side(str, Enum):
    SERVER = "SERVER"
    CLIENT = "CLIENT"
    BOTH = "BOTH"
    NONE = "NONE"
    SERVER_JAVA9 = "SERVER_JAVA9"
    CLIENT_JAVA9 = "CLIENT_JAVA9"
    BOTH_JAVA9 = "BOTH_JAVA9"

    def valid_mod_sides(self) -> Set[Side]:
        mods_included_relations = {
            Side.SERVER: {Side.BOTH, Side.SERVER},
            Side.CLIENT: {Side.BOTH, Side.CLIENT},
            Side.BOTH: {Side.BOTH, Side.SERVER, Side.CLIENT},
            Side.NONE: {Side.NONE},
            Side.SERVER_JAVA9: {Side.BOTH, Side.SERVER, Side.BOTH_JAVA9, Side.SERVER_JAVA9},
            Side.CLIENT_JAVA9: {Side.BOTH, Side.CLIENT, Side.BOTH_JAVA9, Side.CLIENT_JAVA9},
            Side.BOTH_JAVA9: {
                Side.BOTH,
                Side.SERVER,
                Side.CLIENT,
                Side.BOTH_JAVA9,
                Side.SERVER_JAVA9,
                Side.CLIENT_JAVA9,
            },
        }
        return mods_included_relations[self]

    def is_java9(self) -> bool:
        return self in {Side.CLIENT_JAVA9, Side.SERVER_JAVA9, Side.BOTH_JAVA9}

    def is_server(self) -> bool:
        return self in {Side.SERVER, Side.SERVER_JAVA9}

    def is_client(self) -> bool:
        return self in {Side.CLIENT, Side.CLIENT_JAVA9}

    def archive_name(self) -> str:
        if self == Side.CLIENT_JAVA9:
            return f"Client_{JAVA_9_ARCHIVE_SUFFIX}"
        elif self == Side.SERVER_JAVA9:
            return f"Server_{JAVA_9_ARCHIVE_SUFFIX}"
        else:
            return f"{self.value.capitalize()}_Java_8"


class VersionableType(str, Enum):
    mod = "mod"
    config = "config"
    translations = "translations"


class ModSource(str, Enum):
    github = "github"
    curse = "curse"
    modrinth = "modrinth"
    other = "other"


class Position(str, Enum):
    UP = "N"
    DOWN = "S"
    LEFT = "W"
    RIGHT = "E"
    UP_LEFT = "WN"
    UP_RIGHT = "EN"
    DOWN_LEFT = "WS"
    DOWN_RIGHT = "ES"
    HORIZONTAL = "WE"
    VERTICAL = "NS"
    ALL = "WENS"
    NONE = ""


class ServerBrand(str, Enum):
    forge = "forge"
    thermos = "thermos"


class ModEntry:
    def __init__(self, name: str, version: str, is_new: bool) -> None:
        self.name: str = name
        self.version: str = version
        self.side_info: str = ""
        self.is_new: bool = is_new
        self.changes: list[tuple[str, list[str]]] = []
        self.contributors: Set[str] = set()
        self.new_contributors: List[str] = []
        self.oldest_link_version = ""
        self.newest_link_version = ""
