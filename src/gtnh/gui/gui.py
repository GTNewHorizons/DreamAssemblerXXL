import asyncio
import sys
from pathlib import Path
from tkinter import DISABLED, NORMAL, PhotoImage, Widget
from tkinter.messagebox import showerror, showinfo, showwarning
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

import httpx
from colorama import Fore
from structlog import get_logger
from ttkthemes import ThemedTk

from gtnh.assembler.assembler import ReleaseAssembler
from gtnh.defs import Archive, ModSource, Position, Side
from gtnh.exceptions import NoModAssetFound, ReleaseNotFoundException
from gtnh.gui.exclusion.exclusion_panel import ExclusionPanel
from gtnh.gui.external.external_panel import ExternalPanel
from gtnh.gui.github.github_panel import GithubPanel
from gtnh.gui.modpack.modpack_panel import ModpackPanel
from gtnh.models.gtnh_config import GTNHConfig
from gtnh.models.gtnh_release import GTNHRelease
from gtnh.models.gtnh_version import GTNHVersion
from gtnh.models.mod_info import ExternalModInfo, GTNHModInfo
from gtnh.modpack_manager import GTNHModpackManager

logger = get_logger(__name__)

ASYNC_SLEEP: float = 0.05
ICON: Path = Path(__file__).parent.parent.parent.parent / "icon.png"


def check(widget: Widget) -> bool:
    """
    Check if the given widget is matching one of the types that can be disabled.

    :param widget: the given widget
    :return: if yes or no it can be disabled
    """
    widget_list: List[str] = ["CustomButton", "TextWidget", "CustomListbox", "CustomCombobox"]
    for widget_type in widget_list:
        if widget_type.lower() in str(widget):
            return True
    return False


class App:
    """
    Wrapper class to start the GUI.
    """

    def __init__(self) -> None:
        self.instance: Window = Window()

    async def exec(self) -> None:
        """
        Coroutine used to run all the stuff.
        """
        await self.instance.run()


