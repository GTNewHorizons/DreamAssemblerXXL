import bisect

from packaging.version import LegacyVersion
from pydantic import BaseModel, Field

from gtnh.defs import VersionableType
from gtnh.gtnh_logger import get_logger
from gtnh.models.gtnh_version import GTNHVersion

log = get_logger(__name__)


class Versionable(BaseModel):
    name: str
    latest_version: str
    needs_attention: bool = Field(default=False)
    private: bool = Field(default=False)

    versions: list[GTNHVersion] = Field(default_factory=list)
    type: VersionableType = Field(default=VersionableType.mod)

    def add_version(self, version: GTNHVersion) -> None:
        idx = self.get_version_idx(version.version_tag)
        if idx is not None:
            self.versions[idx] = version
        else:
            bisect.insort_right(self.versions, version, key=version_sort_key)  # type: ignore
        self.reset_latest()

    def remove_version(self, version: GTNHVersion) -> bool:
        return self.remove_version_tag(version.version_tag)

    def remove_version_tag(self, version_tag: str) -> bool:
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
        i = bisect.bisect_left(self.versions, LegacyVersion(version), key=version_sort_key)  # type: ignore
        if i != len(self.versions) and self.versions[i] and self.versions[i].version_tag == version:
            return i
        return None

    def has_version(self, version: str) -> bool:
        return self.get_version_idx(version) is not None

    def get_versions(self, left: str | None, right: str) -> list[GTNHVersion]:
        right_idx = bisect.bisect_right(self.versions, LegacyVersion(right), key=version_sort_key)  # type: ignore
        if not left:
            return self.versions[:right_idx]

        left_idx = bisect.bisect_left(self.versions, LegacyVersion(left), key=version_sort_key)  # type: ignore
        return self.versions[left_idx:right_idx]


def version_sort_key(version: GTNHVersion) -> LegacyVersion:
    return LegacyVersion(version.version_tag)


def version_is_newer(test_version: str, existing_version: str) -> bool:
    return LegacyVersion(test_version) > LegacyVersion(existing_version)


def version_is_older(test_version: str, existing_version: str) -> bool:
    return LegacyVersion(test_version) < LegacyVersion(existing_version)
