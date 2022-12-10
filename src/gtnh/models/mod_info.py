# Using LegacyVersion because we want everything to be comparable
from pydantic import Field
from structlog import get_logger

from gtnh.defs import UNKNOWN, ModSource, Side
from gtnh.models.base import GTNHBaseModel
from gtnh.models.versionable import Versionable

log = get_logger(__name__)


class GTNHModInfo(GTNHBaseModel, Versionable):
    license: str | None = Field(default=UNKNOWN)
    repo_url: str | None = Field(default=None)
    maven: str | None = Field(default=None)
    side: Side = Field(default=Side.BOTH)
    source: ModSource = Field(default=ModSource.github)

    external_url: str | None
    project_id: str | None
    slug: str | None

    disabled: bool = Field(default=False)


class ExternalModInfo(GTNHModInfo):
    source: ModSource = Field(default=ModSource.curse)
