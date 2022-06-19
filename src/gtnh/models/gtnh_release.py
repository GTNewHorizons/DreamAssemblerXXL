from typing import Dict, List

from pydantic import BaseModel, Field


class GTNHRelease(BaseModel):
    version: str = Field(default="nightly")

    # ModName, Version
    github_mods: Dict[str, str]
    external_mods: Dict[str, str]

    server_exclusions: List[str] = Field(default_factory=list)
    client_exclusions: List[str] = Field(default_factory=list)
