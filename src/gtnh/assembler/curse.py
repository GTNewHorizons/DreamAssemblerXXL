import shutil
from json import dump, loads
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
from zipfile import ZipFile

from colorama import Fore
from structlog import get_logger

from gtnh.assembler.downloader import get_asset_version_cache_location
from gtnh.assembler.generic_assembler import GenericAssembler
from gtnh.defs import CACHE_DIR, RELEASE_CURSE_DIR, ROOT_DIR, Side
from gtnh.models.gtnh_config import GTNHConfig
from gtnh.models.gtnh_release import GTNHRelease
from gtnh.models.gtnh_version import GTNHVersion
from gtnh.models.mod_info import ExternalModInfo, GTNHModInfo
from gtnh.modpack_manager import GTNHModpackManager

log = get_logger(__name__)


def is_valid_curse_mod(mod: GTNHModInfo | ExternalModInfo, version: GTNHVersion) -> bool:
    """
     Returns whether or not a given mod is a valid curse mod or not.

    :param mod: the given mod object
    :param version: its corresponding version
    :return: true if it is a valid curse mod
    """
    if isinstance(mod, GTNHModInfo):
        return False

    if version.browser_download_url is None:
        return False

    if mod.project_id is None:
        return False

    try:
        int(version.browser_download_url.split("/")[-1])
        return True
    except ValueError:
        return False


def is_mod_from_hidden_repo(mod: GTNHModInfo | ExternalModInfo) -> bool:
    """
    Returns whether or not a given mod is from a private github repo.

    :param mod: the given mod object
    :return: true if it's from a private repo, false otherwise
    """
    if isinstance(mod, ExternalModInfo):
        return False

    return mod.private


