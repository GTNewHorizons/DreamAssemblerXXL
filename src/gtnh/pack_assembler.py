import os
from pathlib import Path
from shutil import rmtree
from typing import Callable, List, Optional
from zipfile import ZipFile

from gtnh.exceptions import LatestReleaseNotFound, PackingInterruptException
from gtnh.pack_downloader import download_pack_archive, ensure_cache_dir
from gtnh.utils import copy_file_to_folder, crawl, load_gtnh_manifest


def pack_clientpack(client_paths: List[Path], pack_version: str, callback: Optional[Callable[[float, str], None]] = None) -> None:
    """
    Method used to pack all the client files into a client archive.

    :param client_paths: a list containing all the Path objects refering to the files needed client side.
    :param pack_version: the version of the pack.
    :param callback: Callable that takes a float and a string in parameters. (mainly the method to update the
            progress bar that takes a progress step per call and the label used to display infos to the user)
    :return: None
    """

    # computation of the progress per mod for the progressbar
    delta_progress = 100 / len(client_paths)

    # remembering the cwd because it'll be changed during the zip operation
    cwd = os.getcwd()
    cache_dir = Path(ensure_cache_dir())
    os.chdir(cache_dir)

    # archive name
    archive_name = f"client-{pack_version}.zip"

    # deleting any previous client archive
    if os.path.exists(archive_name):
        os.remove(archive_name)
        print("previous client archive deleted")

    print("zipping client archive")
    # zipping the files in the archive
    with ZipFile(archive_name, "w") as client_archive:
        for mod_path in client_paths:
            if callback is not None:
                callback(delta_progress, f"Packing client archive version {pack_version}: {mod_path.name}. Progress: {{0}}%")

            # writing the file in the zip
            client_archive.write(mod_path, mod_path.relative_to(cache_dir / "client_archive"))

    print("success!")

    # restoring the cwd
    os.chdir(cwd)


def pack_serverpack(server_paths: List[Path], pack_version: str, callback: Optional[Callable[[float, str], None]] = None) -> None:
    """
    Method used to pack all the server files into a client archive.

    :param server_paths: a list containing all the Path objects refering to the files needed server side.
    :param pack_version: the version of the pack.
    :param callback: Callable that takes a float and a string in parameters. (mainly the method to update the
            progress bar that takes a progress step per call and the label used to display infos to the user)
    :return: None
    """

    # computation of the progress per mod for the progressbar
    delta_progress = 100 / len(server_paths)

    # remembering the cwd because it'll be changed during the zip operation
    cwd = os.getcwd()
    cache_dir = Path(ensure_cache_dir())
    os.chdir(cache_dir)

    # archive name
    archive_name = f"server-{pack_version}.zip"

    # deleting any previous client archive
    if os.path.exists(archive_name):
        os.remove(archive_name)
        print("previous server archive deleted")

    print("zipping client archive")
    # zipping the files in the archive
    with ZipFile(archive_name, "w") as server_archive:
        for mod_path in server_paths:
            if callback is not None:
                callback(delta_progress, f"Packing server archive version {pack_version}: {mod_path.name}. Progress: {{0}}%")

            # writing the file in the zip
            server_archive.write(mod_path, mod_path.relative_to(cache_dir / "server_archive"))

    print("success!")

    # restoring the cwd
    os.chdir(cwd)


def handle_pack_extra_files(error_callback: Optional[Callable[[], None]] = None) -> None:
    """
    Method used to handle all the files needed by the pack like the configs or the scripts.

    :return: None
    """

    # download the gtnh modpack archive
    # catch is overkill but we never know
    try:
        gtnh_archive_path = download_pack_archive()
    except LatestReleaseNotFound:
        if error_callback is not None:
            error_callback()
        raise PackingInterruptException

    # prepare for the temp dir receiving the unzip of the archive
    temp_dir = Path(gtnh_archive_path.parent / "temp")
    if temp_dir.exists():
        rmtree(temp_dir)
    os.makedirs(temp_dir, exist_ok=True)

    # unzip
    with ZipFile(gtnh_archive_path, "r") as zip_ref:
        zip_ref.extractall(temp_dir)
    print("unzipped the pack")

    # load gtnh metadata
    gtnh_metadata = load_gtnh_manifest()

    # path for the prepared archives
    cache_dir = ensure_cache_dir()
    client_folder = cache_dir / "client_archive"
    server_folder = cache_dir / "server_archive"

    # exclusion lists
    client_exclusions = [temp_dir / exclusion for exclusion in gtnh_metadata.client_exclusions]
    server_exclusions = [temp_dir / exclusion for exclusion in gtnh_metadata.server_exclusions]

    # listing of all the files for the archive
    availiable_files = set(crawl(temp_dir))
    client_files = list(availiable_files - set(client_exclusions))
    server_files = list(availiable_files - set(server_exclusions))

    # moving the files where they must go
    print("moving files for the client archive")
    copy_file_to_folder(client_files, temp_dir, client_folder)
    print("moving files for the server archive")
    copy_file_to_folder(server_files, temp_dir, server_folder)
    print("success")
