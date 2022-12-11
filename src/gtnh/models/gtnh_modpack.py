from pydantic import Field
from sortedcontainers import SortedSet

from gtnh.models.base import GTNHBaseModel


class GTNHModpack(GTNHBaseModel):
    releases: SortedSet[str]  # Set of releases, found in the `releases` directory
    server_exclusions: list[str] = Field(default_factory=list)
    client_exclusions: list[str] = Field(default_factory=list)
