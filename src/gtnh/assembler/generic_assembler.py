import os
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set, Tuple, Union
from zipfile import ZipFile

from colorama import Fore
from structlog import get_logger

from gtnh.defs import ModSource, Side
from gtnh.models.gtnh_config import GTNHConfig
from gtnh.models.gtnh_release import GTNHRelease
from gtnh.models.gtnh_version import GTNHVersion
from gtnh.models.mod_info import ExternalModInfo, GTNHModInfo
from gtnh.modpack_manager import GTNHModpackManager

log = get_logger(__name__)


class GenericAssembler:
    def __init__(
        self,
        gtnh_modpack: GTNHModpackManager,
        release: GTNHRelease,
        progress_callback: Optional[Callable[[float, str], None]] = None,
    ):
        self.modpack_manager: GTNHModpackManager = gtnh_modpack
        self.release: GTNHRelease = release
        self.callback: Optional[Callable[[float, str], None]]
        self.progress_callback = progress_callback
        self.exclusions: Dict[str, List[str]] = {
            Side.CLIENT: self.modpack_manager.mod_pack.client_exclusions,
            Side.SERVER: self.modpack_manager.mod_pack.server_exclusions,
        }

    def get_mods(self, side: Side) -> List[Tuple[GTNHModInfo | ExternalModInfo, GTNHVersion]]:
        get_mod: Callable[
            [str, str, Set[Side], ModSource], Optional[tuple[Union[GTNHModInfo, ExternalModInfo], GTNHVersion]]
        ] = self.modpack_manager.assets.get_mod_and_version
        valid_sides: Set[Side] = {side, Side.BOTH}

        github_mods: List[Optional[Tuple[GTNHModInfo | ExternalModInfo, GTNHVersion]]] = [
            get_mod(name, version, valid_sides, ModSource.github) for name, version in self.release.github_mods.items()
        ]

        external_mods: List[Optional[Tuple[GTNHModInfo | ExternalModInfo, GTNHVersion]]] = [
            get_mod(name, version, valid_sides, ModSource.github)
            for name, version in self.release.external_mods.items()
        ]

        mods: List[Tuple[GTNHModInfo | ExternalModInfo, GTNHVersion]] = list(filter(None, github_mods + external_mods))
        return mods

    def get_config(self) -> Tuple[GTNHConfig, GTNHVersion]:
        """
        Method to get the config file from the release.

        :return: a tuple with the GTNHConfig and GTNHVersion of the release's config
        """

        config: GTNHConfig = self.modpack_manager.assets.config
        version: Optional[GTNHVersion] = config.get_version(self.release.config)
        assert version
        return config, version

    def add_mods(
        self, side: Side, mods: list[tuple[GTNHModInfo, GTNHVersion]], archive: ZipFile, verbose: bool = False
    ) -> None:
        """
        Method to add mods in the zip archive.

        :param side: target side
        :param mods: target mods
        :param archive: archive being built
        :param verbose: flag to turn on verbose mode
        :return: None
        """
        pass

    def add_config(
        self, side: Side, config: Tuple[GTNHConfig, GTNHVersion], archive: ZipFile, verbose: bool = False
    ) -> None:
        """
        Method to add config in the zip archive.

        :param side: target side
        :param config: a tuple giving the config object and the version object of the config
        :param archive: archive being built
        :param verbose: flag to turn on verbose mode
        :return: None
        """
        pass

    def remove_excluded_files(self, side: Side, verbose: bool = False) -> None:
        """
        Method to remove the excluded files from the archive.

        :param side: target side
        :param verbose: flag to enable the verbose mode
        :return: None
        """
        pass

    def update_progress(self, side: Side, source_file: Path, verbose: bool = False) -> None:
        """
        Method used to report progress.

        :param side: target side
        :param source_file: file path being added
        :param verbose: flag to turn on verbose mode
        :return: None
        """
        pass

    def assemble(self, side: Side, verbose: bool = False) -> None:
        """
        Method to assemble the release.

        :param side: target side
        :param verbose: flag to enable the verbose mode
        :return: None
        """
        if side not in {Side.CLIENT, Side.SERVER}:
            raise Exception("Can only assemble release for CLIENT or SERVER, not BOTH")

        archive_name: Path = self.get_archive_path(side)

        # deleting any existing archive
        if os.path.exists(archive_name):
            os.remove(archive_name)
            log.warn(f"Previous archive {Fore.YELLOW}'{archive_name}'{Fore.RESET} deleted")

        log.info(f"Constructing {Fore.YELLOW}{side}{Fore.RESET} archive at {Fore.YELLOW}'{archive_name}'{Fore.RESET}")

        with ZipFile(self.get_archive_path(side), "w") as archive:
            log.info("Adding mods to the archive")
            self.add_mods(side, self.get_mods(side), archive, verbose=verbose)
            log.info("Adding config to the archive")
            self.add_config(side, self.get_config(), archive, verbose=verbose)
            self.remove_excluded_files(side, verbose=verbose)

    def get_archive_path(self, side: Side) -> Path:
        """
        Method to get the path to the assembled pack release.

        :return: the path to the release
        """
        pass
