import bisect
from collections.abc import Iterator
from contextlib import contextmanager

try:
    from packaging.version import LegacyVersion
except ImportError:
    from packaging_legacy.version import LegacyVersion

from pydantic import BaseModel, Field

from daxxl.defs import VersionableType
from daxxl.gtnh_logger import get_logger
from daxxl.models.gtnh_version import GTNHVersion

log = get_logger(__name__)


class Versionable(BaseModel):
    name: str
    latest_version: str
    needs_attention: bool = Field(default=False)
    private: bool = Field(default=False)

    versions: list[GTNHVersion] = Field(default_factory=list)
    versionable_type: VersionableType = Field(default=VersionableType.mod, alias="type")

    def add_version(self, version: GTNHVersion) -> None:
        idx = self.get_version_idx(version.version_tag)
        if idx is not None:
            self.versions[idx] = version
        else:
            bisect.insort_right(self.versions, version, key=version_sort_key)
        self.reset_latest()

    def delete_version(self, version: GTNHVersion) -> bool:
        return self.delete_version_tag(version.version_tag)

    def delete_version_tag(self, version_tag: str) -> bool:
        idx = self.get_version_idx(version_tag)

        if idx is not None:
            del self.versions[idx]
            self.reset_latest()
            return True

        return False

    def reset_latest(self) -> bool:
        latest_version = self.get_latest_version()
        if latest_version is not None and self.latest_version != latest_version.version_tag:
            self.latest_version = latest_version.version_tag
            self.needs_attention = False
            return True
        return False

    def get_latest_version(self) -> GTNHVersion | None:
        return self.versions[-1] if self.versions else None

    def get_version(self, version: str) -> GTNHVersion | None:
        idx = self.get_version_idx(version)
        if idx is not None:
            return self.versions[idx]
        return None

    def get_version_idx(self, version: str) -> int | None:
        i = bisect.bisect_left(self.versions, LegacyVersion(version), key=version_sort_key)
        if i != len(self.versions) and self.versions[i] and self.versions[i].version_tag == version:
            return i
        return None

    def has_version(self, version: str) -> bool:
        return self.get_version_idx(version) is not None

    def get_versions(self, left: str | None, right: str) -> list[GTNHVersion]:
        right_idx = bisect.bisect_right(self.versions, LegacyVersion(right), key=version_sort_key)
        if not left:
            return self.versions[:right_idx]

        left_idx = bisect.bisect_left(self.versions, LegacyVersion(left), key=version_sort_key)
        return self.versions[left_idx:right_idx]


@contextmanager
def full_version_refresh(asset: Versionable, latest_version_floor: str = "") -> Iterator[None]:
    """
    Clear `asset`'s known versions so they can be rebuilt from scratch, putting them back if the
    rebuild fails.

    Without the rollback a failed refresh leaves the asset with an empty version list, which the
    next successful save then writes to the asset manifest, losing the versions for good.

    :param asset: the asset whose versions are being rebuilt
    :param latest_version_floor: what `latest_version` is reset to, low enough that every
        rediscovered tag compares as newer
    :return: None
    """
    previous_versions = asset.versions
    previous_latest_version = asset.latest_version
    asset.versions = []
    asset.latest_version = latest_version_floor
    try:
        yield
    except BaseException:
        asset.versions = previous_versions
        asset.latest_version = previous_latest_version
        raise


def version_sort_key(version: GTNHVersion) -> LegacyVersion:
    return LegacyVersion(version.version_tag)


def version_is_newer(test_version: str, existing_version: str) -> bool:
    return bool(LegacyVersion(test_version) > LegacyVersion(existing_version))


def version_is_older(test_version: str, existing_version: str) -> bool:
    return bool(LegacyVersion(test_version) < LegacyVersion(existing_version))
