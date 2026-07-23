import httpx
import pytest

from daxxl.modpack_manager import GTNHModpackManager
from daxxl.utils import get_github_token


def test_services_share_a_single_assets_instance(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Every service must read and mutate the same AvailableAssets object.

    If the AssetService keeps its own copy, the update methods mutate the mods reached through
    the manager while `save_assets` serializes the AssetService's untouched copy. New mod
    versions and the daily/experimental counters are then silently dropped on save, and the
    next build fails with `version '<x>' not found for mod '<y>'`.
    """
    monkeypatch.setenv("GITHUB_TOKEN", "not-a-real-token")
    get_github_token.cache_clear()

    manager = GTNHModpackManager(httpx.AsyncClient())
    assets = manager.asset_service.assets

    assert manager.assets is assets
    assert manager.counter._assets is assets
    assert manager.downloader.assets is assets
    assert manager.comparison.assets is assets
    assert manager.update_service.assets is assets
