import asyncio
import hashlib
import io
import json
import threading
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, create_autospec
from zipfile import ZipFile

import httpx
import pytest
from structlog.testing import capture_logs

from daxxl.services.solder import SolderAPI, publish_solder, read_technic_packages
from daxxl.services.solder_config import load_solder_config


def zip_bytes(filename, content):
    buffer = io.BytesIO()
    with ZipFile(buffer, "w") as archive:
        archive.writestr(filename, content)
    return buffer.getvalue()


def test_gui_config_is_generated_blank_then_read_without_overwriting(tmp_path, monkeypatch):
    for key in ("SOLDER_URL", "SOLDER_PACK", "SOLDER_TOKEN"):
        monkeypatch.setenv(key, "environment-value")
    path = tmp_path / "solder.json"
    blank = {"url": "", "pack": "", "token": ""}
    assert load_solder_config(path) == blank
    assert json.loads(path.read_text()) == blank
    settings = {"url": "https://solder.test", "pack": "pack", "token": "secret", "min_java": "25", "requests_per_minute": "1200"}
    path.write_text(json.dumps(settings), encoding="utf-8-sig")
    original = path.read_bytes()
    assert load_solder_config(path) == settings
    assert path.read_bytes() == original
    settings["url"] = "https://other.test"
    path.write_text(json.dumps(settings), encoding="utf-8")
    assert load_solder_config(path) == settings


@pytest.mark.parametrize("content", ['{"token":"private-secret",', '{"token":{"secret":"private-secret"}}'])
def test_invalid_config_reports_path_without_secret(tmp_path, content):
    path = tmp_path / "solder.json"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(ValueError) as error:
        load_solder_config(path)
    assert str(path) in str(error.value)
    assert "private-secret" not in str(error.value)


@pytest.mark.parametrize("fail", [False, True])
def test_gui_publication_uses_config_and_restores_progress_on_failure(tmp_path, monkeypatch, fail):
    import daxxl.gui.gui as gui

    archive = tmp_path / "GT_New_Horizons_2_(technic).zip"
    archive.write_bytes(b"archive checked by publisher")
    monkeypatch.setattr(gui, "RELEASE_TECHNIC_DIR", tmp_path)
    monkeypatch.setattr(
        gui,
        "load_solder_config",
        lambda: {
            "url": "https://solder.test",
            "pack": "pack",
            "token": "test-token",
            "requests_per_minute": "600",
        },
    )
    values = {"task": 50, "global": 75}

    async def simulate(**kwargs):
        assert values == {"task": 0, "global": 0}
        kwargs["current_task_reset_callback"]()
        kwargs["task_progress_callback"](30, "Processing")
        kwargs["global_progress_callback"](25, "Checking")
        kwargs["progress"]("Waiting for Solder")
        assert values == {"task": 30, "global": 25}
        if fail:
            raise RuntimeError("Publication failed")
        kwargs["task_progress_callback"](70, "Done")
        kwargs["global_progress_callback"](75, "Done")

    def unexpected_popup(*args, **kwargs):
        raise AssertionError("Unexpected popup")

    publisher = AsyncMock(side_effect=simulate)
    monkeypatch.setattr(gui, "publish_solder", publisher)
    monkeypatch.setattr(gui, "showinfo", unexpected_popup)
    errors = []
    monkeypatch.setattr("daxxl.gui.lib.decorators.showerror", lambda *args: errors.append(args))
    window = create_autospec(
        gui.Window,
        instance=True,
        controller=SimpleNamespace(version="2"),
        toggled=True,
        current_task_reset_callback=lambda: values.update(task=0),
        global_reset_callback=lambda: values.update({"global": 0}),
        progress_callback=lambda amount, message: values.update(task=values["task"] + amount),
        global_callback=lambda amount, message: values.update({"global": values["global"] + amount}),
    )
    window.trigger_toggle = lambda: setattr(window, "toggled", not window.toggled)
    if fail:
        with pytest.raises(RuntimeError, match="Publication failed"):
            asyncio.run(gui.Window.publish_solder(window))
    else:
        asyncio.run(gui.Window.publish_solder(window))
    publisher.assert_awaited_once()
    assert publisher.call_args.kwargs["archive"] == archive
    assert publisher.call_args.kwargs["token"] == "test-token"
    assert publisher.call_args.kwargs["requests_per_minute"] == 600
    assert window.toggled
    assert values == ({"task": 0, "global": 0} if fail else {"task": 100, "global": 100})
    assert len(errors) == int(fail)


