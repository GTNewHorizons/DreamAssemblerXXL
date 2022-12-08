from typing import Optional

from gtnh.defs import Side
from gtnh.models.base import GTNHBaseModel


class ModVersionInfo(GTNHBaseModel):
    version: str
    side: Optional[Side]

    def __str__(self) -> str:
        if not self.side:
            return self.version
        else:
            return f"{self.version}@{self.side}"
