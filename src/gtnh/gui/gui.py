import asyncio
from tkinter import END, Button, Entry, Label, LabelFrame, Listbox, Scrollbar, StringVar, Tk
from tkinter.messagebox import showerror, showinfo
from tkinter.ttk import Combobox, Progressbar
from typing import Any, Callable, Coroutine, Dict, List, Optional, Tuple, Union

import httpx

from gtnh.assembler.assembler import ReleaseAssembler
from gtnh.defs import Side
from gtnh.models.gtnh_config import GTNHConfig
from gtnh.models.gtnh_release import GTNHRelease
from gtnh.models.gtnh_version import GTNHVersion
from gtnh.models.mod_info import GTNHModInfo
from gtnh.modpack_manager import GTNHModpackManager

ASYNC_SLEEP = 0.05


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


class Window(Tk):
    """
    Main class for the GUI.
    """

    def __init__(self) -> None:
        """
        Constructor of the Window class.
        """
        Tk.__init__(self)
        self._client: Optional[httpx.AsyncClient] = None
        self._modpack_manager: Optional[GTNHModpackManager] = None
        self._run: bool = True

        self.github_mods: Dict[str, str] = {}  # name <-> version of github mods mappings for the current release
        self.gtnh_config: str = ""  # modpack asset version
        self.external_mods: Dict[str, str] = {}  # name <-> version of external mods mappings for the current release
        self.version: str = ""  # modpack release name

        self.init: bool = False
        self.protocol("WM_DELETE_WINDOW", lambda: asyncio.ensure_future(self.close_app()))

        # frame for the github mods
        github_frame_callbacks: Dict[str, Any] = {
            "get_gtnh": self._get_modpack_manager,
            "get_github_mods": self.get_github_mods,
            "set_github_mod_version": self.set_github_mod_version,
            "set_github_mod_side": lambda name, side: asyncio.ensure_future(self.set_github_mod_side(name, side)),
            "set_modpack_version": self.set_modpack_version,
        }

        self.github_mod_frame: GithubModFrame = GithubModFrame(
            self, frame_name="github mods data", callbacks=github_frame_callbacks
        )

        # frame for the external mods

        external_frame_callbacks: Dict[str, Any] = {
            "set_external_mod_version": self.set_external_mod_version,
            "set_external_mod_side": lambda name, side: None,
        }
        self.external_mod_frame: ExternalModFrame = ExternalModFrame(
            self, frame_name="external mod data", callbacks=external_frame_callbacks
        )

        # frame for the modpack handling
        modpack_list_callbacks: Dict[str, Any] = {
            "load": lambda release_name: asyncio.ensure_future(self.load_gtnh_version(release_name)),
            "add": lambda release_name: asyncio.ensure_future(self.add_gtnh_version(release_name)),
            "delete": lambda release_name: asyncio.ensure_future(self.delete_gtnh_version(release_name)),
            "update_assets": lambda: asyncio.ensure_future(self.update_assets()),
            "generate_nightly": lambda: asyncio.ensure_future(self.generate_nightly()),
            "client_mmc": lambda: asyncio.ensure_future(self.assemble_mmc_release("CLIENT")),
            "server_mmc": lambda: asyncio.ensure_future(self.assemble_mmc_release("SERVER")),
        }

        self.modpack_list_frame: ModPackFrame = ModPackFrame(
            self, frame_name="modpack release actions", callbacks=modpack_list_callbacks
        )

        exclusion_client_callbacks: Dict[str, Any] = {
            "add": lambda exclusion: asyncio.ensure_future(self.add_exclusion("client", exclusion)),
            "del": lambda exclusion: asyncio.ensure_future(self.del_exclusion("client", exclusion)),
        }

        # frame for the client file exclusions
        self.exclusion_frame_client: ExclusionFrame = ExclusionFrame(
            self, "client exclusions", callbacks=exclusion_client_callbacks
        )

        exclusion_server_callbacks: Dict[str, Any] = {
            "add": lambda exclusion: asyncio.ensure_future(self.add_exclusion("server", exclusion)),
            "del": lambda exclusion: asyncio.ensure_future(self.del_exclusion("server", exclusion)),
        }

        # frame for the server side exclusions
        self.exclusion_frame_server: ExclusionFrame = ExclusionFrame(
            self, "server exclusions", callbacks=exclusion_server_callbacks
        )

        self.btn_debug = Button(text="update", command=self.github_mod_frame.update_widget)

    async def assemble_mmc_release(self, side: str) -> None:
        """
        Method used to trigger the assembling of the mmc pack archive corresponding to the provided side.

        :param side: side of the modpack
        :return: None
        """
        gtnh: GTNHModpackManager = await self._get_modpack_manager()
        release: GTNHRelease = GTNHRelease(
            version=self.version,
            config=self.gtnh_config,
            github_mods=self.github_mods,
            external_mods=self.external_mods,
        )
        await gtnh.download_release(
            release, callback=self.modpack_list_frame.action_frame.update_current_task_progress_bar
        )
        ReleaseAssembler(gtnh, release).assemble(Side[side], verbose=True)

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
        if not gtnh.set_github_mod_side(mod_name, side):
            showerror(
                "Error setting up the side of the mod",
                f"Error during the process of setting up {mod_name}'s side to {side}. Check the logs for more details",
            )

    def set_github_mod_version(self, github_mod_name: str, mod_version: str) -> None:
        """
        Callback used when a github mod version is selected.

        :param github_mod_name: mod name
        :param mod_version: mod version
        :return: None
        """
        self.github_mods[github_mod_name] = mod_version

    def set_external_mod_version(self, external_mod_name: str, mod_version: str) -> None:
        """
        Callback used when an external mod version is selected.

        :param external_mod_name: mod name
        :param mod_version: mod version
        :return: None
        """
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
        gtnh: GTNHModpackManager = await self._get_modpack_manager()
        await gtnh.update_all()
        showinfo("assets updated successfully!", "all the assets have been updated correctly!")

    async def generate_nightly(self) -> None:
        """
        Callback used to generate/update the nightly build.

        :return: None
        """
        gtnh: GTNHModpackManager = await self._get_modpack_manager()
        release: GTNHRelease = await gtnh.generate_release("nightly", update_available=True)
        gtnh.add_release(release, update=True)
        gtnh.save_modpack()
        showinfo("updated the nightly release metadata", "The nightly release metadata had been updated!")

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
            releases = sorted(releases, key=lambda release: release.last_updated)

        return releases

    async def load_gtnh_version(self, release: Union[GTNHRelease, str], init: bool = False) -> None:
        """
        Callback to load in memory a pack release.

        :param release: either a release object or a release name
        :param init: bool indicating if this is done manually or at init
        :return: None
        """

        if isinstance(release, str):
            gtnh: GTNHModpackManager = await self._get_modpack_manager()
            release_object = gtnh.get_release(release)
        else:
            release_object = release

        if release_object is not None:
            self.github_mods = release_object.github_mods
            self.gtnh_config = release_object.config
            self.external_mods = release_object.external_mods
            self.version = release_object.version
        else:
            showerror("incorrect version detected", f"modpack version {release} doesn't exist")
            return

        if not init:
            showinfo("version loaded successfully!", f"modpack version {release_object.version} loaded successfully!")

    async def add_gtnh_version(self, release_name: str) -> None:
        """
        Callback to add a new modpack version.

        :param release_name: the name of the release
        :return: None
        """

        gtnh: GTNHModpackManager = await self._get_modpack_manager()
        release: GTNHRelease = GTNHRelease(
            version=release_name,
            config=self.gtnh_config,
            github_mods=self.github_mods,
            external_mods=self.external_mods,
        )

        if gtnh.add_release(release, update=True):
            gtnh.save_modpack()
            showinfo("release successfully generated", f"modpack version {release_name} successfully generated!")

    async def delete_gtnh_version(self, release_name: str) -> None:
        """
        Callback used to delete a modpack version.

        :param release_name: name of the release
        :return: None
        """
        gtnh: GTNHModpackManager = await self._get_modpack_manager()
        gtnh.delete_release(release_name)
        showinfo("release successfully deleted", f"modpack version {release_name} successfully deleted!")

    def show(self) -> None:
        """
        Method used to display widgets and child widgets, as well as to configure the "responsiveness" of the widgets.

        :return: None
        """

        # auto resize config
        for i in range(3):
            self.columnconfigure(i, weight=1)
            self.rowconfigure(i, weight=1)

        # display child widgets
        self.github_mod_frame.grid(row=0, column=0)
        self.external_mod_frame.grid(row=2, column=0)
        self.modpack_list_frame.grid(row=0, column=1, columnspan=2, sticky="WENS")
        self.exclusion_frame_client.grid(row=1, column=1, sticky="WENS", rowspan=3)
        self.exclusion_frame_server.grid(row=1, column=2, sticky="WENS", rowspan=2)

        self.btn_debug.grid(row=10, column=10)

        # child widget's inner display
        self.github_mod_frame.show()
        self.external_mod_frame.show()
        self.modpack_list_frame.show()
        self.exclusion_frame_client.show()
        self.exclusion_frame_server.show()

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
            data = {
                "github_mod_list": await self.get_repos(),
                "modpack_version_frame": {"combobox": await self.get_modpack_versions(), "stringvar": self.gtnh_config},
            }

            self.github_mod_frame.populate_data(data)
            self.modpack_list_frame.populate_data(await self.get_releases())
            self.exclusion_frame_server.populate_data({"exclusions": await self.get_modpack_exclusions("server")})
            self.exclusion_frame_client.populate_data({"exclusions": await self.get_modpack_exclusions("client")})
        while self._run:
            self.update()
            self.update_idletasks()
            await asyncio.sleep(ASYNC_SLEEP)

    async def close_app(self) -> None:
        """
        Callback used when the app is closed.

        :return: None
        """
        if self._client is not None:
            await self._client.aclose()
            self._run = False
        self.destroy()


