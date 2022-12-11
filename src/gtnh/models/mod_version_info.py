from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from gtnh.defs import Side
from gtnh.models.base import GTNHBaseModel

if TYPE_CHECKING:
    from gtnh.models.mod_info import GTNHModInfo


class ModVersionInfo(GTNHBaseModel):
    version: str
    side: Optional[Side]

    @classmethod
    def create(
        cls, version: str | None = None, mod: GTNHModInfo | None = None, side: Side | None = None
    ) -> ModVersionInfo:
        if version is None and mod is not None:
            version = mod.latest_version

        if side is None and mod is not None:
            side = mod.side

        if not version:
            raise ValueError("Version or a mod with a latest version must be provided")

        return ModVersionInfo(version=version, side=side)

    def __str__(self) -> str:
        if not self.side:
            return self.version
        else:
            return f"{self.version}@{self.side}"
