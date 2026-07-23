from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Dict, List, Optional, Set, Tuple, Union

import httpx
from colorama import Fore

from daxxl.assembler.assembler import ReleaseAssembler
from daxxl.defs import Archive, ModSource, Side
from daxxl.exceptions import ReleaseNotFoundException, SideAlreadySetException
from daxxl.gtnh_logger import get_logger
from daxxl.models.gtnh_config import GTNHConfig
from daxxl.models.gtnh_release import GTNHRelease
from daxxl.models.gtnh_version import GTNHVersion
from daxxl.models.mod_info import GTNHModInfo
from daxxl.models.mod_version_info import ModVersionInfo
from daxxl.modpack_manager import GTNHModpackManager

logger = get_logger(__name__)


def _noop(*_: Any) -> None:
    pass


class ReleaseController:
    """
    UI-agnostic controller holding the release state and business operations of the GUI.

    It never touches Tkinter: progress reporting goes through the callbacks passed to the
    constructor, and user-facing outcomes are reported by raising typed exceptions
    (see daxxl.exceptions) or returning results the UI layer can render.
    """

    def __init__(
        self,
        progress_callback: Callable[[float, str], None] = _noop,
        global_callback: Callable[[float, str], None] = _noop,
        global_reset_callback: Callable[[], None] = _noop,
        current_task_reset_callback: Callable[[], None] = _noop,
    ) -> None:
        """
        Constructor of the ReleaseController class.

        :param progress_callback: callback updating the current task progress bar
        :param global_callback: callback updating the global progress bar
        :param global_reset_callback: callback resetting the global progress bar
        :param current_task_reset_callback: callback resetting the current task progress bar
        """
        self.progress_callback = progress_callback
        self.global_callback = global_callback
        self.global_reset_callback = global_reset_callback
        self.current_task_reset_callback = current_task_reset_callback

        self._client: Optional[httpx.AsyncClient] = None
        self._modpack_manager: Optional[GTNHModpackManager] = None

        self.github_mods: Dict[
            str, ModVersionInfo
        ] = {}  # name <-> version of github mods mappings for the current release
        self.gtnh_config: str = ""  # modpack asset version
        self.external_mods: Dict[
            str, ModVersionInfo
        ] = {}  # name <-> version of external mods mappings for the current release
        self.version: str = ""  # modpack release name
        self.last_version: Optional[str] = None  # last version of the release

        self.delta_progress: float = 0  # progression between 2 tasks (in %) for the global progress bar

    async def _get_client(self) -> httpx.AsyncClient:
        """
        Internal getter for the httpx client instance, creating it if it doesn't exist.

        :return: the httpx client instance
        """
        if self._client is None:
            self._client = httpx.AsyncClient(http2=True)
        return self._client

    async def get_modpack_manager(self) -> GTNHModpackManager:
        """
        Getter for the modpack manager instance, creating it if it doesn't exist.

        :return: the modpack manager instance
        """
        if self._modpack_manager is None:
            self._modpack_manager = GTNHModpackManager(await self._get_client())
        return self._modpack_manager

    async def close(self) -> None:
        """
        Release the http client resources.

        :return: None
        """
        if self._client is not None:
            await self._client.aclose()

    def add_github_mod(self, name: str, version: str) -> None:
        """
        add a mod to inmemory github modlist.

        :param name: mod name
        :param version: mod version
        :return: None
        """
        self.github_mods[name] = ModVersionInfo(version=version)

    def del_github_mod(self, name: str) -> None:
        """
        remove a mod from inmemory github modlist.

        :param name: mod name
        :return: None
        """
        del self.github_mods[name]

    def add_external_mod(self, name: str, version: str) -> None:
        """
        add a mod to inmemory external modlist.

        :param name: mod name
        :param version: mod version
        :return: None
        """
        self.external_mods[name] = ModVersionInfo(version=version)

    def del_external_mod(self, name: str) -> None:
        """
        remove a mod from inmemory external modlist.

        :param name: mod name
        :return: None
        """
        del self.external_mods[name]

    def get_github_mods(self) -> Dict[str, ModVersionInfo]:
        """
        Getter for self.github_mods.

        :return: self.github_mods
        """
        return self.github_mods

    def get_external_mods(self) -> Dict[str, ModVersionInfo]:
        """
        Getter for self.external_mods.

        :return: self.external_mods
        """
        return self.external_mods

    def set_github_mod_version(self, github_mod_name: str, mod_version: str) -> None:
        """
        Callback used when a github mod version is selected.

        :param github_mod_name: mod name
        :param mod_version: mod version
        :return: None
        """
        if github_mod_name in self.github_mods:
            self.github_mods[github_mod_name].version = mod_version

    def set_external_mod_version(self, external_mod_name: str, mod_version: str) -> None:
        """
        Callback used when an external mod version is selected.

        :param external_mod_name: mod name
        :param mod_version: mod version
        :return: None
        """
        if external_mod_name in self.external_mods:
            self.external_mods[external_mod_name].version = mod_version

    def set_modpack_version(self, modpack_version: str) -> None:
        """
        Callback used when a modpack version is selected.

        :param modpack_version: modpack version
        :return: None
        """
        self.gtnh_config = modpack_version

    def _set_mod_side(
        self,
        mods: Dict[str, ModVersionInfo],
        mod_name: str,
        side: Side,
        get_default_version: Callable[[], str],
    ) -> None:
        """
        Change the side of a mod in the given dict (github_mods or external_mods),
        creating the entry if it does not exist or deleting the entry if side is Side.NONE.

        :param mods: the given dict (github_mods or external_mods)
        :param mod_name: mod name
        :param side: new Side
        :param get_default_version: callback giving the default value if the entry does not exist in the dict
        :raises SideAlreadySetException: if the mod is already on the given side
        :return: None
        """
        previous_side = mods[mod_name].side if mod_name in mods else Side.NONE
        if previous_side == side:
            raise SideAlreadySetException(f"{mod_name}'s side is already set to {side}")

        if side == Side.NONE:
            del mods[mod_name]
        elif previous_side == Side.NONE:
            mods[mod_name] = ModVersionInfo(version=get_default_version(), side=side)
        else:
            mods[mod_name].side = side

    def set_github_mod_side(self, mod_name: str, side: Side, get_default_version: Callable[[], str]) -> None:
        """
        Method used to set the side of a github mod.

        :param mod_name: the mod name
        :param side: side of the pack, None if use default
        :param get_default_version: callback giving the version to use when the mod is not in the release yet
        :raises SideAlreadySetException: if the mod is already on the given side
        :return: None
        """
        self._set_mod_side(self.github_mods, mod_name, side, get_default_version)

    def set_external_mod_side(self, mod_name: str, side: Side, get_default_version: Callable[[], str]) -> None:
        """
        Method used to set the side of an external mod.

        :param mod_name: the mod name
        :param side: side of the pack
        :param get_default_version: callback giving the version to use when the mod is not in the release yet
        :raises SideAlreadySetException: if the mod is already on the given side
        :return: None
        """
        self._set_mod_side(self.external_mods, mod_name, side, get_default_version)

    async def set_mod_side_default(self, mod_name: str, side: str) -> bool:
        """
        Set the mod side to the given side no matter what is its source (github or external).

        :param mod_name: mod name
        :param side: the default side to apply
        :raises SideAlreadySetException: if the mod is already on the given side
        :return: False if the side couldn't be set
        """
        gtnh: GTNHModpackManager = await self.get_modpack_manager()
        previous_side: Side = gtnh.assets.get_mod(mod_name).side
        if previous_side == side:
            raise SideAlreadySetException(f"{mod_name}'s side is already set on {side}")

        return gtnh.set_mod_side(mod_name, side)

    def set_progress(self, delta_progress: float) -> None:
        """
        Setter for self.delta_progress.

        :param delta_progress: new progress
        :return: None
        """
        self.delta_progress = delta_progress

    def get_progress(self) -> float:
        """
        Getter for self.delta_progress.

        :return: the current delta progress
        """
        return self.delta_progress

    async def add_exclusion(self, side: Side, exclusion: str) -> bool:
        """
        Method used to add an file exclusion to the corresponding side's exclusion list.

        :param side: side of the modpack
        :param exclusion: the string corresponding to the file exclusion
        :return: True if the exclusion was added, False if it was already present
        """
        gtnh: GTNHModpackManager = await self.get_modpack_manager()
        added = gtnh.add_exclusion(side, exclusion)
        if added:
            gtnh.save_modpack()
        return added

    async def del_exclusion(self, side: Side, exclusion: str) -> bool:
        """
        Method used to remove a file exclusion from the corresponding side's exclusion list.

        :param side: side of the modpack
        :param exclusion: the string corresponding to the file exclusion
        :return: True if the exclusion was removed, False if it wasn't present
        """
        gtnh: GTNHModpackManager = await self.get_modpack_manager()
        removed = gtnh.delete_exclusion(side, exclusion)
        if removed:
            gtnh.save_modpack()
        return removed

    async def get_modpack_exclusions(self, side: Side) -> List[str]:
        """
        Method used to gather the file exclusion list of the modpack corresponding to the provided side.

        :param side: side of the pack
        :return: list of strings corresponding to the file exclusions
        """
        gtnh: GTNHModpackManager = await self.get_modpack_manager()
        if side == Side.CLIENT:
            return sorted([exclusion for exclusion in gtnh.mod_pack.client_exclusions])
        elif side == Side.SERVER:
            return sorted([exclusion for exclusion in gtnh.mod_pack.server_exclusions])
        else:
            raise ValueError(f"side {side} is an invalid side")

    async def get_repos(self) -> List[str]:
        """
        Method to grab all the repo names known.

        :return: a list of github mod names
        """
        gtnh: GTNHModpackManager = await self.get_modpack_manager()
        return [x.name for x in gtnh.assets.mods if x.source == ModSource.github]

    async def get_external_modlist(self) -> List[str]:
        """
        Method to get all the external mods from the assets.

        :return: a list of string with all the external mods availiable
        """
        gtnh: GTNHModpackManager = await self.get_modpack_manager()
        return [mod.name for mod in gtnh.assets.mods if mod.source != ModSource.github]

    async def get_modpack_versions(self) -> List[str]:
        """
        Method used to gather all the version of the GT-New-Horizons-Modpack repo.

        :return: a list of all the versions availiable.
        """
        gtnh: GTNHModpackManager = await self.get_modpack_manager()
        modpack_config: GTNHConfig = gtnh.assets.config
        return [version.version_tag for version in modpack_config.versions]

    async def get_releases(self) -> List[GTNHRelease]:
        """
        Method used to return a list of known releases with valid metadata.
        The list is sorted in ascending order (from oldest to the latest).

        :return: a sorted list of all the gtnh releases availiable
        """
        gtnh: GTNHModpackManager = await self.get_modpack_manager()

        releases: List[GTNHRelease] = []

        # if there is any release, chose last
        if len(gtnh.mod_pack.releases) > 0:
            # gtnh.mod_pack.releases is actually a set of the release names
            for release_name in gtnh.mod_pack.releases:
                release: Optional[GTNHRelease] = gtnh.get_release(release_name)

                # discarding all the None releases, as it means the json data couldn't be loaded
                if release is not None:
                    releases.append(release)

            # sorting releases by date. Some manifests store last_updated as offset-naive and others as
            # offset-aware; normalize naive timestamps to UTC so they can be compared with each other.
            def _sort_key(release_object: GTNHRelease) -> datetime:
                last_updated = release_object.last_updated
                if last_updated.tzinfo is None:
                    return last_updated.replace(tzinfo=timezone.utc)
                return last_updated

            releases = sorted(releases, key=_sort_key)

        return releases

    async def load_gtnh_version(self, release: Union[GTNHRelease, str]) -> GTNHRelease:
        """
        Load in memory a pack release.

        :param release: either a release object or a release name
        :raises ReleaseNotFoundException: if the release name is unknown
        :return: the release object loaded in memory
        """
        release_object: Optional[GTNHRelease]

        if isinstance(release, str):
            gtnh: GTNHModpackManager = await self.get_modpack_manager()
            release_object = gtnh.get_release(release)
        else:
            release_object = release

        if release_object is None:
            raise ReleaseNotFoundException(f"modpack version {release} doesn't exist")

        release_object = await self.strip_disabled_mods(release_object)
        self.github_mods = release_object.github_mods
        self.gtnh_config = release_object.config
        self.external_mods = release_object.external_mods
        self.version = release_object.version
        self.last_version = release_object.last_version
        logger.info(f"Loaded pack version {Fore.CYAN}{release_object.version}{Fore.RESET} in memory.")
        return release_object

    async def strip_disabled_mods(self, release: GTNHRelease) -> GTNHRelease:
        """
        Method used to strip the disabled mods from any release improperly generated during its loading.

        :param release: the target release
        :return: the release with the stripped disabled mods
        """
        # todo: create a new instance for release object and edit it instead, because mutating args is bad mkay?
        mod_name: str
        version: ModVersionInfo
        gtnh_modpack: GTNHModpackManager = await self.get_modpack_manager()
        github_mods: Dict[str, ModVersionInfo] = release.github_mods
        external_mods: Dict[str, ModVersionInfo] = release.external_mods
        valid_side: Set[Side] = {Side.NONE}
        github_mods_to_delete: List[str] = []
        external_mods_to_delete: List[str] = []
        mod_data: Optional[Tuple[GTNHModInfo, GTNHVersion]]

        for mod_name, version in github_mods.items():
            mod_data = gtnh_modpack.assets.get_mod_and_version(mod_name, version, valid_sides=valid_side)
            if mod_data is not None:
                logger.warn(
                    f"{Fore.YELLOW}Release {release.version} had github mod {mod_name}"
                    f" in its manifest but it is disabled. Stripping it from memory.{Fore.RESET}"
                )
                github_mods_to_delete.append(mod_name)

        for mod_name in github_mods_to_delete:
            del github_mods[mod_name]

        for mod_name, version in external_mods.items():
            mod_data = gtnh_modpack.assets.get_mod_and_version(mod_name, version, valid_sides=valid_side)
            if mod_data is not None:
                logger.warn(
                    f"{Fore.YELLOW}Release {self.version} had external mod {mod_name}"
                    f"in its manifest but it is disabled. Stripping it from memory.{Fore.RESET}"
                )
                external_mods_to_delete.append(mod_name)

        for mod_name in external_mods_to_delete:
            del external_mods[mod_name]

        release.github_mods = github_mods
        release.external_mods = external_mods
        return release

    async def add_gtnh_version(self, release_name: str, previous_version: str) -> bool:
        """
        Add a new modpack version and load it in memory.

        :param release_name: the name of the release
        :param previous_version: the previous modpack version
        :return: True if the release was added
        """
        gtnh: GTNHModpackManager = await self.get_modpack_manager()
        release: GTNHRelease = GTNHRelease(
            version=release_name,
            config=self.gtnh_config,
            github_mods={
                mod_name: ModVersionInfo(
                    version=info.version, side=info.side if info.side else gtnh.assets.get_mod(mod_name).side
                )
                for mod_name, info in self.github_mods.items()
            },
            external_mods={
                mod_name: ModVersionInfo(
                    version=info.version, side=info.side if info.side else gtnh.assets.get_mod(mod_name).side
                )
                for mod_name, info in self.external_mods.items()
            },
            last_version=previous_version,
        )

        self.last_version = previous_version

        is_release_added: bool = gtnh.add_release(release, update=True)

        if is_release_added:
            await self.load_gtnh_version(release)
            gtnh.save_modpack()

        return is_release_added

    async def delete_gtnh_version(self, release_name: str) -> None:
        """
        Delete a modpack version, loading the latest remaining release if the deleted one was loaded.

        :param release_name: name of the release
        :return: None
        """
        gtnh: GTNHModpackManager = await self.get_modpack_manager()
        was_loaded = self.version == release_name
        gtnh.delete_release(release_name)

        if was_loaded:
            releases: List[GTNHRelease] = await self.get_releases()
            if releases:
                await self.load_gtnh_version(releases[-1])
            else:
                self.github_mods.clear()
                self.external_mods.clear()
                self.gtnh_config = ""
                self.version = ""
                self.last_version = None

    async def update_assets(self) -> Tuple[List[GTNHModInfo], List[str]]:
        """
        Update all the availiable assets.

        :return: a tuple consisting of the List of mods needing attention after the update and the list of error
         messages for individual assets that failed to update.
        """
        self.global_reset_callback()
        self.current_task_reset_callback()

        gtnh: GTNHModpackManager = await self.get_modpack_manager()
        global_delta_progress: float = 100 / (1 + 1)  # 1 for the syncing of the mods, 1 for update checks
        update_errors: List[str] = await gtnh.update_all(
            progress_callback=self.progress_callback,
            global_progress_callback=lambda msg: self.global_callback(global_delta_progress, msg),
        )

        return [mod for mod in gtnh.assets.mods if mod.needs_attention], update_errors

    async def update_rolling_release(self, release_type: str) -> Tuple[List[GTNHModInfo], List[str]]:
        """
        update dev release (experimental/daily)

        :param release_type: "experimental" or "daily"
        :raises ReleaseNotFoundException: if the dev release doesn't exist yet
        :return: a tuple of (mods needing attention after the update, error messages for
            individual assets that failed to update - the rest of the batch still completes)
        """
        self.current_task_reset_callback()
        self.global_reset_callback()

        gtnh: GTNHModpackManager = await self.get_modpack_manager()

        # 1 for the data download on github, 1 for the asset updates and 1 for the release update
        global_delta_progress: float = 100 / (1 + 1 + 1)
        _, update_errors = await gtnh.update_rolling_release(
            release_type,
            update_available=True,
            progress_callback=self.progress_callback,
            reset_progress_callback=self.current_task_reset_callback,
            global_progress_callback=lambda msg: self.global_callback(global_delta_progress, msg),
        )

        return [mod for mod in gtnh.assets.mods if mod.needs_attention], update_errors

    async def pre_assembling(self) -> ReleaseAssembler:
        """
        Method to downloads the mods before constructing the ReleaseAssembler object.

        :return: the ReleaseAssembler object constructed
        """
        gtnh: GTNHModpackManager = await self.get_modpack_manager()
        release: GTNHRelease = GTNHRelease(
            version=self.version,
            config=self.gtnh_config,
            github_mods=self.github_mods,
            external_mods=self.external_mods,
            last_version=self.last_version,
        )
        logger.info(f"version: {self.version}")

        # clean the previous state of the progress bars
        self.global_reset_callback()
        self.current_task_reset_callback()

        self.global_callback(self.get_progress(), "Downloading assets")
        await gtnh.download_release(release, download_callback=self.progress_callback)
        self.current_task_reset_callback()

        return ReleaseAssembler(
            gtnh,
            release,
            task_callback=self.progress_callback,
            global_callback=self.global_callback,
            current_task_reset_callback=self.current_task_reset_callback,
        )

    async def generate_changelog(self) -> None:
        """
        Generate the changelog between the loaded release and its previous version.

        :return: None
        """
        self.set_progress(100 / 2)
        release_assembler: ReleaseAssembler = await self.pre_assembling()
        release_assembler.generate_changelog()
        self.global_callback(self.get_progress(), f"Generate changelog from {self.last_version} to {self.version}")

    async def generate_intermediate_cf_files(self, task_progressbar: Any) -> None:
        """
        Generate curseforge intermediate files.

        :param task_progressbar: progress bar object forwarded to the curse assembler
        :return: None
        """
        self.set_progress(100 / 3)
        release_assembler: ReleaseAssembler = await self.pre_assembling()
        self.global_callback(self.get_progress(), "Generating the dependencies.json")
        await release_assembler.curse_assembler.generate_json_dep(task_progressbar)
        self.global_callback(self.get_progress(), "Generating the archive containing the mods to upload")
        release_assembler.curse_assembler.generate_mods_to_upload(task_progressbar)

    async def assemble_release(self, side: Side, archive_type: Archive) -> None:
        """
        Assemble the archive corresponding to the provided side and archive type.

        :return: None
        """
        self.set_progress(100 / 2)
        release_assembler: ReleaseAssembler = await self.pre_assembling()
        assembler_dict: Dict[Archive, Callable[[Side, bool], Awaitable[None]]] = {
            Archive.ZIP: release_assembler.assemble_zip,
            Archive.MMC: release_assembler.assemble_mmc,
            Archive.MODRINTH: release_assembler.assemble_modrinth,
            Archive.CURSEFORGE: release_assembler.assemble_curse,
            Archive.TECHNIC: release_assembler.assemble_technic,
        }
        self.global_callback(self.get_progress(), f"Assembling {side.value} {archive_type.value} archive")
        await assembler_dict[archive_type](side=side, verbose=True)  # type: ignore

    async def assemble_all(self) -> None:
        """
        Assemble all the archives for a full update.

        :return: None
        """
        self.set_progress(100 / (1 + 5 + 1))  # download + archives for client + archive for server
        release_assembler: ReleaseAssembler = await self.pre_assembling()

        release_assembler.set_progress(self.get_progress())

        await release_assembler.assemble(Side.CLIENT, verbose=True)

        await self.assemble_release(Side.CLIENT_JAVA9, Archive.MMC)
        await self.assemble_release(Side.SERVER_JAVA9, Archive.ZIP)

        # todo: redo the bar resets less hacky: they are spread all over the place and it's inconsistent
        if release_assembler.current_task_reset_callback is not None:
            release_assembler.current_task_reset_callback()

        self.global_callback(self.get_progress(), f"Assembling {Side.SERVER} {Archive.ZIP} archive")
        await release_assembler.assemble_zip(Side.SERVER, verbose=True)

    async def assemble_beta(self) -> None:
        """
        Assemble all the archives for a beta/RC update.

        :return: None
        """
        self.set_progress(100 / (1 + 3 + 2))  # download + archives for client + archive for server
        release_assembler: ReleaseAssembler = await self.pre_assembling()

        release_assembler.set_progress(self.get_progress())

        # zip archives
        await self.assemble_release(Side.CLIENT, Archive.ZIP)
        await self.assemble_release(Side.SERVER, Archive.ZIP)
        await self.assemble_release(Side.SERVER_JAVA9, Archive.ZIP)

        # MMC archives
        await self.assemble_release(Side.CLIENT, Archive.MMC)
        await self.assemble_release(Side.CLIENT_JAVA9, Archive.MMC)