@pytest.mark.parametrize("options,interval", [({}, 0.0525), ({"requests_per_minute": 60}, 1.05)])
def test_api_respects_configured_request_limit(monkeypatch, options, interval):
    clock = 0.0
    starts = []

    async def sleep(delay):
        nonlocal clock
        clock += delay

    def handle(request):
        starts.append(clock)
        return httpx.Response(200, json={})

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            with monkeypatch.context() as patch:
                patch.setattr(asyncio.get_running_loop(), "time", lambda: clock)
                patch.setattr(asyncio, "sleep", sleep)
                api = SolderAPI(client, "https://solder.test", "test-token", lambda _: None, **options)
                for _ in range(3):
                    await api.request("GET", "token")

    asyncio.run(run())
    assert starts == pytest.approx([0, interval, 2 * interval])


class SolderServer:
    """Protocol double: drafts are unreadable, existing versions are global, old build reads are forbidden."""

    def __init__(self, archive: Path):
        self.packages = read_technic_packages(archive)
        with ZipFile(archive) as file:
            self.files = {name: file.read(name) for name in file.namelist()}
        self.versions = {
            ("same", "1"): self.mod("same", "1", self.files["mods/same/same-1.zip"]),
            ("changed", "1"): self.mod("changed", "1", b"old"),
            ("removed", "1"): self.mod("removed", "1", b"removed"),
            ("modpack", "1.7.10-10.13.4.1614-version-less"): self.mod("modpack", "1.7.10-10.13.4.1614-version-less", b"loader"),
        }
        self.mod_names = {name for name, _ in self.versions}
        self.existing_builds = ["1"]
        self.build = None
        self.deleted_builds = []
        self.mods = {}
        self.pointers = {"latest": "1", "recommended": "1"}
        self.calls = []
        self.waits = []
        self.rate_limited = False
        self.bad_manifest = False
        self.reject = None

    @staticmethod
    def mod(name, version, content):
        return {
            "name": name,
            "version": version,
            "md5": hashlib.md5(content).hexdigest(),
            "filesize": len(content),
            "url": f"https://mirror.test/mods/{name}/{name}-{version}.zip",
        }

    def handle(self, request):
        method, path = request.method, request.url.path
        data = json.loads(request.content) if request.content else None
        self.calls.append((method, path, data))
        if request.url.host == "mirror.test":
            assert "authorization" not in request.headers
            assert all(method == "GET" for method, _, _ in self.calls), "Verification must precede all writes"
            return httpx.Response(200, content=self.files[path.lstrip("/")])
        assert request.headers["authorization"] == "Bearer test-secret"
        if self.reject and (method, path) == self.reject[:2]:
            if self.reject[2] == "timeout":
                raise httpx.ReadTimeout("Lost response", request=request)
            return httpx.Response(self.reject[2], json={"error": "Rejected test-secret"}, headers={"Retry-After": "2"})
        if method == "GET":
            if path == "/api/token":
                return httpx.Response(200, json={"tokens": []})
            if path == "/api/modpack":
                return httpx.Response(200, json={"mirror_url": "https://mirror.test/", "modpacks": {"pack": "Pack"}})
            if path == "/api/modpack/pack":
                return httpx.Response(200, json={"builds": self.existing_builds, **self.pointers})
            if path.startswith("/api/modpack/pack/") and path != "/api/modpack/pack/2":
                raise AssertionError("Publication must not read any previous build")
            if path == "/api/modpack/pack/2" and self.build and self.build["is_published"]:
                assert self.build["private"] is True
                assert not any(method == "PUT" and path == "/api/modpack/pack" for method, path, _ in self.calls)
                return httpx.Response(
                    200,
                    json={
                        "minecraft": self.build["minecraft"],
                        "java": self.build["min_java"],
                        "memory": self.build["min_memory"],
                        "java_runtime": self.build["java_runtime"],
                        "forge": self.build["forge"],
                        "mods": [] if self.bad_manifest else list(self.mods.values()),
                    },
                )
            if path == "/api/mod":
                return httpx.Response(200, json={"mods": {name: name for name in self.mod_names}})
            if path.startswith("/api/mod/"):
                _, _, _, name, version = path.split("/")
                remote = self.versions.get((name, version))
                return httpx.Response(200, json=remote) if remote else httpx.Response(404, json={"error": "missing"})
        if method == "DELETE" and path == "/api/modpack/pack/2":
            if self.build is None:
                return httpx.Response(404, json={"error": "Build not found"})
            self.deleted_builds.append(self.build)
            self.build = None
            self.mods = {}
            self.existing_builds = [version for version in self.existing_builds if version != "2"]
            return httpx.Response(200, json={"success": "Build deleted"})
        assert isinstance(data, dict), "Write requests must have a JSON object body"
        if method == "POST" and path == "/api/modpack/pack/build":
            assert "clone_from" not in data and "clone_from_modpack" not in data
            if self.build is not None:
                return httpx.Response(422, json={"error": "Build version already exists"})
            self.build = data
            self.mods = {}
            return httpx.Response(201, json=data)
        if method == "POST" and path == "/api/mod":
            assert data["name"] not in self.mod_names
            self.mod_names.add(data["name"])
            return httpx.Response(201, json=data)
        if method == "POST" and path.endswith("/version"):
            if not self.rate_limited:
                self.rate_limited = True
                return httpx.Response(429, headers={"Retry-After": "7"}, json={"message": "Too Many Requests"})
            name = path.split("/")[3]
            assert name in self.mod_names
            remote = self.mod(name, data["version"], self.files[f"mods/{name}/{name}-{data['version']}.zip"])
            assert data["md5"] == remote["md5"] and data["filesize"] == remote["filesize"]
            self.versions[name, data["version"]] = remote
            return httpx.Response(201, json=remote)
        if method == "POST" and path == "/api/modpack/pack/2/mod":
            name = data["mod_slug"]
            assert name not in self.mods
            self.mods[name] = self.versions[name, data["mod_version"]]
            return httpx.Response(200, json={"success": "OK"})
        if method == "PUT" and path == "/api/modpack/pack/2":
            assert self.build is not None
            self.build.update(data)
            return httpx.Response(200, json=self.build)
        if method == "PUT" and path == "/api/modpack/pack":
            assert self.build is not None
            assert self.build["is_published"] and not self.build["private"]
            self.pointers.update(data)
            return httpx.Response(200, json=self.pointers)
        raise AssertionError((method, path, data))