class Window(ThemedTk):
    """
    Main class for the GUI.
    """

    def __init__(self) -> None:
        """
        Constructor of the Window class.
        """
        theme = "winnative" if sys.platform == "win32" else "plastik"
        ThemedTk.__init__(self, theme=theme)
        self._client: Optional[httpx.AsyncClient] = None
        self._modpack_manager: Optional[GTNHModpackManager] = None
        self._run: bool = True
        self.title("DreamAssemblerXXL")
        self.iconphoto(False, PhotoImage(file=ICON))

        self.xpadding: int = 0
        self.ypadding: int = 0

        self.github_mods: Dict[str, str] = {}  # name <-> version of github mods mappings for the current release
        self.gtnh_config: str = ""  # modpack asset version
        self.external_mods: Dict[str, str] = {}  # name <-> version of external mods mappings for the current release
        self.version: str = ""  # modpack release name
        self.last_version: Optional[str] = None  # last version of the release

        self.download_error_list: List[str] = []  # list of errors happened during the download of a release's assets

        self.init: bool = False
        self.protocol("WM_DELETE_WINDOW", lambda: asyncio.ensure_future(self.close_app()))

        self.delta_progress: float = 0  # progression between 2 tasks (in %) for the global progress bar

        # frame for the modpack handling
        modpack_list_callbacks: Dict[str, Any] = {
            "load": lambda release_name: asyncio.ensure_future(self.load_gtnh_version(release_name)),
            "add": lambda release_name, previous_version: asyncio.ensure_future(
                self.add_gtnh_version(release_name, previous_version)
            ),
            "delete": lambda release_name: asyncio.ensure_future(self.delete_gtnh_version(release_name)),
            "update_assets": lambda: asyncio.ensure_future(self.update_assets()),
            "generate_nightly": lambda: asyncio.ensure_future(self.update_nightly()),
            "client_mmc": lambda: asyncio.ensure_future(self.assemble_release(Side.CLIENT, Archive.MMC)),
            "client_zip": lambda: asyncio.ensure_future(self.assemble_release(Side.CLIENT, Archive.ZIP)),
            "server_zip": lambda: asyncio.ensure_future(self.assemble_release(Side.SERVER, Archive.ZIP)),
            "client_curse": lambda: asyncio.ensure_future(self.assemble_release(Side.CLIENT, Archive.CURSEFORGE)),
            "client_modrinth": lambda: asyncio.ensure_future(self.assemble_release(Side.CLIENT, Archive.MODRINTH)),
            "client_technic": lambda: asyncio.ensure_future(self.assemble_release(Side.CLIENT, Archive.TECHNIC)),
            "all": lambda: asyncio.ensure_future(self.assemble_all()),
        }

        self.modpack_list_frame: ModpackPanel = ModpackPanel(
            self, frame_name="Modpack release actions", callbacks=modpack_list_callbacks
        )

        self.progress_callback: Callable[
            [float, str], None
        ] = self.modpack_list_frame.action_frame.update_current_task_progress_bar
        self.global_callback: Callable[
            [float, str], None
        ] = self.modpack_list_frame.action_frame.update_global_progress_bar
        self.global_reset_callback: Callable[[], None] = self.modpack_list_frame.action_frame.reset_global_progress_bar
        self.current_task_reset_callback: Callable[
            [], None
        ] = self.modpack_list_frame.action_frame.reset_current_task_progress_bar

        # frame for the github mods
        github_frame_callbacks: Dict[str, Any] = {
            "get_gtnh": self._get_modpack_manager,
            "get_github_mods": self.get_github_mods,
            "set_github_mod_version": self.set_github_mod_version,
            "set_github_mod_side": lambda name, side: asyncio.ensure_future(self.set_github_mod_side(name, side)),
            "set_modpack_version": self.set_modpack_version,
            "update_current_task_progress_bar": self.progress_callback,
            "update_global_progress_bar": self.global_callback,
            "reset_current_task_progress_bar": self.current_task_reset_callback,
            "reset_global_progress_bar": self.global_reset_callback,
            "add_mod_in_memory": self._add_github_mod,
            "del_mod_in_memory": self._del_github_mod,
        }

        self.github_panel: GithubPanel = GithubPanel(
            self, frame_name="Github mods data", callbacks=github_frame_callbacks
        )

        # frame for the external mods

        external_frame_callbacks: Dict[str, Any] = {
            "set_external_mod_version": self.set_external_mod_version,
            "set_external_mod_side": lambda name, side: asyncio.ensure_future(self.set_external_mod_side(name, side)),
            "get_gtnh": self._get_modpack_manager,
            "get_external_mods": self.get_external_mods,
            "add_mod_in_memory": self._add_external_mod,
            "del_mod_in_memory": self._del_external_mod,
            "refresh_external_mods": self.refresh_external_mods,
            "freeze": self.trigger_toggle,
        }

        self.external_mod_frame: ExternalPanel = ExternalPanel(
            self, frame_name="External mod data", callbacks=external_frame_callbacks
        )

        exclusion_client_callbacks: Dict[str, Any] = {
            "add": lambda exclusion: asyncio.ensure_future(self.add_exclusion("client", exclusion)),
            "del": lambda exclusion: asyncio.ensure_future(self.del_exclusion("client", exclusion)),
        }

        # frame for the client file exclusions
        self.exclusion_frame_client: ExclusionPanel = ExclusionPanel(
            self, "Client exclusions", callbacks=exclusion_client_callbacks
        )

        exclusion_server_callbacks: Dict[str, Any] = {
            "add": lambda exclusion: asyncio.ensure_future(self.add_exclusion("server", exclusion)),
            "del": lambda exclusion: asyncio.ensure_future(self.del_exclusion("server", exclusion)),
        }

        # frame for the server side exclusions
        self.exclusion_frame_server: ExclusionPanel = ExclusionPanel(
            self, "Server exclusions", callbacks=exclusion_server_callbacks
        )

        width: int = self.github_panel.get_width()
        self.external_mod_frame.set_width(width)

        self.toggled: bool = True  # state variable indicating if the widgets are disabled or not

    def _add_github_mod(self, name: str, version: str) -> None:
        """
        add a mod to inmemory github modlist.

        :param name: mod name
        :param version: mod version
        :return: None
        """
        self.github_mods[name] = version

    def _del_github_mod(self, name: str) -> None:
        """
        remove a mod from inmemory github modlist.

        :param name: mod name
        :return: None
        """
        del self.github_mods[name]

    def _add_external_mod(self, name: str, version: str) -> None:
        """
        add a mod to inmemory external modlist.

        :param name: mod name
        :param version: mod version
        :return: None
        """
        self.external_mods[name] = version

    def _del_external_mod(self, name: str) -> None:
        """
        remove a mod from inmemory external modlist.

        :param name: mod name
        :return: None
        """
        del self.external_mods[name]

    def trigger_toggle(self) -> None:
        """
        Enable/disable the widgets that can be toggled.

        :return: None
        """
        self.toggled = not self.toggled
        # print(f"{'toggled' if not self.toggled else 'untoggled'}") # debug
        self.toggle(self)

    def toggle(self, widget: Any) -> None:
        """
        Recursion algorithm to toggle the widgets.

        :param widget: the widget to recurse from
        :return: None
        """
        state: str
        if self.toggled:
            state = NORMAL
        else:
            state = DISABLED

        if check(widget):
            widget.configure(state=state)  # type: ignore
        else:
            if len(widget.winfo_children()) > 0:
                for child in widget.winfo_children():
                    self.toggle(child)

    async def assemble_release(self, side: Side, archive_type: Archive) -> None:
        """
        Method used to trigger the assembling of the client archive corresponding to the provided source.

        :return: None
        """
        global_callback: Callable[[float, str], None] = self.modpack_list_frame.action_frame.update_global_progress_bar

        try:
            self.set_progress(100 / 2)
            self.trigger_toggle()
            release_assembler: ReleaseAssembler = await self.pre_assembling()
            assembler_dict: Dict[Archive, Callable[[Side, bool], None]] = {
                Archive.ZIP: release_assembler.assemble_zip,
                Archive.MMC: release_assembler.assemble_mmc,
                Archive.MODRINTH: release_assembler.assemble_modrinth,
                Archive.CURSEFORGE: release_assembler.assemble_curse,
                Archive.TECHNIC: release_assembler.assemble_technic,
            }
            global_callback(self.get_progress(), f"Assembling {side} {archive_type} archive")
            assembler_dict[archive_type](side=side, verbose=True)  # type: ignore
            self.trigger_toggle()
        except BaseException as e:
            showerror(
                f"An error occured during the assembling {side} {archive_type} archive",
                f"An error occurended during the assembling {side} {archive_type} archive."
                "\n Please check the logs for more information",
            )
            if not self.toggled:
                self.trigger_toggle()
            raise e

    async def pre_assembling(self) -> ReleaseAssembler:
        """
        Method to downloads the mods before constructing the ReleaseAssembler object.

        :return: the ReleaseAssembler object constructed
        """
        gtnh: GTNHModpackManager = await self._get_modpack_manager()
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
        await gtnh.download_release(
            release, download_callback=self.progress_callback, error_callback=self.add_error_message
        )
        self.current_task_reset_callback()

        if len(self.download_error_list) > 0:
            error = "The following error(s) happened during the downloading of assets:\n" + "\n".join(
                self.download_error_list
            )

            showerror("Error(s) happened during the downloading of assets", error)
            self.download_error_list = []
            self.trigger_toggle()

            raise NoModAssetFound(error)

        return ReleaseAssembler(
            gtnh,
            release,
            task_callback=self.progress_callback,
            global_callback=self.global_callback,
            current_task_reset_callback=self.current_task_reset_callback,
        )

    def add_error_message(self, error_message: str) -> None:
        """
        Method used as error callback when an error happens during the download of a mod/release.

        :param error_message: the error message to add to the error list
        :return: None
        """
        self.download_error_list.append(error_message)

    async def assemble_all(self) -> None:
        """
        Assemble all the archives.

        :return: None
        """
        global_callback: Callable[[float, str], None] = self.modpack_list_frame.action_frame.update_global_progress_bar
        try:
            self.trigger_toggle()

            self.set_progress(100 / (1 + 5 + 1))  # download + archives for client + archive for server
            release_assembler: ReleaseAssembler = await self.pre_assembling()

            release_assembler.set_progress(self.get_progress())

            release_assembler.assemble(Side.CLIENT, verbose=True)

            # todo: redo the bar resets less hacky: they are all spread all over the place and it's inconsistent
            if release_assembler.current_task_reset_callback is not None:
                release_assembler.current_task_reset_callback()

            global_callback(self.get_progress(), f"Assembling {Side.SERVER} {Archive.ZIP} archive")
            release_assembler.assemble_zip(Side.SERVER, verbose=True)

            self.trigger_toggle()

        except BaseException as e:
            showerror(
                "An error occured during the update of the assembling of the archives",
                "An error occurended during the update of the assembling of the archives."
                "\n Please check the logs for more information",
            )
            if not self.toggled:
                self.trigger_toggle()
            raise e

    def set_progress(self, delta_progress: float) -> None:
        """
        Setter for self.delta_progress.

        :param delta_progress: new progress
        :return: None
        """
        self.delta_progress = delta_progress

    def get_progress(self) -> float:
        """
        Setter for self.delta_progress.

        :return: the current delta progress
        """
        return self.delta_progress

    async def add_exclusion(self, side: str, exclusion: str) -> None:
        """
        Method used to add an file exclusion to the corresponding side's exclusion list.

        :param side: side of the modpack
        :param exclusion: the string corresponding to the file exclusion
        :return: None
        """
        gtnh: GTNHModpackManager = await self._get_modpack_manager()
        gtnh.add_exclusion(side, exclusion)
        gtnh.save_modpack()

    async def del_exclusion(self, side: str, exclusion: str) -> None:
        """
        Method used to add an file exclusion to the corresponding side's exclusion list.

        :param side: side of the modpack
        :param exclusion: the string corresponding to the file exclusion
        :return: None
        """
        gtnh: GTNHModpackManager = await self._get_modpack_manager()
        gtnh.delete_exclusion(side, exclusion)
        gtnh.save_modpack()

    async def get_modpack_exclusions(self, side: str) -> List[str]:
        """
        Method used to gather the file exclusion list of the modpack corresponding to the provided side.

        :param side: side of the pack
        :return: list of strings corresponding to the file exclusions
        """
        gtnh: GTNHModpackManager = await self._get_modpack_manager()
        if side == "client":
            return sorted([exclusion for exclusion in gtnh.mod_pack.client_exclusions])
        elif side == "server":
            return sorted([exclusion for exclusion in gtnh.mod_pack.server_exclusions])
        else:
            raise ValueError(f"side {side} is an invalid side")

    async def set_github_mod_side(self, mod_name: str, side: str) -> None:
        """
        Method used to set the side of a github mod.

        :param mod_name: the mod name
        :param side: side of the pack
        :return: None
        """
        gtnh: GTNHModpackManager = await self._get_modpack_manager()
        previous_side: Side = gtnh.assets.get_github_mod(mod_name).side
        if previous_side == side:
            showwarning(
                "Side already set up",
                f"{mod_name}'s side is already set on {side}",
            )
            return

        if not gtnh.set_github_mod_side(mod_name, side):
            showerror(
                "Error setting up the side of the mod",
                f"Error during the process of setting up {mod_name}'s side to {side}. Check the logs for more details",
            )
            return

        if side == Side.NONE and mod_name in self.github_mods:
            del self.github_mods[mod_name]

        if side != Side.NONE and mod_name not in self.github_mods:
            # dirty hack to add the mod back if it's switched from disabled to something else
            self.github_mods[mod_name] = self.github_panel.mod_info_frame.version.get()

    async def set_external_mod_side(self, mod_name: str, side: str) -> None:
        """
        Method used to set the side of an external mod.

        :param mod_name: the mod name
        :param side: side of the pack
        :return: None
        """
        gtnh: GTNHModpackManager = await self._get_modpack_manager()
        previous_side: Side = gtnh.assets.get_external_mod(mod_name).side
        if previous_side == side:
            showwarning(
                "Side already set up",
                f"{mod_name}'s side is already set on {side}",
            )
            return

        if not gtnh.set_external_mod_side(mod_name, side):
            showerror(
                "Error setting up the side of the mod",
                f"Error during the process of setting up {mod_name}'s side to {side}. Check the logs for more details",
            )
            return

        if side == Side.NONE and mod_name in self.external_mods:
            del self.external_mods[mod_name]

        if side != Side.NONE and mod_name not in self.external_mods:
            # dirty hack to add the mod back if it's switched from disabled to something else
            self.external_mods[mod_name] = self.external_mod_frame.mod_info_frame.version.get()

    def set_github_mod_version(self, github_mod_name: str, mod_version: str) -> None:
        """
        Callback used when a github mod version is selected.

        :param github_mod_name: mod name
        :param mod_version: mod version
        :return: None
        """
        if github_mod_name in self.github_mods:
            self.github_mods[github_mod_name] = mod_version

    def set_external_mod_version(self, external_mod_name: str, mod_version: str) -> None:
        """
        Callback used when an external mod version is selected.

        :param external_mod_name: mod name
        :param mod_version: mod version
        :return: None
        """
        if external_mod_name in self.external_mods:
            self.external_mods[external_mod_name] = mod_version

    def set_modpack_version(self, modpack_version: str) -> None:
        """
        Callback used when a modpack version is selected.

        :param modpack_version: modpack version
        :return: None
        """
        self.gtnh_config = modpack_version

    async def get_repos(self) -> List[str]:
        """
        Method to grab all the repo names known.

        :return: a list of github mod names
        """
        gtnh: GTNHModpackManager = await self._get_modpack_manager()
        return [x.name for x in gtnh.assets.github_mods]

    def get_github_mods(self) -> Dict[str, str]:
        """
        Getter for self.github_mods.

        :return: self.github_mods
        """
        return self.github_mods

    def get_external_mods(self) -> Dict[str, str]:
        """
        Getter for self.external_mods.

        :return: self.external_mods
        """
        return self.external_mods

    async def _get_client(self) -> httpx.AsyncClient:
        """
        Internal getter for the httpx client instance, creating it if it doesn't exist.

        :return: the httpx client instance
        """
        if self._client is None:
            self._client = httpx.AsyncClient(http2=True)
        return self._client

    async def _get_modpack_manager(self) -> GTNHModpackManager:
        """
        Internal getter for the modpack manager instance, creating it if it doesn't exist.

        :return: the modpack manager instance
        """
        if self._modpack_manager is None:
            self._modpack_manager = GTNHModpackManager(await self._get_client())
        return self._modpack_manager

    async def update_assets(self) -> None:
        """
        Callback to update all the availiable assets.

        :return: None
        """

        self.global_reset_callback()
        self.current_task_reset_callback()

        try:
            self.trigger_toggle()
            gtnh: GTNHModpackManager = await self._get_modpack_manager()
            global_delta_progress: float = 100 / (1 + 1)  # 1 for the syncing of the mods, 1 for update checks
            await gtnh.update_all(
                progress_callback=self.progress_callback,
                global_progress_callback=lambda msg: self.global_callback(global_delta_progress, msg),
            )
            self.trigger_toggle()
            errored_mods = []

            # checking for errored mods
            for mod in gtnh.assets.github_mods:
                if mod.needs_attention:
                    errored_mods.append(mod)

            if len(errored_mods) == 0:
                showinfo("assets updated successfully!", "all the assets have been updated correctly!")
            else:
                showwarning(
                    "updated the nightly release metadata",
                    "The nightly release metadata had been updated BUT:\n"
                    + "\n".join(
                        [
                            f"mod {mod.name} has {mod.latest_version} which is "
                            "older than newest version availiable on github"
                            for mod in errored_mods
                        ]
                    )
                    + "\nThis means tags had been done wrongly.",
                )

        except BaseException as e:
            showerror(
                "An error occured during the update of the assets",
                "An error occurended during the update of the assets." "\n Please check the logs for more information",
            )
            if not self.toggled:
                self.trigger_toggle()
            raise e

    async def update_nightly(self) -> None:
        """
        Callback used to generate/update the nightly build.

        :return: None
        """

        self.current_task_reset_callback()
        self.global_reset_callback()

        try:
            self.trigger_toggle()
            gtnh: GTNHModpackManager = await self._get_modpack_manager()
            existing_release = gtnh.get_release("nightly")
            if not existing_release:
                raise ReleaseNotFoundException("Nightly release not found")

            # 1 for the data download on github, 1 for the asset updates and 1 for the nightly build update
            global_delta_progress: float = 100 / (1 + 1 + 1)
            release: GTNHRelease = await gtnh.update_release(
                "nightly",
                existing_release=existing_release,
                update_available=True,
                progress_callback=self.progress_callback,
                reset_progress_callback=self.current_task_reset_callback,
                global_progress_callback=lambda msg: self.global_callback(global_delta_progress, msg),
            )
            gtnh.add_release(release, update=True)
            gtnh.save_modpack()
            self.trigger_toggle()
            errored_mods = []

            # checking for errored mods
            for mod in gtnh.assets.github_mods:
                if mod.needs_attention:
                    errored_mods.append(mod)

            if len(errored_mods) == 0:
                showinfo("updated the nightly release metadata", "The nightly release metadata had been updated!")
            else:
                showwarning(
                    "updated the nightly release metadata",
                    "The nightly release metadata had been updated BUT:\n"
                    + "\n".join(
                        [
                            f"mod {mod.name} has {mod.latest_version} which is "
                            "older than newest version availiable on github"
                            for mod in errored_mods
                        ]
                    )
                    + "\nThis means tags had been done wrongly.",
                )
        except BaseException as e:
            showerror(
                "An error occured during the update of the nightly build",
                "An error occurended during the update of the nightly build."
                "\n Please check the logs for more information",
            )
            if not self.toggled:
                self.trigger_toggle()
            raise e

    async def get_releases(self) -> List[GTNHRelease]:
        """
        Method used to return a list of known releases with valid metadata.
        The list is sorted in ascending order (from oldest to the latest).

        :return: a sorted list of all the gtnh releases availiable
        """
        gtnh: GTNHModpackManager = await self._get_modpack_manager()

        releases: List[GTNHRelease] = []

        # if there is any release, chose last
        if len(gtnh.mod_pack.releases) > 0:
            # gtnh.mod_pack.releases is actually a set of the release names
            for release_name in gtnh.mod_pack.releases:
                release: Optional[GTNHRelease] = gtnh.get_release(release_name)

                # discarding all the None releases, as it means the json data couldn't be loaded
                if release is not None:
                    releases.append(release)

            # sorting releases by date
            releases = sorted(releases, key=lambda release_object: release_object.last_updated)

        return releases

    async def load_gtnh_version(self, release: Union[GTNHRelease, str], init: bool = False) -> None:
        """
        Callback to load in memory a pack release.

        :param release: either a release object or a release name
        :param init: bool indicating if this is done manually or at init
        :return: None
        """
        release_object: Optional[GTNHRelease]

        if isinstance(release, str):
            gtnh: GTNHModpackManager = await self._get_modpack_manager()
            release_object = gtnh.get_release(release)
        else:
            release_object = release

        if release_object is not None:
            release_object = await self.strip_disabled_mods(release_object)
            self.github_mods = release_object.github_mods
            self.gtnh_config = release_object.config
            self.external_mods = release_object.external_mods
            self.version = release_object.version
            self.last_version = release_object.last_version
            logger.info(f"Loaded pack version {Fore.CYAN}{release_object.version}{Fore.RESET} in memory.")
        else:
            showerror("incorrect version detected", f"modpack version {release} doesn't exist")
            return

        if not init:
            showinfo("version loaded successfully!", f"modpack version {release_object.version} loaded successfully!")
        else:
            # display the loaded version at boot
            self.modpack_list_frame.modpack_list.set_loaded_version(self.version)

    async def strip_disabled_mods(self, release: GTNHRelease) -> GTNHRelease:
        """
        Method used to strip the disabled mods from any release improperly generated during its loading.

        :param gtnh_modpack: the modpack manager instance. It is passed externally to make this function synced
        :return: the release with the stripped disabled mods
        """
        # todo: create a new instance for release object and edit it instead, because mutating args is bad mkay?
        mod_name: str
        version: str
        gtnh_modpack: GTNHModpackManager = await self._get_modpack_manager()
        github_mods: Dict[str, str] = release.github_mods
        external_mods: Dict[str, str] = release.external_mods
        valid_side: Set[Side] = {Side.NONE}
        github_mods_to_delete: List[str] = []
        external_mods_to_delete: List[str] = []
        mod_data: Optional[Tuple[GTNHModInfo | ExternalModInfo, GTNHVersion]] = None
        for mod_name, version in github_mods.items():
            mod_data = gtnh_modpack.assets.get_mod_and_version(
                mod_name, version, valid_sides=valid_side, source=ModSource.github
            )
            if mod_data is not None:
                logger.warn(
                    f"{Fore.YELLOW}Release {release.version} had github mod {mod_name}"
                    " in its manifest but it is disabled. Stripping it from memory.{Fore.RESET}"
                )
                github_mods_to_delete.append(mod_name)

        for mod_name in github_mods_to_delete:
            del github_mods[mod_name]

        for mod_name, version in external_mods.items():
            mod_data = gtnh_modpack.assets.get_mod_and_version(
                mod_name, version, valid_sides=valid_side, source=ModSource.other
            )
            if mod_data is not None:
                logger.warn(
                    f"{Fore.YELLOW}Release {self.version} had external mod {mod_name}"
                    "in its manifest but it is disabled. Stripping it from memory.{Fore.RESET}"
                )
                external_mods_to_delete.append(mod_name)

        for mod_name in external_mods_to_delete:
            del external_mods[mod_name]

        release.github_mods = github_mods
        release.external_mods = external_mods
        return release

    async def add_gtnh_version(self, release_name: str, previous_version: str) -> None:
        """
        Callback to add a new modpack version.

        :param release_name: the name of the release
        :param previous_version: the previous modpack version
        :return: None
        """

        gtnh: GTNHModpackManager = await self._get_modpack_manager()
        release: GTNHRelease = GTNHRelease(
            version=release_name,
            config=self.gtnh_config,
            github_mods=self.github_mods,
            external_mods=self.external_mods,
            last_version=previous_version,
        )

        self.last_version = previous_version

        is_release_added: bool = gtnh.add_release(release, update=True)

        if is_release_added:
            await self.load_gtnh_version(release)
            gtnh.save_modpack()
            showinfo("release successfully generated", f"modpack version {release_name} successfully generated!")

    async def delete_gtnh_version(self, release_name: str) -> None:
        """
        Callback used to delete a modpack version.

        :param release_name: name of the release
        :return: None
        """
        gtnh: GTNHModpackManager = await self._get_modpack_manager()
        if self.version == release_name:
            releases: List[GTNHRelease] = await self.get_releases()
            await self.load_gtnh_version(releases[-1], init=True)

        gtnh.delete_release(release_name)
        showinfo("release successfully deleted", f"modpack version {release_name} successfully deleted!")

    def show(self) -> None:
        """
        Method used to display widgets and child widgets, as well as to configure the "responsiveness" of the widgets.

        :return: None
        """
        x: int = 0
        y: int = 0
        rows: int = 2
        columns: int = 5

        for i in range(rows):
            self.rowconfigure(i, weight=1, pad=self.xpadding)

        for i in range(columns):
            self.columnconfigure(i, weight=1, pad=self.ypadding)

        # display child widgets
        self.github_panel.grid(row=x, column=y, rowspan=1, sticky=Position.ALL)
        self.modpack_list_frame.grid(row=x, column=y + 1, columnspan=4, sticky=Position.ALL)
        self.external_mod_frame.grid(row=x + 1, column=y, rowspan=1, sticky=Position.ALL)
        self.exclusion_frame_client.grid(row=x + 1, column=y + 1, columnspan=2, sticky=Position.ALL)
        self.exclusion_frame_server.grid(row=x + 1, column=y + 3, columnspan=2, sticky=Position.ALL)

        # child widget's inner display
        self.github_panel.show()
        self.external_mod_frame.show()
        self.modpack_list_frame.show()
        self.exclusion_frame_client.show()
        self.exclusion_frame_server.show()

    async def get_external_modlist(self) -> List[str]:
        """
        Method to get all the external mods from the assets.

        :return: a list of string with all the external mods availiable
        """
        gtnh: GTNHModpackManager = await self._get_modpack_manager()
        return [mod.name for mod in gtnh.assets.external_mods]

    async def get_modpack_versions(self) -> List[str]:
        """
        Method used to gather all the version of the GT-New-Horizons-Modpack repo.

        :return: a list of all the versions availiable.
        """
        gtnh: GTNHModpackManager = await self._get_modpack_manager()
        modpack_config: GTNHConfig = gtnh.assets.config
        return [version.version_tag for version in modpack_config.versions]

    async def run(self) -> None:
        """
        async entrypoint to trigger the mainloop

        :return: None
        """
        self.show()
        await self.update_widget()

    async def update_widget(self) -> None:
        """
        Method handling the loop of the gui.

        :return: None
        """
        if not self.init:
            self.init = True
            # load last gtnh version if there is any:
            releases: List[GTNHRelease] = await self.get_releases()
            if len(releases) > 0:
                await self.load_gtnh_version(releases[-1], init=True)

            data_github_mods: Dict[str, Any] = {
                "github_mod_list": await self.get_repos(),
                "modpack_version_frame": {"combobox": await self.get_modpack_versions(), "stringvar": self.gtnh_config},
            }

            self.github_panel.populate_data(data_github_mods)

            data_external_mods: Dict[str, Any] = {"external_mod_list": await self.get_external_modlist()}

            self.external_mod_frame.populate_data(data_external_mods)

            self.modpack_list_frame.populate_data(await self.get_releases())
            self.exclusion_frame_server.populate_data({"exclusions": await self.get_modpack_exclusions("server")})
            self.exclusion_frame_client.populate_data({"exclusions": await self.get_modpack_exclusions("client")})
        while self._run:
            self.update()
            self.update_idletasks()
            await asyncio.sleep(ASYNC_SLEEP)

    async def refresh_external_mods(self) -> None:
        """
        Method used to refresh the external modlist.

        :return: None
        """
        data_external_mods: Dict[str, Any] = {"external_mod_list": await self.get_external_modlist()}

        self.external_mod_frame.populate_data(data_external_mods)

    async def close_app(self) -> None:
        """
        Callback used when the app is closed.

        :return: None
        """
        if self._client is not None:
            await self._client.aclose()
            self._run = False
        self.destroy()


if __name__ == "__main__":
    asyncio.run(App().exec())
