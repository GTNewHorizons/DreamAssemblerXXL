import asyncio
import tkinter as tk
from tkinter import ttk
from tkinter.messagebox import showerror, showinfo
from tkinter.ttk import Combobox
from typing import Any, Callable, Coroutine, Dict, List, Optional, Tuple, Union

import httpx

from gtnh.defs import Side
from gtnh.models.gtnh_release import GTNHRelease
from gtnh.models.gtnh_version import GTNHVersion
from gtnh.models.mod_info import GTNHModInfo
from gtnh.modpack_manager import GTNHModpackManager

ASYNC_SLEEP = 0.05


class App:
    """wrapper class to start the GUI"""

    async def exec(self) -> None:
        """
        Coroutine used to run all the stuff
        """
        self.instance = Window(asyncio.get_event_loop())
        self.instance.modpack_list_frame.action_frame.pb_current_task["value"] = 69
        await self.instance.run()


class Window(tk.Tk):
    """Main class for the GUI"""

    def __init__(self, loop: asyncio.AbstractEventLoop):
        tk.Tk.__init__(self)
        self.loop: asyncio.AbstractEventLoop = loop
        self._client: Optional[httpx.AsyncClient] = None
        self._modpack_manager: Optional[GTNHModpackManager] = None
        self.github_mods: Dict[str, str] = {}
        self.init: bool = False
        self.protocol("WM_DELETE_WINDOW", lambda: asyncio.ensure_future(self.close_app()))

        # frame for the github mods
        self.github_mod_frame = GithubModFrame(
            self, frame_name="github mods data", get_gtnh_callback=self._get_modpack_manager, get_github_mods_callback=self.get_github_mods
        )

        # frame for the external mods
        self.external_mod_frame = ExternalModFrame(self, frame_name="external mod data")

        # frame for the modpack handling
        modpack_list_callbacks = {
            "load": lambda release_name: asyncio.ensure_future(self.load_gtnh_version(release_name)),
            "add": lambda release_name: asyncio.ensure_future(self.add_gtnh_version(release_name)),
            "delete": lambda release_name: asyncio.ensure_future(self.delete_gtnh_version(release_name)),
            "update_assets": lambda: asyncio.ensure_future(self.update_assets()),
            "generate_nightly": lambda: asyncio.ensure_future(self.generate_nightly()),
        }

        self.modpack_list_frame = ModPackFrame(self, frame_name="modpack release actions", callbacks=modpack_list_callbacks)

        exclusion_client_callbacks = {"add": lambda: None, "del": lambda: None}

        # frame for the client file exclusions
        self.exclusion_frame_client = ExclusionFrame(self, "client exclusions", exclusion_client_callbacks)

        exclusion_server_callbacks = {"add": lambda: None, "del": lambda: None}

        # frame for the server side exclusions
        self.exclusion_frame_server = ExclusionFrame(self, "server exclusions", exclusion_server_callbacks)

    async def get_repos(self) -> List[str]:
        """Method to grab all the repo names known"""
        m: GTNHModpackManager = await self._get_modpack_manager()
        return [x.name for x in m.assets.github_mods]

    def get_github_mods(self) -> Dict[str, str]:
        """getter for self.github_mods"""
        return self.github_mods

    async def _get_client(self) -> httpx.AsyncClient:
        """internal method returning the httpx client instance, creating it if it doesn't exist"""
        if self._client is None:
            self._client = httpx.AsyncClient(http2=True)
        return self._client

    async def _get_modpack_manager(self) -> GTNHModpackManager:
        """internal method returning the modpack manager instance, creating it if it doesn't exist"""
        if self._modpack_manager is None:
            self._modpack_manager = GTNHModpackManager(await self._get_client())
        return self._modpack_manager

    async def update_assets(self) -> None:
        """method to update all the assets"""
        gtnh: GTNHModpackManager = await self._get_modpack_manager()
        await gtnh.update_all()
        showinfo("assets updated successfully!", "all the assets have been updated correctly!")

    async def generate_nightly(self) -> None:
        """method to update the nightly build"""
        gtnh: GTNHModpackManager = await self._get_modpack_manager()
        release: GTNHRelease = await gtnh.generate_release("nightly", update_available=True)
        gtnh.add_release(release, update=True)
        gtnh.save_modpack()
        showinfo("updated the nightly release metadata", "The nightly release metadata had been updated!")

    async def get_releases(self) -> List[GTNHRelease]:
        """
        Method used to return a list of known releases with valid metadata.
        The list is sorted in ascending order (from oldest to the latest)
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
        """Method to load a version in memory"""

        if isinstance(release, str):
            gtnh: GTNHModpackManager = await self._get_modpack_manager()
            release_object = gtnh.get_release(release)
            if release_object is not None:
                self.github_mods = release_object.github_mods
            else:
                showerror("incorrect version detected", f"modpack version {release} doesn't exist")
                return

        else:
            release_object = release
            self.github_mods = release.github_mods
        if not init:

            showinfo("version loaded successfully!", f"modpack version {release_object.version} loaded successfully!")

    async def add_gtnh_version(self, release_name: str) -> None:
        """method to generate a new version"""

        gtnh: GTNHModpackManager = await self._get_modpack_manager()
        release = await gtnh.generate_release(release_name, update_available=False)  # we don't want to update assets this way
        if gtnh.add_release(release, update=True):
            gtnh.save_modpack()
            showinfo("release successfully generated", f"modpack version {release_name} successfully generated!")

    async def delete_gtnh_version(self, release_name: str) -> None:
        """method used to delete a version matching the provided release name"""
        gtnh: GTNHModpackManager = await self._get_modpack_manager()
        gtnh.delete_release(release_name)
        showinfo("release successfully deleted", f"modpack version {release_name} successfully deleted!")

    def show(self) -> None:
        """method used to show the widget elements and its child widgets"""

        # auto resize config
        for i in range(3):
            self.columnconfigure(i, weight=1)
            self.rowconfigure(i, weight=1)

        # display child widgets
        self.github_mod_frame.grid(row=0, column=0, sticky="WE")
        self.external_mod_frame.grid(row=2, column=0, sticky="WE")
        self.modpack_list_frame.grid(row=0, column=1, columnspan=2, sticky="WENS")
        self.exclusion_frame_client.grid(row=1, column=1, sticky="WENS", rowspan=3)
        self.exclusion_frame_server.grid(row=1, column=2, sticky="WENS", rowspan=2)

        # child widget's inner display
        self.github_mod_frame.show()
        self.external_mod_frame.show()
        self.modpack_list_frame.show()
        self.exclusion_frame_client.show()
        self.exclusion_frame_server.show()

    async def run(self) -> None:
        """
        async entrypoint to trigger the mainloop
        """
        self.show()
        await self.update_widget()

    async def update_widget(self) -> None:
        """
        Method handling the loop
        """
        if not self.init:
            self.init = True
            # load last gtnh version if there is any:
            releases: List[GTNHRelease] = await self.get_releases()
            if len(releases) > 0:
                await self.load_gtnh_version(releases[-1], init=True)

            self.github_mod_frame.populate_data(await self.get_repos())
            self.modpack_list_frame.populate_data(await self.get_releases())

        while True:
            self.update()
            await asyncio.sleep(ASYNC_SLEEP)

    async def close_app(self) -> None:
        """Method used whenever the app is closed"""
        if self._client is not None:
            await self._client.aclose()
        self.destroy()


class ModInfoFrame(tk.LabelFrame):
    """
    Widget used to display info about a mod passed to it
    """

    def __init__(self, master: Any, frame_name: str, **kwargs: Any):
        tk.LabelFrame.__init__(self, master, text=frame_name, **kwargs)
        self.ypadding = 5  # todo: tune this
        self.xpadding = 0  # todo: tune this
        self.label_mod_name = tk.Label(self, text="mod name:")
        self.label_version = tk.Label(self, text="mod version:")
        self.label_license = tk.Label(self, text="mod license:")
        self.label_side = tk.Label(self, text="mod side:")

        self.sv_mod_name = tk.StringVar(self, value="")
        self.sv_version = tk.StringVar(self, value="")
        self.sv_license = tk.StringVar(self, value="")
        self.sv_side = tk.StringVar(self, value="")

        self.label_mod_name_value = tk.Label(self, textvariable=self.sv_mod_name)
        self.cb_version = Combobox(self, textvariable=self.sv_version, values=[])
        self.label_license_value = tk.Label(self, textvariable=self.sv_license)
        self.cb_side = Combobox(self, textvariable=self.sv_side, values=[side.value for side in Side])

    def show(self) -> None:
        """method used to show the widget's elements and its child widgets"""
        x, y = 0, 0
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
        """method used to populate data"""
        self.sv_mod_name.set(data["name"])
        self.cb_version["values"] = data["versions"]
        self.cb_version.set(data["current_version"])
        self.sv_license.set(data["license"])
        self.cb_side.set(data["side"])


