from collections.abc import Iterable
from pathlib import Path


class Exclusions:
    exclusions: list[str]

    def __init__(self, exclusions: list[str]) -> None:
        self.exclusions = exclusions

    def __contains__(self, item: str) -> bool:
        obj = Path(item)
        for exclu in self.exclusions:
            if item == exclu:  # if the file is explicitely listed as excluded
                return True
            if Path(exclu) in obj.parents:  # if a file is in an excluded folder
                return True

            if exclu.endswith("*") and Path(exclu[:-1]) in obj.parents:
                return True

        return False

    def append(self, exclusion: str) -> None:
        self.exclusions.append(exclusion)

    def extend(self, exclusions: Iterable[str]) -> None:
        self.exclusions.extend(exclusions)