class ModInfoFrame(LabelFrame):
    """
    Widget used to display info about a mod passed to it.
    """

    def __init__(
        self,
        master: Any,
        frame_name: str,
        callbacks: Dict[str, Callable[[str, str], None]],
        width: Optional[int] = None,
        **kwargs: Any,
    ) -> None:
        """
        Constructor of the ModInfoFrame class.

        :param master: the parent widget
        :param frame_name: the name displayed in the framebox
        :param callbacks: a dict of callbacks passed to this instance
        :param kwargs: params to init the parent class
        """
        LabelFrame.__init__(self, master, text=frame_name, **kwargs)
        self.ypadding: int = 0  # todo: tune this
        self.xpadding: int = 0  # todo: tune this
        self.callbacks: Dict[str, Any] = callbacks

        self.label_mod_name_text: str = "mod name:"
        self.label_version_text: str = "mod version:"
        self.label_license_text: str = "mod license:"
        self.label_size_text: str = "mod side:"

        self.width = (
            width
            if width is not None
            else max(
                len(self.label_mod_name_text),
                len(self.label_version_text),
                len(self.label_license_text),
                len(self.label_size_text),
            )
        )
        self.label_mod_name: Label = Label(self, text=self.label_mod_name_text)
        self.label_version: Label = Label(self, text=self.label_version_text)
        self.label_license: Label = Label(self, text=self.label_license_text)
        self.label_side: Label = Label(self, text=self.label_size_text)

        self.sv_mod_name: StringVar = StringVar(self, value="")
        self.sv_version: StringVar = StringVar(self, value="")
        self.sv_license: StringVar = StringVar(self, value="")
        self.sv_side: StringVar = StringVar(self, value="")

        self.label_mod_name_value: Label = Label(self, textvariable=self.sv_mod_name)
        self.cb_version: Combobox = Combobox(self, textvariable=self.sv_version, values=[])
        self.cb_version.bind("<<ComboboxSelected>>", self.set_mod_version)

        self.label_license_value: Label = Label(self, textvariable=self.sv_license)
        self.cb_side: Combobox = Combobox(self, textvariable=self.sv_side, values=[])
        self.cb_side.bind("<<ComboboxSelected>>", self.set_mod_side)

    def set_mod_side(self, event: Any) -> None:
        """
        Callback used when the user selects a mod side.

        :param event: the tkinter event passed by the tkinter in the Callback (unused)
        :return: None
        """
        mod_name: str = self.sv_mod_name.get()
        if mod_name == "":
            raise ValueError("empty mod cannot have a side")
        side: str = self.sv_side.get()
        self.callbacks["set_mod_side"](mod_name, side)

    def set_mod_version(self, event: Any) -> None:
        """
        Callback used when a mod version is being set by the user.

        :param event: the tkinter event passed by the tkinter in the Callback (unused)
        :return: None
        """
        mod_name: str = self.sv_mod_name.get()
        if mod_name == "":
            raise ValueError("empty mod cannot have a version")

        mod_version: str = self.sv_version.get()
        self.callbacks["set_mod_version"](mod_name, mod_version)

    def configure_widgets(self) -> None:
        """
        Method to configure the widgets.

        :return: None
        """
        self.label_mod_name.configure(width=self.width)
        self.label_version.configure(width=self.width)
        self.label_license.configure(width=self.width)
        self.label_side.configure(width=self.width)
        self.label_mod_name_value.configure(width=self.width)
        self.cb_version.configure(width=self.width)
        self.label_license_value.configure(width=self.width)
        self.cb_side.configure(width=self.width)

    def set_width(self, width: int) -> None:
        """
        Method to set the widgets' width.

        :param width: the new width
        :return: None
        """
        self.width = width
        self.configure_widgets()

    def get_width(self) -> int:
        """
        Getter for self.width.

        :return: the width in character sizes of the normalised widgets
        """
        return self.width

    def update_widget(self) -> None:
        """
        Method to update the widget and all its childs

        :return: None
        """
        self.hide()
        self.configure_widgets()
        self.show()

    def hide(self) -> None:
        """
        Method to hide the widget and all its childs
        :return None:
        """
        self.label_mod_name.grid_forget()
        self.label_mod_name_value.grid_forget()
        self.label_version.grid_forget()
        self.cb_version.grid_forget()
        self.label_license.grid_forget()
        self.label_license_value.grid_forget()
        self.label_side.grid_forget()
        self.cb_side.grid_forget()

        self.master.update_idletasks()

    def show(self) -> None:
        """
        Method used to display widgets and child widgets, as well as to configure the "responsiveness" of the widgets.

        :return: None
        """
        x: int = 0
        y: int = 0
        self.columnconfigure(0, weight=1, pad=self.ypadding)
        self.columnconfigure(1, weight=2, pad=self.ypadding)

        for i in range(0, 4):
            self.rowconfigure(i, weight=1, pad=self.xpadding)

        self.label_mod_name.grid(row=x, column=y)
        self.label_mod_name_value.grid(row=x, column=y + 1)
        self.label_version.grid(row=x + 1, column=y)
        self.cb_version.grid(row=x + 1, column=y + 1)
        self.label_license.grid(row=x + 2, column=y)
        self.label_license_value.grid(row=x + 2, column=y + 1)
        self.label_side.grid(row=x + 3, column=y)
        self.cb_side.grid(row=x + 3, column=y + 1)

    def populate_data(self, data: Any) -> None:
        """
        Method called by parent class to populate data in this class.

        :param data: the data to pass to this class
        :return: None
        """
        self.sv_mod_name.set(data["name"])
        self.cb_version["values"] = data["versions"]
        self.cb_side["values"] = [side.name for side in Side]
        self.cb_version.set(data["current_version"])
        self.sv_license.set(data["license"])
        self.cb_side.set(data["side"])


