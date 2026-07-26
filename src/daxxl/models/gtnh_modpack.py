from __future__ import annotations

from pydantic import Field

from daxxl.defs import Side
from daxxl.models.base import GTNHBaseModel


class GTNHModpack(GTNHBaseModel):
    releases: set[str] = Field(default_factory=set)  # Set of releases, found in the `releases` directory
    server_exclusions: list[str] = Field(default_factory=list)
    client_exclusions: list[str] = Field(default_factory=list)
    client_java8_exclusions: list[str] = Field(default_factory=list)
    server_java8_exclusions: list[str] = Field(default_factory=list)
    client_java9_exclusions: list[str] = Field(default_factory=list)
    server_java9_exclusions: list[str] = Field(default_factory=list)

    def add_exclusion(self, side: Side, exclusion: str) -> bool:
        if side == Side.CLIENT:
            if exclusion in self.client_exclusions:
                return False
            self.client_exclusions.append(exclusion)
            return True
        if side == Side.SERVER:
            if exclusion in self.server_exclusions:
                return False
            self.server_exclusions.append(exclusion)
            return True
        raise ValueError(f"{side} isn't a valid side")

    def delete_exclusion(self, side: Side, exclusion: str) -> bool:
        if side == Side.CLIENT:
            self.client_exclusions.sort()
            if exclusion not in self.client_exclusions:
                return False
            self.client_exclusions.remove(exclusion)
            return True
        if side == Side.SERVER:
            self.server_exclusions.sort()
            if exclusion not in self.server_exclusions:
                return False
            self.server_exclusions.remove(exclusion)
            return True
        raise ValueError(f"{side} isn't a valid side")
