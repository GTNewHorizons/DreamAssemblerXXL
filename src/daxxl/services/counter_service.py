from typing import Callable

from daxxl.defs import DevRelease
from daxxl.exceptions import InvalidDailyIDException, InvalidExperimentalIDException
from daxxl.gtnh_logger import get_logger
from daxxl.models.available_assets import AvailableAssets

log = get_logger(__name__)


class CounterService:
    def __init__(self, assets: AvailableAssets, save_callback: Callable[[], None]) -> None:
        self._assets = assets
        self._save = save_callback

    def get_dev_release_count(self, release_type: DevRelease) -> int:
        """
        Return the current count for the desired dev release.

        Returns
        -------
        int: the current count for the desired dev release.
        """
        if release_type == DevRelease.EXPERIMENTAL:
            return self._assets.latest_experimental
        elif release_type == DevRelease.DAILY:
            return self._assets.latest_daily
        else:
            raise NotImplementedError(f"{release_type} dev release is not yet supported")

    def set_dev_release_id(self, release_type: DevRelease, build_id: int) -> None:
        """
        Set the dev release id to a specific number. Has to be greater than the last id.

        Returns
        -------
        None
        """
        if release_type == DevRelease.EXPERIMENTAL:
            if build_id <= self._assets.latest_experimental:
                raise InvalidExperimentalIDException(
                    f"Cannot set new experimental id to {build_id}, needs to be greater than latest experimental count {self._assets.latest_experimental}"
                )
            self._assets.latest_experimental = build_id

        elif release_type == DevRelease.DAILY:
            if build_id <= self._assets.latest_daily:
                raise InvalidDailyIDException(
                    f"Cannot set new daily id to {build_id}, needs to be greater than latest daily count {self._assets.latest_daily}"
                )
            self._assets.latest_daily = build_id
        else:
            raise NotImplementedError(f"{release_type} dev release is not yet supported")

    def increment_dev_build_id(self, release_type: DevRelease) -> None:
        """
        Increment the dev build id.

        Returns
        -------
        None
        """
        if release_type == DevRelease.EXPERIMENTAL:
            self._assets.latest_experimental += 1
        elif release_type == DevRelease.DAILY:
            self._assets.latest_daily += 1
        else:
            raise NotImplementedError(f"{release_type} dev release is not yet supported")
        self._save()

    def set_last_successful_dev_build_id(self, release_type: DevRelease, build_id: int) -> None:
        """
        Set the last successful dev build id.

        Parameters
        ----------
        build_id: int
            The last successful dev build id.

        Returns
        -------
        None
        """
        if release_type == DevRelease.EXPERIMENTAL:
            self._assets.latest_successful_experimental = build_id
        elif release_type == DevRelease.DAILY:
            self._assets.latest_successful_daily = build_id
        else:
            raise NotImplementedError(f"{release_type} dev release is not yet supported")
        self._save()
        log.info(f"last successful build set to {build_id}")

    def get_last_successful_dev_build_id(self, release_type: DevRelease) -> int:
        """
        get the last successful dev build id.

        Returns
        -------
        int
            The last successful dev build id.
        """
        if release_type == DevRelease.EXPERIMENTAL:
            return self._assets.latest_successful_experimental
        elif release_type == DevRelease.DAILY:
            return self._assets.latest_successful_daily
        else:
            raise NotImplementedError(f"{release_type} dev release is not yet supported")
