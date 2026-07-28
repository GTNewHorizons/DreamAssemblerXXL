import asyncio
import os
import shutil
from collections.abc import Callable
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from colorama import Fore

from daxxl.app_context import AppContext
from daxxl.assembler.downloader import get_asset_version_cache_location
from daxxl.assembler.exclusions import Exclusions
from daxxl.defs import README_TEMPLATE, RELEASE_README_DIR, Side
from daxxl.exceptions import InvalidConfigException
from daxxl.gtnh_logger import get_logger
from daxxl.models.gtnh_config import GTNHConfig
from daxxl.models.gtnh_release import GTNHRelease
from daxxl.models.gtnh_version import GTNHVersion
from daxxl.models.mod_info import GTNHModInfo
from daxxl.utils import normalize_archive_permissions

log = get_logger(__name__)


class GenericAssembler:
    """
    Generic assembler class.
    """

    # config entries dropped regardless of the side's exclusions
    excluded_config_files: frozenset[str] = frozenset()

    # config entries whose content is modified before being added to the archive
    modified_config_files: frozenset[str] = frozenset({"config/txloader/load/mainmenu/version.txt"})

    def __init__(
        self,
        context: AppContext,
        release: GTNHRelease,
        task_progress_callback: Callable[[float, str], None] | None = None,
        global_progress_callback: Callable[[float, str], None] | None = None,
        changelog_path: Path | None = None,
        current_task_reset_callback: Callable[[], None] | None = None,
    ):
        """
        Constructor of the GenericAssembler class.

        :param context: the context instance
        :param release: the target release object
        :param task_progress_callback: the callback to report the progress of the task
        :param global_progress_callback: the callback to report the global progress
        :param current_task_reset_callback: the callback to reset the progress bar for the current task
        """
        self.context: AppContext = context
        self.release: GTNHRelease = release
        self.global_progress_callback: Callable[[float, str], None] | None = global_progress_callback
        self.task_progress_callback: Callable[[float, str], None] | None = task_progress_callback
        self.changelog_path: Path | None = changelog_path
        self.current_task_reset_callback: Callable[[], None] | None = current_task_reset_callback

        mod_pack = self.context.mod_pack
        self.exclusions: dict[str, Exclusions] = {
            Side.CLIENT: Exclusions(mod_pack.client_exclusions + mod_pack.client_java8_exclusions),
            Side.SERVER: Exclusions(mod_pack.server_exclusions + mod_pack.server_java8_exclusions),
            Side.CLIENT_JAVA9: Exclusions(mod_pack.client_exclusions + mod_pack.client_java9_exclusions),
            Side.SERVER_JAVA9: Exclusions(mod_pack.server_exclusions + mod_pack.server_java9_exclusions),
        }
        self.delta_progress: float = 0.0

    @property
    def config_root(self) -> Path | None:
        """
        Folder inside the archive the config is written under, or None to write it at the archive root.
        """
        return None

    @staticmethod
    async def yield_to_event_loop() -> None:
        await asyncio.sleep(0)

    def get_amount_of_files_in_config(self, side: Side) -> int:
        """
        Method to get the amount of files inside the config zip.

        :param side: targeted side for the release
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
        total: int = 0
        for language in self.context.assets.translations.versions:
            locale_zip_path: Path = get_asset_version_cache_location(self.context.assets.translations, language)
            with ZipFile(locale_zip_path, "r", compression=ZIP_DEFLATED) as locale_zip:
                total += len([item for item in locale_zip.namelist() if not item.endswith("/")])
        return total

    def get_mods(self, side: Side) -> list[tuple[GTNHModInfo, GTNHVersion]]:
        """
        Method to grab the mod info objects as well as their targeted version.

        :param side: the targeted side
        :return: a list of couples where the first object is the mod info object, the second is the targeted version.
        """

        valid_sides: set[Side] = side.valid_mod_sides()

        github_mods: list[tuple[GTNHModInfo, GTNHVersion]] = self.github_mods(valid_sides)

        external_mods: list[tuple[GTNHModInfo, GTNHVersion]] = self.external_mods(valid_sides)

        mods: list[tuple[GTNHModInfo, GTNHVersion]] = github_mods + external_mods
        return mods

    def external_mods(self, valid_sides: set[Side], release: GTNHRelease | None = None) -> list[tuple[GTNHModInfo, GTNHVersion]]:
        """
        Method to grab the external mod info objects as well as their targeted version.

        :param valid_sides: a set of valid sides to retrieve the mods from.
        :param release: if specified, the release version to get data from instead of the one used for the assembling.
        """
        release = self.release if release is None else release

        external_mods: list[tuple[GTNHModInfo, GTNHVersion]] = list(
            filter(
                None,
                [self.context.assets.get_mod_and_version(name, version, valid_sides) for name, version in release.external_mods.items()],
            )
        )

        return external_mods

    def github_mods(self, valid_sides: set[Side], release: GTNHRelease | None = None) -> list[tuple[GTNHModInfo, GTNHVersion]]:
        """
        Method to grab the github mod info objects as well as their targeted version.

        :param valid_sides: a set of valid sides to retrieve the mods from.
        :param release: if specified, the release version to get data from instead of the one used for the assembling.
        """
        release = self.release if release is None else release

        github_mods: list[tuple[GTNHModInfo, GTNHVersion]] = list(
            filter(
                None,
                [self.context.assets.get_mod_and_version(name, version, valid_sides) for name, version in release.github_mods.items()],
            )
        )

        return github_mods

    def get_config(self) -> tuple[GTNHConfig, GTNHVersion]:
        """
        Method to get the config file from the release.

        :return: a tuple with the GTNHConfig and GTNHVersion of the release's config
        """

        config: GTNHConfig = self.context.assets.config
        version: GTNHVersion | None = config.get_version(self.release.config)
        if version is None:
            raise InvalidConfigException
        return config, version

    async def add_mods(
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

    async def _add_config_files(self, side: Side, config_file: Path, destination: ZipFile, root: Path | None = None) -> None:
        """
        Copy the contents of the config archive into `destination`, skipping the side's exclusions.

        :param side: target side, selects which exclusion list applies
        :param config_file: the cached config archive to read from
        :param destination: the archive being written into
        :param root: folder inside `destination` to write under, or None to write at its root
        :return: None
        """
        with ZipFile(config_file, "r", compression=ZIP_DEFLATED) as config_zip:
            for item in config_zip.namelist():
                if item in self.excluded_config_files or item in self.exclusions[side]:
                    continue
                # can't use Path for the whole path here as it strips leading / but those are used by
                # zipfile to know if it's a file or a folder. If used here, Path objects will lead to
                # the creation of empty files for every folder.
                arcname = f"{root.as_posix()}/{item}" if root is not None else item
                if item in self.modified_config_files:
                    data = config_zip.read(item)
                    data = self._modify_config_file(item, data)
                    destination.writestr(arcname, data)
                else:
                    with config_zip.open(item) as config_item:
                        with destination.open(arcname, "w") as target:
                            shutil.copyfileobj(config_item, target)
                if self.task_progress_callback is not None:
                    self.task_progress_callback(self.delta_progress, f"adding {item} to the archive")
                await self.yield_to_event_loop()

    def _modify_config_file(self, filename: str, data: bytes) -> bytes:
        if filename == "config/txloader/load/mainmenu/version.txt":
            display_version = self.release.get_display_version(self.context.counter)
            date_str = self.release.last_updated.strftime("%Y-%m-%d")
            return f"GTNH {display_version} ({date_str})".encode("utf-8")
        return data

    async def add_config(self, side: Side, config: tuple[GTNHConfig, GTNHVersion], archive: ZipFile, verbose: bool = False) -> None:
        """
        Method to add config in the zip archive.

        :param side: target side
        :param config: a tuple giving the config object and the version object of the config
        :param archive: archive being built
        :param verbose: flag to turn on verbose mode
        :return: None
        """
        modpack_config: GTNHConfig
        config_version: GTNHVersion | None
        modpack_config, config_version = config

        config_file: Path = get_asset_version_cache_location(modpack_config, config_version)

        await self._add_config_files(side, config_file, archive, self.config_root)

        changelog_arcname = self.config_root / self.changelog_path.name if self.config_root is not None and self.changelog_path is not None else None
        self.add_changelog(archive, arcname=changelog_arcname)

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
            await self.add_mods(side, self.get_mods(side), archive, verbose=verbose)
            await self.yield_to_event_loop()
            log.info("Adding config to the archive")
            await self.add_config(side, self.get_config(), archive, verbose=verbose)
            await self.yield_to_event_loop()
            log.info("Generating the readme for the modpack repo")
            self.generate_readme()
            await self.yield_to_event_loop()
            await normalize_archive_permissions(archive)
            log.info("Archive created successfully!")

    def get_archive_path(self, side: Side) -> Path:
        """
        Method to get the path to the assembled pack release.

        :return: the path to the release
        """
        raise NotImplementedError

    def add_changelog(self, archive: ZipFile, arcname: Path | None = None) -> None:
        """
        Method to add the changelog to the archive.

        :param archive: the archive object
        :return: None
        """

        if self.changelog_path is not None:
            if self.task_progress_callback is not None:
                self.task_progress_callback(self.delta_progress, "adding changelog to the archive")
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

        with open(README_TEMPLATE) as f:
            data = "".join(f.readlines())

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
        valid_sides: set[Side] = {
            Side.CLIENT,
            Side.SERVER,
            Side.BOTH,
            Side.CLIENT_JAVA9,
            Side.SERVER_JAVA9,
            Side.BOTH_JAVA9,
        }
        lines: list[str] = []

        # it seems i'm obligated to get mods separatedly because self.get_mods is somehow
        # casting external mods into github mods

        github_mods: list[tuple[GTNHModInfo, GTNHVersion]] = self.github_mods(valid_sides)

        for mod, version in github_mods:
            assert isinstance(mod, GTNHModInfo)
            lines.append(f"| [{mod.name}]({mod.repo_url}) | {version.version_tag} |")

        external_mods: list[tuple[GTNHModInfo, GTNHVersion]] = self.external_mods(valid_sides)

        for mod, version in external_mods:
            assert not mod.is_github()
            lines.append(f"| [{mod.name}]({mod.external_url}) | {version.version_tag} |")

        return "\n".join(sorted(lines, key=lambda x: x.lower()))

    async def add_localisation_files(self, archive: ZipFile, root_path: str | None = None) -> None:
        """
        Method adding the localisation files found in the cache.

        Returns
        -------
        None
        """
        for language in self.context.assets.translations.versions:
            locale_zip_path: Path = get_asset_version_cache_location(self.context.assets.translations, language)
            list_of_files = archive.namelist()
            with ZipFile(locale_zip_path, "r", compression=ZIP_DEFLATED) as locale_zip:
                for item in locale_zip.namelist():
                    if item.endswith("/"):
                        continue  # skipping folders creation

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
                                    self.delta_progress,
                                    f"locale {locale_zip_path.name.split('-')[1]}: adding {item} to the archive",
                                )
                    await self.yield_to_event_loop()