class GithubModList(LabelFrame):
    """
    Widget handling the list of github mods.
    """

    def __init__(
        self, master: Any, frame_name: str, callbacks: Dict[str, Any], width: Optional[int] = None, **kwargs: Any
    ):
        """
        Constructor of the GithubModList class.

        :param master: the parent widget
        :param frame_name: the name displayed in the framebox
        :param callbacks: a dict of callbacks passed to this instance
        :param kwargs: params to init the parent class
        """
        LabelFrame.__init__(self, master, text=frame_name, **kwargs)
        self.get_gtnh_callback: Callable[[], Coroutine[Any, Any, GTNHModpackManager]] = callbacks["get_gtnh"]
        self.get_github_mods_callback: Callable[[], Dict[str, str]] = callbacks["get_github_mods"]
        self.ypadding: int = 0  # todo: tune this
        self.xpadding: int = 0  # todo: tune this

        new_repo_text: str = "enter the new repo here"
        add_repo_text: str = "add repository"
        del_repo_text: str = "delete highlighted"
        self.width: int = (
            width if width is not None else max(len(new_repo_text), len(add_repo_text), len(del_repo_text))
        )

        self.sv_repo_name: StringVar = StringVar(self, value="")

        self.mod_info_callback: Callable[[Any], None] = callbacks["mod_info"]

        self.lb_mods: Listbox = Listbox(self, exportselection=False)
        self.lb_mods.bind("<<ListboxSelect>>", lambda event: asyncio.ensure_future(self.on_listbox_click(event)))

        self.label_entry: Label = Label(self, text=new_repo_text)
        self.entry: Entry = Entry(self, textvariable=self.sv_repo_name)

        self.btn_add: Button = Button(self, text=add_repo_text)
        self.btn_rem: Button = Button(self, text=del_repo_text)

        self.scrollbar: Scrollbar = Scrollbar(self)
        self.lb_mods.configure(yscrollcommand=self.scrollbar.set)
        self.scrollbar.configure(command=self.lb_mods.yview)

    def configure_widgets(self) -> None:
        """
        Method to configure the widgets.

        :return: None
        """
        self.label_entry.configure(width=self.width)
        self.entry.configure(width=self.width + 4)

        self.btn_add.configure(width=self.width)
        self.btn_rem.configure(width=self.width)

    def set_width(self, width: int) -> None:
        """
        Method to set the widgets' width.

        :param width: the new width
        :return: None
        """
        self.width = width
        self.configure_widgets()

    def get_width(self) -> int:
        """
        Getter for self.width.

        :return: the width in character sizes of the normalised widgets
        """
        return self.width

    def update_widget(self) -> None:
        """
        Method to update the widget and all its childs

        :return: None
        """
        self.hide()
        self.configure_widgets()
        self.show()

    def hide(self) -> None:
        """
        Method to hide the widget and all its childs
        :return None:
        """
        self.lb_mods.grid_forget()
        self.scrollbar.grid_forget()
        self.label_entry.grid_forget()
        self.entry.grid_forget()
        self.btn_add.grid_forget()
        self.btn_rem.grid_forget()

        self.master.update_idletasks()

    def show(self) -> None:
        """
        Method used to display widgets and child widgets, as well as to configure the "responsiveness" of the widgets.

        :return: None
        """
        x: int = 0
        y: int = 0
        self.columnconfigure(0, weight=1, pad=self.ypadding)
        self.columnconfigure(1, weight=1, pad=self.ypadding)

        for i in range(0, 5):
            self.rowconfigure(i, weight=1, pad=self.xpadding)

        self.lb_mods.grid(row=x, column=y, columnspan=2, sticky="WE")
        self.scrollbar.grid(row=x, column=y + 2, columnspan=2, sticky="NS")
        self.label_entry.grid(row=x + 1, column=y)
        self.entry.grid(row=x + 1, column=y + 1, columnspan=2)
        self.btn_add.grid(row=x + 2, column=y)
        self.btn_rem.grid(row=x + 2, column=y + 1, columnspan=2)

        self.master.update_idletasks()

    def populate_data(self, data: List[str]) -> None:
        """
        Method called by parent class to populate data in this class.

        :param data: the data to pass to this class
        :return: None
        """
        self.lb_mods.insert(END, *data)

    async def on_listbox_click(self, event: Any) -> None:
        """
        Callback used when the user clicks on the github mods' listbox.

        :param event: the tkinter event passed by the tkinter in the Callback (unused)
        :return: None
        """

        index: int = self.lb_mods.curselection()[0]
        gtnh: GTNHModpackManager = await self.get_gtnh_callback()
        mod_info: GTNHModInfo = gtnh.assets.get_github_mod(self.lb_mods.get(index))
        name: str = mod_info.name
        mod_versions: list[GTNHVersion] = mod_info.versions
        latest_version: Optional[GTNHVersion] = mod_info.get_latest_version()
        assert latest_version
        current_version: str = (
            self.get_github_mods_callback()[name]
            if name in self.get_github_mods_callback()
            else latest_version.version_tag
        )
        license: str = mod_info.license or "No license detected"
        side: str = mod_info.side

        data = {
            "name": name,
            "versions": [version.version_tag for version in mod_versions],
            "current_version": current_version,
            "license": license,
            "side": side,
        }

        self.mod_info_callback(data)


