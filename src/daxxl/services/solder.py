"""Publish an existing Technic archive after its ZIPs have been uploaded to the mirror."""

import asyncio
import hashlib
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlsplit
from zipfile import ZipFile

import httpx

from daxxl.defs import TECHNIC_JAVA_RUNTIME, TECHNIC_JAVA_VERSION
from daxxl.gtnh_logger import get_logger

log = get_logger(__name__)

TECHNIC_REQUIRED_MOD = ("modpack", "1.7.10-10.13.4.1614-version-less")
DEFAULT_REQUESTS_PER_MINUTE = 1200


@dataclass(frozen=True)
class SolderPackage:
    name: str
    version: str
    path: str
    md5: str
    filesize: int


def read_technic_packages(path: Path, progress_callback: Callable[[int, int, str], None] | None = None) -> list[SolderPackage]:
    """Hash the nested ZIP bytes, without extracting files or loading the archive into RAM."""
    packages: dict[str, SolderPackage] = {}
    with ZipFile(path) as archive:
        entries = [entry for entry in archive.infolist() if not entry.is_dir()]
        total_bytes = sum(entry.file_size for entry in entries)
        bytes_read = 0
        for entry in entries:
            match = re.fullmatch(r"mods/([a-z0-9][a-z0-9.-]*)/\1-([a-z0-9][a-z0-9.-]*)\.zip", entry.filename)
            if match is None:
                raise ValueError(f"Not a Technic package path: {entry.filename}")
            name, version = match.groups()
            if name in packages:
                raise ValueError(f"Duplicate mod in Technic archive: {name}")
            digest = hashlib.md5(usedforsecurity=False)
            with archive.open(entry) as package:
                signature = package.read(4)
                if signature != b"PK\x03\x04":
                    raise ValueError(f"Not a non-empty ZIP: {entry.filename}")
                digest.update(signature)
                bytes_read += len(signature)
                if progress_callback:
                    progress_callback(bytes_read, total_bytes, entry.filename)
                while chunk := package.read(1024 * 1024):
                    digest.update(chunk)
                    bytes_read += len(chunk)
                    if progress_callback:
                        progress_callback(bytes_read, total_bytes, entry.filename)
            packages[name] = SolderPackage(name, version, entry.filename, digest.hexdigest(), entry.file_size)
    if not packages:
        raise ValueError("The Technic archive contains no packages.")
    return list(packages.values())


def _identifier(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._+-]{0,189}", value):
        raise ValueError(f"Invalid Solder slug/version: {value!r}")
    return quote(value, safe="")


def _http_url(value: str, *, api: bool = False) -> str:
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("Expected an HTTP(S) URL without credentials, query or fragment.")
    if api and parsed.scheme != "https" and parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise ValueError("Use HTTPS for the Solder API to protect the bearer token.")
    return value


class SolderAPI:
    """Sequential API calls; only explicit 429 rejections are retried, never ambiguous writes."""

    def __init__(
        self,
        client: httpx.AsyncClient,
        url: str,
        token: str,
        progress: Callable[[str], None],
        requests_per_minute: int = DEFAULT_REQUESTS_PER_MINUTE,
    ):
        if type(requests_per_minute) is not int or requests_per_minute <= 0:
            raise ValueError("requests_per_minute must be a positive integer.")
        base = _http_url(url.strip().rstrip("/"), api=True)
        self.url = base if base.endswith("/api") else base + "/api"
        self.token = token.strip()
        if not self.token or any(char.isspace() for char in self.token):
            raise ValueError("A valid Solder bearer token is required.")
        self.client = client
        self.progress = progress
        self.request_interval = 60 / requests_per_minute * 1.05
        self.next_request = 0.0

    async def request(self, method: str, path: str, *, data: dict[str, Any] | None = None, missing_ok: bool = False) -> Any:
        for attempt in range(4):
            loop = asyncio.get_running_loop()
            await asyncio.sleep(max(0, self.next_request - loop.time()))
            self.next_request = loop.time() + self.request_interval
            try:
                response = await self.client.request(
                    method,
                    self.url + "/" + path,
                    headers={"Authorization": f"Bearer {self.token}", "Accept": "application/json"},
                    json=data,
                    follow_redirects=False,
                )
            except httpx.RequestError:
                raise RuntimeError(f"Solder {method} {path}: connection failed. The outcome may be unknown; inspect the build before retrying.") from None
            if response.status_code == 429 and attempt < 3:
                try:
                    delay = max(1, int(response.headers.get("Retry-After", "60")))
                except ValueError:
                    delay = 60
                self.progress(f"Solder rate limit: waiting {delay}s")
                await asyncio.sleep(delay)
                continue
            if response.status_code == 404 and missing_ok:
                return None
            if not response.is_success:
                detail = response.text.replace(self.token, "[redacted]")[:500]
                raise RuntimeError(f"Solder {method} {path}: HTTP {response.status_code}: {detail}")
            try:
                return response.json()
            except ValueError:
                raise RuntimeError(f"Solder {method} {path}: expected a JSON response. Inspect the server before retrying.") from None
        raise AssertionError("Unreachable")


