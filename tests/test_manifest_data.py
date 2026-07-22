from collections import Counter

from daxxl.defs import AVAILABLE_ASSETS_FILE, ROOT_DIR
from daxxl.models.available_assets import AvailableAssets


def test_asset_names_are_unique() -> None:
    assets = AvailableAssets.parse_raw((ROOT_DIR / AVAILABLE_ASSETS_FILE).read_text(encoding="utf-8"))
    duplicates = sorted(name for name, count in Counter(mod.name for mod in assets.mods).items() if count > 1)

    assert duplicates == [], f"duplicate assets: {', '.join(duplicates)}"