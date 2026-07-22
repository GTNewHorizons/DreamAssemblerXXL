import asyncio
import sys
from pathlib import Path
from tkinter import DISABLED, NORMAL, PhotoImage, Tk, Widget
from tkinter.messagebox import showerror, showinfo, showwarning
from typing import Any, Callable, Dict, List, Union

from ttkthemes import ThemedTk

from daxxl.defs import Archive, Position, Side, DevRelease
from daxxl.exceptions import ReleaseNotFoundException, SideAlreadySetException
from daxxl.gtnh_logger import get_logger
from daxxl.gui.exclusion.exclusion_panel import ExclusionPanel, ExclusionPanelCallback
from daxxl.gui.external.external_panel import ExternalPanel, ExternalPanelCallback
from daxxl.gui.github.github_panel import GithubPanel, GithubPanelCallback
from daxxl.gui.lib.decorators import with_error_dialog
from daxxl.gui.modpack.modpack_panel import ModpackPanel, ModpackPanelCallback
from daxxl.models.gtnh_release import GTNHRelease
from daxxl.models.mod_info import GTNHModInfo
from daxxl.release_controller import ReleaseController

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
            if widget_type == "CustomButton":
                if widget["text"] == "Modrinth client archive":  # disabling modrinth archive packaging
                    return False
            return True
    return False


class App:
    """
    Wrapper class to start the GUI.
    """

    def __init__(self, themed: bool = False) -> None:
        self.instance: Window = Window(themed=themed)

    async def exec(self) -> None:
        """
        Coroutine used to run the GUI.
        """
        await self.instance.run()


