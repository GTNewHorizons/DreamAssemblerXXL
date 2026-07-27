from collections.abc import Callable
from json import dump
from pathlib import Path
from urllib.parse import quote as urlquote
from zipfile import ZIP_DEFLATED, ZipFile

import httpx
from colorama import Fore

from daxxl.app_context import AppContext
from daxxl.assembler.downloader import get_asset_version_cache_location
from daxxl.assembler.platforms.generic_assembler import GenericAssembler
from daxxl.defs import CURSEFORGE_CACHE_DIR, MAVEN_BASE_URL, RELEASE_CURSE_DIR, ROOT_DIR, ModSource, Side
from daxxl.exceptions import MissingModFileException
from daxxl.gtnh_logger import get_logger
from daxxl.gui.lib.progress_bar import CustomProgressBar
from daxxl.models.gtnh_release import GTNHRelease
from daxxl.models.gtnh_version import GTNHVersion
from daxxl.models.mod_info import GTNHModInfo
from daxxl.utils import normalize_archive_permissions

log = get_logger(__name__)

# shipped in the curse overrides rather than pulled from curse, so it always has to be present
CORE_MOD_NAME = "NewHorizonsCoreMod"


def is_valid_curse_mod(mod: GTNHModInfo, version: GTNHVersion) -> bool:
    """
     Returns whether or not a given mod is a valid curse mod or not.

    :param mod: the given mod object
    :param version: its corresponding version
    :return: true if it is a valid curse mod
    """
    # If we don't have curse file info, it's not a valid curse file
    if version.curse_file is None:
        return False

    # If we don't have a file no, or a project no, it's not a valid curse file
    if not version.curse_file.file_no or not version.curse_file.project_no:
        return False

    return True


def get_maven_url(mod: GTNHModInfo, version: GTNHVersion) -> str | None:
    """
    Returns the maven url for a github mod.

    :param mod: the github mod
    :param version: the mod version
    :return: the url from the GT:NH maven
    """
    if not isinstance(mod, GTNHModInfo):
        raise TypeError("Only github mods have a maven url")

    if mod.maven:
        base = mod.maven
    else:
        log.warn(f"Missing mod.maven for {mod.name}, trying fallback url.")
        base = f"{MAVEN_BASE_URL}{mod.name}/"

    url: str = f"{base}{version.version_tag}/{mod.name}-{version.version_tag}.jar"

    return url


async def resolve_github_url(client: httpx.AsyncClient, mod: GTNHModInfo, version: GTNHVersion) -> str:
    """
    Method to check if maven download url is available. If not, falling back to github. For now, it is reasonable, but
    we may hit the anonymous request quota limit if we have too much missing maven urls. Better not to rely too much on
    this.

    :param mod: the github mod
    :param version: it's associated version
    """

    url = get_maven_url(mod, version)
    if url:
        response: httpx.Response = await client.head(url)
        if response.status_code in {200, 204}:
            return url
    log.warn(f"Using fallback url, couldn't find {url}")
    assert version.browser_download_url
    return version.browser_download_url


