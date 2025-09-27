import os
import shutil
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set, Tuple, Union
from zipfile import ZIP_DEFLATED, ZipFile

from colorama import Fore

from gtnh.assembler.downloader import get_asset_version_cache_location
from gtnh.assembler.exclusions import Exclusions
from gtnh.defs import README_TEMPLATE, RELEASE_README_DIR, ModSource, Side
from gtnh.gtnh_logger import get_logger
from gtnh.models.gtnh_config import GTNHConfig
from gtnh.models.gtnh_release import GTNHRelease
from gtnh.models.gtnh_version import GTNHVersion
from gtnh.models.mod_info import GTNHModInfo
from gtnh.models.mod_version_info import ModVersionInfo
from gtnh.modpack_manager import GTNHModpackManager

log = get_logger(__name__)


class GenericAssembler:
    """
    Generic assembler class.
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
        Constructor of the GenericAssembler class.

        :param gtnh_modpack: the modpack manager instance
        :param release: the target release object
        :param task_progress_callback: the callback to report the progress of the task
        :param global_progress_callback: the callback to report the global progress
        """
        self.modpack_manager: GTNHModpackManager = gtnh_modpack
        self.release: GTNHRelease = release
        self.global_progress_callback: Optional[Callable[[float, str], None]] = global_progress_callback
        self.task_progress_callback: Optional[Callable[[float, str], None]] = task_progress_callback
        self.changelog_path: Optional[Path] = changelog_path

        mod_pack = self.modpack_manager.mod_pack
        self.exclusions: Dict[str, Exclusions] = {
            Side.CLIENT: Exclusions(mod_pack.client_exclusions + mod_pack.client_java8_exclusions),
            Side.SERVER: Exclusions(mod_pack.server_exclusions + mod_pack.server_java8_exclusions),
            Side.CLIENT_JAVA9: Exclusions(mod_pack.client_exclusions + mod_pack.client_java9_exclusions),
            Side.SERVER_JAVA9: Exclusions(mod_pack.server_exclusions + mod_pack.server_java9_exclusions),
        }
        self.delta_progress: float = 0.0

    def get_progress(self) -> float:
        """
        Getter for self.delta_progress.

        :return: current delta progress value
        """
        return self.delta_progress

    def set_progress(self, delta_progress: float) -> None:
        """
        Setter for self.delta_progress.

        :param delta_progress: the new delta progress
        :return: None
        """
        self.delta_progress = delta_progress

    def get_amount_of_files_in_config(self, side: Side) -> int:
        """
        Method to get the amount of files inside the config zip.

        :param side: targetted side for the release
        :return: the amount of files
        """
        modpack_config: GTNHConfig
        config_version: GTNHVersion

        modpack_config, config_version = self.get_config()
        config_file: Path = get_asset_version_cache_location(modpack_config, config_version)

        with ZipFile(config_file, "r", compression=ZIP_DEFLATED) as config_zip:
            return len([item for item in config_zip.namelist() if item not in self.exclusions[side]])

    def get_amount_of_files_in_locales(self) -> int:
        """
        Method to get the amount of files inside all the locale zips.

        Returns
        -------
        int: the amount of files for the locales.
        """
        sum: int = 0
        for language in self.modpack_manager.assets.translations.versions:
            locale_zip_path: Path = get_asset_version_cache_location(self.modpack_manager.assets.translations, language)
            with ZipFile(locale_zip_path, "r", compression=ZIP_DEFLATED) as locale_zip:
                sum += len([item for item in locale_zip.namelist() if not item.endswith("/")])
        return sum

    def get_mods(self, side: Side) -> List[Tuple[GTNHModInfo, GTNHVersion]]:
        """
        Method to grab the mod info objects as well as their targetted version.

        :param side: the targetted side
        :return: a list of couples where the first object is the mod info object, the second is the targetted version.
        """

        valid_sides: Set[Side] = side.valid_mod_sides()

        github_mods: List[Tuple[GTNHModInfo, GTNHVersion]] = self.github_mods(valid_sides)

        external_mods: List[Tuple[GTNHModInfo, GTNHVersion]] = self.external_mods(valid_sides)

        mods: List[Tuple[GTNHModInfo, GTNHVersion]] = github_mods + external_mods
        return mods

    def external_mods(
        self, valid_sides: Set[Side], release: Optional[GTNHRelease] = None
    ) -> List[Tuple[GTNHModInfo, GTNHVersion]]:
        """
        Method to grab the external mod info objects as well as their targetted version.

        :param valid_sides: a set of valid sides to retrieve the mods from.
        :param release: if specified, the release version to get data from instead of the one used for the assembling.
        """
        get_mod: Callable[
            [str, ModVersionInfo, Set[Side], ModSource],
            Optional[tuple[Union[GTNHModInfo], GTNHVersion]],
        ] = self.modpack_manager.assets.get_mod_and_version

        release = self.release if release is None else release

        external_mods: List[Tuple[GTNHModInfo, GTNHVersion]] = list(
            filter(
                None,
                [
                    get_mod(name, version, valid_sides, ModSource.other)
                    for name, version in release.external_mods.items()
                ],
            )
        )

        return external_mods

    def github_mods(
        self, valid_sides: Set[Side], release: Optional[GTNHRelease] = None
    ) -> List[Tuple[GTNHModInfo, GTNHVersion]]:
        """
        Method to grab the github mod info objects as well as their targetted version.

        :param valid_sides: a set of valid sides to retrieve the mods from.
        :param release: if specified, the release version to get data from instead of the one used for the assembling.
        """
        get_mod: Callable[
            [str, ModVersionInfo, Set[Side], ModSource],
            Optional[tuple[GTNHModInfo, GTNHVersion]],
        ] = self.modpack_manager.assets.get_mod_and_version
        release = self.release if release is None else release

        github_mods: List[Tuple[GTNHModInfo, GTNHVersion]] = list(
            filter(
                None,
                [
                    get_mod(name, version, valid_sides, ModSource.github)
                    for name, version in release.github_mods.items()
                ],
            )
        )

        return github_mods

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
        self,
        side: Side,
        mods: list[tuple[GTNHModInfo, GTNHVersion]],
        archive: ZipFile,
        verbose: bool = False,
    ) -> None:
        """
        Method to add mods in the zip archive.

        :param side: target side
        :param mods: target mods
        :param archive: archive being built
        :param verbose: flag to turn on verbose mode
        :return: None
        """
        raise NotImplementedError

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
        self.add_changelog(archive)

    async def assemble(self, side: Side, verbose: bool = False) -> None:
        """
        Method to assemble the release.

        :param side: target side
        :param verbose: flag to enable the verbose mode
        :return: None
        """
        if side not in {Side.CLIENT, Side.SERVER, Side.CLIENT_JAVA9, Side.SERVER_JAVA9}:
            raise Exception(f"Can only assemble release for CLIENT or SERVER, not {side}")

        archive_name: Path = self.get_archive_path(side)

        # deleting any existing archive
        if os.path.exists(archive_name):
            os.remove(archive_name)
            log.warn(f"Previous archive {Fore.YELLOW}'{archive_name}'{Fore.RESET} deleted")

        log.info(f"Constructing {Fore.YELLOW}{side}{Fore.RESET} archive at {Fore.YELLOW}'{archive_name}'{Fore.RESET}")

        with ZipFile(self.get_archive_path(side), "w", compression=ZIP_DEFLATED) as archive:
            log.info("Adding mods to the archive")
            self.add_mods(side, self.get_mods(side), archive, verbose=verbose)
            log.info("Adding config to the archive")
            self.add_config(side, self.get_config(), archive, verbose=verbose)
            log.info("Generating the readme for the modpack repo")
            self.generate_readme()
            log.info("Archive created successfully!")

    def get_archive_path(self, side: Side) -> Path:
        """
        Method to get the path to the assembled pack release.

        :return: the path to the release
        """
        raise NotImplementedError

    def add_changelog(self, archive: ZipFile, arcname: Optional[Path] = None) -> None:
        """
        Method to add the changelog to the archive.

        :param archive: the archive object
        :return: None
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
        Generates the readme for the modpack repo, based on the mods in the given release.

        :param version: the given release
        :return: None
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
        Generates the markdown for the modlist in the readme for the given release.

        :return: the string for the modlist
        """
        valid_sides: Set[Side] = {
            Side.CLIENT,
            Side.SERVER,
            Side.BOTH,
            Side.CLIENT_JAVA9,
            Side.SERVER_JAVA9,
            Side.BOTH_JAVA9,
        }
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

    def add_localisation_files(self, archive: ZipFile, root_path: Optional[str] = None) -> None:
        """
        Method adding the localisation files found in the cache.

        Returns
        -------
        None
        """
        for language in self.modpack_manager.assets.translations.versions:
            locale_zip_path: Path = get_asset_version_cache_location(self.modpack_manager.assets.translations, language)
            list_of_files = archive.namelist()
            with ZipFile(locale_zip_path, "r", compression=ZIP_DEFLATED) as locale_zip:
                for item in locale_zip.namelist():
                    if item.endswith("/"):
                        continue # skipping folders creation

                    with locale_zip.open(item) as config_item:
                        item_path = item if root_path is None else f"{root_path}/{item}"
                        if item_path in list_of_files:
                            log.error(
                                f"{item_path} from locale {language.filename.split('-')[1]}"  # type: ignore
                                " would overwrite the same file in the archive, skipping it."
                            )
                            continue
                        with archive.open(item_path, "w") as target:
                            shutil.copyfileobj(config_item, target)
                            if self.task_progress_callback is not None:
                                self.task_progress_callback(
                                    self.get_progress(),
                                    f"locale {locale_zip_path.name.split('-')[1]}: adding {item} to the archive",
                                )
