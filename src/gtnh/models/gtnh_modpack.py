from typing import List

from pydantic import BaseModel, Field

from gtnh.models.gtnh_release import GTNHRelease


class GTNHModpack(BaseModel):
    releases = List[GTNHRelease]

    default_server_exclusions: List[str] = Field(default_factory=list)
    default_client_exclusions: List[str] = Field(default_factory=list)