@pytest.fixture
def publication(tmp_path, monkeypatch):
    archive = tmp_path / "GT_New_Horizons_2_(technic).zip"
    with ZipFile(archive, "w") as file:
        for name, version in (("same", "1"), ("changed", "2"), ("new", "1")):
            file.writestr(f"mods/{name}/{name}-{version}.zip", zip_bytes(f"mods/{name}.jar", name.encode()))
    server = SolderServer(archive)
    client = httpx.AsyncClient
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: client(transport=httpx.MockTransport(server.handle), **kwargs))

    async def sleep(delay):
        server.waits.append(delay)

    monkeypatch.setattr(asyncio, "sleep", sleep)
    return archive, server


def publish(archive, **kwargs):
    kwargs.setdefault("progress", lambda _: None)
    asyncio.run(publish_solder(archive, "2", "https://solder.test/api/", "test-secret", "pack", **kwargs))


@pytest.mark.parametrize("replace_draft", [False, True])
def test_publication_creates_or_replaces_build_and_registers_only_missing_versions(publication, replace_draft):
    from daxxl.assembler.platforms.technic import build_java_args_package

    archive, server = publication
    profile = b'{"id":"1.7.10-lwjgl3ify-3.0.37","mainClass":"example.Main","libraries":[]}'
    payload = build_java_args_package("-Dfile.encoding=UTF-8", profile)
    path = "mods/gtnh-java-args/gtnh-java-args-2.zip"
    with ZipFile(archive, "a") as file:
        file.writestr(path, payload)
    server.files[path] = payload
    old = {"version": "2", "minecraft": "old", "is_published": False}
    server.existing_builds = []  # No visible source build, including when an unreadable draft exists.
    server.pointers = {"latest": None, "recommended": None}
    if replace_draft:
        server.build = old
        server.mods = {"removed": server.versions["removed", "1"]}
    with capture_logs() as logs:
        publish(archive)
    assert server.deleted_builds == ([old] if replace_draft else [])
    assert server.build is not old and server.build["is_published"] and not server.build["private"]
    assert server.build["minecraft"] == "1.7.10" and server.build["min_java"] == "25"
    assert server.build["java_runtime"] == "java-runtime-epsilon"
    assert set(server.mods) == {"same", "changed", "new", "modpack", "gtnh-java-args"}
    assert server.mods["changed"]["version"] == "2"
    assert server.mods["modpack"]["version"] == "1.7.10-10.13.4.1614-version-less"
    assert server.mods["gtnh-java-args"]["version"] == "2"
    assert server.mods["gtnh-java-args"]["md5"] == hashlib.md5(payload).hexdigest()
    assert {data["name"] for method, path, data in server.calls if (method, path) == ("POST", "/api/mod")} == {"new", "gtnh-java-args"}
    assert ("removed", "1") in server.versions
    assert 7 in server.waits  # Retry-After is honored; an explicit 429 rejection may be retried.
    assert sum(call[:2] == ("POST", "/api/mod/changed/version") for call in server.calls) == 2
    delete_index = server.calls.index(("DELETE", "/api/modpack/pack/2", None))
    assert all(method == "GET" for method, _, _ in server.calls[:delete_index])
    assert server.calls[delete_index + 1][:2] == ("POST", "/api/modpack/pack/build")
    assert server.pointers == {"latest": "2", "recommended": None}
    warnings = [entry["event"] for entry in logs if entry["log_level"] == "warning"]
    assert warnings == (["Deleted existing Solder build pack/2; republishing from scratch."] if replace_draft else [])