async def _verify_mirror(client: httpx.AsyncClient, url: str, package: SolderPackage, progress_callback: Callable[[int, int], None] | None = None) -> None:
    _http_url(url)
    digest = hashlib.md5(usedforsecurity=False)
    size = 0
    async with client.stream("GET", url, headers={"Accept-Encoding": "identity"}, follow_redirects=True) as response:
        response.raise_for_status()
        async for chunk in response.aiter_bytes():
            size += len(chunk)
            if size > package.filesize:
                raise ValueError(f"Mirror ZIP size differs from the local archive: {package.path}")
            digest.update(chunk)
            if progress_callback:
                progress_callback(size, package.filesize)
    if size != package.filesize or digest.hexdigest() != package.md5:
        raise ValueError(f"Mirror ZIP differs from the local archive: {package.path}. Upload the exact ZIP before publishing.")


def _check_version(package: SolderPackage, remote: dict[str, Any]) -> None:
    recorded_size = int(remote.get("filesize") or 0)  # Older Solder records may not have a size.
    if str(remote.get("md5", "")).lower() != package.md5 or recorded_size not in {0, package.filesize}:
        raise ValueError(
            f"Solder already has different bytes for {package.name}/{package.version}. "
            "Keep the original ZIP or use a new version; existing mod versions are never overwritten."
        )


