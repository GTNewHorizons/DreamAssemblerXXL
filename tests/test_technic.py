import asyncio
import hashlib
import io
import json
import shlex
import threading
import time
from types import SimpleNamespace
from unittest.mock import AsyncMock, create_autospec
from zipfile import ZIP_DEFLATED, ZIP_STORED, ZipFile

import httpx
import pytest

from daxxl.app_context import AppContext
from daxxl.assembler.platforms.generic_assembler import GenericAssembler
from daxxl.assembler.platforms.technic import TechnicAssembler, build_java_args_package, java_args_version
from daxxl.defs import SERVER_ASSETS_DIR, Archive, ModSource, Side
from daxxl.exceptions import ReleaseNotFoundException
from daxxl.models.available_assets import AvailableAssets
from daxxl.models.gtnh_config import GTNHConfig
from daxxl.models.gtnh_release import GTNHRelease
from daxxl.models.gtnh_version import ExtraAsset, GTNHVersion
from daxxl.models.mod_info import GTNHModInfo
from daxxl.models.mod_version_info import ModVersionInfo
from daxxl.release_controller import ReleaseController
from daxxl.services.download_service import DownloadService
from daxxl.services.solder import read_technic_packages
from daxxl.utils import normalize_archive_permissions


def lwjgl_profile(version="3.0.37"):
    return json.dumps(
        {
            "id": f"1.7.10-forge-lwjgl3ify-{version}",
            "mainClass": "com.gtnewhorizons.retrofuturabootstrap.MainStartOnFirstThread",
            "libraries": [{"name": f"com.github.GTNewHorizons:lwjgl3ify:{version}:forgePatches"}],
            "arguments": {"game": ["--tweakClass", "cpw.mods.fml.common.launcher.FMLTweaker"], "jvm": ["-Dfrom.lwjgl3ify=true"]},
        },
        indent=2,
    ).encode()


def test_java_patch_preserves_repeated_options_and_selects_java25():
    text = "# Comment\n-Dfile.encoding=UTF-8\n--add-opens\njava.base/java.io=ALL-UNNAMED\n--add-opens java.base/java.lang=ALL-UNNAMED\n"
    text += '"-Dmessage=two words"\n-XX:-UseCompactObjectHeaders\n-XX:+UseCompactObjectHeaders\n'
    content = build_java_args_package(text, lwjgl_profile())
    assert build_java_args_package(text, lwjgl_profile()) == content
    with ZipFile(io.BytesIO(content)) as archive:
        assert archive.namelist() == ["patches/gtnh-jvm.json", "bin/version.json"]
        assert archive.read("bin/version.json") == lwjgl_profile()
        assert archive.getinfo("bin/version.json").date_time == (1980, 1, 1, 0, 0, 0)
        assert archive.getinfo("patches/gtnh-jvm.json").date_time == (1980, 1, 1, 0, 0, 0)
        patch = json.loads(archive.read("patches/gtnh-jvm.json"))
    assert patch["javaVersion"] == {"component": "java-runtime-epsilon", "majorVersion": 25}
    assert patch["formatVersion"] == 1
    assert patch["+jvmArgs"] == [
        "-Dfile.encoding=UTF-8",
        "--add-opens",
        "java.base/java.io=ALL-UNNAMED",
        "--add-opens",
        "java.base/java.lang=ALL-UNNAMED",
        "-Dmessage=two words",
        "-XX:+UseCompactObjectHeaders",
    ]
    assert build_java_args_package(text + "\n-Dextra=true", lwjgl_profile()) != content
    new_content = build_java_args_package(text, lwjgl_profile("3.0.40"))
    assert java_args_version("2", hashlib.md5(new_content).hexdigest()) != java_args_version("2", hashlib.md5(content).hexdigest())