class GithubModList(tk.LabelFrame):
    """
    Widget used to rule the addition/deletion of a mod
    """

    def __init__(
        self,
        master: Any,
        frame_name: str,
        mod_info_callback: Callable[[Any], None],
        get_gtnh_callback: Callable[[], Coroutine[Any, Any, GTNHModpackManager]],
        get_github_mods_callback: Callable[[], Dict[str, str]],
        **kwargs: Any,
    ):
        tk.LabelFrame.__init__(self, master, text=frame_name, **kwargs)
        self.get_gtnh_callback = get_gtnh_callback
        self.get_github_mods_callback = get_github_mods_callback
        self.ypadding = 20  # todo: tune this
        self.xpadding = 0  # todo: tune this

        self.sv_repo_name = tk.StringVar(self, value="")

        self.mod_info_callback = mod_info_callback

        self.lb_mods = tk.Listbox(self, exportselection=False)
        self.lb_mods.bind("<<ListboxSelect>>", lambda event: asyncio.ensure_future(self.on_listbox_click(event)))

        self.label_entry = tk.Label(self, text="enter the new repo here")
        self.entry = tk.Entry(self, textvariable=self.sv_repo_name)

        self.btn_add = tk.Button(self, text="add repository")
        self.btn_rem = tk.Button(self, text="delete highlighted")

    def show(self) -> None:
        """method used to show the widget's elements and its child widgets"""
        x, y = 0, 0
        self.columnconfigure(0, weight=1, pad=self.ypadding)
        self.columnconfigure(1, weight=1, pad=self.ypadding)

        for i in range(0, 5):
            self.rowconfigure(i, weight=1, pad=self.xpadding)

        self.lb_mods.grid(row=x, column=y, columnspan=2, sticky="WE")
        self.label_entry.grid(row=x + 1, column=y, sticky="WE")
        self.entry.grid(row=x + 1, column=y + 1, sticky="WE")
        self.btn_add.grid(row=x + 2, column=y, sticky="WE")
        self.btn_rem.grid(row=x + 2, column=y + 1, sticky="WE")

        self.master.update_idletasks()

    def populate_data(self, data: List[str]) -> None:
        """method used to populate the widget from parent"""
        for repo_name in sorted(data):
            self.lb_mods.insert(tk.END, repo_name)

    async def on_listbox_click(self, event: Any) -> None:

        index = self.lb_mods.curselection()[0]
        gtnh: GTNHModpackManager = await self.get_gtnh_callback()
        mod_info: GTNHModInfo = gtnh.assets.get_github_mod(self.lb_mods.get(index))
        name: str = mod_info.name
        mod_versions: list[GTNHVersion] = mod_info.versions

        current_version = self.get_github_mods_callback()[name] if name in self.get_github_mods_callback() else mod_info.get_latest_version()
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


