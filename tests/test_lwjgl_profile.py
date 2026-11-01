import asyncio
import json

import httpx
import pytest

from daxxl.assembler.downloader import get_asset_version_cache_location
from daxxl.defs import VersionableType
from daxxl.models.available_assets import AvailableAssets
from daxxl.models.gtnh_version import ExtraAsset, GTNHVersion, get_asset
from daxxl.models.mod_info import GTNHModInfo
from daxxl.services.download_service import DownloadService
from daxxl.utils import AttributeDict


def version_info(tag):
    return GTNHVersion(
        version_tag=tag,
        filename=f"lwjgl3ify-{tag}.jar",
        download_url="https://api.github.com/repos/GTNewHorizons/lwjgl3ify/releases/assets/100",
        browser_download_url=f"https://github.com/GTNewHorizons/lwjgl3ify/releases/download/{tag}/lwjgl3ify-{tag}.jar",
    )


def test_old_catalog_downloads_exact_tag_and_keeps_versions_separate(tmp_path, monkeypatch):
    monkeypatch.setattr("daxxl.assembler.downloader.CACHE_DIR", tmp_path)
    versions = [version_info(tag) for tag in ("3.0.37", "3.0.40")]
    asset = GTNHModInfo(name="lwjgl3ify", latest_version="3.0.40", versions=versions)
    requests = []

    def handle(request):
        assert "authorization" not in request.headers
        requests.append(str(request.url))
        tag = request.url.path.split("/")[-2]
        return httpx.Response(200, json={"id": f"1.7.10-lwjgl3ify-{tag}"})

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            service = DownloadService(client, AvailableAssets.construct(mods=[asset]))
            old = await service.download_version_json(asset, versions[0])
            new = await service.download_version_json(asset, versions[1])
            assert old != new
            assert old.name == "lwjgl3ify-3.0.37-version.json"
            assert new.name == "lwjgl3ify-3.0.40-version.json"
            assert json.loads(old.read_bytes())["id"] == "1.7.10-lwjgl3ify-3.0.37"
            assert json.loads(new.read_bytes())["id"] == "1.7.10-lwjgl3ify-3.0.40"
            assert await service.download_version_json(asset, versions[0]) == old
            assert not old.with_suffix(".json.part").exists()

    asyncio.run(run())
    assert requests == [f"https://github.com/GTNewHorizons/lwjgl3ify/releases/download/{tag}/version.json" for tag in ("3.0.37", "3.0.40")]


def test_indexed_profile_uses_normal_asset_download_and_shared_versioned_cache(tmp_path, monkeypatch):
    monkeypatch.setattr("daxxl.assembler.downloader.CACHE_DIR", tmp_path)
    monkeypatch.setattr("daxxl.services.download_service.get_github_token", lambda: "test-token")
    version = version_info("3.0.37")
    profile_url = "https://api.github.com/repos/GTNewHorizons/lwjgl3ify/releases/assets/200"
    release = AttributeDict(
        tag_name="3.0.37",
        assets=[
            {"name": "version.json", "url": profile_url},
            {"name": version.filename, "url": version.download_url},
            {"name": "lwjgl3ify-3.0.37-sources.jar"},
        ],
    )
    primary, extras = get_asset(release, VersionableType.mod)
    assert primary is not None
    assert primary.name == version.filename
    version.extra_assets = [ExtraAsset(filename=item.name, download_url=item.url) for item in extras]
    asset = GTNHModInfo(name="lwjgl3ify", latest_version="3.0.37", versions=[version])
    requests = []

    def handle(request):
        assert request.headers["Authorization"] == "token test-token"
        requests.append(str(request.url))
        return httpx.Response(200, content=b'{"id":"release-profile"}' if str(request.url) == profile_url else b"main jar")

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            service = DownloadService(client, AvailableAssets.construct(mods=[asset]))
            await service.download_asset(asset, "3.0.37", is_github=True)
            path = await service.download_version_json(asset, version)
            assert path == get_asset_version_cache_location(asset, version, "version.json")
            assert path.read_bytes() == b'{"id":"release-profile"}'

    asyncio.run(run())
    assert requests == [version.download_url, profile_url]


def test_missing_release_asset_fails_without_leaving_a_cached_profile(tmp_path, monkeypatch):
    monkeypatch.setattr("daxxl.assembler.downloader.CACHE_DIR", tmp_path)
    version = version_info("3.0.37")
    asset = GTNHModInfo(name="lwjgl3ify", latest_version="3.0.37", versions=[version])
    requests = []

    def handle(request):
        requests.append(str(request.url))
        return httpx.Response(404)

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            service = DownloadService(client, AvailableAssets.construct(mods=[asset]))
            with pytest.raises(httpx.HTTPStatusError):
                await service.download_version_json(asset, version)
            path = get_asset_version_cache_location(asset, version, "version.json")
            assert not path.exists()
            assert not path.with_suffix(".json.part").exists()

    asyncio.run(run())
    assert requests == ["https://github.com/GTNewHorizons/lwjgl3ify/releases/download/3.0.37/version.json"]