class Window(ThemedTk, Tk):
    """
    Main class for the GUI. Only handles widgets, dialogs and the event loop;
    all the business logic is delegated to the ReleaseController.
    """

    def __init__(self, themed: bool = False) -> None:
        """
        Constructor of the Window class.

        :param themed: for those who prefered themed versions of the widget. Default to false.
        """
        self.themed = themed
        if themed:
            theme = "winnative" if sys.platform == "win32" else "plastik"
            ThemedTk.__init__(self, theme=theme)
        else:
            Tk.__init__(self)
        self._run: bool = True
        self.title("DreamAssemblerXXL")
        self.iconphoto(False, PhotoImage(file=ICON))

        self.xpadding: int = 0
        self.ypadding: int = 0
        self.minsize(1000, 600)  # Minimum to even see all the buttons

        self.init: bool = False
        self.protocol("WM_DELETE_WINDOW", lambda: asyncio.ensure_future(self.close_app()))

        # frame for the modpack handling
        modpack_panel_callbacks: ModpackPanelCallback = ModpackPanelCallback(
            update_asset=lambda: asyncio.ensure_future(self.update_assets()),
            generate_experimental=lambda: asyncio.ensure_future(self.update_experimental()),
            generate_daily=lambda: asyncio.ensure_future(self.update_daily()),
            client_mmc=lambda: asyncio.ensure_future(self.assemble_release(Side.CLIENT, Archive.MMC)),
            client_mmc_j9=lambda: asyncio.ensure_future(self.assemble_release(Side.CLIENT_JAVA9, Archive.MMC)),
            client_zip=lambda: asyncio.ensure_future(self.assemble_release(Side.CLIENT, Archive.ZIP)),
            server_zip=lambda: asyncio.ensure_future(self.assemble_release(Side.SERVER, Archive.ZIP)),
            server_zip_j9=lambda: asyncio.ensure_future(self.assemble_release(Side.SERVER_JAVA9, Archive.ZIP)),
            client_curse=lambda: asyncio.ensure_future(self.assemble_release(Side.CLIENT, Archive.CURSEFORGE)),
            client_modrinth=lambda: asyncio.ensure_future(self.assemble_release(Side.CLIENT, Archive.MODRINTH)),
            client_technic=lambda: asyncio.ensure_future(self.assemble_release(Side.CLIENT, Archive.TECHNIC)),
            update_all=lambda: asyncio.ensure_future(self.assemble_all()),
            update_beta=lambda: asyncio.ensure_future(self.assemble_beta()),
            generate_changelog=lambda: asyncio.ensure_future(self.generate_changelog()),
            generate_cf_files=lambda: asyncio.ensure_future(self.generate_intermediate_cf_files()),
            load=lambda release_name: asyncio.ensure_future(self.load_gtnh_version(release_name)),
            delete=lambda release_name: asyncio.ensure_future(self.delete_gtnh_version(release_name)),
            add=lambda release_name, previous_version: asyncio.ensure_future(
                self.add_gtnh_version(release_name, previous_version)
            ),
        )

        self.modpack_list_frame: ModpackPanel = ModpackPanel(
            self, frame_name="Modpack release actions", callbacks=modpack_panel_callbacks
        )

        self.progress_callback: Callable[[float, str], None] = (
            self.modpack_list_frame.action_frame.progress_bar_current_task.add_progress
        )
        self.global_callback: Callable[[float, str], None] = (
            self.modpack_list_frame.action_frame.progress_bar_global.add_progress
        )
        self.global_reset_callback: Callable[[], None] = self.modpack_list_frame.action_frame.progress_bar_global.reset
        self.current_task_reset_callback: Callable[[], None] = (
            self.modpack_list_frame.action_frame.progress_bar_current_task.reset
        )

        self.controller: ReleaseController = ReleaseController(
            progress_callback=self.progress_callback,
            global_callback=self.global_callback,
            global_reset_callback=self.global_reset_callback,
            current_task_reset_callback=self.current_task_reset_callback,
        )

        # frame for the github mods
        github_panel_callbacks: GithubPanelCallback = GithubPanelCallback(
            get_gtnh_callback=self.controller.get_modpack_manager,
            get_github_mods_callback=self.controller.get_github_mods,
            set_mod_version=self.controller.set_github_mod_version,
            set_mod_side=lambda name, side: asyncio.ensure_future(self.set_github_mod_side(name, side)),
            set_mod_side_default=lambda name, side: asyncio.ensure_future(self.set_mod_side_default(name, side)),
            set_modpack_version=self.controller.set_modpack_version,
            update_current_task_progress_bar=self.progress_callback,
            update_global_progress_bar=self.global_callback,
            reset_current_task_progress_bar=self.current_task_reset_callback,
            reset_global_progress_bar=self.global_reset_callback,
            add_mod_in_memory=self.controller.add_github_mod,
            del_mod_in_memory=self.controller.del_github_mod,
        )

        self.github_panel: GithubPanel = GithubPanel(
            self, frame_name="Github mods data", callbacks=github_panel_callbacks
        )

        # frame for the external mods

        external_panel_callbacks: ExternalPanelCallback = ExternalPanelCallback(
            set_mod_version=self.controller.set_external_mod_version,
            set_mod_side=lambda name, side: asyncio.ensure_future(self.set_external_mod_side(name, side)),
            set_mod_side_default=lambda name, side: asyncio.ensure_future(self.set_mod_side_default(name, side)),
            get_gtnh_callback=self.controller.get_modpack_manager,
            get_external_mods_callback=self.controller.get_external_mods,
            toggle_freeze=self.trigger_toggle,
            add_mod_in_memory=self.controller.add_external_mod,
            del_mod_in_memory=self.controller.del_external_mod,
            refresh_external_modlist=self.refresh_external_mods,
        )

        self.external_mod_frame: ExternalPanel = ExternalPanel(
            self, frame_name="External mod data", callbacks=external_panel_callbacks, themed=self.themed
        )

        exclusion_client_callbacks: ExclusionPanelCallback = ExclusionPanelCallback(
            add=lambda exclusion: asyncio.ensure_future(self.controller.add_exclusion("client", exclusion)),
            delete=lambda exclusion: asyncio.ensure_future(self.controller.del_exclusion("client", exclusion)),
        )

        # frame for the client file exclusions
        self.exclusion_frame_client: ExclusionPanel = ExclusionPanel(
            self, "Client exclusions", callbacks=exclusion_client_callbacks, themed=self.themed
        )

        exclusion_server_callbacks: ExclusionPanelCallback = ExclusionPanelCallback(
            add=lambda exclusion: asyncio.ensure_future(self.controller.add_exclusion("server", exclusion)),
            delete=lambda exclusion: asyncio.ensure_future(self.controller.del_exclusion("server", exclusion)),
        )

        # frame for the server side exclusions
        self.exclusion_frame_server: ExclusionPanel = ExclusionPanel(
            self, "Server exclusions", callbacks=exclusion_server_callbacks, themed=self.themed
        )

        width: int = self.github_panel.get_width()
        self.external_mod_frame.set_width(width)

        self.toggled: bool = True  # state variable indicating if the widgets are disabled or not

    def trigger_toggle(self) -> None:
        """
        Enable/disable the widgets that can be toggled.

        :return: None
        """
        self.toggled = not self.toggled
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
            widget.configure(state=state)
        else:
            if len(widget.winfo_children()) > 0:
                for child in widget.winfo_children():
                    self.toggle(child)

    @with_error_dialog(
        title="An error occured during the generation of the changelog",
        message=lambda self: (
            f"An error occured during the generation of the changelog from "
            f"{self.controller.last_version} to {self.controller.version}."
            "\nPlease check the logs for more information."
        ),
    )
    async def generate_changelog(self) -> None:
        """
        Callback used to generate the changelog of the loaded release.

        :return: None
        """
        self.trigger_toggle()
        await self.controller.generate_changelog()
        self.trigger_toggle()

    @with_error_dialog(
        title="An error occured during the generation of the intermediate curseforge files",
        message="An error occured during the generation of the intermediate curseforge files."
        "\nPlease check the logs for more information.",
    )
    async def generate_intermediate_cf_files(self) -> None:
        """
        Callback used to generate curseforge intermediate files.

        :return: None
        """
        self.trigger_toggle()
        await self.controller.generate_intermediate_cf_files(
            self.modpack_list_frame.action_frame.progress_bar_current_task
        )
        self.trigger_toggle()

    @with_error_dialog(
        title=lambda self, side, archive_type: (
            f"An error occured during the assembling {side.value} {archive_type.value} archive"
        ),
        message=lambda self, side, archive_type: (
            f"An error occurended during the assembling {side.value} {archive_type.value} archive."
            "\nPlease check the logs for more information."
        ),
    )
    async def assemble_release(self, side: Side, archive_type: Archive) -> None:
        """
        Callback used to trigger the assembling of the archive corresponding to the provided side and type.

        :return: None
        """
        self.trigger_toggle()
        await self.controller.assemble_release(side, archive_type)
        self.trigger_toggle()

    @with_error_dialog(
        title="An error occured during the update of the assembling of the archives",
        message="An error occured during the update of the assembling of the archives."
        "\nPlease check the logs for more information.",
    )
    async def assemble_all(self) -> None:
        """
        Callback used to assemble all the archives for a full update.

        :return: None
        """
        self.trigger_toggle()
        await self.controller.assemble_all()
        self.trigger_toggle()

    @with_error_dialog(
        title="An error occured during the update of the assembling of the archives",
        message="An error occured during the update of the assembling of the archives."
        "\nPlease check the logs for more information.",
    )
    async def assemble_beta(self) -> None:
        """
        Callback used to assemble all the archives for a beta/RC update.

        :return: None
        """
        self.trigger_toggle()
        await self.controller.assemble_beta()
        self.trigger_toggle()

    async def set_github_mod_side(self, mod_name: str, side: Side) -> None:
        """
        Callback used to set the side of a github mod.

        :param mod_name: the mod name
        :param side: side of the pack, None if use default
        :return: None
        """
        try:
            self.controller.set_github_mod_side(mod_name, side, self.github_panel.mod_info_frame.version.get)
        except SideAlreadySetException as e:
            showwarning("Side already set up", str(e))

    async def set_external_mod_side(self, mod_name: str, side: Side) -> None:
        """
        Callback used to set the side of an external mod.

        :param mod_name: the mod name
        :param side: side of the pack
        :return: None
        """
        try:
            self.controller.set_external_mod_side(mod_name, side, self.external_mod_frame.mod_info_frame.version.get)
        except SideAlreadySetException as e:
            showwarning("Side already set up", str(e))

    async def set_mod_side_default(self, mod_name: str, side: str) -> None:
        """
        Callback used to set the default side of a mod no matter what is its source (github or external).

        :param mod_name: mod name
        :param side: the default side to apply
        :return: None
        """
        try:
            if not await self.controller.set_mod_side_default(mod_name, side):
                showerror(
                    "Error setting up the side of the mod",
                    f"Error during the process of setting up {mod_name}'s side to {side}. "
                    "Check the logs for more details",
                )
        except SideAlreadySetException as e:
            showwarning("Side already set up", str(e))

    def _notify_errored_mods(
        self,
        errored_mods: List[GTNHModInfo],
        update_errors: List[str],
        title: str,
        success_message: str,
        warning_intro: str,
    ) -> None:
        """
        Show a warning if there was at least an errored mod or a failed asset update,
        an ok message otherwise.

        :param errored_mods: the mods needing attention (suspiciously outdated tags)
        :param update_errors: error messages for individual assets that failed to update
            (network/API hiccups) - these don't block the rest of the batch, but the user
            should still know some assets may be stale
        :param title: dialogue title
        :param success_message: success message
        :param warning_intro: warning message prefix
        :return: None
        """
        if not errored_mods and not update_errors:
            showinfo(title, success_message)
            return

        sections: List[str] = []
        if update_errors:
            sections.append("The following assets failed to update and may be stale:\n" + "\n".join(update_errors))
        if errored_mods:
            sections.append(
                "\n".join(
                    f"mod {mod.name} has {mod.latest_version} which is older than newest version availiable on github"
                    for mod in errored_mods
                )
                + "\nThis means tags had been done wrongly."
            )

        showwarning(title, warning_intro + "\n\n".join(sections))

    @with_error_dialog(
        title="An error occured during the update of the assets",
        message="An error occured during the update of the assets.\nPlease check the logs for more information.",
    )
    async def update_assets(self) -> None:
        """
        Callback to update update all the availiable assets.

        :return: None
        """
        self.trigger_toggle()
        errored_mods, update_errors = await self.controller.update_assets()
        self.trigger_toggle()

        self._notify_errored_mods(
            errored_mods,
            update_errors,
            title="assets update",
            success_message="All the assets have been updated correctly!",
            warning_intro="The assets had been updated BUT:\n",
        )

    async def _update_dev_release(self, release_type: str) -> None:
        """
        update dev release (experimental/daily).

        :param release_type: "experimental" or "daily"
        :return: None
        """
        self.trigger_toggle()
        errored_mods, update_errors = await self.controller.update_rolling_release(release_type)
        self.trigger_toggle()

        self._notify_errored_mods(
            errored_mods,
            update_errors,
            title=f"updated the {release_type} release metadata",
            success_message=f"The {release_type} release metadata had been updated!",
            warning_intro=f"The {release_type} release metadata had been updated BUT:\n",
        )

    @with_error_dialog(
        title="An error occured during the update of the experimental build",
        message="An error occured during the update of the experimental build."
        "\nPlease check the logs for more information.",
    )
    async def update_experimental(self) -> None:
        """
        Callback used to generate/update the experimental build.

        :return: None
        """
        await self._update_dev_release(DevRelease.EXPERIMENTAL.value)

    @with_error_dialog(
        title="An error occured during the update of the daily build",
        message="An error occured during the update of the daily build.\nPlease check the logs for more information.",
    )
    async def update_daily(self) -> None:
        """
        Callback used to generate/update the daily build.

        :return: None
        """
        await self._update_dev_release(DevRelease.DAILY.value)

    async def load_gtnh_version(self, release: Union[GTNHRelease, str], init: bool = False) -> None:
        """
        Callback to load in memory a pack release.

        :param release: either a release object or a release name
        :param init: bool indicating if this is done manually or at init
        :return: None
        """
        try:
            release_object: GTNHRelease = await self.controller.load_gtnh_version(release)
        except ReleaseNotFoundException:
            showerror("incorrect version detected", f"modpack version {release} doesn't exist")
            return

        if not init:
            showinfo("version loaded successfully!", f"modpack version {release_object.version} loaded successfully!")
        else:
            # display the loaded version at boot
            self.modpack_list_frame.modpack_list.set_loaded_version(self.controller.version)

    async def add_gtnh_version(self, release_name: str, previous_version: str) -> None:
        """
        Callback to add a new modpack version.

        :param release_name: the name of the release
        :param previous_version: the previous modpack version
        :return: None
        """
        if await self.controller.add_gtnh_version(release_name, previous_version):
            showinfo("release successfully generated", f"modpack version {release_name} successfully generated!")

    async def delete_gtnh_version(self, release_name: str) -> None:
        """
        Callback used to delete a modpack version.

        :param release_name: name of the release
        :return: None
        """
        await self.controller.delete_gtnh_version(release_name)
        self.modpack_list_frame.modpack_list.set_loaded_version(self.controller.version)
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

        debug: bool = False
        if debug:
            # display child widgets
            # self.github_panel.grid(row=x, column=y, rowspan=1, sticky=Position.ALL)
            self.modpack_list_frame.grid(row=x, column=y + 1, columnspan=4, sticky=Position.ALL)
            # self.external_mod_frame.grid(row=x + 1, column=y, rowspan=1, sticky=Position.ALL)
            # self.exclusion_frame_client.grid(row=x + 1, column=y + 1, columnspan=2, sticky=Position.ALL)
            # self.exclusion_frame_server.grid(row=x + 1, column=y + 3, columnspan=2, sticky=Position.ALL)
            #
            # child widget's inner display
            # self.github_panel.show()
            self.modpack_list_frame.show()
            # self.external_mod_frame.show()
            # self.exclusion_frame_client.show()
            # self.exclusion_frame_server.show()
        else:
            # display child widgets
            self.github_panel.grid(row=x, column=y, rowspan=1, sticky=Position.ALL)
            self.modpack_list_frame.grid(row=x, column=y + 1, columnspan=4, sticky=Position.ALL)
            self.external_mod_frame.grid(row=x + 1, column=y, rowspan=1, sticky=Position.ALL)
            self.exclusion_frame_client.grid(row=x + 1, column=y + 1, columnspan=2, sticky=Position.ALL)
            self.exclusion_frame_server.grid(row=x + 1, column=y + 3, columnspan=2, sticky=Position.ALL)

            # child widget's inner display
            self.github_panel.show()
            self.modpack_list_frame.show()
            self.external_mod_frame.show()
            self.exclusion_frame_client.show()
            self.exclusion_frame_server.show()

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
            releases: List[GTNHRelease] = await self.controller.get_releases()
            if len(releases) > 0:
                await self.load_gtnh_version(releases[-1], init=True)

            data_github_mods: Dict[str, Any] = {
                "github_mod_list": await self.controller.get_repos(),
                "modpack_version_frame": {
                    "combobox": await self.controller.get_modpack_versions(),
                    "stringvar": self.controller.gtnh_config,
                },
            }

            self.github_panel.populate_data(data_github_mods)

            data_external_mods: Dict[str, Any] = {"external_mod_list": await self.controller.get_external_modlist()}

            self.external_mod_frame.populate_data(data_external_mods)

            self.modpack_list_frame.populate_data(await self.controller.get_releases())
            self.exclusion_frame_server.populate_data(
                {"exclusions": await self.controller.get_modpack_exclusions("server")}
            )
            self.exclusion_frame_client.populate_data(
                {"exclusions": await self.controller.get_modpack_exclusions("client")}
            )
        while self._run:
            self.update()
            self.update_idletasks()
            await asyncio.sleep(ASYNC_SLEEP)

    async def refresh_external_mods(self) -> None:
        """
        Method used to refresh the external modlist.

        :return: None
        """
        data_external_mods: Dict[str, Any] = {"external_mod_list": await self.controller.get_external_modlist()}

        self.external_mod_frame.populate_data(data_external_mods)

    async def close_app(self) -> None:
        """
        Callback used when the app is closed.

        :return: None
        """
        await self.controller.close()
        self._run = False
        self.destroy()


if __name__ == "__main__":
    asyncio.run(App(themed=False).exec())