class GithubModFrame(LabelFrame):
    """
    Main frame widget for the github mods' management.
    """

    def __init__(
        self,
        master: Any,
        frame_name: str,
        callbacks: Dict[str, Any],
        **kwargs: Any,
    ):
        """
        Constructor of the GithubModFrame class.

        :param master: the parent widget
        :param frame_name: the name displayed in the framebox
        :param callbacks: a dict of callbacks passed to this instance
        :param kwargs: params to init the parent class
        """
        LabelFrame.__init__(self, master, text=frame_name, **kwargs)
        self.ypadding: int = 0  # todo: tune this
        self.xpadding: int = 0  # todo: tune this

        modpack_version_callbacks: Dict[str, Any] = {"set_modpack_version": callbacks["set_modpack_version"]}

        self.modpack_version_frame: ModpackVersionFrame = ModpackVersionFrame(
            self, frame_name="Modpack version", callbacks=modpack_version_callbacks
        )

        mod_info_callbacks: Dict[str, Any] = {
            "set_mod_version": callbacks["set_github_mod_version"],
            "set_mod_side": callbacks["set_github_mod_side"],
        }

        self.mod_info_frame: ModInfoFrame = ModInfoFrame(
            self, frame_name="github mod info", callbacks=mod_info_callbacks
        )

        github_mod_list_callbacks: Dict[str, Any] = {
            "mod_info": self.mod_info_frame.populate_data,
            "get_github_mods": callbacks["get_github_mods"],
            "get_gtnh": callbacks["get_gtnh"],
        }

        self.github_mod_list: GithubModList = GithubModList(
            self, frame_name="github mod list", callbacks=github_mod_list_callbacks
        )

        width: int = self.github_mod_list.get_width()
        self.mod_info_frame.set_width(width)
        self.modpack_version_frame.set_width(width)
        self.update_widget()

    def update_widget(self) -> None:
        """
        Method to update the widget and all its childs

        :return: None
        """
        self.hide()
        self.configure_widgets()
        self.show()

        self.modpack_version_frame.update_widget()
        self.mod_info_frame.update_widget()
        self.github_mod_list.update_widget()

    def hide(self) -> None:
        """
        Method to hide the widget and all its childs
        :return None:
        """
        self.modpack_version_frame.grid_forget()
        self.github_mod_list.grid_forget()  # ref widget
        self.mod_info_frame.grid_forget()

        self.modpack_version_frame.hide()
        self.github_mod_list.hide()
        self.mod_info_frame.hide()

        self.master.update_idletasks()

    def configure_widgets(self) -> None:
        """
        Method to configure the widgets.

        :return: None
        """
        pass

    def show(self) -> None:
        """
        Method used to display widgets and child widgets, as well as to configure the "responsiveness" of the widgets.

        :return: None
        """
        self.columnconfigure(0, weight=1, pad=self.ypadding)
        self.rowconfigure(0, weight=1, pad=self.xpadding)
        self.rowconfigure(1, weight=1, pad=self.xpadding)
        self.rowconfigure(2, weight=1, pad=self.xpadding)

        self.modpack_version_frame.grid(row=0, column=0, sticky="WE")
        self.github_mod_list.grid(row=1, column=0)  # ref widget
        self.mod_info_frame.grid(row=2, column=0, sticky="WE")
        self.master.update_idletasks()

        self.modpack_version_frame.show()
        self.github_mod_list.show()
        self.mod_info_frame.show()

    def populate_data(self, data: Dict[str, Any]) -> None:
        """
        Method called by parent class to populate data in this class.

        :param data: the data to pass to this class
        :return: None
        """
        self.github_mod_list.populate_data(data["github_mod_list"])
        self.modpack_version_frame.populate_data(data["modpack_version_frame"])


