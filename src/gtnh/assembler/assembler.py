import os
import shutil
from pathlib import Path
from typing import Callable, Optional
from zipfile import ZIP_DEFLATED, ZipFile

from colorama import Fore
from structlog import get_logger

from gtnh.assembler.downloader import get_asset_version_cache_location
from gtnh.defs import RELEASE_ZIP_DIR, ModSource, Side
from gtnh.models.gtnh_release import GTNHRelease
from gtnh.models.gtnh_version import GTNHVersion
from gtnh.models.mod_info import GTNHModInfo
from gtnh.modpack_manager import GTNHModpackManager

log = get_logger(__name__)


class ReleaseAssembler:
    def __init__(self, mod_manager: GTNHModpackManager, release: GTNHRelease, callback: Optional[Callable[[float, str], None]] = None) -> None:
        self.mod_manager = mod_manager
        self.release = release
        self.callback = callback

        # computation of the progress per mod for the progressbar
        self.count = 0.0
        self.progress = 0.0
        self.delta_progress = 0.0

    def assemble(self, side: Side, verbose: bool = False) -> None:
        if side not in {Side.CLIENT, Side.SERVER}:
            raise Exception("Can only assemble release for CLIENT or SERVER, not BOTH")

        valid_sides = {side, Side.BOTH}

        archive_name = RELEASE_ZIP_DIR / f"GTNewHorizons-{side}-{self.release.version}.zip"
        get_mod = self.mod_manager.assets.get_mod_and_version
        github_mods = list(filter(None, (get_mod(name, version, valid_sides, source=ModSource.github) for name, version in self.release.github_mods.items())))

        self.count = len(github_mods) + 1  # + len(self.release.external_mods)
        self.delta_progress = 100.0 / self.count

        # deleting any existing archive
        if os.path.exists(archive_name):
            os.remove(archive_name)
            log.warn(f"Previous archive {Fore.YELLOW}'{archive_name}'{Fore.RESET} deleted")

        log.info(f"Constructing {Fore.YELLOW}{side}{Fore.RESET} archive at {Fore.YELLOW}'{archive_name}'{Fore.RESET}")

        with ZipFile(archive_name, "w") as archive:
            self.add_mods(side, github_mods, archive, verbose=verbose)
            self.add_config(side, archive, verbose=verbose)

    def add_mods(self, side: Side, mods: list[tuple[GTNHModInfo, GTNHVersion]], archive: ZipFile, verbose: bool = False) -> None:
        for mod, version in mods:
            source_file = get_asset_version_cache_location(mod, version)
            self.update_progress(side, source_file, verbose=verbose)
            archive_path = Path("mods") / source_file.name
            archive.write(source_file, arcname=archive_path)

    def add_config(self, side: Side, archive: ZipFile, verbose: bool = False) -> None:
        config = self.mod_manager.assets.config
        version = config.get_version(self.release.config)
        assert version
        config_file = get_asset_version_cache_location(config, version)
        exclusions = self.mod_manager.mod_pack.client_exclusions if side == Side.CLIENT else self.mod_manager.mod_pack.server_exclusions
        with ZipFile(config_file, "r", compression=ZIP_DEFLATED) as config_zip:
            self.update_progress(side, config_file, verbose=verbose)

            for item in config_zip.namelist():
                if item in exclusions:
                    continue
                with config_zip.open(item) as config_item:
                    with archive.open(item, "w") as target:
                        shutil.copyfileobj(config_item, target)

    def update_progress(self, side: Side, source_file: Path, verbose: bool = False) -> None:
        if self.callback is not None:
            self.callback(self.delta_progress, f"Packing {side.value} archive version {self.release.version}: {source_file}. Progress: {{0}}%")
        if verbose:
            self.progress += self.delta_progress
            log.info(f"({self.progress:3.0f}%) Adding `{Fore.GREEN}{source_file}{Fore.RESET}`")