class GithubModFrame(tk.LabelFrame):
    """
    Widget ruling all the github related mods
    """

    def __init__(
        self,
        master: Any,
        frame_name: str,
        get_gtnh_callback: Callable[[], Coroutine[Any, Any, GTNHModpackManager]],
        get_github_mods_callback: Callable[[], Dict[str, str]],
        **kwargs: Any,
    ):
        tk.LabelFrame.__init__(self, master, text=frame_name, **kwargs)
        self.ypadding = 100  # todo: tune this
        self.xpadding = 0  # todo: tune this
        self.mod_info_frame = ModInfoFrame(self, frame_name="github mod info")
        self.github_mod_list = GithubModList(
            self,
            frame_name="github mod list",
            mod_info_callback=self.mod_info_frame.populate_data,
            get_gtnh_callback=get_gtnh_callback,
            get_github_mods_callback=get_github_mods_callback,
        )

    def show(self) -> None:
        """method used to show the widget's elements and its child widgets"""
        self.columnconfigure(0, weight=1, pad=self.ypadding)
        self.rowconfigure(0, weight=1, pad=self.xpadding)
        self.rowconfigure(1, weight=1, pad=self.xpadding)

        self.github_mod_list.grid(row=0, column=0, sticky="WE")
        self.mod_info_frame.grid(row=1, column=0, sticky="WE")
        self.master.update_idletasks()

        self.github_mod_list.show()
        self.mod_info_frame.show()

    def populate_data(self, data: List[str]) -> None:
        """method used to populate the widget from parent"""
        self.github_mod_list.populate_data(data)


