from daxxl.models.base import GTNHBaseModel
from daxxl.models.versionable import Versionable

TRANSLATIONS_REPO_NAME = "GTNH-Translations"


class GTNHTranslations(GTNHBaseModel, Versionable):
    repo_url: str