async def publish_solder(
    archive: Path,
    version: str,
    url: str,
    token: str,
    pack: str,
    *,
    minecraft: str = "1.7.10",
    forge: str | None = "10.13.4.1614",
    min_java: str = str(TECHNIC_JAVA_VERSION),
    java_runtime: str | None = TECHNIC_JAVA_RUNTIME,
    min_memory: int | None = None,
    recommended: bool = False,
    private: bool = False,
    requests_per_minute: int = DEFAULT_REQUESTS_PER_MINUTE,
    progress: Callable[[str], None] = print,
    task_progress_callback: Callable[[float, str], None] | None = None,
    global_progress_callback: Callable[[float, str], None] | None = None,
    current_task_reset_callback: Callable[[], None] | None = None,
) -> None:
    """Create a new build from the full package set, verify privately, then promote.

    The full Technic archive supplies packages, plus the mandatory pinned Technic loader.
    Replace the target build only after preflight succeeds; leave failed writes for inspection.
    Numeric callbacks receive percentage increments, with the task bar reset for each phase.
    """
    phase = 0
    phase_name = ""
    task_percent = 0.0
    global_percent = 0.0

    def advance(completed: float, total: float, message: str) -> None:
        nonlocal task_percent, global_percent
        target = max(task_percent, min(100.0, 100 * completed / total if total else 100.0))
        overall = min(100.0, (phase - 1 + target / 100) * 100 / 7)
        if task_progress_callback:
            task_progress_callback(target - task_percent, message)
        if global_progress_callback:
            global_progress_callback(overall - global_percent, f"{phase}/7: {phase_name}")
        task_percent, global_percent = target, overall

    def begin_task(message: str) -> None:
        nonlocal phase, phase_name, task_percent
        phase += 1
        phase_name = message
        task_percent = 0.0
        if current_task_reset_callback:
            current_task_reset_callback()
        progress(message)
        advance(0, 1, message)

    pack_path = "modpack/" + _identifier(pack)
    build_path = pack_path + "/" + _identifier(version)
    if private and recommended:
        raise ValueError("A private build cannot be promoted to recommended.")
    if not minecraft.strip() or not min_java.strip():
        raise ValueError("Minecraft and minimum Java versions must not be empty.")
    if min_java.strip() != str(TECHNIC_JAVA_VERSION):
        raise ValueError(f"The Technic JVM patch requires min_java={TECHNIC_JAVA_VERSION}. Update the option or solder.json.")
    if java_runtime not in {None, "", TECHNIC_JAVA_RUNTIME}:
        raise ValueError(f"The Technic JVM patch requires java_runtime={TECHNIC_JAVA_RUNTIME} (Java {TECHNIC_JAVA_VERSION}), or no override.")
    if min_memory is not None and (type(min_memory) is not int or min_memory < 1):
        raise ValueError("Minimum memory must be a positive number of MB.")
    build_settings = {
        "minecraft": minecraft.strip(),
        "forge": forge or None,
        "min_java": min_java.strip(),
        "java_runtime": java_runtime or None,
        "min_memory": min_memory,
    }
    if archive.name != f"GT_New_Horizons_{version}_(technic).zip":
        raise ValueError(f"Select the full GT_New_Horizons_{version}_(technic).zip archive, not a partial update or another release.")
    begin_task("Reading full Technic archive")
    loop = asyncio.get_running_loop()

    # Hashing runs in a worker; marshal progress back to the Tk/asyncio thread.
    def read_progress(done: int, total: int, name: str) -> None:
        loop.call_soon_threadsafe(advance, done, total, f"Reading {name}")

    packages = await asyncio.to_thread(read_technic_packages, archive, read_progress if task_progress_callback or global_progress_callback else None)
    advance(1, 1, "Technic archive read")
    required_name, required_version = TECHNIC_REQUIRED_MOD
    desired_versions = {package.name: package.version for package in packages}
    if required_name in desired_versions and desired_versions[required_name] != required_version:
        raise ValueError(f"Technic requires {required_name}/{required_version}; the archive contains a different version.")
    required_in_archive = required_name in desired_versions
    desired_versions[required_name] = required_version
    # Separate clients keep credentials/cookies away from the download mirror.
    async with httpx.AsyncClient(timeout=60) as api_client, httpx.AsyncClient(timeout=60) as mirror_client:
        begin_task("Connecting to Solder")
        api = SolderAPI(api_client, url, token, progress, requests_per_minute=requests_per_minute)
        await api.request("GET", "token")  # Fail on invalid credentials even for public packs.
        advance(1, 4, "Authenticated with Solder")
        await api.request("GET", pack_path)
        advance(2, 4, "Modpack loaded")
        mirror = (await api.request("GET", "modpack"))["mirror_url"]
        _http_url(mirror)
        if not mirror.endswith("/"):
            raise ValueError("Solder mirror_url must end with '/'. Fix the server configuration first.")
        advance(3, 4, "Mirror configuration loaded")
        known_mods = (await api.request("GET", "mod"))["mods"]
        advance(4, 4, "Mod library loaded")

        # Trust exact versions already registered; verify every new ZIP before any server writes.
        begin_task("Checking packages and mirror files")
        check_count = len(desired_versions)
        checked_offset = int(not required_in_archive)
        new_versions: list[SolderPackage] = []
        existing_versions: set[str] = set()
        expected_urls: dict[str, str] = {}
        verification_errors: list[str] = []
        if not required_in_archive:
            progress(f"Looking up mandatory Technic mod: {required_name}/{required_version}")
            try:
                required = await api.request("GET", f"mod/{required_name}/{required_version}", missing_ok=True)
                if required is None:
                    raise ValueError("Register this version in Solder or include its ZIP in the full Technic archive before publishing.")
            except Exception as error:
                detail = str(error).replace(api.token, "[redacted]")
                message = f"Required Technic mod {required_name}/{required_version}: {detail}"
                verification_errors.append(message)
                progress(f"Verification failed; continuing: {message}")
            advance(1, check_count, f"Processed mandatory mod {required_name}")
        for index, package in enumerate(packages, 1):
            progress(f"Looking up version {index}/{len(packages)}: {package.name}/{package.version}")
            try:
                remote = None
                if package.name in known_mods:
                    remote = await api.request("GET", f"mod/{package.name}/{package.version}", missing_ok=True)
                if remote is not None:
                    existing_versions.add(package.name)
                    progress(f"Already registered; skipping verification: {package.name}/{package.version}")
                    continue
                progress(f"Verifying new ZIP: {package.name}/{package.version}")
                download_url = mirror + package.path
                await _verify_mirror(
                    mirror_client,
                    download_url,
                    package,
                    progress_callback=lambda done, total: advance(
                        checked_offset + index - 1 + done / total, check_count, f"Verifying {package.name}: {done}/{total} bytes"
                    ),
                )
            except Exception as error:
                detail = str(error).replace(api.token, "[redacted]")
                message = f"{package.path}: {type(error).__name__}: {detail}"
                verification_errors.append(message)
                progress(f"Verification failed; continuing: {message}")
                continue
            finally:
                advance(checked_offset + index, check_count, f"Processed {checked_offset + index}/{check_count}: {package.name}")
            new_versions.append(package)
            expected_urls[package.name] = download_url

        if verification_errors:
            raise ValueError(
                f"Metadata/mirror verification failed for {len(verification_errors)}/{len(desired_versions)} packages. "
                "All packages were processed; existing versions were trusted. No changes were made to Solder.\n- " + "\n- ".join(verification_errors)
            )

        try:
            begin_task("Creating the build")
            # DELETE also finds unpublished drafts, which Solder does not expose through GET.
            deleted = await api.request("DELETE", build_path, missing_ok=True)
            if deleted is not None:
                message = f"Deleted existing Solder build {pack}/{version}; republishing from scratch."
                log.warning(message)
                progress(message)
            advance(1, 2, "Target build ready for creation")
            progress(f"Creating new unpublished build {version}")
            await api.request(
                "POST",
                pack_path + "/build",
                data={
                    "version": version,
                    **build_settings,
                    "is_published": False,
                    "private": True,
                },
            )
            advance(2, 2, "New unpublished build created")
            begin_task("Registering new mod versions")
            registration_count = len(new_versions) + sum(package.name not in known_mods for package in new_versions)
            registered = 0
            for package in new_versions:
                progress(f"Registering {package.name}/{package.version}")
                if package.name not in known_mods:
                    await api.request("POST", "mod", data={"name": package.name, "pretty_name": package.name})
                    registered += 1
                    advance(registered, registration_count, f"Created mod {package.name}")
                await api.request(
                    "POST",
                    f"mod/{package.name}/version",
                    data={"version": package.version, "md5": package.md5, "filesize": package.filesize},
                )
                registered += 1
                advance(registered, registration_count, f"Registered {package.name}/{package.version}")
            advance(registration_count, registration_count, "Mod versions ready")

            begin_task("Assigning mods to the build")
            for index, (name, mod_version) in enumerate(desired_versions.items(), 1):
                progress(f"Assigning {name}/{mod_version}")
                await api.request("POST", build_path + "/mod", data={"mod_slug": name, "mod_version": mod_version})
                advance(index, len(desired_versions), f"Assigned {index}/{len(desired_versions)}: {name}/{mod_version}")

            # Solder cannot read drafts. Publish privately first to verify the actual manifest.
            begin_task("Verifying and publishing the build")
            publication_count = 2 if private else 4
            progress("Verifying the private build manifest")
            await api.request("PUT", build_path, data={"is_published": True, "private": True})
            advance(1, publication_count, "Build published privately for verification")
            manifest = await api.request("GET", build_path)
            actual = {mod["name"]: mod for mod in manifest["mods"]}
            if len(actual) != len(manifest["mods"]) or actual.keys() != desired_versions.keys():
                raise ValueError("Published manifest has an unexpected mod list; build remains private.")
            for name, mod_version in desired_versions.items():
                if actual[name]["version"] != mod_version:
                    raise ValueError(f"Published manifest has the wrong version of {name}; build remains private.")
            for package in packages:
                remote = actual[package.name]
                if package.name in existing_versions:
                    continue
                _check_version(package, remote)
                if remote["url"] != expected_urls[package.name]:
                    raise ValueError(f"Published manifest differs for {package.name}; build remains private.")
            for field, setting in (
                ("minecraft", "minecraft"),
                ("java", "min_java"),
                ("java_runtime", "java_runtime"),
                ("memory", "min_memory"),
                ("forge", "forge"),
            ):
                if manifest.get(field) != build_settings[setting]:
                    raise ValueError(f"Build setting {field} differs from the requested value; build remains private.")
            advance(2, publication_count, "Build manifest verified")
            if not private:
                progress("Publishing build and updating pack pointers")
                await api.request("PUT", build_path, data={"private": False})
                advance(3, publication_count, "Build made public")
                pointers = {"latest": version}
                if recommended:
                    pointers["recommended"] = version
                await api.request("PUT", pack_path, data=pointers)
                advance(4, publication_count, "Pack pointers updated")
        except Exception as error:
            raise RuntimeError(
                f"Publication of {pack}/{version} stopped: {error}\n"
                "Inspect this build in Solder before retrying. The previous build may have been deleted; "
                "a retry will recreate this version after verification. Registered mods/versions are retained."
            ) from error
        progress(f"Published {'private ' if private else ''}build {pack}/{version}")
