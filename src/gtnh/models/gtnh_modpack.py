from __future__ import annotations

from pydantic import Field

from gtnh.models.base import GTNHBaseModel


class GTNHModpack(GTNHBaseModel):
    releases: set[str] = Field(default_factory=set)  # Set of releases, found in the `releases` directory
    server_exclusions: list[str] = Field(default_factory=list)
    client_exclusions: list[str] = Field(default_factory=list)
    client_java8_exclusions: list[str] = Field(default_factory=list)
    server_java8_exclusions: list[str] = Field(default_factory=list)
    client_java9_exclusions: list[str] = Field(default_factory=list)
    server_java9_exclusions: list[str] = Field(default_factory=list)
