import os
from pathlib import Path
from typing import Callable, Optional
from zipfile import ZipFile

from structlog import get_logger

from gtnh.assembler.downloader import get_mod_version_cache_location
from gtnh.defs import RELEASE_ZIP_DIR, Side
from gtnh.mod_manager import GTNHModManager
from gtnh.models.gtnh_release import GTNHRelease

log = get_logger(__name__)


def assemble_release(mod_manager: GTNHModManager, side: Side, release: GTNHRelease, callback: Optional[Callable[[float, str], None]] = None) -> None:
    """
    Assemble a release.  Assumes the mods have already been downloaded and cached.
    :param mod_manager: GTNH Mod Manager
    :param release: GTNHRelease specifying the release to assemble
    :param callback: Callable to update the progress bar
    """
    if side not in {Side.CLIENT, Side.SERVER}:
        log.error("Can only assemble release for CLIENT or SERVER, not BOTH")
        return

    valid_sides = {side, Side.BOTH}

    # computation of the progress per mod for the progressbar
    delta_progress = 100 / (len(release.github_mods) + len(release.external_mods))

    archive_name = RELEASE_ZIP_DIR / f"GTNewHorizons-{side}-{release.version}.zip"

    # deleting any existing archive
    if os.path.exists(archive_name):
        os.remove(archive_name)
        log.warn(f"Previous archive `{archive_name}` deleted")

    log.info(f"Constructing {side} archive at `{archive_name}`")

    with ZipFile(archive_name, "w") as archive:
        for mod_name, mod_version in release.github_mods.items():
            mod = mod_manager.mods.get_github_mod(mod_name)
            if not mod:
                log.error(f"Cannot find mod {mod_name}")
                return

            if mod.side not in valid_sides:
                continue

            version = mod.get_version(mod_version)
            if not version:
                log.error(f"Cannot find {mod_name}:{mod_version}")
                return

            source_file = get_mod_version_cache_location(mod.name, version)

            if callback is not None:
                callback(delta_progress, f"Packing client archive version {release.version}: {source_file}. Progress: {{0}}%")
            archive_path = Path("mods") / source_file.name
            archive.write(source_file, arcname=archive_path)

    log.info(f"Zip {archive_name} created")


#
# def handle_pack_extra_files(error_callback: Optional[Callable[[], None]] = None) -> None:
#     """
#     Method used to handle all the files needed by the pack like the configs or the scripts.
#
#     :return: None
#     """
#
#     # download the gtnh modpack archive
#     # catch is overkill but we never know
#     try:
#         gtnh_archive_path = download_pack_archive()
#     except LatestReleaseNotFound:
#         if error_callback is not None:
#             error_callback()
#         raise PackingInterruptException
#
#     # prepare for the temp dir receiving the unzip of the archive
#     temp_dir = Path(gtnh_archive_path.parent / "temp")
#     if temp_dir.exists():
#         rmtree(temp_dir)
#     os.makedirs(temp_dir, exist_ok=True)
#
#     # unzip
#     with ZipFile(gtnh_archive_path, "r") as zip_ref:
#         zip_ref.extractall(temp_dir)
#     print("unzipped the pack")
#
#     # load gtnh metadata
#     gtnh_metadata = load_gtnh_manifest()
#
#     # path for the prepared archives
#     client_folder = Path(__file__).parent / "cache" / "client_archive"
#     server_folder = Path(__file__).parent / "cache" / "server_archive"
#
#     # exclusion lists
#     client_exclusions = [temp_dir / exclusion for exclusion in gtnh_metadata.client_exclusions]
#     server_exclusions = [temp_dir / exclusion for exclusion in gtnh_metadata.server_exclusions]
#
#     # listing of all the files for the archive
#     availiable_files = set(crawl(temp_dir))
#     client_files = list(availiable_files - set(client_exclusions))
#     server_files = list(availiable_files - set(server_exclusions))
#
#     # moving the files where they must go
#     print("moving files for the client archive")
#     copy_file_to_folder(client_files, temp_dir, client_folder)
#     print("moving files for the server archive")
#     copy_file_to_folder(server_files, temp_dir, server_folder)
#     print("success")
