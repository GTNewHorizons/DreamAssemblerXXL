from typing import Optional

# Using LegacyVersion because we want everything to be comparable
from pydantic import Field
from structlog import get_logger

from gtnh.defs import UNKNOWN, Side
from gtnh.models.base import GTNHBaseModel
from gtnh.models.versionable import Versionable

log = get_logger(__name__)


class GTNHModInfo(GTNHBaseModel, Versionable):
    license: Optional[str] = Field(default=UNKNOWN)
    repo_url: Optional[str] = Field(default=None)
    maven: Optional[str] = Field(default=None)
    side: Side = Field(default=Side.BOTH)

    disabled: bool = Field(default=False)
