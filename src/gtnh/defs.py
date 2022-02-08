from enum import Enum

GTNH_MODPACK_FILE = "gtnh-modpack.json"
BLACKLISTED_REPOS_FILE = "repo-blacklist.json"
UNKNOWN = "Unknown"
OTHER = "Other"
MAVEN_BASE_URL = "http://jenkins.usrv.eu:8081/nexus/content/repositories/releases/com/github/GTNewHorizons/"


class Side(str, Enum):
    SERVER = "SERVER"
    CLIENT = "CLIENT"
    BOTH = "BOTH"
    NONE = "NONE"
