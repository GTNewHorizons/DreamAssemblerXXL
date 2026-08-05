import asyncio
import json
from pathlib import Path, PurePosixPath
from urllib.parse import urlparse
from zipfile import ZipFile

import pytest
from httpx import AsyncClient

from daxxl.app_context import AppContext
from daxxl.assembler.platforms.zip_assembler import ZipAssembler
from daxxl.defs import Side
from daxxl.fullpack_manifest import write_fullpack_manifest


def test_daily_manifest_writes_a_matching_fullpack_installation_plan(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "test")
    client = AsyncClient()
    context = AppContext(client)
    release = context.release_service.get_release("daily")
    assert release is not None
    assembler = ZipAssembler(context, release)

    originals = {
        "config/txloader/load/mainmenu/version.txt": b"stale",
        "config/GTNewHorizons/dreamcraft.cfg": b"S:ModPackVersion=stale\n",
        "config/DreamCoreMod.properties": b"displayedModpackVersion=stale\n",
    }
    config_path = tmp_path / "config.zip"
    with ZipFile(config_path, "w") as archive:
        for destination, content in originals.items():
            archive.writestr(destination, content)

    manifest_path = tmp_path / "releases/manifests/daily.json"
    write_fullpack_manifest(manifest_path, assembler, asset_path=lambda _asset, _version: config_path)
    plan = json.loads((manifest_path.parent / "fullpack" / manifest_path.name).read_text(encoding="utf-8"))
    asyncio.run(client.aclose())

    assert set(plan) == {"version", "files", "archives", "textFiles"}
    assert plan["version"] == 1

    files = plan["files"]
    assert isinstance(files, list)
    files_by_path = {entry["path"]: entry for entry in files}
    resolved_mods = assembler.get_mods(Side.CLIENT_JAVA9)
    assert len(files) == len(resolved_mods) + 1

    for mod, version in resolved_mods:
        assert version.filename is not None
        entry = files_by_path[f"mods/{version.filename}"]
        expected_url = version.browser_download_url if mod.is_github() and not mod.private else version.download_url
        assert entry["url"] == expected_url

        if mod.is_github():
            assert mod.repo_url is not None
            repo = PurePosixPath(urlparse(mod.repo_url).path).name
            assert entry["owner"] == repo
            if mod.repo_url.startswith("https://github.com/GTNewHorizons/"):
                assert entry["maven"] == f"com.github.GTNewHorizons:{mod.name}:{version.version_tag}"
        else:
            assert "owner" not in entry
            assert "maven" not in entry

        if mod.is_github() and mod.private:
            assert entry["authentication"] == "github"
        else:
            assert "authentication" not in entry

    lwjgl = next(version for mod, version in resolved_mods if mod.name == "lwjgl3ify")
    launcher_asset = next(asset for asset in lwjgl.extra_assets if (asset.filename or "").endswith("forgePatches.jar"))
    assert files_by_path[".gtnh/launcher/lwjgl3ify-forgePatches.jar"] == {
        "path": ".gtnh/launcher/lwjgl3ify-forgePatches.jar",
        "url": launcher_asset.browser_download_url,
    }

    archives = plan["archives"]
    assert isinstance(archives, list)
    config, config_version = assembler.get_config()
    exclusions = list(assembler.exclusions[Side.CLIENT_JAVA9].exclusions)
    exclusions.extend(sorted(assembler.excluded_config_files - set(exclusions)))
    assert archives[0] == {
        "url": config_version.browser_download_url,
        "exclude": exclusions,
    }
    assert archives[1:] == [
        {
            "url": version.browser_download_url,
            "keepExisting": True,
        }
        for version in context.assets.translations.versions
    ]

    assert plan["textFiles"] == {destination: assembler._modify_config_file(destination, content).decode("utf-8") for destination, content in originals.items()}

    removed_fields = {"packId", "variant", "runtime", "mode", "role", "size", "sha256"}
    for entry in [*files, *archives]:
        assert removed_fields.isdisjoint(entry)
