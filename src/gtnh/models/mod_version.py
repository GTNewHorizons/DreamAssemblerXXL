from datetime import datetime
from typing import Optional

from github.GitRelease import GitRelease
from github.GitReleaseAsset import GitReleaseAsset
from pydantic import BaseModel, Field
from structlog import get_logger

log = get_logger(__name__)


class ModVersion(BaseModel):
    version_tag: str
    prerelease: bool = Field(default=False)
    tagged_at: Optional[datetime] = Field(default=None)
    filename: Optional[str] = Field(default=None)
    download_url: Optional[str] = Field(default=None)
    browser_download_url: Optional[str] = Field(default=None)


def version_from_release(release: GitRelease) -> ModVersion | None:
    """
    Get ModVersion and assets from a GitRelease
    :param release: GithubRelease
    :return: ModVersion
    """
    version = release.tag_name
    asset = get_mod_asset(release)

    if not asset:
        return None

    return ModVersion(
        version_tag=version,
        prerelease=release.prerelease,
        tagged_at=asset.created_at,
        filename=asset.name,
        download_url=asset.url,
        browser_download_url=asset.browser_download_url,
    )


def get_mod_asset(release: GitRelease) -> GitReleaseAsset | None:
    """
    Get mod assets from a release; excludes dev, source, and api jars
    :param release: GithubRelease
    :return: GithubReleaseAsset
    """
    tag_name = release.tag_name
    is_dev = tag_name.endswith("-dev")

    release_assets = release.get_assets()
    for asset in release_assets:
        asset_name = asset.name

        if is_dev:
            # A dev release will have two "-dev" suffixes, so remove the first one
            asset_name = asset_name.replace("-dev", "", 1)

        if not asset_name.endswith(".jar") or any(asset_name.endswith(s) for s in ["dev.jar", "sources.jar", "api.jar", "api2.jar"]):
            continue

        return asset

    return None