class ModpackVersionFrame(LabelFrame):
    """
    Frame to chose the gtnh modpack repo assets' version.
    """

    def __init__(
        self,
        master: Any,
        frame_name: str,
        callbacks: Dict[str, Callable[[str], None]],
        width: Optional[int] = None,
        **kwargs: Any,
    ):
        """
        Constructor of the ModpackVersionFrame.

        :param master: the parent widget
        :param frame_name: the name displayed in the framebox
        :param callbacks: a dict of callbacks passed to this instance
        :param kwargs: params to init the parent class
        """
        LabelFrame.__init__(self, master, text=frame_name, **kwargs)
        self.ypadding: int = 0  # todo: tune this
        self.xpadding: int = 0  # todo: tune this
        modpack_version_text: str = "Modpack version:"
        self.width: int = width if width is not None else len(modpack_version_text)
        self.label_modpack_version: Label = Label(self, text=modpack_version_text)
        self.sv_version: StringVar = StringVar(value="")
        self.cb_modpack_version: Combobox = Combobox(self, textvariable=self.sv_version, values=[])
        self.cb_modpack_version.bind(
            "<<ComboboxSelected>>", lambda event: callbacks["set_modpack_version"](self.sv_version.get())
        )

    def configure_widgets(self) -> None:
        """
        Method to configure the widgets.

        :return: None
        """
        self.label_modpack_version.configure(width=self.width)
        self.cb_modpack_version.configure(width=self.width)

    def set_width(self, width: int) -> None:
        """
        Method to set the widgets' width.

        :param width: the new width
        :return: None
        """
        self.width = width
        self.configure_widgets()

    def get_width(self) -> int:
        """
        Getter for self.width.

        :return: the width in character sizes of the normalised widgets
        """
        return self.width

    def update_widget(self) -> None:
        """
        Method to update the widget and all its childs

        :return: None
        """
        self.hide()
        self.configure_widgets()
        self.show()

    def hide(self) -> None:
        """
        Method to hide the widget and all its childs
        :return None:
        """
        self.label_modpack_version.grid_forget()
        self.cb_modpack_version.grid_forget()

        self.master.update_idletasks()

    def show(self) -> None:
        """
        Method used to display widgets and child widgets, as well as to configure the "responsiveness" of the widgets.

        :return: None
        """
        self.columnconfigure(0, weight=1, pad=self.ypadding)
        self.columnconfigure(1, weight=1, pad=self.ypadding)
        self.rowconfigure(0, weight=1, pad=self.xpadding)

        self.label_modpack_version.grid(row=0, column=0)
        self.cb_modpack_version.grid(row=0, column=1)

    def populate_data(self, data: Dict[str, Any]) -> None:
        """
        Method called by parent class to populate data in this class.

        :param data: the data to pass to this class
        :return: None
        """
        self.cb_modpack_version["values"] = data["combobox"]
        self.sv_version.set(data["stringvar"])


class ExternalModList(LabelFrame):
    """Widget handling the list of external mods."""

    def __init__(self, master: Any, frame_name: str, callbacks: Dict[str, Any], **kwargs: Any):
        """
        Constructor of the ExternalModList class.

        :param master: the parent widget
        :param frame_name: the name displayed in the framebox
        :param callbacks: a dict of callbacks passed to this instance
        :param kwargs: params to init the parent class
        """
        LabelFrame.__init__(self, master, text=frame_name, **kwargs)
        self.ypadding: int = 20  # todo: tune this
        self.xpadding: int = 0  # todo: tune this
        self.sv_repo_name: StringVar = StringVar(self, value="")

        self.lb_mods: Listbox = Listbox(self, exportselection=False)

        self.btn_add: Button = Button(self, text="add new")
        self.btn_rem: Button = Button(self, text="delete highlighted")

        self.scrollbar: Scrollbar = Scrollbar(self)
        self.lb_mods.configure(yscrollcommand=self.scrollbar.set)
        self.scrollbar.configure(command=self.lb_mods.yview)

    def show(self) -> None:
        """
        Method used to display widgets and child widgets, as well as to configure the "responsiveness" of the widgets.

        :return: None
        """
        x: int = 0
        y: int = 0

        self.columnconfigure(0, weight=1, pad=self.ypadding)
        self.rowconfigure(0, weight=1, pad=self.xpadding)
        self.rowconfigure(1, weight=1, pad=self.xpadding)
        self.rowconfigure(2, weight=1, pad=self.xpadding)

        self.lb_mods.grid(row=x, column=y, columnspan=2, sticky="WE")
        self.scrollbar.grid(row=x, column=y + 2, columnspan=2, sticky="NS")
        self.btn_add.grid(row=x + 1, column=y, sticky="WE")
        self.btn_rem.grid(row=x + 1, column=y + 1, sticky="WE")

    def populate_data(self, data: Any) -> None:
        """
        Method called by parent class to populate data in this class.

        :param data: the data to pass to this class
        :return: None
        """
        pass