@pytest.fixture
def technic():
    assets = AvailableAssets.construct(
        config=GTNHConfig(name="config", repo_url="test", latest_version="1", versions=[GTNHVersion(version_tag="1", filename="config.zip")]),
        mods=[
            GTNHModInfo(name="regular", latest_version="1", side=Side.BOTH, versions=[GTNHVersion(version_tag="1", filename="regular-1.jar")]),
            GTNHModInfo(name="removed", latest_version="1", side=Side.BOTH, versions=[GTNHVersion(version_tag="1", filename="removed-1.jar")]),
            GTNHModInfo(
                name="lwjgl3ify",
                latest_version="3.0.40",
                side=Side.BOTH_JAVA9,
                versions=[GTNHVersion(version_tag=version, filename=f"lwjgl3ify-{version}.jar") for version in ("3.0.36", "3.0.37", "3.0.40")],
            ),
            GTNHModInfo(
                name="other-java9",
                latest_version="1",
                side=Side.CLIENT_JAVA9,
                versions=[GTNHVersion(version_tag="1", filename="other-java9-1.jar")],
            ),
            GTNHModInfo(
                name="external-java9",
                latest_version="1",
                side=Side.BOTH_JAVA9,
                source=ModSource.other,
                versions=[GTNHVersion(version_tag=version, filename=f"external-java9-{version}.jar") for version in ("0.9", "1")],
            ),
        ],
    )
    release = GTNHRelease(
        version="2",
        last_version="1",
        config="1",
        external_mods={"external-java9": ModVersionInfo(version="1")},
        github_mods={
            "regular": ModVersionInfo(version="1"),
            "lwjgl3ify": ModVersionInfo(version="3.0.37", side=Side.BOTH_JAVA9),
            "other-java9": ModVersionInfo(version="1"),
        },
    )
    previous = release.copy(deep=True)
    previous.version = "1"
    del previous.github_mods["other-java9"]
    previous.github_mods["removed"] = ModVersionInfo(version="1")
    previous.github_mods["lwjgl3ify"].version = "3.0.36"
    previous.external_mods["external-java9"].version = "0.9"
    context = create_autospec(
        AppContext,
        instance=True,
        assets=assets,
        mod_pack=SimpleNamespace(
            client_exclusions=[],
            client_java8_exclusions=[],
            client_java9_exclusions=[],
            server_exclusions=[],
            server_java8_exclusions=[],
            server_java9_exclusions=[],
        ),
        release_service=SimpleNamespace(get_release=lambda version: previous if version == "1" else None),
    )
    return TechnicAssembler(context, release)


@pytest.mark.parametrize("problem", ["missing-profile", "wrong-version", "missing-jar"])
def test_technic_errors_preserve_existing_update(technic, tmp_path, monkeypatch, problem):
    output = tmp_path / "technic"
    output.mkdir()
    existing = output / "update.zip"
    existing.write_bytes(b"previous archive")
    monkeypatch.setattr(technic, "get_archive_path", lambda side: existing)
    monkeypatch.setattr("daxxl.assembler.platforms.technic.get_asset_version_cache_location", lambda mod, version: tmp_path / version.filename)
    profile_path = tmp_path / "lwjgl3ify-3.0.37-version.json"
    technic.context.downloader = SimpleNamespace(download_version_json=AsyncMock(return_value=profile_path))
    if problem == "missing-profile":
        # A usable embedded copy must not be used as a fallback.
        with ZipFile(tmp_path / "lwjgl3ify-3.0.37.jar", "w") as jar:
            jar.writestr("me/eigenraven/lwjgl3ify/relauncher/version.json", lwjgl_profile())
    elif problem == "wrong-version":
        profile_path.write_bytes(lwjgl_profile("3.0.40"))
    else:
        profile_path.write_bytes(lwjgl_profile())
    with pytest.raises((ValueError, FileNotFoundError), match="lwjgl3ify"):
        asyncio.run(technic.assemble(Side.CLIENT))
    assert existing.read_bytes() == b"previous archive"
    assert list(output.iterdir()) == [existing]


def test_technic_compresses_at_most_four_mods_in_parallel_without_blocking_gui(technic, tmp_path, monkeypatch):
    import daxxl.assembler.platforms.technic as module

    mods = [(SimpleNamespace(name=f"mod-{index}"), GTNHVersion(version_tag="1", filename=f"mod-{index}.jar")) for index in range(8)]
    for mod, version in mods:
        (tmp_path / version.filename).write_bytes(mod.name.encode())
    monkeypatch.setattr(module, "get_asset_version_cache_location", lambda mod, version: tmp_path / version.filename)
    original = module._build_mod_zip
    barrier = threading.Barrier(4, timeout=5)
    gui_ready = threading.Event()
    worker_threads = set()
    staged_paths = []
    lock = threading.Lock()
    active = 0
    peak = 0

    def build(source, destination):
        nonlocal active, peak
        with lock:
            active += 1
            peak = max(peak, active)
            worker_threads.add(threading.get_ident())
            staged_paths.append(destination)
        try:
            barrier.wait()
            assert gui_ready.wait(5), "GUI event loop was blocked during compression"
            original(source, destination)
        finally:
            with lock:
                active -= 1

    monkeypatch.setattr(module, "_build_mod_zip", build)
    main_thread = threading.get_ident()
    callback_threads = []
    technic.task_progress_callback = lambda amount, message: callback_threads.append(threading.get_ident())

    async def run():
        with ZipFile(tmp_path / "parallel.zip", "w") as archive:
            task = asyncio.create_task(technic.add_mods(Side.CLIENT, mods, archive))
            while not task.done() and active == 0:
                await asyncio.sleep(0.001)
            gui_ready.set()
            await task

    asyncio.run(run())
    assert peak == 4
    assert main_thread not in worker_threads
    assert callback_threads == [main_thread] * len(mods)
    assert not any(path.exists() for path in staged_paths)
    with ZipFile(tmp_path / "parallel.zip") as archive:
        assert archive.namelist() == [f"mods/mod-{index}/mod-{index}-1.zip" for index in range(8)]


