from gtnh.models.base import GTNHBaseModel
from gtnh.models.versionable import Versionable

CONFIG_REPO_NAME = "GT-New-Horizons-Modpack"


class GTNHConfig(GTNHBaseModel, Versionable):
    repo_url: str