class ExternalModList(tk.LabelFrame):
    """Widget used to rule the list for the external mods"""

    def __init__(self, master: Any, frame_name: str, **kwargs: Any):
        tk.LabelFrame.__init__(self, master, text=frame_name, **kwargs)
        self.ypadding, self.xpadding = 20, 0  # todo: tune this
        self.sv_repo_name = tk.StringVar(self, value="")

        self.lb_mods = tk.Listbox(self, exportselection=False)

        self.btn_add = tk.Button(self, text="add new")
        self.btn_rem = tk.Button(self, text="delete highlighted")

    def show(self) -> None:
        """method used to show the widget's elements and its child widgets"""
        x, y = 0, 0

        self.columnconfigure(0, weight=1, pad=self.ypadding)
        self.rowconfigure(0, weight=1, pad=self.xpadding)
        self.rowconfigure(1, weight=1, pad=self.xpadding)
        self.rowconfigure(2, weight=1, pad=self.xpadding)

        self.lb_mods.grid(row=x, column=y, columnspan=2, sticky="WE")
        self.btn_add.grid(row=x + 1, column=y, sticky="WE")
        self.btn_rem.grid(row=x + 1, column=y + 1, sticky="WE")

    def populate_data(self, data: Any) -> None:
        """method used to populate the widget from parent"""
        pass


class ExternalModFrame(tk.LabelFrame):
    """Widget ruling the external mods"""

    def __init__(self, master: Any, frame_name: str, **kwargs: Any):
        self.ypadding = 20  # todo:tune this
        self.xpadding = 0  # todo: tune this
        tk.LabelFrame.__init__(self, master, text=frame_name, **kwargs)
        self.mod_info_frame = ModInfoFrame(self, frame_name="external mod info")
        self.external_mod_list = ExternalModList(self, frame_name="external mod list")

    def show(self) -> None:
        """method used to show the widget's elements and its child widgets"""
        self.columnconfigure(0, weight=1, pad=self.ypadding)
        self.rowconfigure(0, weight=1, pad=self.xpadding)
        self.rowconfigure(1, weight=1, pad=self.xpadding)

        self.external_mod_list.grid(row=0, column=0, sticky="WE")
        self.mod_info_frame.grid(row=1, column=0, sticky="WE")

        self.master.update_idletasks()

        self.external_mod_list.show()
        self.mod_info_frame.show()

    def populate_data(self, data: Any) -> None:
        """method used to populate the widget from parent"""
        pass


class ModPackFrame(tk.LabelFrame):
    """Widget ruling all the packaging stuff"""

    def __init__(self, master: Any, frame_name: str, callbacks: Dict[str, Any], **kwargs: Any) -> None:
        tk.LabelFrame.__init__(self, master, text=frame_name, **kwargs)
        self.xpadding, self.ypadding = 0, 20  # todo: tune this
        self.generate_nightly_callback = callbacks["generate_nightly"]
        action_callbacks = {
            "client_cf": lambda: None,
            "client_modrinth": lambda: None,
            "client_mmc": lambda: None,
            "client_technic": lambda: None,
            "server_cf": lambda: None,
            "server_modrinth": lambda: None,
            "server_mmc": lambda: None,
            "server_technic": lambda: None,
            "generate_all": lambda: None,
            "generate_nightly": self.update_nightly,
            "update_assets": callbacks["update_assets"],
        }
        self.action_frame = ActionFrame(self, frame_name="availiable tasks", callbacks=action_callbacks)

        modpack_list_callbacks = {"load": callbacks["load"], "delete": callbacks["delete"], "add": callbacks["add"]}
        self.modpack_list = ModpackList(self, frame_name="Modpack Versions", callbacks=modpack_list_callbacks)

    def update_nightly(self) -> None:
        """method used to trigger different actions in both ActionFrame and ModpackList"""
        self.generate_nightly_callback()
        data: List[str] = list(self.modpack_list.lb_modpack_versions.get(0, tk.END))
        if "nightly" not in data:
            data.insert(0, "nightly")
            self.modpack_list.lb_modpack_versions.delete(0, tk.END)
            self.modpack_list.lb_modpack_versions.insert(tk.END, *data)

    def show(self) -> None:
        """method used to show the widget's elements and its child widgets"""
        self.columnconfigure(0, weight=1, pad=self.ypadding)
        self.columnconfigure(1, weight=1, pad=self.ypadding)
        self.rowconfigure(0, weight=1, pad=self.xpadding)

        self.modpack_list.grid(row=0, column=0)
        self.action_frame.grid(row=0, column=1)

        self.master.update_idletasks()

        self.modpack_list.show()
        self.action_frame.show()

    def populate_data(self, data: Any) -> None:
        """method used to populate the widget from parent"""
        self.modpack_list.populate_data(data)


