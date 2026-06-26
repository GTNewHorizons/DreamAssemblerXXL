# Using LegacyVersion because we want everything to be comparable
from pydantic import Field

from daxxl.defs import UNKNOWN, ModSource, Side
from daxxl.gtnh_logger import get_logger
from daxxl.models.base import GTNHBaseModel
from daxxl.models.versionable import Versionable

log = get_logger(__name__)


class GTNHModInfo(GTNHBaseModel, Versionable):
    license: str | None = Field(default=UNKNOWN)
    repo_url: str | None = Field(default=None)
    maven: str | None = Field(default=None)
    side: Side = Field(default=Side.BOTH)
    source: ModSource = Field(default=ModSource.github)

    external_url: str | None = Field(default=None)
    project_id: str | None = Field(default=None)
    slug: str | None = Field(default=None)

    disabled: bool = Field(default=False)

    def is_github(self) -> bool:
        return self.source == ModSource.github
