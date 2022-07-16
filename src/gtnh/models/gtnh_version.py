from datetime import datetime
from typing import Optional

from pydantic import Field
from structlog import get_logger

from gtnh.defs import VersionableType
from gtnh.models.base import GTNHBaseModel
from gtnh.utils import AttributeDict

log = get_logger(__name__)


class GTNHVersion(GTNHBaseModel):
    version_tag: str
    changelog: str = Field(default="")
    prerelease: bool = Field(default=False)
    tagged_at: Optional[datetime] = Field(default=None)
    filename: str | None = Field(default=None)
    download_url: str | None = Field(default=None)
    browser_download_url: str | None = Field(default=None)


def version_from_release(release: AttributeDict, type: VersionableType) -> GTNHVersion | None:
    """
    Get ModVersion and assets from a GitRelease
    :param release: GithubRelease
    :return: ModVersion
    """
    version = release.tag_name
    asset = get_asset(release, type)

    if not asset:
        return None

    return GTNHVersion(
        version_tag=version,
        changelog=release.body or "",
        prerelease=release.prerelease,
        tagged_at=asset.created_at,
        filename=asset.name,
        download_url=asset.url,
        browser_download_url=asset.browser_download_url,
    )


def get_asset(release: AttributeDict, type: VersionableType) -> AttributeDict | None:
    """
    Get mod assets from a release; excludes dev, source, and api jars
    :param release: A github release
    :return: A github release asset
    """
    tag_name = release.tag_name
    is_dev = tag_name.endswith("-dev")

    release_assets = [AttributeDict(a) for a in release.assets]
    for asset in release_assets:
        asset_name = asset.name

        if is_dev:
            # A dev release will have two "-dev" suffixes, so remove the first one
            asset_name = asset_name.replace("-dev", "", 1)

        if type == VersionableType.mod:
            if not asset_name.endswith(".jar") or any(asset_name.endswith(s) for s in ["dev.jar", "sources.jar", "api.jar", "api2.jar"]):
                continue
        elif type == VersionableType.config:
            if not asset_name.endswith(".zip"):
                continue

        return asset

    return None
