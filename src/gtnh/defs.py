from enum import Enum

GTNH_MODPACK_FILE = "gtnh-modpack.json"
UNKNOWN = "Unknown"
OTHER = "Other"


class Side(str, Enum):
    SERVER = "SERVER"
    CLIENT = "CLIENT"
    BOTH = "BOTH"
    NONE = "NONE"