def is_mod_from_github(mod: GTNHModInfo | ExternalModInfo) -> bool:
    """
    Returns wheter or not a given mod is from github.

    :param mod: the given mod object
    :return: true if it's from github
    """
    return isinstance(mod, GTNHModInfo)


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
        self.tempfile = CACHE_DIR / "temp"
        self.overrides = ROOT_DIR / "overrides.png"
        self.overrideslash = ROOT_DIR / "overrideslash.png"

    def get_archive_path(self, side: Side) -> Path:
        return RELEASE_CURSE_DIR / f"GTNewHorizons-{side}-{self.release.version}.zip"

    def assemble(self, side: Side, verbose: bool = False) -> None:
        if side not in {Side.CLIENT}:
            raise Exception("Can only assemble release for CLIENT")

        # + 2 pictures in the overrides + manifest.json + dependencies.json
        delta_progress: float = 100 / (
            len(self.get_mods_to_override(side)) + 2 + self.get_amount_of_files_in_config(side) + 1 + 1
        )
        self.set_progress(delta_progress)

        archive_name: Path = self.get_archive_path(side)

        # deleting any existing archive
        if archive_name.exists():
            archive_name.unlink()
            log.warn(f"Previous archive {Fore.YELLOW}'{archive_name}'{Fore.RESET} deleted")

        log.info(f"Constructing {Fore.YELLOW}{side}{Fore.RESET} archive at {Fore.YELLOW}'{archive_name}'{Fore.RESET}")

        with ZipFile(self.get_archive_path(side), "w") as archive:
            log.info("Adding config to the archive")
            self.add_config(side, self.get_config(), archive, verbose=verbose)
            log.info("Adding manifest.json to the archive")
            self.generate_meta_data(side, archive)
            log.info("Adding dependencies.json to the archive")
            self.generate_json_dep(side, archive)
            log.info("Adding overrides to the archive")
            self.add_overrides(side, archive)
            log.info("Archive created successfully!")

    def get_mods_to_override(self, side: Side) -> List[Tuple[GTNHModInfo | ExternalModInfo, GTNHVersion]]:
        """
        Method to get the mods to override in the curse archive.

        :param side: client side
        :return: a list of couples where the first element is the mod object and the second is the version object
        """
        mods_to_override: List[Tuple[GTNHModInfo | ExternalModInfo, GTNHVersion]] = [
            (mod, version) for mod, version in self.get_mods(side) if is_mod_from_github(mod)
        ]

        return mods_to_override

    def add_overrides(self, side: Side, archive: ZipFile) -> None:
        """
        Method to add the overrides to the curse archive.

        :param side: client side
        :param archive: curse archive
        :return: None
        """
        archive.write(self.overrides, arcname="overrides/overrides.png")
        archive.write(self.overrideslash, arcname="overrides/overrideslash.png")

        mods_to_override: List[Tuple[GTNHModInfo | ExternalModInfo, GTNHVersion]] = self.get_mods_to_override(side)
        # if curse reject the archive because reasons, we will have
        # to find an alternative for that, as downloading the files
        # hosted on github from the deploader will get the players
        # rate limited and the deploader will receive 403 http errors

        for mod, version in mods_to_override:
            source_file: Path = get_asset_version_cache_location(mod, version)
            archive_path: Path = self.overrides_folder / "mods" / source_file.name
            archive.write(source_file, arcname=archive_path)
            if self.task_progress_callback is not None:
                self.task_progress_callback(self.get_progress(), f"adding {source_file.name} to the archive")

    def add_config(
        self, side: Side, config: Tuple[GTNHConfig, GTNHVersion], archive: ZipFile, verbose: bool = False
    ) -> None:
        modpack_config: GTNHConfig
        config_version: Optional[GTNHVersion]
        modpack_config, config_version = config

        config_file: Path = get_asset_version_cache_location(modpack_config, config_version)

        with ZipFile(config_file, "r") as config_zip:

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

    def generate_json_dep(self, side: Side, archive: ZipFile) -> None:
        """
        Generates the dependencies.json and puts it in the archive.

        :param side: the side of the archive
        :param archive: the zipfile object
        :return: None
        """
        mod_list: List[Tuple[GTNHModInfo | ExternalModInfo, GTNHVersion]] = self.get_mods(side)
        mod: GTNHModInfo | ExternalModInfo
        version: GTNHVersion
        dep_json: List[Dict[str, str]] = []
        for mod, version in mod_list:
            if not is_valid_curse_mod(mod, version) and not is_mod_from_github(mod):

                url: Optional[str] = version.download_url
                assert url
                mod_obj: Dict[str, str] = {"path": f"mods/{version.filename}", "url": url}

                dep_json.append(mod_obj)

        with open(self.tempfile, "w") as temp:
            dump(dep_json, temp, indent=2)

        archive.write(self.tempfile, arcname=str(self.dependencies_json))
        if self.task_progress_callback is not None:
            self.task_progress_callback(self.get_progress(), f"adding {self.dependencies_json} to the archive")
        self.tempfile.unlink()

    def generate_meta_data(self, side: Side, archive: ZipFile) -> None:
        """
        Generates the manifest.json and places it in the archive.

        :param side: the side of the pack
        :param archive: the zipfile
        :return: None
        """

        metadata: str = """{
  "minecraft": {
    "version": "1.7.10",
    "modLoaders": [
      {
        "id": "forge-10.13.4.1614",
        "primary": true
      }
    ]
  },
  "manifestType": "minecraftModpack",
  "manifestVersion": 1,
  "name": "GT New Horizons",
  "version": "{0}-1.7.10",
  "author": "DreamMasterXXL",
  "files": [],
  "overrides": "overrides"
}"""
        metadata_object: Dict[str, Any] = loads(metadata)
        metadata_object["version"] = metadata_object["version"].format(self.release.version)

        mod: GTNHModInfo | ExternalModInfo
        version: GTNHVersion
        for mod, version in self.get_mods(side):

            if is_valid_curse_mod(mod, version):
                # ignoring mypy errors here because it's all good in the check above
                data: Dict[str, Any] = {
                    "projectID": int(mod.project_id),  # type: ignore
                    # hacky af but i don't want to go in the process of readding them all by hand while the data is
                    # still stored somewhere else in the metadata
                    "fileID": int(version.browser_download_url.split("/")[-1]),  # type: ignore
                    "required": True,
                }
                metadata_object["files"].append(data)

        with open(self.tempfile, "w") as temp:
            dump(metadata_object, temp, indent=2)

        archive.write(self.tempfile, arcname=str(self.manifest_json))

        if self.task_progress_callback is not None:
            self.task_progress_callback(self.get_progress(), f"adding {self.manifest_json} to the archive")

        self.tempfile.unlink()