@pytest.mark.parametrize("cancel", [False, True])
def test_technic_waits_for_workers_before_cleaning_up_on_error_or_cancel(technic, tmp_path, monkeypatch, cancel):
    import daxxl.assembler.platforms.technic as module

    mods = technic.get_mods(Side.CLIENT)
    for mod, version in mods:
        (tmp_path / version.filename).write_bytes(mod.name.encode())
    monkeypatch.setattr(module, "get_asset_version_cache_location", lambda mod, version: tmp_path / version.filename)
    original = module._build_mod_zip
    started = threading.Event()
    release = threading.Event()
    completed = []
    staged_paths = []

    def build(source, destination):
        staged_paths.append(destination)
        started.set()
        if not cancel and source.name == "regular-1.jar":
            raise OSError("test compression failure")
        if cancel:
            assert release.wait(5)
        else:
            time.sleep(0.03)
        original(source, destination)
        completed.append(destination)

    monkeypatch.setattr(module, "_build_mod_zip", build)

    async def run():
        with ZipFile(tmp_path / "interrupted.zip", "w") as archive:
            task = asyncio.create_task(technic.add_mods(Side.CLIENT, mods, archive))
            if cancel:
                while not started.is_set():
                    await asyncio.sleep(0.001)
                task.cancel()
                await asyncio.sleep(0.01)
                assert not task.done(), "Cancellation must wait for workers before closing ZIPs and deleting temporary files"
                release.set()
                with pytest.raises(asyncio.CancelledError):
                    await task
            else:
                with pytest.raises(OSError, match="test compression failure"):
                    await task
            assert archive.namelist() == []

    asyncio.run(run())
    assert len(completed) == len(mods) - int(not cancel)
    assert not any(path.exists() for path in staged_paths)