class ExternalModFrame(LabelFrame):
    """Main frame widget for the external mods' management."""

    def __init__(self, master: Any, frame_name: str, callbacks: Dict[str, Any], **kwargs: Any):
        """
        Constructor of the ExternalModFrame class.

        :param master: the parent widget
        :param frame_name: the name displayed in the framebox
        :param callbacks: a dict of callbacks passed to this instance
        :param kwargs: params to init the parent class
        """
        self.ypadding: int = 20  # todo:tune this
        self.xpadding: int = 0  # todo: tune this
        LabelFrame.__init__(self, master, text=frame_name, **kwargs)

        mod_info_callbacks: Dict[str, Any] = {
            "set_mod_version": callbacks["set_external_mod_version"],
            "set_mod_side": callbacks["set_external_mod_side"],
        }
        self.mod_info_frame: ModInfoFrame = ModInfoFrame(
            self, frame_name="external mod info", callbacks=mod_info_callbacks
        )
        self.external_mod_list: ExternalModList = ExternalModList(self, frame_name="external mod list", callbacks={})

    def show(self) -> None:
        """
        Method used to display widgets and child widgets, as well as to configure the "responsiveness" of the widgets.

        :return: None
        """
        self.columnconfigure(0, weight=1, pad=self.ypadding)
        self.rowconfigure(0, weight=1, pad=self.xpadding)
        self.rowconfigure(1, weight=1, pad=self.xpadding)

        self.external_mod_list.grid(row=0, column=0, sticky="WE")
        self.mod_info_frame.grid(row=1, column=0, sticky="WE")

        self.master.update_idletasks()

        self.external_mod_list.show()
        self.mod_info_frame.show()

    def populate_data(self, data: Any) -> None:
        """
        Method called by parent class to populate data in this class.

        :param data: the data to pass to this class
        :return: None
        """
        pass


class ModPackFrame(LabelFrame):
    """Main frame for managing the releases."""

    def __init__(self, master: Any, frame_name: str, callbacks: Dict[str, Any], **kwargs: Any) -> None:
        """
        Constructor of the ModPackFrame class.

        :param master: the parent widget
        :param frame_name: the name displayed in the framebox
        :param callbacks: a dict of callbacks passed to this instance
        :param kwargs: params to init the parent class
        """
        LabelFrame.__init__(self, master, text=frame_name, **kwargs)
        self.xpadding: int = 0  # todo: tune this
        self.ypadding: int = 20  # todo: tune this
        self.generate_nightly_callback: Callable[[], None] = callbacks["generate_nightly"]
        action_callbacks: Dict[str, Any] = {
            "client_cf": lambda: None,
            "client_modrinth": lambda: None,
            "client_mmc": callbacks["client_mmc"],
            "client_technic": lambda: None,
            "server_cf": lambda: None,
            "server_modrinth": lambda: None,
            "server_mmc": callbacks["server_mmc"],
            "server_technic": lambda: None,
            "generate_all": lambda: None,
            "generate_nightly": self.update_nightly,
            "update_assets": callbacks["update_assets"],
        }
        self.action_frame: ActionFrame = ActionFrame(self, frame_name="availiable tasks", callbacks=action_callbacks)

        modpack_list_callbacks: Dict[str, Any] = {
            "load": callbacks["load"],
            "delete": callbacks["delete"],
            "add": callbacks["add"],
        }

        self.modpack_list: ModpackList = ModpackList(
            self, frame_name="Modpack Versions", callbacks=modpack_list_callbacks
        )

    def update_nightly(self) -> None:
        """
        Callback to generate/update the nightly builds.

        :return: None
        """
        self.generate_nightly_callback()
        data: List[str] = list(self.modpack_list.lb_modpack_versions.get(0, END))
        if "nightly" not in data:
            data.insert(0, "nightly")
            self.modpack_list.lb_modpack_versions.delete(0, END)
            self.modpack_list.lb_modpack_versions.insert(END, *data)

    def show(self) -> None:
        """
        Method used to display widgets and child widgets, as well as to configure the "responsiveness" of the widgets.

        :return: None
        """
        self.columnconfigure(0, weight=1, pad=self.ypadding)
        self.columnconfigure(1, weight=1, pad=self.ypadding)
        self.rowconfigure(0, weight=1, pad=self.xpadding)

        self.modpack_list.grid(row=0, column=0)
        self.action_frame.grid(row=0, column=1)

        self.master.update_idletasks()

        self.modpack_list.show()
        self.action_frame.show()

    def populate_data(self, data: Any) -> None:
        """
        Method called by parent class to populate data in this class.

        :param data: the data to pass to this class
        :return: None
        """
        self.modpack_list.populate_data(data)


