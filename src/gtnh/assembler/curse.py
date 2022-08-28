import shutil
from pathlib import Path
from typing import Callable, Optional, List, Tuple, Dict
from zipfile import ZipFile

from colorama import Fore
from structlog import get_logger

from gtnh.assembler.downloader import get_asset_version_cache_location
from gtnh.assembler.generic_assembler import GenericAssembler
from gtnh.defs import RELEASE_CURSE_DIR, Side, ModSource, CACHE_DIR, ROOT_DIR
from gtnh.models.gtnh_config import GTNHConfig
from gtnh.models.gtnh_release import GTNHRelease
from gtnh.models.gtnh_version import GTNHVersion
from gtnh.models.mod_info import GTNHModInfo, ExternalModInfo
from gtnh.modpack_manager import GTNHModpackManager

from json import dump, dumps, loads

log = get_logger(__name__)

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
            archive.write(self.overrides, arcname="overrides/overrides.png")

            archive.write(self.overrideslash, arcname="overrides/overrideslash.png")

            log.info("Archive created successfully!")

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

    def generate_json_dep(self, side:Side, archive:ZipFile):
        mod_list: List[Tuple[GTNHModInfo | ExternalModInfo, GTNHVersion]] = self.get_mods(side)
        mod: GTNHModInfo | ExternalModInfo
        version: GTNHVersion
        dep_json: List[Dict[str, str]] = []
        for mod, version in mod_list:
            if mod.source != ModSource.curse:
                mod_obj: Dict[str, str] = {
                    "path":f"mods/{version.filename}",
                    "url":version.download_url
                }

                dep_json.append(mod_obj)

        with open(self.tempfile, "w") as temp:
            dump(dep_json,temp, indent=2)

        archive.write(self.tempfile, arcname=str(self.dependencies_json))



    def generate_meta_data(self, side:Side, archive:ZipFile):
        metadata=\
"""{
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
        metadata_object = loads(metadata)
        metadata_object["version"] = metadata_object["version"].format(self.release.version)
        for mod, version in self.get_mods(side):
            if mod.source == ModSource.curse:
                data: Dict[str, int|bool]={
                    "projectID": mod.project_id,
                    "fileID": version.browser_download_url.split("/")[-1],  # hacky af but i don't want to go in the
                                                                            # process of readding them all by hand
                                                                            # while the data is still stored somewhere
                                                                            # else in the metadata
                    "required": True
                }
                metadata_object["files"].append(data)

        with open(self.tempfile, "w") as temp:
            dump(metadata_object, temp, indent=2)

        archive.write(self.tempfile, arcname=str(self.manifest_json))

