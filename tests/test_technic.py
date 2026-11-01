import asyncio
import io
import json
import shlex
import threading
import time
from types import SimpleNamespace
from unittest.mock import AsyncMock, create_autospec
from zipfile import ZIP_DEFLATED, ZIP_STORED, ZipFile

import pytest

from daxxl.app_context import AppContext
from daxxl.assembler.platforms.generic_assembler import GenericAssembler
from daxxl.assembler.platforms.technic import DifferentialUpdateMode, TechnicAssembler, build_java_args_package
from daxxl.defs import SERVER_ASSETS_DIR, ModSource, Side
from daxxl.models.available_assets import AvailableAssets
from daxxl.models.gtnh_release import GTNHRelease
from daxxl.models.gtnh_version import GTNHVersion
from daxxl.models.mod_info import GTNHModInfo
from daxxl.models.mod_version_info import ModVersionInfo
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


@pytest.fixture
def technic():
    assets = AvailableAssets.construct(
        mods=[
            GTNHModInfo(name="regular", latest_version="1", side=Side.BOTH, versions=[GTNHVersion(version_tag="1", filename="regular-1.jar")]),
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
        ]
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
        comparison=SimpleNamespace(
            get_new_mods=lambda current, old: {"lwjgl3ify", "other-java9", "external-java9"},
            get_changed_mods=lambda current, old: {"lwjgl3ify", "other-java9", "external-java9"},
            get_removed_mods=lambda current, old: {"lwjgl3ify", "other-java9", "external-java9"},
        ),
    )
    return TechnicAssembler(context, release)


@pytest.mark.parametrize("problem", ["missing-profile", "wrong-version"])
def test_technic_profile_errors_preserve_existing_full_archive(technic, tmp_path, monkeypatch, problem):
    existing = tmp_path / "full.zip"
    existing.write_bytes(b"previous archive")
    monkeypatch.setattr(technic, "get_archive_path", lambda side: existing)
    monkeypatch.setattr("daxxl.assembler.platforms.technic.get_asset_version_cache_location", lambda mod, version: tmp_path / version.filename)
    profile_path = tmp_path / "lwjgl3ify-3.0.37-version.json"
    technic.context.downloader = SimpleNamespace(download_version_json=AsyncMock(return_value=profile_path))
    if problem == "missing-profile":
        # A usable embedded copy must not be used as a fallback.
        with ZipFile(tmp_path / "lwjgl3ify-3.0.37.jar", "w") as jar:
            jar.writestr("me/eigenraven/lwjgl3ify/relauncher/version.json", lwjgl_profile())
    else:
        profile_path.write_bytes(lwjgl_profile("3.0.40"))
    with pytest.raises((ValueError, FileNotFoundError), match="lwjgl3ify"):
        asyncio.run(technic.assemble(Side.CLIENT))
    assert existing.read_bytes() == b"previous archive"


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