def test_preflight_collects_errors_preserves_old_build_and_rechecks_failed_files(publication):
    archive, server = publication
    old = {"version": "2", "is_published": True}
    server.build = old
    server.existing_builds.append("2")
    # Also check an empty mod record: it must not count as an existing version.
    empty_path = "mods/empty/empty-1.zip"
    server.files[empty_path] = zip_bytes("mods/empty.jar", b"empty mod's first version")
    with ZipFile(archive, "a") as file:
        file.writestr(empty_path, server.files[empty_path])
    server.mod_names.add("empty")
    original_mods, original_versions = server.mod_names.copy(), server.versions.copy()
    originals = {path: server.files[path] for path in ("mods/changed/changed-2.zip", "mods/new/new-1.zip")}
    server.files.update(dict.fromkeys(originals, b"bad ZIP"))
    server.reject = ("GET", "/api/mod/same/1", 500)
    for _ in range(2):
        with capture_logs() as logs, pytest.raises(ValueError, match="failed for 3/5 packages") as error:
            publish(archive)
        assert all(name in str(error.value) for name in ("same-1.zip", "changed-2.zip", "new-1.zip"))
        assert "test-secret" not in str(error.value)
        assert server.build is old and server.deleted_builds == []
        assert server.mod_names == original_mods and server.versions == original_versions
        assert not any(entry["log_level"] == "warning" for entry in logs)
        assert server.calls[-1] == ("GET", "/" + empty_path, None)
    assert all(method == "GET" for method, _, _ in server.calls)
    server.files.update(originals)
    server.reject = None
    publish(archive)
    for path in originals:
        assert server.calls.count(("GET", "/" + path, None)) == 3
    assert ("new", "1") in server.versions and ("changed", "2") in server.versions
    assert ("empty", "1") in server.versions
    assert server.pointers["latest"] == "2"


@pytest.mark.parametrize(
    "method,path,failure",
    [
        ("DELETE", "/api/modpack/pack/2", 403),
        ("DELETE", "/api/modpack/pack/2", "timeout"),
        ("POST", "/api/modpack/pack/2/mod", "timeout"),
    ],
)
def test_failed_writes_are_not_retried_or_followed_by_publication(publication, method, path, failure):
    archive, server = publication
    old = {"version": "2", "is_published": True}
    server.build = old
    server.reject = (method, path, failure)
    with pytest.raises(RuntimeError, match="HTTP 403|outcome may be unknown"):
        publish(archive)
    assert server.calls[-1][:2] == (method, path)
    assert sum(call[:2] == (method, path) for call in server.calls) == 1
    assert server.pointers == {"latest": "1", "recommended": "1"}
    if method == "DELETE":
        assert server.build is old
        assert not any(method in {"POST", "PUT"} for method, _, _ in server.calls)
    else:
        assert not server.build["is_published"] and server.build["private"]


