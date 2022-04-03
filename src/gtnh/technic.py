import re
from pathlib import Path
import os
from shutil import rmtree, copy
from zipfile import ZipFile

from utils import load_gtnh_manifest, crawl
from pack_assembler import ensure_cache_dir
from urllib import parse
from exceptions import MissingModFileException

CACHE_DIR = "cache"

def ensure_technic_root_folder()->Path:
    """
    returns the path of the technic root folder and make the missing folders if they don't exist.

    :return: the path object pointing the technic root folder
    """

    cache_dir = Path(os.getcwd()) / CACHE_DIR / "technic"
    os.makedirs(cache_dir, exist_ok=True)

    return cache_dir

def process_files(modpack_version:str):
    """
    takes the list of files destinated to the client and assemble a solder architecture.

    :param modpack_version: string representing the version of the pack
    :return:
    """

    # flush technic folders if they exist
    root = ensure_technic_root_folder()

    destination = root / modpack_version
    if destination.is_dir():
        rmtree(destination)
    os.makedirs(destination, exist_ok=True)

    #load gtnh metadata
    gtnh_modpack = load_gtnh_manifest()

    # load mod cache folder
    mod_cache_dir = ensure_cache_dir() / "mods"

    # for each mod, processing it
    modlist = [mod for mod in gtnh_modpack.github_mods + gtnh_modpack.external_mods if mod.side in ["CLIENT", "BOTH"]]
    for mod in modlist:
        #get mod stripped name
        mod_name = get_mod_name(mod.name)

        # destination folder
        mod_dir = destination / mod_name
        os.mkdir(mod_dir)

        # get the corresponding jar in the mod cache
        try:
            # blame boubou_19 for mixing up browser_download_url and download_url
            url = mod.browser_download_url if mod.browser_download_url.endswith(".jar") else mod.download_url

            # get ride of any %20 like chars in urls
            mod_file_name = parse.unquote_plus(
                Path(
                    parse.urlparse(
                        url
                    ).path
                ).name
            )

            # path to the mod in the cache
            mod_file_path = mod_cache_dir / mod_file_name

            if not mod_file_path.is_file():
                raise MissingModFileException(mod_file_name)

        except MissingModFileException as error:
            print(error)
            print("mods are supposed to be downloaded first before packing the technic assets")
            return

        # making temp dir structure for the zip
        os.makedirs(mod_dir / "mods")
        copy(mod_file_path, mod_dir / "mods")

        # zipping with technic format
        with ZipFile(mod_dir / f"{mod_name}-{mod.version}.zip", "w") as mod_archive:
            for x in (mod_dir / "mods").iterdir():
                if x.is_file():
                    mod_archive.write(x, x.relative_to(mod_dir))

        # removing temp dir structure
        rmtree(mod_dir / "mods")


    # handling of the modpack repo

    # path for the already made client dev pack archive
    modpack_folder = ensure_cache_dir() / "client_archive"

    # zipping of the archive
    os.makedirs(destination / "gtnhmodpack", exist_ok=True)
    with ZipFile(destination / "gtnhmodpack" / f"gtnhmodpack-{modpack_version}.zip", "w") as mod_archive:
        def crawl_zip(path:Path)->None:
            for x in path.iterdir():
                if x.is_dir():
                    crawl_zip(x)
                elif x.is_file() and not x.name.endswith(".jar"): # excluding all the jar files as we use the client dev
                                                                  # pack folder that is already filled with mod jars
                    mod_archive.write(x, x.relative_to(modpack_folder))
                    print(f"zipped {x.relative_to(modpack_folder)}")

        crawl_zip(modpack_folder)


    print("success")
def get_mod_name(mod_name: str) -> str:
    """
    takes the mod name and process it so it has only lower alphanumerical chars
    :return: the a
    """

    return re.sub("[^a-zA-Z0-9]", "", mod_name).lower()

if __name__ == "__main__":
    process_files("2.1.2.4")