def test_full_and_partial_archives_preserve_packages_profile_arguments_and_progress(technic, tmp_path, monkeypatch):
    import daxxl.assembler.platforms.technic as module

    technic.release.version = "2.9.0-RC-2"
    mods = technic.get_mods(Side.CLIENT)
    expected = {("regular", "1"), ("lwjgl3ify", "3.0.37"), ("other-java9", "1"), ("external-java9", "1")}
    assert {(mod.name, version.version_tag) for mod, version in mods} == expected
    assert [mod.name for mod, _ in GenericAssembler(technic.context, technic.release).get_mods(Side.CLIENT)] == ["regular"]
    original_packages = {}
    for mod, version in mods:
        (tmp_path / version.filename).write_bytes(mod.name.encode())
        with io.BytesIO() as buffer:
            with ZipFile(buffer, "w", compression=ZIP_DEFLATED) as nested:
                nested.write(tmp_path / version.filename, arcname=f"mods/{version.filename}")
                asyncio.run(normalize_archive_permissions(nested))
            original_packages[mod.name] = buffer.getvalue()
    profile_path = tmp_path / "lwjgl3ify-3.0.37-version.json"
    profile_path.write_bytes(lwjgl_profile())
    technic.context.downloader = SimpleNamespace(download_version_json=AsyncMock(return_value=profile_path))
    config_version = GTNHVersion(version_tag="1", filename="config.zip")
    with ZipFile(tmp_path / "config.zip", "w") as archive:
        archive.writestr("config/test.cfg", "some config")
    technic.changelog_path = tmp_path / "changes.md"
    technic.changelog_path.write_text("changes", encoding="utf-8")
    monkeypatch.setattr(module, "get_asset_version_cache_location", lambda mod, version: tmp_path / version.filename)
    monkeypatch.setattr(technic, "get_config", lambda: (SimpleNamespace(name="config"), config_version))
    monkeypatch.setattr(technic, "get_amount_of_files_in_config", lambda side: 1)
    monkeypatch.setattr(technic, "get_amount_of_files_in_locales", lambda: 0)
    monkeypatch.setattr(technic, "add_localisation_files", AsyncMock())
    monkeypatch.setattr(technic, "generate_readme", lambda: None)
    monkeypatch.setattr(technic, "get_archive_path", lambda side: tmp_path / "full.zip")
    monkeypatch.setattr(technic, "get_updated_mods_archive_path", lambda: tmp_path / "updated.zip")
    monkeypatch.setattr(technic, "get_new_mods_archive_path", lambda: tmp_path / "new.zip")
    monkeypatch.setattr(technic, "get_removed_modlist_path", lambda: tmp_path / "removed.txt")
    config_copy = AsyncMock(wraps=technic._add_config_files)
    monkeypatch.setattr(technic, "_add_config_files", config_copy)
    original = module._build_mod_zip
    compressed_sources = []

    def build(source, destination):
        compressed_sources.append(source)
        original(source, destination)

    monkeypatch.setattr(module, "_build_mod_zip", build)
    phases = [0.0]
    technic.task_progress_callback = lambda amount, message: phases.__setitem__(-1, phases[-1] + amount)
    technic.current_task_reset_callback = lambda: phases.append(0.0)
    asyncio.run(technic.assemble(Side.CLIENT))
    assert len(compressed_sources) == len(mods)
    config_copy.assert_awaited_once()
    assert phases == pytest.approx([100, 100])
    assert technic._reuse_archive is None
    download = technic.context.downloader.download_version_json
    download.assert_awaited()
    assert {call.args[1].version_tag for call in download.await_args_list} == {"3.0.37"}
    assert {(package.name, package.version) for package in read_technic_packages(tmp_path / "full.zip")} == (
        expected | {("config", "1"), ("gtnh-java-args", "2.9.0-rc-2")}
    )
    with ZipFile(tmp_path / "full.zip") as full:
        for name, version in expected:
            entry = f"mods/{name}/{name}-{version}.zip"
            assert full.getinfo(entry).compress_type == ZIP_STORED
            assert full.read(entry) == original_packages[name], "Nested ZIP bytes/MD5 must not change"
        java_packages = [name for name in full.namelist() if name.startswith("mods/gtnh-java-args/")]
        assert len(java_packages) == 1
        java_package = java_packages[0]
        data = full.read(java_package)
        assert java_package == "mods/gtnh-java-args/gtnh-java-args-2.9.0-rc-2.zip"
        with ZipFile(io.BytesIO(data)) as nested:
            assert nested.read("bin/version.json") == lwjgl_profile()
            patch = json.loads(nested.read("patches/gtnh-jvm.json"))
            assert patch["javaVersion"]["majorVersion"] == 25
            args = (SERVER_ASSETS_DIR / "forge" / "java9args.txt").read_text(encoding="utf-8-sig")
            assert patch["+jvmArgs"] == shlex.split(args, comments=True) + ["-XX:+UseCompactObjectHeaders"]
        for path in (tmp_path / "updated.zip", tmp_path / "new.zip"):
            with ZipFile(path) as partial:
                assert partial.namelist()
                assert ("mods/config/config-1.zip" in partial.namelist()) == (path.name == "updated.zip")
                assert (java_package in partial.namelist()) == (path.name == "updated.zip")
                for name in partial.namelist():
                    assert partial.getinfo(name).compress_type == ZIP_STORED
                    assert partial.read(name) == full.read(name)


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
    technic.context.assets = AvailableAssets.construct(mods=assets)
    technic.release.github_mods["github-server"].side = Side.CLIENT
    technic.release.external_mods["external-client_java9"].side = Side.NONE
    technic.context.comparison.get_new_mods = lambda current, old: set(current.github_mods) | set(current.external_mods)
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
    assert {mod.name for mod, _ in technic.differential_update(Side.CLIENT, DifferentialUpdateMode.NEW_MODS)} == expected


@pytest.mark.parametrize("mode", [DifferentialUpdateMode.UPDATED_MODS, DifferentialUpdateMode.REMOVED_MODS])
def test_technic_differential_selects_java9_mods_from_correct_release(technic, mode):
    mods = technic.differential_update(Side.CLIENT, mode)
    expected_version = "3.0.36" if mode == DifferentialUpdateMode.REMOVED_MODS else "3.0.37"
    external_version = "0.9" if mode == DifferentialUpdateMode.REMOVED_MODS else "1"
    assert {(mod.name, version.version_tag) for mod, version in mods} == {
        ("lwjgl3ify", expected_version),
        ("other-java9", "1"),
        ("external-java9", external_version),
    }
