import shutil
from json import dump
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple
from urllib.parse import quote as urlquote
from zipfile import ZIP_DEFLATED, ZipFile

import httpx
from colorama import Fore

from gtnh.assembler.downloader import get_asset_version_cache_location
from gtnh.assembler.generic_assembler import GenericAssembler
from gtnh.defs import CACHE_DIR, MAVEN_BASE_URL, RELEASE_CURSE_DIR, ROOT_DIR, ModSource, Side, CURSEFORGE_CACHE_DIR
from gtnh.gtnh_logger import get_logger
from gtnh.gui.lib.progress_bar import CustomProgressBar
from gtnh.models.gtnh_config import GTNHConfig
from gtnh.models.gtnh_release import GTNHRelease
from gtnh.models.gtnh_version import GTNHVersion
from gtnh.models.mod_info import GTNHModInfo
from gtnh.modpack_manager import GTNHModpackManager

log = get_logger(__name__)


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


def is_mod_from_hidden_repo(mod: GTNHModInfo) -> bool:
    """
    Returns whether or not a given mod is from a private github repo.

    :param mod: the given mod object
    :return: true if it's from a private repo, false otherwise
    """
    if not mod.is_github():
        return False

    return mod.private


def is_mod_from_github(mod: GTNHModInfo) -> bool:
    """
    Returns whether or not a given mod is from github.

    :param mod: the given mod object
    :return: true if it's from github
    """
    return isinstance(mod, GTNHModInfo)


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
    Method to check if maven download url is availiable. If not, falling back to github. For now, it is reasonable, but
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
        gtnh_modpack: GTNHModpackManager,
        release: GTNHRelease,
        task_progress_callback: Optional[Callable[[float, str], None]] = None,
        global_progress_callback: Optional[Callable[[float, str], None]] = None,
        changelog_path: Optional[Path] = None,
    ):
        """
        Constructor of the CurseAssembler class.

        :param gtnh_modpack: the modpack manager instance
        :param release: the target release object
        :param task_progress_callback: the callback to report the progress of the task
        :param global_progress_callback: the callback to report the global progress
        """
        GenericAssembler.__init__(
            self,
            gtnh_modpack=gtnh_modpack,
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
        delta_progress: float = 100 / (
            2 + self.get_amount_of_files_in_config(side) + self.get_amount_of_files_in_locales() + 1 + 1
        )
        self.set_progress(delta_progress)

        archive_name: Path = self.get_archive_path(side)

        # deleting any existing archive
        if archive_name.exists():
            archive_name.unlink()
            log.warn(f"Previous archive {Fore.YELLOW}'{archive_name}'{Fore.RESET} deleted")

        log.info(f"Constructing {Fore.YELLOW}{side}{Fore.RESET} archive at {Fore.YELLOW}'{archive_name}'{Fore.RESET}")

        with ZipFile(self.get_archive_path(side), "w", compression=ZIP_DEFLATED) as archive:
            log.info("Adding config to the archive")
            self.add_config(side, self.get_config(), archive, verbose=verbose)
            log.info("Adding manifest.json to the archive")
            self.generate_meta_data(side, archive)
            log.info("Adding dependencies.json to the archive")
            await self.add_dep_file_to_archive(archive)
            log.info("Adding overrides to the archive")
            self.add_overrides(side, archive)
            log.info("Adding locales to the archive")
            self.add_localisation_files(archive, str(self.overrides_folder))
            log.info("Archive created successfully!")

    def add_overrides(self, side: Side, archive: ZipFile) -> None:
        """
        Method to add the overrides to the curse archive.

        :param side: client side
        :param archive: curse archive
        :return: None
        """
        archive.write(self.overrides, arcname=self.overrides_folder / "overrides.png")
        archive.write(self.overrideslash, arcname=self.overrides_folder / "overrideslash.png")
        coremod, coremod_version = [
            (mod, version) for mod, version in self.get_mods(side) if mod.name == "NewHorizonsCoreMod"
        ][0]
        source_file: Path = get_asset_version_cache_location(coremod, coremod_version)
        archive_path: Path = self.overrides_folder / "mods" / source_file.name
        archive.write(source_file, arcname=archive_path)

    def add_config(
        self, side: Side, config: Tuple[GTNHConfig, GTNHVersion], archive: ZipFile, verbose: bool = False
    ) -> None:
        modpack_config: GTNHConfig
        config_version: Optional[GTNHVersion]
        modpack_config, config_version = config

        config_file: Path = get_asset_version_cache_location(modpack_config, config_version)

        with ZipFile(config_file, "r", compression=ZIP_DEFLATED) as config_zip:

            for item in config_zip.namelist():
                if item in self.exclusions[side]:
                    continue
                with config_zip.open(item) as config_item:
                    with archive.open(
                        str(self.overrides_folder) + "/" + item, "w"
                    ) as target:  # can't use Path for the whole
                        # path here as it strips leading / but those are used by
                        # zipfile to know if it's a file or a folder. If used here,
                        # Path objects will lead to the creation of empty files for
                        # every folder.
                        shutil.copyfileobj(config_item, target)
                        if self.task_progress_callback is not None:
                            self.task_progress_callback(self.get_progress(), f"adding {item} to the archive")

        assert self.changelog_path
        self.add_changelog(archive, arcname=self.overrides_folder / self.changelog_path.name)

    def strip_curse_mods_from_mod_list(self, side:Side) -> List[Tuple[GTNHModInfo, GTNHVersion]]:
        filtering = lambda mod, version: not (mod.name == "NewHorizonsCoreMod" or is_valid_curse_mod(mod, version))
        return [(mod, version) for mod, version in self.get_mods(side) if filtering(mod, version)]

    async def add_dep_file_to_archive(self, archive:ZipFile) -> None:
        """
        Add the dependencies.json file to the archive.

        :param archive: the archive ZIP file
        """
        if not self.has_tempfile_been_generated:
            await self.generate_json_dep()

        archive.write(self.tempfile, arcname=str(self.dependencies_json))
        if self.task_progress_callback is not None:
            self.task_progress_callback(self.get_progress(), f"adding {self.dependencies_json} to the archive")

    def generate_mods_to_upload(self, task_progressbar:CustomProgressBar) -> None:
        """
        Generates the mods to upload on the download server listed in the dependencies.json

        :param task_progressbar: the progressbar corresponding to the current task progress
        :return: None
        """
        if task_progressbar is not None:
            task_progressbar.reset()
        with ZipFile(self.download_archive, "w", compression=ZIP_DEFLATED) as file:
            mod_list = self.strip_curse_mods_from_mod_list(Side.CLIENT)
            progress = 100.0 / len(mod_list)
            for mod, version in mod_list:
                path: Path = get_asset_version_cache_location(mod, version)
                if task_progressbar is not None:
                    task_progressbar.add_progress(progress, f"Adding {mod.name} to the archives of the mods to be uploaded")
                file.write(path, arcname=path.name)
        if task_progressbar is not None:
            task_progressbar.add_progress(1, "Done!")


    async def generate_json_dep(self, task_progressbar:Optional[CustomProgressBar]=None) -> None:
        """
        Generates the dependencies.json.

        :param task_progressbar: the progressbar corresponding to the current task progress
        :return: None
        """
        dep_json: List[Dict[str, str]] = []
        if task_progressbar is not None:
            task_progressbar.reset()
        async with httpx.AsyncClient(http2=True) as client:
            mod_list = self.strip_curse_mods_from_mod_list(Side.CLIENT)
            progress = 100.0 / len(mod_list)

            for mod, version in mod_list:
                url: Optional[str]
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
                mod_obj: Dict[str, str] = {"path": f"mods/{version.filename}", "url": url}
                if task_progressbar is not None:
                    task_progressbar.add_progress(progress, f"Adding {mod.name} to dependencies.json")
                dep_json.append(mod_obj)
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

        metadata = {
            "minecraft": {"version": "1.7.10", "modLoaders": [{"id": "forge-10.13.4.1614", "primary": True}]},
            "manifestType": "minecraftModpack",
            "manifestVersion": 1,
            "name": "GT New Horizons",
            "version": "{0}-1.7.10".format(self.release.version),
            "author": "DreamMasterXXL",
            "overrides": "overrides",
        }

        mod: GTNHModInfo
        version: GTNHVersion
        files = []
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
            self.task_progress_callback(self.get_progress(), f"adding {self.manifest_json} to the archive")

        self.tempfile.unlink()