class ModpackList(LabelFrame):
    """Widget ruling the list of modpack versions"""

    def __init__(self, master: Any, frame_name: str, callbacks: Dict[str, Any], **kwargs: Any) -> None:
        """
        Constructor of the ModpackList class.

        :param master: the parent widget
        :param frame_name: the name displayed in the framebox
        :param callbacks: a dict of callbacks passed to this instance
        :param kwargs: params to init the parent class
        """
        LabelFrame.__init__(self, master, text=frame_name, **kwargs)
        self.xpadding: int = 20  # todo: tune this
        self.ypadding: int = 0  # todo: tune this
        self.lb_modpack_versions: Listbox = Listbox(self, exportselection=False)
        self.lb_modpack_versions.bind("<<ListboxSelect>>", self.on_listbox_click)

        self.scrollbar: Scrollbar = Scrollbar(self)
        self.lb_modpack_versions.configure(yscrollcommand=self.scrollbar.set)
        self.scrollbar.configure(command=self.lb_modpack_versions.yview)

        self.btn_load: Button = Button(
            self, text="Load version", command=lambda: self.btn_load_command(callbacks["load"])
        )
        self.btn_del: Button = Button(
            self, text="Delete version", command=lambda: self.btn_del_command(callbacks["delete"])
        )
        self.sv_entry: StringVar = StringVar(self)
        self.entry: Entry = Entry(self, textvariable=self.sv_entry)
        self.btn_add: Button = Button(self, text="add/update", command=lambda: self.btn_add_command(callbacks["add"]))

    def show(self) -> None:
        """
        Method used to display widgets and child widgets, as well as to configure the "responsiveness" of the widgets.

        :return: None
        """
        self.columnconfigure(0, weight=1, pad=self.ypadding)
        self.columnconfigure(1, weight=1, pad=self.ypadding)
        self.rowconfigure(0, weight=1, pad=self.xpadding)
        self.rowconfigure(1, weight=1, pad=self.xpadding)
        self.rowconfigure(2, weight=1, pad=self.xpadding)

        self.lb_modpack_versions.grid(row=0, column=0, columnspan=2, sticky="WE")
        self.scrollbar.grid(row=0, column=2, columnspan=2, sticky="NS")
        self.btn_load.grid(row=1, column=0, sticky="WE")
        self.btn_del.grid(row=1, column=1, sticky="WE")
        self.entry.grid(row=2, column=0, sticky="WE")
        self.btn_add.grid(row=2, column=1, sticky="WE")

    def on_listbox_click(self, event: Any) -> None:
        """
        Callback used to fill the entry widget when a modpack version is selected.

        :param event: the tkinter event passed by the tkinter in the Callback (unused)
        :return: None
        """
        index: int = self.lb_modpack_versions.curselection()[0]
        self.sv_entry.set(self.lb_modpack_versions.get(index))

    def btn_load_command(self, callback: Optional[Callable[[str], None]] = None) -> None:
        """
        Callback for the button self.btn_load.

        :param callback: external call back to process added release name.
        :return: None
        """
        if self.lb_modpack_versions.curselection():
            index: int = self.lb_modpack_versions.curselection()[0]
            release_name = self.lb_modpack_versions.get(index)

            if callback is not None:
                callback(release_name)

    def btn_add_command(self, callback: Optional[Callable[[str], None]] = None) -> None:
        """
        Callback for the button self.btn_add.

        :param callback: external call back to process added release name.
        :return: None
        """
        release_name: str = self.sv_entry.get()
        if release_name != "":
            if callback is not None:
                callback(release_name)

        if release_name not in self.lb_modpack_versions.get(0, END):
            self.lb_modpack_versions.insert(END, release_name)

    def btn_del_command(self, callback: Optional[Callable[[str], None]] = None) -> None:
        """
        Callback for the button self.btn_del.

        :param callback: external call back to process deleted release name.
        :return: None
        """
        sel: Tuple[int] = self.lb_modpack_versions.curselection()
        if sel:
            index: int = sel[0]
            release_name: str = self.lb_modpack_versions.get(index)
            self.lb_modpack_versions.delete(index)
            if callback is not None:
                callback(release_name)

    def populate_data(self, data: List[GTNHRelease]) -> None:
        """
        Method called by parent class to populate data in this class.

        :param data: the data to pass to this class
        :return: None
        """
        for release in data:
            self.lb_modpack_versions.insert(END, release.version)


class ActionFrame(LabelFrame):
    """
    Widget managing all the buttons related to pack assembling.
    """

    def __init__(self, master: Any, frame_name: str, callbacks: Dict[str, Any], **kwargs: Any):
        """
        Constructor of the ActionFrame class.

        :param master: the parent widget
        :param frame_name: the name displayed in the framebox
        :param callbacks: a dict of callbacks passed to this instance
        :param kwargs: params to init the parent class
        """
        LabelFrame.__init__(self, master, text=frame_name, **kwargs)
        self.xpadding: int = 0  # todo: tune this
        self.ypadding: int = 20  # todo: tune this
        client_archive_text: str = "client archive"
        server_archive_text: str = "server archive"
        generate_all_text: str = "Generate all archives"
        update_nightly_text: str = "Update nightly"
        update_assets_text: str = "Update assets"
        button_size: int = max(
            len(client_archive_text),
            len(server_archive_text),
            len(generate_all_text),
            len(update_nightly_text),
            len(update_assets_text),
        )

        self.label_cf: Label = Label(self, text="CurseForge")
        self.btn_client_cf: Button = Button(
            self, text=client_archive_text, command=callbacks["client_cf"], width=button_size
        )
        self.btn_server_cf: Button = Button(
            self, text=server_archive_text, command=callbacks["server_cf"], width=button_size
        )
        self.label_technic: Label = Label(self, text="Technic")
        self.btn_client_technic: Button = Button(
            self, text=client_archive_text, command=callbacks["client_technic"], width=button_size
        )
        self.btn_server_technic: Button = Button(
            self, text=server_archive_text, command=callbacks["server_technic"], width=button_size
        )
        self.label_mmc: Label = Label(self, text="MultiMC")
        self.btn_client_mmc: Button = Button(
            self, text=client_archive_text, command=callbacks["client_mmc"], width=button_size
        )
        self.btn_server_mmc: Button = Button(
            self, text=server_archive_text, command=callbacks["server_mmc"], width=button_size
        )
        self.label_modrinth: Label = Label(self, text="Modrinth")
        self.btn_client_modrinth: Button = Button(
            self, text=client_archive_text, command=callbacks["client_modrinth"], width=button_size
        )
        self.btn_server_modrinth: Button = Button(
            self, text=server_archive_text, command=callbacks["server_modrinth"], width=button_size
        )
        self.btn_generate_all: Button = Button(
            self, text="generate all", command=callbacks["generate_all"], width=button_size
        )
        self.btn_update_nightly: Button = Button(
            self, text="update nightly", command=callbacks["generate_nightly"], width=button_size
        )
        self.btn_update_assets: Button = Button(
            self, text="update assets", command=callbacks["update_assets"], width=button_size
        )

        progress_bar_length: int = 500

        self.pb_global: Progressbar = Progressbar(
            self, orient="horizontal", mode="determinate", length=progress_bar_length
        )
        self.sv_pb_global: StringVar = StringVar(self, value="current task: Coding DreamAssemblerXXL")
        self.label_pb_global: Label = Label(self, textvariable=self.sv_pb_global)

        self.pb_current_task: Progressbar = Progressbar(
            self, orient="horizontal", mode="determinate", length=progress_bar_length
        )
        self.sv_pb_current_task: StringVar = StringVar(self, value="doing stuff")
        self.label_pb_current_task: Label = Label(self, textvariable=self.sv_pb_current_task)

    def populate_data(self, data: Any) -> None:
        """
        Method called by parent class to populate data in this class.

        :param data: the data to pass to this class
        :return: None
        """
        pass

    def update_current_task_progress_bar(self, progress: float, data: str) -> None:
        """
        Callback to update the task bar showing the current task's progress.

        :param progress: value to add to the progress
        :param data: what is currently done
        :return: None
        """
        self.pb_current_task["value"] += progress
        self.sv_pb_current_task.set(data)
        self.update_idletasks()

    def show(self) -> None:
        """
        Method used to display widgets and child widgets, as well as to configure the "responsiveness" of the widgets.

        :return: None
        """
        x: int = 0
        y: int = 0
        for i in range(8):
            self.rowconfigure(i, weight=1, pad=self.xpadding)

        for i in range(4):
            self.columnconfigure(i, weight=1, pad=self.ypadding)

        self.label_pb_global.grid(row=x, column=y, columnspan=4)
        self.pb_global.grid(row=x + 1, column=y, columnspan=4)
        self.label_pb_current_task.grid(row=x + 2, column=y, columnspan=4)
        self.pb_current_task.grid(row=x + 3, column=y, columnspan=4)
        self.label_cf.grid(row=x + 4, column=y)
        self.btn_client_cf.grid(row=x + 5, column=y, sticky="WE")
        self.btn_server_cf.grid(row=x + 6, column=y, sticky="WE")
        self.label_technic.grid(row=x + 4, column=y + 1)
        self.btn_client_technic.grid(row=x + 5, column=y + 1, sticky="WE")
        self.btn_server_technic.grid(row=x + 6, column=y + 1, sticky="WE")
        self.label_modrinth.grid(row=x + 4, column=y + 2)
        self.btn_client_modrinth.grid(row=x + 5, column=y + 2, sticky="WE")
        self.btn_server_modrinth.grid(row=x + 6, column=y + 2, sticky="WE")
        self.label_mmc.grid(row=x + 4, column=y + 3)
        self.btn_client_mmc.grid(row=x + 5, column=y + 3, sticky="WE")
        self.btn_server_mmc.grid(row=x + 6, column=y + 3, sticky="WE")
        self.btn_generate_all.grid(row=x + 7, column=y + 1, columnspan=2)
        self.btn_update_nightly.grid(row=x + 7, column=y, columnspan=2)
        self.btn_update_assets.grid(row=x + 7, column=y + 2, columnspan=2)