@pytest.mark.parametrize("baseline", ["same_config", "changed_config", "first_release", "java_args_only"])
def test_single_update_archive_contains_only_new_or_changed_packages(technic, tmp_path, monkeypatch, baseline):
    import daxxl.assembler.platforms.technic as module

    technic.release.version = "2.9.0-RC-2"
    previous = technic.context.release_service.get_release("1")
    if baseline == "changed_config":
        previous.config = "0.9"
    elif baseline == "first_release":
        technic.release.last_version = None
    elif baseline == "java_args_only":
        previous.github_mods = technic.release.github_mods
        previous.external_mods = technic.release.external_mods
    mods = technic.get_mods(Side.CLIENT)
    expected = {("regular", "1"), ("lwjgl3ify", "3.0.37"), ("other-java9", "1"), ("external-java9", "1")}
    assert {(mod.name, version.version_tag) for mod, version in mods} == expected
    assert [mod.name for mod, _ in GenericAssembler(technic.context, technic.release).get_mods(Side.CLIENT)] == ["regular"]
    desired = expected | {("config", "1")}
    assert technic.get_package_versions(Side.CLIENT) == dict(desired)
    updates = desired.copy()
    if baseline != "first_release":
        updates.remove(("regular", "1"))
    config_changed = baseline in {"changed_config", "first_release"}
    if not config_changed:
        updates.remove(("config", "1"))
    if baseline == "java_args_only":
        updates = set()
    original_packages = {}
    for mod, version in mods:
        if (mod.name, version.version_tag) not in updates:
            continue  # Unchanged packages must not need local JARs.
        (tmp_path / version.filename).write_bytes(mod.name.encode())
        with io.BytesIO() as buffer:
            with ZipFile(buffer, "w", compression=ZIP_DEFLATED) as nested:
                nested.write(tmp_path / version.filename, arcname=f"mods/{version.filename}")
                asyncio.run(normalize_archive_permissions(nested))
            original_packages[mod.name] = buffer.getvalue()
    profile_path = tmp_path / "lwjgl3ify-3.0.37-version.json"
    profile_path.write_bytes(lwjgl_profile())
    technic.context.downloader = SimpleNamespace(download_version_json=AsyncMock(return_value=profile_path))
    if config_changed:
        with ZipFile(tmp_path / "config.zip", "w") as archive:
            archive.writestr("config/test.cfg", "some config")
    technic.changelog_path = tmp_path / "changes.md"
    technic.changelog_path.write_text("changes", encoding="utf-8")
    monkeypatch.setattr(module, "get_asset_version_cache_location", lambda mod, version: tmp_path / version.filename)
    monkeypatch.setattr("daxxl.assembler.platforms.generic_assembler.get_asset_version_cache_location", lambda mod, version: tmp_path / version.filename)
    monkeypatch.setattr(technic, "get_amount_of_files_in_locales", lambda: 0)
    monkeypatch.setattr(technic, "add_localisation_files", AsyncMock())
    output = tmp_path / "technic"
    output.mkdir()
    monkeypatch.setattr(module, "RELEASE_TECHNIC_DIR", output)
    progress = []
    technic.task_progress_callback = lambda amount, message: progress.append(amount)
    asyncio.run(technic.assemble(Side.CLIENT))
    path = output / "GT_New_Horizons_2.9.0-RC-2_(updated mods).zip"
    assert list(output.iterdir()) == [path]
    assert sum(progress) == pytest.approx(100)
    download = technic.context.downloader.download_version_json
    download.assert_awaited_once()
    assert download.await_args.args[1].version_tag == "3.0.37"
    selection, packages = read_technic_packages(path)
    assert selection == dict(desired)
    java = packages.pop("gtnh-java-args")
    assert java.version == f"2.9.0-rc-2-{java.md5[:12]}"
    assert {(package.name, package.version) for package in packages.values()} == updates
    with ZipFile(path) as archive:
        for name, version in updates & expected:
            entry = f"mods/{name}/{name}-{version}.zip"
            assert archive.getinfo(entry).compress_type == ZIP_STORED
            assert archive.read(entry) == original_packages[name], "Nested ZIP bytes/MD5 must not change"
        if config_changed:
            with ZipFile(io.BytesIO(archive.read("mods/config/config-1.zip"))) as nested:
                assert nested.read("config/test.cfg") == b"some config"
                assert nested.read("changes.md") == b"changes"
        data = archive.read(java.path)
        with ZipFile(io.BytesIO(data)) as nested:
            assert nested.read("bin/version.json") == lwjgl_profile()
            patch = json.loads(nested.read("patches/gtnh-jvm.json"))
            assert patch["javaVersion"]["majorVersion"] == 25
            args = (SERVER_ASSETS_DIR / "forge" / "java9args.txt").read_text(encoding="utf-8-sig")
            assert patch["+jvmArgs"] == shlex.split(args, comments=True) + ["-XX:+UseCompactObjectHeaders"]


def test_technic_filters_mixed_github_and_external_mods_with_release_side_overrides(technic):
    assets = []
    technic.release.github_mods.clear()
    technic.release.external_mods.clear()
    for prefix, source, entries in (
        ("github", ModSource.github, technic.release.github_mods),
        ("external", ModSource.other, technic.release.external_mods),
    ):
        for side in Side:
            name = f"{prefix}-{side.value.lower()}"
            assets.append(GTNHModInfo(name=name, latest_version="1", side=side, source=source, versions=[GTNHVersion(version_tag="1")]))
            entries[name] = ModVersionInfo(version="1")
    assets.append(GTNHModInfo(name="unused", latest_version="1", side=Side.BOTH, versions=[GTNHVersion(version_tag="1")]))
    technic.context.assets = AvailableAssets.construct(config=technic.context.assets.config, mods=assets)
    technic.release.github_mods["github-server"].side = Side.CLIENT
    technic.release.external_mods["external-client_java9"].side = Side.NONE
    expected = {
        "github-client",
        "github-both",
        "github-client_java9",
        "github-both_java9",
        "github-server",
        "external-client",
        "external-both",
        "external-both_java9",
    }
    assert {mod.name for mod, _ in technic.get_mods(Side.CLIENT)} == expected
    assert technic.get_package_versions(Side.CLIENT).keys() == {name.replace("_", "-") for name in expected} | {"config"}


