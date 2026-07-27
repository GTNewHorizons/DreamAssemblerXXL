from __future__ import annotations

from colorama import Fore
from pydantic import Field

from daxxl.defs import Side
from daxxl.gtnh_logger import get_logger
from daxxl.models.base import GTNHBaseModel

log = get_logger(__name__)


class GTNHModpack(GTNHBaseModel):
    releases: set[str] = Field(default_factory=set)
    server_exclusions: list[str] = Field(default_factory=list)
    client_exclusions: list[str] = Field(default_factory=list)
    client_java8_exclusions: list[str] = Field(default_factory=list)
    server_java8_exclusions: list[str] = Field(default_factory=list)
    client_java9_exclusions: list[str] = Field(default_factory=list)
    server_java9_exclusions: list[str] = Field(default_factory=list)

    def add_exclusion(self, side: Side, exclusion: str) -> bool:
        if side == Side.CLIENT:
            if exclusion in self.client_exclusions:
                log.warn(f"{Fore.YELLOW}{exclusion} is already in {side} side exclusions{Fore.RESET}")
                return False
            self.client_exclusions.append(exclusion)
            log.info(f"{Fore.GREEN}{exclusion} has been added to {side} side exclusions{Fore.RESET}")
            return True
        if side == Side.SERVER:
            if exclusion in self.server_exclusions:
                log.warn(f"{Fore.YELLOW}{exclusion} is already in {side} side exclusions{Fore.RESET}")
                return False
            self.server_exclusions.append(exclusion)
            log.info(f"{Fore.GREEN}{exclusion} has been added to {side} side exclusions{Fore.RESET}")
            return True
        raise ValueError(f"{side} isn't a valid side")

    def delete_exclusion(self, side: Side, exclusion: str) -> bool:
        if side == Side.CLIENT:
            self.client_exclusions.sort()
            if exclusion not in self.client_exclusions:
                log.warn(f"{Fore.YELLOW}{exclusion} is not in {side} side exclusions{Fore.RESET}")
                return False
            self.client_exclusions.remove(exclusion)
            log.info(f"{Fore.GREEN}{exclusion} has been removed from {side} side exclusions{Fore.RESET}")
            return True
        if side == Side.SERVER:
            self.server_exclusions.sort()
            if exclusion not in self.server_exclusions:
                log.warn(f"{Fore.YELLOW}{exclusion} is not in {side} side exclusions{Fore.RESET}")
                return False
            self.server_exclusions.remove(exclusion)
            log.info(f"{Fore.GREEN}{exclusion} has been removed from {side} side exclusions{Fore.RESET}")
            return True
        raise ValueError(f"{side} isn't a valid side")
