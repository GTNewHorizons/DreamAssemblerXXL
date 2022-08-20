# import logging
# import os
# import re
# from pathlib import Path
# from shutil import copy, rmtree
# from typing import Callable, Dict, Optional
# from urllib import parse
# from zipfile import ZipFile
#
# import requests
# from pip._internal.cli.cmdoptions import cache_dir
#
# from gtnh.assembler.downloader import ensure_cache_dir
# from gtnh.defs import TECHNIC_CACHE_DIR
# from gtnh.exceptions import MissingModFileException
# from gtnh.utils import load_gtnh_manifest
#
# log = logging.getLogger("technic process")
# log.setLevel(logging.INFO)
#
#
# def ensure_technic_root_folder() -> Path:
#     """
#     returns the path of the technic root folder and make the missing folders if they don't exist.
#
#     :return: the path object pointing the technic root folder
#     """
#
#     os.makedirs(TECHNIC_CACHE_DIR, exist_ok=True)
#
#     return cache_dir
#
#
# def process_files(modpack_version: str, global_progress_callback: Optional[Callable[[float, str], None]] = None) -> None:
#     """
#     takes the list of files destinated to the client and assemble a solder architecture.
#
#     :param modpack_version: string representing the version of the pack
#     :return: None
#     """
#
#     # flush technic folders if they exist
#     root = ensure_technic_root_folder()
#
#     destination = root / modpack_version
#     if destination.is_dir():
#         rmtree(destination)
#         log.warn(f"deleted previous instance of {destination}")
#     os.makedirs(destination, exist_ok=True)
#
#     # load gtnh metadata
#     gtnh_modpack = load_gtnh_manifest()
#
#     # load mod cache folder
#     mod_cache_dir = ensure_cache_dir() / "mods"
#
#     # generating mod list
#     modlist = [mod for mod in gtnh_modpack.github_mods + gtnh_modpack.external_mods if mod.side in ["CLIENT", "BOTH"]]
#
#     # progress step for global_progress_callback
#     delta_progress = 100 / (len(modlist) + 2)
#
#     for mod in modlist:
#         log.info(f"processing the mod {mod.name}")
#         if global_progress_callback is not None:
#             global_progress_callback(delta_progress, f"generating technic assets for {mod.name}")
#         # get mod stripped name
#         mod_name = get_mod_name(mod.name)
#
#         # destination folder
#         mod_dir = destination / mod_name
#         os.mkdir(mod_dir)
#
#         # get the corresponding jar in the mod cache
#         try:
#             # blame boubou_19 for mixing up browser_download_url and download_url
#             if mod.browser_download_url is None or mod.download_url is None:
#                 raise ValueError(f"mod {mod.name} has its download_url and/or browser_download_url missing")
#
#             url = mod.browser_download_url if mod.browser_download_url.endswith(".jar") else mod.download_url
#
#             # get ride of any %20 like chars in urls
#             mod_file_name = parse.unquote_plus(Path(parse.urlparse(url).path).name)
#
#             # path to the mod in the cache
#             mod_file_path = mod_cache_dir / mod_file_name
#
#             if not mod_file_path.is_file():
#                 raise MissingModFileException(mod_file_name)
#
#         except MissingModFileException as error:
#             log.error(error)
#             log.error("mods are supposed to be downloaded first before packing the technic assets")
#             return
#
#         except ValueError as error:
#             log.error(error)
#             log.error("Please check the mod attributes and retry.")
#
#         # making temp dir structure for the zip
#         os.makedirs(mod_dir / "mods")
#         copy(mod_file_path, mod_dir / "mods")
#
#         # zipping with technic format
#         with ZipFile(mod_dir / f"{mod_name}-{mod.version_tag}.zip", "w") as mod_archive:
#             for x in (mod_dir / "mods").iterdir():
#                 if x.is_file():
#                     mod_archive.write(x, x.relative_to(mod_dir))
#
#         # removing temp dir structure
#         rmtree(mod_dir / "mods")
#
#     # handling of the modpack repo
#     if global_progress_callback is not None:
#         global_progress_callback(delta_progress, "generating technic assets for additional modpack files")
#     # path for the already made client dev pack archive
#     modpack_folder = ensure_cache_dir() / "client_archive"
#
#     # zipping of the archive
#     os.makedirs(destination / "gtnhmodpack", exist_ok=True)
#     log.info("Processing gtnh modpack assets.")
#     with ZipFile(destination / "gtnhmodpack" / f"gtnhmodpack-{modpack_version}.zip", "w") as mod_archive:
#
#         def crawl_zip(path: Path) -> None:
#             for x in path.iterdir():
#                 if x.is_dir():
#                     crawl_zip(x)
#                 # excluding all the jar files as we use the client dev
#                 elif x.is_file() and not x.name.endswith(".jar"):
#                     # pack folder that is already filled with mod jars
#                     mod_archive.write(x, x.relative_to(modpack_folder))
#                     log.info(f"zipped {x.relative_to(modpack_folder)}")
#
#         crawl_zip(modpack_folder)
#
#     # handling forge asset
#     if global_progress_callback is not None:
#         global_progress_callback(delta_progress, "generating technic assets for forge")
#
#     forge_path = destination / "modpack" / "modpack-1.7.10-10.13.4.1614.zip"
#     os.makedirs(forge_path.parent)
#     log.info("downloading forge assets")
#     download_file("http://downloads.gtnewhorizons.com/DreamAssemblerXXL/Technic/modpack-1.7.10-10.13.4.1614.zip",
#     forge_path)
#
#     log.info(f"successfully finished the assembling of technic assets. Folder availiable for upload at {destination}")
#
#
# def get_mod_name(mod_name: str) -> str:
#     """
#     takes the mod name and process it so it has only lower alphanumerical chars
#     :return: the normalised mod name
#     """
#
#     return re.sub("[^a-zA-Z0-9]", "", mod_name).lower()
#
#
# def download_file(url: str, path: Path, headers: Optional[Dict[str, str]] = None) -> None:
#     """
#     Downloads a file from the url and save it to path
#
#     :param url: specified url
#     :param path: specified path
#     :param headers: optional headers when dowloading the file
#     :return: None
#     """
#     if headers is None:
#         headers = {"Accept": "application/octet-stream"}
#
#     with requests.get(url, stream=True, headers=headers) as r:
#         r.raise_for_status()
#         with open(path, "wb") as f:
#             for chunk in r.iter_content(chunk_size=8192):
#                 f.write(chunk)
#
#
# if __name__ == "__main__":
#     process_files("2.1.2.4")
from pathlib import Path
from typing import Optional, Callable

from gtnh.assembler.generic_assembler import GenericAssembler
from gtnh.defs import Side, RELEASE_TECHNIC_DIR
from gtnh.models.gtnh_release import GTNHRelease
from gtnh.modpack_manager import GTNHModpackManager


class TechnicAssembler(GenericAssembler):
    """
    Technic assembler class. Allows for the assembling of technic archives.
    """
    def __init__(
        self,
        gtnh_modpack: GTNHModpackManager,
        release: GTNHRelease,
        task_progress_callback: Optional[Callable[[float, str], None]] = None,
        global_progress_callback: Optional[Callable[[float, str], None]] = None,
    ):
        """
        Constructor of the TechnicAssembler class.

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

    def get_archive_path(self, side: Side) -> Path:
        return RELEASE_TECHNIC_DIR / f"GTNewHorizons-{side}-{self.release.version}.zip"