def test_technic_rejects_a_missing_previous_release(technic):
    technic.release.last_version = "missing"
    with pytest.raises(ReleaseNotFoundException, match="previous release 'missing'"):
        asyncio.run(technic.assemble(Side.CLIENT))


def test_regenerating_refreshes_lwjgl_profile_at_the_same_tag(technic, tmp_path, monkeypatch):
    previous = technic.context.release_service.get_release("1")
    previous.github_mods = technic.release.github_mods
    previous.external_mods = technic.release.external_mods
    path = tmp_path / "update.zip"
    monkeypatch.setattr(technic, "get_archive_path", lambda side: path)
    monkeypatch.setattr("daxxl.assembler.downloader.CACHE_DIR", tmp_path / "cache")
    version = technic.context.assets.get_mod("lwjgl3ify").get_version("3.0.37")
    assert version is not None
    release_url = "https://github.com/GTNewHorizons/lwjgl3ify/releases/download/3.0.37/"
    version.browser_download_url = release_url + "lwjgl3ify-3.0.37.jar"
    version.extra_assets = [ExtraAsset(filename="version.json", download_url="https://api.github.com/repos/GTNewHorizons/lwjgl3ify/releases/assets/200")]
    original = lwjgl_profile()
    corrected = original.replace(b"-Dfrom.lwjgl3ify=true", b"-Dfrom.lwjgl3ify=corrected")
    profiles = iter((original, None, corrected))

    def handle(request):
        assert str(request.url) == release_url + "version.json"
        assert request.headers["Cache-Control"] == "no-cache"
        profile = next(profiles)
        return httpx.Response(404) if profile is None else httpx.Response(200, content=profile)

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            technic.context.downloader = DownloadService(client, technic.context.assets)
            await technic.assemble(Side.CLIENT)
            selection, packages = read_technic_packages(path)
            first_version = packages["gtnh-java-args"].version
            first_zip = path.read_bytes()
            with pytest.raises(httpx.HTTPStatusError):
                await technic.assemble(Side.CLIENT)
            assert path.read_bytes() == first_zip

            await technic.assemble(Side.CLIENT)
            updated_selection, packages = read_technic_packages(path)
            assert updated_selection == selection
            java = packages["gtnh-java-args"]
            assert java.version != first_version
            with ZipFile(path) as update, ZipFile(io.BytesIO(update.read(java.path))) as nested:
                assert nested.read("bin/version.json") == corrected

    asyncio.run(run())


def test_assembly_cache_tracks_release_edits_and_resets_progress(monkeypatch):
    progress = {"task": 0, "global": 0}

    def advance(bar, amount):
        progress[bar] += amount

    controller = ReleaseController(
        lambda amount, _: advance("task", amount),
        lambda amount, _: advance("global", amount),
        lambda: progress.update({"global": 0}),
        lambda: progress.update(task=0),
    )
    controller.version = "2"
    controller.gtnh_config = "first"
    controller.github_mods = {"lwjgl3ify": ModVersionInfo(version="3.0.37")}
    download = AsyncMock()
    monkeypatch.setattr(controller, "get_context", AsyncMock(return_value=SimpleNamespace(downloader=SimpleNamespace(download_release=download))))
    assembled = []

    class TestAssembler:
        def __init__(self, context, release, **kwargs):
            self.release = release
            self.assemble_zip = self.assemble_prism = self.assemble_modrinth = self.assemble_curse = self.assemble_mobile = None

        async def assemble_technic(self, side, verbose):
            assembled.append((self.release.config, self.release.github_mods["lwjgl3ify"].version))
            advance("task", 100)

    monkeypatch.setattr("daxxl.release_controller.ReleaseAssemblerController", TestAssembler)

    async def run():
        await controller.pre_assembling()  # A preceding changelog action cached the first selection.
        controller.set_modpack_version("second")
        await controller.assemble_release(Side.CLIENT, Archive.TECHNIC)
        controller.set_github_mod_version("lwjgl3ify", "3.0.40")
        await controller.assemble_release(Side.CLIENT, Archive.TECHNIC)
        await controller.assemble_release(Side.CLIENT, Archive.TECHNIC)

    asyncio.run(run())
    assert assembled == [("second", "3.0.37"), ("second", "3.0.40"), ("second", "3.0.40")]
    assert download.await_count == 3  # Only the identical last run can reuse the cached inputs.
    assert progress == {"task": 100, "global": 100}
