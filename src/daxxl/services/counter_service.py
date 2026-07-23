from typing import Callable

from daxxl.exceptions import InvalidDailyIdException, InvalidExperimentalIdException
from daxxl.gtnh_logger import get_logger
from daxxl.models.available_assets import AvailableAssets

log = get_logger(__name__)


class CounterService:
    def __init__(self, assets: AvailableAssets, save_callback: Callable[[], None]) -> None:
        self._assets = assets
        self._save = save_callback

    def get_experimental_count(self) -> int:
        """
        Return the current experimental count.

        Returns
        -------
        int: The current experimental count.
        """
        return self._assets.latest_experimental

    def set_experimental_id(self, id: int) -> None:
        """
        Set the experimental id to a specific number. Has to be greater than the last experimental id.

        Returns
        -------
        None
        """
        latest_id = self._assets.latest_experimental
        if id > latest_id:
            self._assets.latest_experimental = id
        else:
            raise InvalidExperimentalIdException(
                f"Cannot set new experimental id to {id}, needs to be greater than latest experimental count {latest_id}"
            )

    def increment_experimental_count(self) -> None:
        """
        Increment the experimental count.

        Returns
        -------
        None
        """
        self._assets.latest_experimental += 1
        self._save()

    def set_last_successful_experimental_id(self, id: int) -> None:
        """
        Set the last successful experimental id.

        Parameters
        ----------
        id: int
            The last successful experimental id.

        Returns
        -------
        None
        """
        self._assets.latest_successful_experimental = id
        self._save()
        log.info(f"last successful build set to {id}")

    def get_last_successful_experimental(self) -> int:
        """
        get the last successful experimental id.

        Returns
        -------
        int
            The last successful experimental id.
        """
        return self._assets.latest_successful_experimental

    def get_daily_count(self) -> int:
        """
        Return the current daily count.

        Returns
        -------
        int: The current daily count.
        """
        return self._assets.latest_daily

    def set_daily_id(self, id: int) -> None:
        """
        Set the daily id to a specific number. Has to be greater than the last daily id.

        Returns
        -------
        None
        """
        latest_id = self._assets.latest_daily
        if id > latest_id:
            self._assets.latest_daily = id
        else:
            raise InvalidDailyIdException(
                f"Cannot set new daily id to {id}, needs to be greater than latest daily count {latest_id}"
            )

    def increment_daily_count(self) -> None:
        """
        Increment the daily count.

        Returns
        -------
        None
        """
        self._assets.latest_daily += 1
        self._save()

    def set_last_successful_daily_id(self, id: int) -> None:
        """
        Set the last successful daily id.

        Parameters
        ----------
        id: int
            The last successful daily id.

        Returns
        -------
        None
        """
        self._assets.latest_successful_daily = id
        self._save()
        log.info(f"last successful build set to {id}")

    def get_last_successful_daily(self) -> int:
        """
        get the last successful daily id.

        Returns
        -------
        int
            The last successful daily id.
        """
        return self._assets.latest_successful_daily