class ExclusionFrame(LabelFrame):
    """Widget managing an exclusion list."""

    def __init__(self, master: Any, frame_name: str, callbacks: Dict[str, Any], **kwargs: Any) -> None:
        """
        Constructor of the ExclusionFrame class.

        :param master: the parent widget
        :param frame_name: the name displayed in the framebox
        :param callbacks: a dict of callbacks passed to this instance
        :param kwargs: params to init the parent class
        """
        LabelFrame.__init__(self, master, text=frame_name, **kwargs)
        self.xpadding: int = 0  # todo: tune this
        self.ypadding: int = 20  # todo: tune this
        self.listbox: Listbox = Listbox(self, exportselection=False)
        self.sv_entry: StringVar = StringVar(value="")
        self.entry: Entry = Entry(self, textvariable=self.sv_entry)
        self.btn_add: Button = Button(self, text="add new exclusion", command=self.add)
        self.btn_del: Button = Button(self, text="remove highlighted", command=self.delete)
        self.add_callback: Callable[[str], None] = callbacks["add"]
        self.del_callback: Callable[[str], None] = callbacks["del"]

        self.scrollbar: Scrollbar = Scrollbar(self)
        self.listbox.configure(yscrollcommand=self.scrollbar.set)
        self.scrollbar.configure(command=self.listbox.yview)

    def add_to_list_sorted(self, elem: str) -> None:
        """
        Method used to insert an element into the listbox and sort the elements at the same time.

        :param elem: the element to add in the listbox
        :return: None
        """
        exclusions: List[str] = list(self.listbox.get(0, END))
        if elem in exclusions:
            return

        exclusions.append(elem)
        self.listbox.delete(0, END)
        self.listbox.insert(0, *(sorted(exclusions)))

    def add(self) -> None:
        """
        Callback of self.btn_add.

        :return: None
        """
        exclusion: str = self.sv_entry.get()
        if exclusion == "":
            return

        self.add_to_list_sorted(exclusion)
        self.add_callback(exclusion)

    def delete(self) -> None:
        """
        Callback of self.btn_del.

        :return: None
        """
        position: Tuple[int] = self.listbox.curselection()
        if position:
            exclusion: str = self.listbox.get(position[0])
            self.listbox.delete(position)
            self.del_callback(exclusion)

    def show(self) -> None:
        """
        Method used to display widgets and child widgets, as well as to configure the "responsiveness" of the widgets.

        :return: None
        """
        x: int = 0
        y: int = 0

        self.rowconfigure(0, weight=1, pad=self.xpadding)
        self.rowconfigure(1, weight=1, pad=self.xpadding)
        self.rowconfigure(2, weight=1, pad=self.xpadding)
        self.columnconfigure(0, weight=1, pad=self.ypadding)
        self.columnconfigure(1, weight=1, pad=self.ypadding)

        self.listbox.grid(row=x, column=y, columnspan=2, sticky="WENS")
        self.scrollbar.grid(row=x, column=y + 2, columnspan=2, sticky="NS")
        self.entry.grid(row=x + 1, column=y, columnspan=2, sticky="WE")
        self.btn_add.grid(row=x + 2, column=y, sticky="WE")
        self.btn_del.grid(row=x + 2, column=y + 1, sticky="WE")

    def populate_data(self, data: Dict[str, Any]) -> None:
        """
        Method called by parent class to populate data in this class.

        :param data: the data to pass to this class
        :return: None
        """
        self.listbox.insert(END, *data["exclusions"])


if __name__ == "__main__":
    asyncio.run(App().exec())