class ModpackList(tk.LabelFrame):
    """Widget ruling the list of modpack versions"""

    def __init__(self, master: Any, frame_name: str, callbacks: Dict[str, Any], **kwargs: Any) -> None:
        tk.LabelFrame.__init__(self, master, text=frame_name, **kwargs)
        self.xpadding, self.ypadding = 0, 20  # todo: tune this
        self.lb_modpack_versions = tk.Listbox(self, exportselection=False)
        self.lb_modpack_versions.bind("<<ListboxSelect>>", self.on_listbox_click)

        self.btn_load = tk.Button(self, text="Load version", command=lambda: self.btn_load_command(callbacks["load"]))
        self.btn_del = tk.Button(self, text="Delete version", command=lambda: self.btn_del_command(callbacks["delete"]))
        self.sv_entry = tk.StringVar(self)
        self.entry = tk.Entry(self, textvariable=self.sv_entry)
        self.btn_add = tk.Button(self, text="add/update", command=lambda: self.btn_add_command(callbacks["add"]))

    def show(self) -> None:
        """method used to show the widget's elements and its child widgets"""
        self.columnconfigure(0, weight=1, pad=self.ypadding)
        self.columnconfigure(1, weight=1, pad=self.ypadding)
        self.rowconfigure(0, weight=1, pad=self.xpadding)
        self.rowconfigure(1, weight=1, pad=self.xpadding)
        self.rowconfigure(2, weight=1, pad=self.xpadding)

        self.lb_modpack_versions.grid(row=0, column=0, columnspan=2, sticky="WE")
        self.btn_load.grid(row=1, column=0, sticky="WE")
        self.btn_del.grid(row=1, column=1, sticky="WE")
        self.entry.grid(row=2, column=0, sticky="WE")
        self.btn_add.grid(row=2, column=1, sticky="WE")

    def on_listbox_click(self, event: Any) -> None:
        """Method used to fill the entry widget when a modpack version is selected"""
        index: int = self.lb_modpack_versions.curselection()[0]
        self.sv_entry.set(self.lb_modpack_versions.get(index))

    def btn_load_command(self, callback: Optional[Callable[[str], None]] = None) -> None:
        """method used when the loading button gets clicked on"""
        if self.lb_modpack_versions.curselection():
            index: int = self.lb_modpack_versions.curselection()[0]
            release_name = self.lb_modpack_versions.get(index)

            if callback is not None:
                callback(release_name)

    def btn_add_command(self, callback: Optional[Callable[[str], None]] = None) -> None:
        """method used when the add/update button gets clicked on"""
        release_name: str = self.sv_entry.get()
        if release_name != "":
            if callback is not None:
                callback(release_name)

            self.lb_modpack_versions.insert(tk.END, release_name)

    def btn_del_command(self, callback: Optional[Callable[[str], None]] = None) -> None:
        sel: Tuple[int] = self.lb_modpack_versions.curselection()
        if sel:
            index: int = sel[0]
            release_name: str = self.lb_modpack_versions.get(index)
            self.lb_modpack_versions.delete(index)
            if callback is not None:
                callback(release_name)

    def populate_data(self, data: List[GTNHRelease]) -> None:
        """method used to populate the widget from parent"""
        for release in data:
            self.lb_modpack_versions.insert(tk.END, release.version)


