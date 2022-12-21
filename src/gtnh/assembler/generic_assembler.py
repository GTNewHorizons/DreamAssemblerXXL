"""Module defining a generic assembler class which other assemblers will extend."""
import os
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set, Tuple, Union
from zipfile import ZIP_DEFLATED, ZipFile

from colorama import Fore
from structlog import get_logger

from gtnh.assembler.downloader import get_asset_version_cache_location
from gtnh.assembler.exclusions import Exclusions
from gtnh.defs import README_TEMPLATE, RELEASE_README_DIR, ModSource, Side
from gtnh.models.gtnh_config import GTNHConfig
from gtnh.models.gtnh_release import GTNHRelease
from gtnh.models.gtnh_version import GTNHVersion
from gtnh.models.mod_info import GTNHModInfo
from gtnh.models.mod_version_info import ModVersionInfo
from gtnh.modpack_manager import GTNHModpackManager

log = get_logger(__name__)


class GenericAssembler:
    """Generic assembler class."""

    def __init__(
        self,
        gtnh_modpack: GTNHModpackManager,
        release: GTNHRelease,
        task_progress_callback: Optional[Callable[[float, str], None]] = None,
        global_progress_callback: Optional[Callable[[float, str], None]] = None,
        changelog_path: Optional[Path] = None,
    ):
        """
        Construct the GenericAssembler class.

        Parameters
        ----------
        gtnh_modpack: GTNHModpackManager
            The modpack manager instance.

        release: GTNHRelease
            The targetted release.

        task_progress_callback: Optional[Callable[[float, str], None]]
            The callback used to report progress within the task process.

        global_progress_callback: Optional[Callable[[float, str], None]]
            The callback used to report total progress.

        changelog_path: Optional[Path]
            The path of the changelog.
        """
        self.modpack_manager: GTNHModpackManager = gtnh_modpack
        self.release: GTNHRelease = release
        self.global_progress_callback: Optional[Callable[[float, str], None]] = global_progress_callback
        self.task_progress_callback: Optional[Callable[[float, str], None]] = task_progress_callback
        self.changelog_path: Optional[Path] = changelog_path

        self.exclusions: Dict[str, Exclusions] = {
            Side.CLIENT: Exclusions(self.modpack_manager.mod_pack.client_exclusions),
            Side.SERVER: Exclusions(self.modpack_manager.mod_pack.server_exclusions),
        }
        self.delta_progress: float = 0.0

    def get_progress(self) -> float:
        """
        Get the value of self.delta_progress.

        Returns
        -------
        A float corresponding to the value  of self.delta_progress.
        """
        return self.delta_progress

    def set_progress(self, delta_progress: float) -> None:
        """
        Set the value of self.delta_progress.

        Parameters
        ----------
        delta_progress: float
            The new value.

        Returns
        -------
        None
        """
        self.delta_progress = delta_progress

    def get_amount_of_files_in_config(self, side: Side) -> int:
        """
        Get the amount of files inside the config zip.

        Parameters
        ----------
        side: Side
            The targeted side to assemble.

        Returns
        -------
        An int corresponding to the amount of files in the config zip.
        """
        modpack_config: GTNHConfig
        config_version: GTNHVersion

        modpack_config, config_version = self.get_config()
        config_file: Path = get_asset_version_cache_location(modpack_config, config_version)

        with ZipFile(config_file, "r", compression=ZIP_DEFLATED) as config_zip:
            return len([item for item in config_zip.namelist() if item not in self.exclusions[side]])

    def get_mods(self, side: Side) -> List[Tuple[GTNHModInfo, GTNHVersion]]:
        """
        Grab the mod info objects as well as their targeted version.

        Parameters
        ----------
        side: Side
            The targeted side.

        Returns
        -------
        A list of (mod, mod version).
        """
        valid_sides: Set[Side] = {side, Side.BOTH}

        github_mods: List[Tuple[GTNHModInfo, GTNHVersion]] = self.github_mods(valid_sides)

        external_mods: List[Tuple[GTNHModInfo, GTNHVersion]] = self.external_mods(valid_sides)

        mods: List[Tuple[GTNHModInfo, GTNHVersion]] = github_mods + external_mods
        return mods

    def external_mods(self, valid_sides: Set[Side]) -> List[Tuple[GTNHModInfo, GTNHVersion]]:
        """
        Grab the external mod info objects as well as their targeted version.

        Parameters
        ----------
        valid_sides: Set[Side]
            A set of valid sides for the release.

        Returns
        -------
        A list of couple (github mod, version).
        """
        get_mod: Callable[
            [str, ModVersionInfo, Set[Side], ModSource],
            Optional[tuple[Union[GTNHModInfo], GTNHVersion]],
        ] = self.modpack_manager.assets.get_mod_and_version

        external_mods: List[Tuple[GTNHModInfo, GTNHVersion]] = list(
            filter(
                None,
                [
                    get_mod(name, version, valid_sides, ModSource.other)
                    for name, version in self.release.external_mods.items()
                ],
            )
        )

        return external_mods

    def github_mods(self, valid_sides: Set[Side]) -> List[Tuple[GTNHModInfo, GTNHVersion]]:
        """
        Grab the GitHub mod info objects as well as their targeted version.

        Parameters
        ----------
        valid_sides: Set[Side]
            A set of valid sides for the release.

        Returns
        -------
        A list of couple (github mod, version).
        """
        get_mod: Callable[
            [str, ModVersionInfo, Set[Side], ModSource],
            Optional[tuple[GTNHModInfo, GTNHVersion]],
        ] = self.modpack_manager.assets.get_mod_and_version

        github_mods: List[Tuple[GTNHModInfo, GTNHVersion]] = list(
            filter(
                None,
                [
                    get_mod(name, version, valid_sides, ModSource.github)
                    for name, version in self.release.github_mods.items()
                ],
            )
        )

        return github_mods

    def get_config(self) -> Tuple[GTNHConfig, GTNHVersion]:
        """
        Get the config file from the release.

        Returns
        -------
        A couple (config, version) corresponding to the targeted release.
        """
        config: GTNHConfig = self.modpack_manager.assets.config
        version: Optional[GTNHVersion] = config.get_version(self.release.config)
        assert version
        return config, version

    def add_mods(
        self,
        side: Side,
        mods: list[tuple[GTNHModInfo, GTNHVersion]],
        archive: ZipFile,
        verbose: bool = False,
    ) -> None:
        """
        Add mods to the archive being assembled.

        Parameters
        ----------
        side: Side
            The side of the archive being assembled.

        mods: list[tuple[GTNHModInfo, GTNHVersion]]
            List of (mod info / version) being added to the assembled archive.

        archive: ZipFile
            The assembled archive.

        verbose: bool
            Boolean controlling if yes or no the assembling process should be verbose.

        Returns
        -------
        None.
        """
        raise NotImplementedError

    def add_config(
        self, side: Side, config: Tuple[GTNHConfig, GTNHVersion], archive: ZipFile, verbose: bool = False
    ) -> None:
        """
        Add config to the archive being assembled.

        Parameters
        ----------
        side : Side
            The side of the archive being assembled.

        config: Tuple[GTNHConfig, GTNHVersion]
            (config / version) couple used to determine config release used to assemble the pack.

        archive : ZipFile
            The assembled archive.

        verbose : bool
            Boolean controlling if yes or no the assembling process should be verbose.

        Returns
        -------
        None.
        """
        self.add_changelog(archive)

    async def assemble(self, side: Side, verbose: bool = False) -> None:
        """
        Assemble the release.

        Parameters
        ----------
        side : Side
            The side of the archive being assembled.

        verbose : bool
            Boolean controlling if yes or no the assembling process should be verbose.

        Returns
        -------
        None.
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
            log.info("Generating the readme for the modpack repo")
            self.generate_readme()
            log.info("Archive created successfully!")

    def get_archive_path(self, side: Side) -> Path:
        """
        Get the archive path for the release.

        Parameters
        ----------
        side : Side
            The side of the archive being assembled.

        Returns
        -------
        A Path object representing the archive's path.
        """
        raise NotImplementedError

    def add_changelog(self, archive: ZipFile, arcname: Optional[Path] = None) -> None:
        """
        Add the changelog to the archive.

        Parameters
        ----------
        archive: ZipFile
            The archive being created.

        arcname: Optional[Path]
            The path of the file inside the archive, if provided.

        Returns
        -------
        None
        """
        if self.changelog_path is not None:
            if self.task_progress_callback is not None:
                self.task_progress_callback(self.get_progress(), "adding changelog to the archive")
            if arcname is None:
                archive.write(self.changelog_path, arcname=self.changelog_path.name)
            else:
                archive.write(self.changelog_path, arcname=arcname)

    def generate_readme(self) -> None:
        """
        Generate the readme for the modpack repo, based on the mods in the given release.

        Returns
        -------
        None
        """
        with open(README_TEMPLATE, "r") as file:
            data = "".join(file.readlines())

            version: str = self.release.version
            release_date: str = str(self.release.last_updated.date())
            mod_list: str = self.generate_modlist()

            data = data.format(version, release_date, mod_list)
            with open(RELEASE_README_DIR / f"README_{self.release.version}.MD", "w") as readme:
                readme.write(data)

    def generate_modlist(self) -> str:
        """
        Generate the markdown for the modlist in the readme for the given release.

        Returns
        -------
        A string for the modlist.
        """
        valid_sides: Set[Side] = {Side.CLIENT, Side.SERVER, Side.BOTH}
        lines: List[str] = []

        # it seems i'm obligated to get mods separatedly because self.get_mods is somehow
        # casting external mods into github mods

        github_mods: List[Tuple[GTNHModInfo, GTNHVersion]] = self.github_mods(valid_sides)

        for mod, version in github_mods:
            assert isinstance(mod, GTNHModInfo)
            lines.append(f"| [{mod.name}]({mod.repo_url}) | {version.version_tag} |")

        external_mods: List[Tuple[GTNHModInfo, GTNHVersion]] = self.external_mods(valid_sides)

        for mod, version in external_mods:
            assert not mod.is_github()
            lines.append(f"| [{mod.name}]({mod.external_url}) | {version.version_tag} |")

        return "\n".join(sorted(lines, key=lambda x: x.lower()))