class CurseAssembler(GenericAssembler):
    """
    Curse assembler class. Allows for the assembling of curse archives.
    """

    def __init__(
        self,
        context: AppContext,
        release: GTNHRelease,
        task_progress_callback: Callable[[float, str], None] | None = None,
        global_progress_callback: Callable[[float, str], None] | None = None,
        changelog_path: Path | None = None,
    ):
        """
        Constructor of the CurseAssembler class.

        :param context: the context instance
        :param release: the target release object
        :param task_progress_callback: the callback to report the progress of the task
        :param global_progress_callback: the callback to report the global progress
        """
        GenericAssembler.__init__(
            self,
            context=context,
            release=release,
            task_progress_callback=task_progress_callback,
            global_progress_callback=global_progress_callback,
            changelog_path=changelog_path,
        )

        self.overrides_folder = Path("overrides")
        self.manifest_json = Path("manifest.json")
        self.dependencies_json = self.overrides_folder / "config" / "dependencies.json"
        self.tempfile = CURSEFORGE_CACHE_DIR / f"dependencies-{release.version}.json"
        self.download_archive = RELEASE_CURSE_DIR / f"downloads-{release.version}.zip"
        self.has_tempfile_been_generated: bool = False
        self.overrides = ROOT_DIR / "overrides.png"
        self.overrideslash = ROOT_DIR / "overrideslash.png"

    def get_archive_path(self, side: Side) -> Path:
        return RELEASE_CURSE_DIR / f"GT_New_Horizons_{self.release.version}.zip"

    async def assemble(self, side: Side, verbose: bool = False) -> None:
        if side not in {Side.CLIENT}:
            raise Exception("Can only assemble release for CLIENT")

        # + 2 pictures in the overrides + manifest.json + dependencies.json
        self.delta_progress = 100 / (2 + self.get_amount_of_files_in_config(side) + self.get_amount_of_files_in_locales() + 1 + 1)

        archive_name: Path = self.get_archive_path(side)

        # deleting any existing archive
        if archive_name.exists():
            archive_name.unlink()
            log.warn(f"Previous archive {Fore.YELLOW}'{archive_name}'{Fore.RESET} deleted")

        log.info(f"Constructing {Fore.YELLOW}{side}{Fore.RESET} archive at {Fore.YELLOW}'{archive_name}'{Fore.RESET}")

        with ZipFile(self.get_archive_path(side), "w", compression=ZIP_DEFLATED) as archive:
            log.info("Adding config to the archive")
            await self.add_config(side, self.get_config(), archive, verbose=verbose)
            await self.yield_to_event_loop()
            log.info("Adding manifest.json to the archive")
            self.generate_meta_data(side, archive)
            await self.yield_to_event_loop()
            log.info("Adding dependencies.json to the archive")
            await self.add_dep_file_to_archive(archive)
            await self.yield_to_event_loop()
            log.info("Adding overrides to the archive")
            self.add_overrides(side, archive)
            await self.yield_to_event_loop()
            log.info("Adding locales to the archive")
            await self.add_localisation_files(archive, str(self.overrides_folder))
            await self.yield_to_event_loop()
            await normalize_archive_permissions(archive)
            log.info("Archive created successfully!")

    def add_overrides(self, side: Side, archive: ZipFile) -> None:
        """
        Method to add the overrides to the curse archive.

        :param side: client side
        :param archive: curse archive
        :raises MissingModFileException: if the core mod isn't part of the release
        :return: None
        """
        archive.write(self.overrides, arcname=self.overrides_folder / "overrides.png")
        archive.write(self.overrideslash, arcname=self.overrides_folder / "overrideslash.png")
        core_mod = next(((mod, version) for mod, version in self.get_mods(side) if mod.name == CORE_MOD_NAME), None)
        if core_mod is None:
            raise MissingModFileException(f"{CORE_MOD_NAME} has to be in the {side.value} side of release {self.release.version} to build the curse overrides")

        coremod, coremod_version = core_mod
        source_file: Path = get_asset_version_cache_location(coremod, coremod_version)
        archive_path: Path = self.overrides_folder / "mods" / source_file.name
        archive.write(source_file, arcname=archive_path)

    @property
    def config_root(self) -> Path | None:
        return self.overrides_folder

    def get_list_of_mods_to_upload(self, side: Side) -> list[tuple[GTNHModInfo, GTNHVersion]]:
        def should_upload(mod: GTNHModInfo, version: GTNHVersion) -> bool:
            return not (mod.name == CORE_MOD_NAME or is_valid_curse_mod(mod, version))

        return [(mod, version) for mod, version in self.get_mods(side) if should_upload(mod, version)]

    async def add_dep_file_to_archive(self, archive: ZipFile) -> None:
        """
        Add the dependencies.json file to the archive.

        :param archive: the archive ZIP file
        """
        if not self.has_tempfile_been_generated:
            await self.generate_json_dep()

        archive.write(self.tempfile, arcname=str(self.dependencies_json))
        if self.task_progress_callback is not None:
            self.task_progress_callback(self.delta_progress, f"adding {self.dependencies_json} to the archive")

    async def generate_mods_to_upload(self, task_progressbar: CustomProgressBar) -> None:
        """
        Generates the mods to upload on the download server listed in the dependencies.json

        :param task_progressbar: the progressbar corresponding to the current task progress
        :return: None
        """
        if task_progressbar is not None:
            task_progressbar.reset()
        with ZipFile(self.download_archive, "w", compression=ZIP_DEFLATED) as f:
            mod_list = self.get_list_of_mods_to_upload(Side.CLIENT)
            progress = 100.0 / len(mod_list) if mod_list else 100.0
            for mod, version in mod_list:
                path: Path = get_asset_version_cache_location(mod, version)
                if task_progressbar is not None:
                    task_progressbar.add_progress(progress, f"Adding {mod.name} to the archives of the mods to be uploaded")
                f.write(path, arcname=path.name)
                await self.yield_to_event_loop()
            await normalize_archive_permissions(f)
        if task_progressbar is not None:
            task_progressbar.add_progress(1, "Done!")

    async def generate_json_dep(self, task_progressbar: CustomProgressBar | None = None) -> None:
        """
        Generates the dependencies.json.

        :param task_progressbar: the progressbar corresponding to the current task progress
        :return: None
        """
        dep_json: list[dict[str, str]] = []
        if task_progressbar is not None:
            task_progressbar.reset()
        async with httpx.AsyncClient(http2=True) as client:
            mod_list = self.get_list_of_mods_to_upload(Side.CLIENT)
            progress = 100.0 / len(mod_list) if mod_list else 100.0

            for mod, version in mod_list:
                url: str | None
                if mod.source == ModSource.github:
                    if not version.maven_url:
                        url = await resolve_github_url(client, mod, version)
                    else:
                        url = version.maven_url

                    # Hacky detection
                    if url and "nexus.gtnewhorizons.com" in url:
                        version.maven_url = url
                else:
                    url = version.download_url

                path: Path = get_asset_version_cache_location(mod, version)

                assert url
                url = f"https://downloads.gtnewhorizons.com/Mods_for_Twitch/{urlquote(path.name)}"  # temporary override until maven is fixed
                mod_obj: dict[str, str] = {"path": f"mods/{version.filename}", "url": url}
                if task_progressbar is not None:
                    task_progressbar.add_progress(progress, f"Adding {mod.name} to dependencies.json")
                dep_json.append(mod_obj)
            await self.yield_to_event_loop()
        self.tempfile.parent.mkdir(parents=True, exist_ok=True)
        with open(self.tempfile, "w") as temp:
            dump(dep_json, temp, indent=2)
        if task_progressbar is not None:
            task_progressbar.add_progress(1, "Done!")

    def generate_meta_data(self, side: Side, archive: ZipFile) -> None:
        """
        Generates the manifest.json and places it in the archive.

        :param side: the side of the pack
        :param archive: the zipfile
        :return: None
        """

        metadata: dict[
            str,
            dict[str, str | list[dict[str, str | bool | int]]] | list[dict[str, str | bool | int]] | str | int,
        ] = {
            "minecraft": {"version": "1.7.10", "modLoaders": [{"id": "forge-10.13.4.1614", "primary": True}]},
            "manifestType": "minecraftModpack",
            "manifestVersion": 1,
            "name": "GT New Horizons",
            "version": f"{self.release.version}-1.7.10",
            "author": "DreamMasterXXL",
            "overrides": "overrides",
        }

        mod: GTNHModInfo
        version: GTNHVersion
        files: list[dict[str, str | int | bool]] = []
        for mod, version in self.get_mods(side):
            if is_valid_curse_mod(mod, version):
                assert version.curse_file  # make mypy happy
                # ignoring mypy errors here because it's all good in the check above
                files.append(
                    {
                        "projectID": int(version.curse_file.project_no),
                        "fileID": int(version.curse_file.file_no),
                        "required": True,
                    }
                )

        metadata["files"] = files

        with open(self.tempfile, "w") as temp:
            dump(metadata, temp, indent=2)

        archive.write(self.tempfile, arcname=str(self.manifest_json))

        if self.task_progress_callback is not None:
            self.task_progress_callback(self.delta_progress, f"adding {self.manifest_json} to the archive")

        self.tempfile.unlink()