def test_registered_versions_skip_checks_and_both_progress_bars_complete_on_gui_thread(publication):
    archive, server = publication
    for package in server.packages:
        server.versions[package.name, package.version] = server.mod(package.name, package.version, server.files[package.path])
        server.mod_names.add(package.name)
    server.versions["same", "1"].update(md5="0" * 32, filesize=None)
    server.files.clear()  # Any mirror request would fail; existing metadata must not be compared with local ZIPs.
    phases, overall = [], [0.0]
    gui_thread = threading.get_ident()

    def reset_task():
        assert threading.get_ident() == gui_thread
        phases.append([0.0])

    def update_task(amount, message):
        assert threading.get_ident() == gui_thread and amount >= 0
        phases[-1].append(phases[-1][-1] + amount)

    def update_global(amount, message):
        assert threading.get_ident() == gui_thread and amount >= 0
        overall.append(overall[-1] + amount)

    publish(archive, task_progress_callback=update_task, global_progress_callback=update_global, current_task_reset_callback=reset_task)
    for values in [overall, *phases]:
        assert values == sorted(values)
        assert all(0 <= value <= 100.000001 for value in values)
        assert values[-1] == pytest.approx(100)
    assert any(0 < value < 100 for value in overall)
    assert server.mods["same"]["md5"] == "0" * 32 and server.mods["same"]["filesize"] is None
    assert not any(method == "POST" and (path == "/api/mod" or path.endswith("/version")) for method, path, _ in server.calls)


def test_bad_manifest_remains_private_without_claiming_completion(publication):
    archive, server = publication
    server.bad_manifest = True
    progress = []
    with pytest.raises(RuntimeError, match="unexpected mod list"):
        publish(archive, global_progress_callback=lambda amount, message: progress.append(amount))
    assert server.build["private"]
    assert server.pointers == {"latest": "1", "recommended": "1"}
    assert 0 < sum(progress) < 100


@pytest.mark.parametrize("wrong_archive_version", [False, True])
def test_mandatory_loader_must_have_required_version_before_any_writes(publication, wrong_archive_version):
    archive, server = publication
    if wrong_archive_version:
        with ZipFile(archive, "a") as file:
            file.writestr("mods/modpack/modpack-wrong.zip", zip_bytes("bin/modpack.jar", b"wrong loader"))
    else:
        del server.versions["modpack", "1.7.10-10.13.4.1614-version-less"]
    with pytest.raises(ValueError, match="modpack/1.7.10-10.13.4.1614-version-less"):
        publish(archive)
    assert all(method == "GET" for method, _, _ in server.calls)
    assert server.build is None


@pytest.mark.parametrize("options", [{"min_java": "1.8"}, {"java_runtime": "jre-legacy"}])
def test_incompatible_java_settings_fail_before_network(publication, options):
    archive, server = publication
    with pytest.raises(ValueError, match="Technic JVM patch requires"):
        publish(archive, **options)
    assert server.calls == []


@pytest.mark.parametrize("status,attempts", [(401, 1), (429, 4)])
def test_authentication_errors_stop_and_rate_limit_retries_are_bounded(publication, status, attempts):
    archive, server = publication
    server.reject = ("GET", "/api/token", status)
    with pytest.raises(RuntimeError, match=f"HTTP {status}") as error:
        publish(archive)
    assert "test-secret" not in str(error.value)
    assert len(server.calls) == attempts
    assert server.waits.count(2) == attempts - 1


def test_partial_archive_is_rejected_before_network(publication):
    archive, server = publication
    with pytest.raises(ValueError, match="full GT_New_Horizons"):
        publish(archive.with_name("GT_New_Horizons_2_(updated mods).zip"))
    assert server.calls == []


def test_invalid_package_path_is_rejected(tmp_path):
    archive = tmp_path / "bad.zip"
    with ZipFile(archive, "w") as file:
        file.writestr("mods/../x.zip", zip_bytes("mods/foo.jar", b"mod"))
    with pytest.raises(ValueError, match="Not a Technic package path"):
        read_technic_packages(archive)
