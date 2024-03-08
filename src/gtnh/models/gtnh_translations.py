from gtnh.models.base import GTNHBaseModel
from gtnh.models.versionable import Versionable

TRANSLATIONS_REPO_NAME = "GTNH-Translations"


class GTNHTranslations(GTNHBaseModel, Versionable):
    repo_url: str
