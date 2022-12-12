"""Module defining a convenient way of checking for exclusions inside DAXXL's GUI."""

from pathlib import Path
from typing import Iterable, List


class Exclusions:
    """Class defining a convenient way of checking for exclusions inside DAXXL's GUI."""

    exclusions: List[str]

    def __init__(self, exclusions: List[str]) -> None:
        """
        Construct the Exclusions class.

        Parameters
        ----------
        exclusions : List[str]
            A list of string representing a path from the root of the instance.
        """
        self.exclusions = exclusions

    def __contains__(self, item: str) -> bool:
        """
        Implement the "in" operator for the class.

        Parameters
        ----------
        item : str
            the exclusion to check if it's inside the exclusion list.

        Returns
        -------
        out : bool
            True if it's in the exclusion list, False otherwise.
        """
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
        """
        Append the given exclusion to the exclusion list.

        Parameters
        ----------
        exclusion : str
            the given exclusion to append to the exclusion list.

        Returns
        -------
        None

        """
        self.exclusions.append(exclusion)

    def extend(self, exclusions: Iterable[str]) -> None:
        """
        Extend the exclusion list with all the exclusions within the passed iterable object.

        Parameters
        ----------
        exclusions : Iterable[str]
            An iterable containing exclusions to add to the exclusion list.

        Returns
        -------
        None
        """
        self.exclusions.extend(exclusions)