class ActionFrame(tk.LabelFrame):
    """
    Widget ruling all the packaging buttons of the section
    """

    def __init__(self, master: Any, frame_name: str, callbacks: Dict[str, Any], **kwargs: Any):
        tk.LabelFrame.__init__(self, master, text=frame_name, **kwargs)
        self.xpadding, self.ypadding = 0, 20  # todo: tune this
        self.label_cf = tk.Label(self, text="CurseForge")
        self.btn_client_cf = tk.Button(self, text="client archive", command=callbacks["client_cf"])
        self.btn_server_cf = tk.Button(self, text="server archive", command=callbacks["server_cf"])
        self.label_technic = tk.Label(self, text="Technic")
        self.btn_client_technic = tk.Button(self, text="client archive", command=callbacks["client_technic"])
        self.btn_server_technic = tk.Button(self, text="server archive", command=callbacks["server_technic"])
        self.label_mmc = tk.Label(self, text="MultiMC")
        self.btn_client_mmc = tk.Button(self, text="client archive", command=callbacks["client_mmc"])
        self.btn_server_mmc = tk.Button(self, text="server archive", command=callbacks["server_mmc"])
        self.label_modrinth = tk.Label(self, text="Modrinth")
        self.btn_client_modrinth = tk.Button(self, text="client archive", command=callbacks["client_modrinth"])
        self.btn_server_modrinth = tk.Button(self, text="server archive", command=callbacks["server_modrinth"])
        self.btn_generate_all = tk.Button(self, text="generate all", command=callbacks["generate_all"])
        self.btn_update_nightly = tk.Button(self, text="update nightly", command=callbacks["generate_nightly"])
        self.btn_update_assets = tk.Button(self, text="update assets", command=callbacks["update_assets"])

        progress_bar_length = 500
        self.pb_global = ttk.Progressbar(self, orient="horizontal", mode="determinate", length=progress_bar_length)
        self.sv_pb_global = tk.StringVar(self, value="current task: Coding DreamAssemblerXXL")
        self.label_pb_global = tk.Label(self, textvariable=self.sv_pb_global)

        self.pb_current_task = ttk.Progressbar(self, orient="horizontal", mode="determinate", length=progress_bar_length)
        self.sv_pb_current_task = tk.StringVar(self, value="doing stuff")
        self.label_pb_current_task = tk.Label(self, textvariable=self.sv_pb_current_task)

    def populate_data(self, data: Any) -> None:
        """method used to populate the widget from parent"""
        pass

    def show(self) -> None:
        """method used to show the widget's elements and its child widgets"""
        x, y = 0, 0
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


class ExclusionFrame(tk.LabelFrame):
    """Widget ruling the exclusion file list"""

    def __init__(self, master: Any, frame_name: str, callbacks: Dict[str, Callable[[], None]], **kwargs: Any) -> None:
        tk.LabelFrame.__init__(self, master, text=frame_name, **kwargs)
        self.xpadding, self.ypadding = 0, 20  # todo: tune this
        self.listbox = tk.Listbox(self, exportselection=False)
        self.sv_entry = tk.StringVar(value="")
        self.entry = tk.Entry(self, textvariable=self.sv_entry)
        self.btn_add = tk.Button(self, text="add new exclusion", command=self.add)
        self.btn_del = tk.Button(self, text="remove highlighted", command=self.delete)
        self.add_callback = callbacks["add"]
        self.del_callback = callbacks["del"]

    def add(self) -> None:
        """Method called when self.btn_add is triggered"""
        pass

    def delete(self) -> None:
        """Method called when self.btn_del is triggered"""
        pass

    def show(self) -> None:
        """method used to show the widget's elements and its child widgets"""
        x, y = 0, 0

        self.rowconfigure(0, weight=1, pad=self.xpadding)
        self.rowconfigure(1, weight=1, pad=self.xpadding)
        self.rowconfigure(2, weight=1, pad=self.xpadding)
        self.columnconfigure(0, weight=1, pad=self.ypadding)
        self.columnconfigure(1, weight=1, pad=self.ypadding)

        self.listbox.grid(row=x, column=y, columnspan=2, sticky="WEN")
        self.entry.grid(row=x + 1, column=y, columnspan=2, sticky="WEN")
        self.btn_add.grid(row=x + 2, column=y, sticky="WE")
        self.btn_del.grid(row=x + 2, column=y + 1, sticky="WE")

    def populate_data(self, *args: Optional[List[Any]], **kwargs: Optional[Dict[str, Any]]) -> None:
        """method used to populate the widget from parent"""
        pass


if __name__ == "__main__":
    asyncio.run(App().exec())
