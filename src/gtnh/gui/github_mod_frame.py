import asyncio
from tkinter import END, Button, Entry, Label, LabelFrame, Listbox, Scrollbar, StringVar
from tkinter.messagebox import showerror, showinfo, showwarning
from tkinter.ttk import Combobox
from typing import Any, Callable, Coroutine, Dict, List, Optional

from gtnh.defs import Position
from gtnh.exceptions import RepoNotFoundException
from gtnh.gui.mod_info_frame import ModInfoFrame
from gtnh.models.gtnh_version import GTNHVersion
from gtnh.models.mod_info import GTNHModInfo
from gtnh.modpack_manager import GTNHModpackManager


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
        :param width: the width to harmonize widgets in characters
        :param kwargs: params to init the parent class
        """
        LabelFrame.__init__(self, master, text=frame_name, **kwargs)
        self.get_gtnh_callback: Callable[[], Coroutine[Any, Any, GTNHModpackManager]] = callbacks["get_gtnh"]
        self.get_github_mods_callback: Callable[[], Dict[str, str]] = callbacks["get_github_mods"]
        self.update_current_task_progress_bar: Callable[[float, str], None] = callbacks[
            "update_current_task_progress_bar"
        ]
        self.update_global_progress_bar: Callable[[float, str], None] = callbacks["update_global_progress_bar"]
        self.reset_current_task_progress_bar: Callable[[], None] = callbacks["reset_current_task_progress_bar"]
        self.reset_global_progress_bar: Callable[[], None] = callbacks["reset_global_progress_bar"]

        self.ypadding: int = 0
        self.xpadding: int = 0

        new_repo_text: str = "Enter the new repo here"
        add_repo_text: str = "Add repository"
        del_repo_text: str = "Delete highlighted"
        refresh_all_text: str = "Refresh all the repositories"
        refresh_repo_text: str = "Refresh repository data"
        self.width: int = (
            width
            if width is not None
            else max(
                len(new_repo_text),
                len(add_repo_text),
                len(del_repo_text),
                len(refresh_repo_text),
                len(refresh_all_text),
            )
        )

        self.sv_repo_name: StringVar = StringVar(self, value="")

        self.mod_info_callback: Callable[[Any], None] = callbacks["mod_info"]
        self.reset_mod_info_callback: Callable[[], None] = callbacks["reset_mod_info"]

        self.lb_mods: Listbox = Listbox(self, exportselection=False)
        self.lb_mods.bind("<<ListboxSelect>>", lambda event: asyncio.ensure_future(self.on_listbox_click(event)))

        self.label_entry: Label = Label(self, text=new_repo_text)
        self.entry: Entry = Entry(self, textvariable=self.sv_repo_name)

        self.btn_add: Button = Button(self, text=add_repo_text, command=lambda: asyncio.ensure_future(self.add_repo()))
        self.btn_rem: Button = Button(self, text=del_repo_text, command=lambda: asyncio.ensure_future(self.del_repo()))
        self.btn_refresh: Button = Button(
            self, text=refresh_repo_text, command=lambda: asyncio.ensure_future(self.refresh_repo())
        )
        self.btn_refresh_all: Button = Button(
            self, text=refresh_all_text, command=lambda: asyncio.ensure_future(self.refresh_all())
        )

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
        self.btn_refresh.configure(width=self.width)
        self.btn_refresh_all.configure(width=self.width)

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
        self.btn_refresh.grid_forget()
        self.btn_refresh_all.grid_forget()

        self.update_idletasks()

    def show(self) -> None:
        """
        Method used to display widgets and child widgets, as well as to configure the "responsiveness" of the widgets.

        :return: None
        """
        x: int = 0
        y: int = 0
        rows: int = 10
        columns: int = 2

        for i in range(rows):
            self.rowconfigure(i, weight=1, pad=self.xpadding)

        for i in range(columns):
            self.columnconfigure(i, weight=1, pad=self.ypadding)

        self.lb_mods.grid(row=x, column=y, columnspan=2, sticky=Position.HORIZONTAL)
        self.scrollbar.grid(row=x, column=y + 2, columnspan=2, sticky=Position.VERTICAL)
        self.label_entry.grid(row=x + 1, column=y)
        self.entry.grid(row=x + 1, column=y + 1, columnspan=2)
        self.btn_add.grid(row=x + 2, column=y)
        self.btn_rem.grid(row=x + 2, column=y + 1, columnspan=2)
        self.btn_refresh.grid(row=x + 3, column=y + 1, columnspan=2)
        self.btn_refresh_all.grid(row=x + 3, column=y)

        self.update_idletasks()

    def populate_data(self, data: List[str]) -> None:
        """
        Method called by parent class to populate data in this class.

        :param data: the data to pass to this class
        :return: None
        """
        self.lb_mods.insert(END, *data)

    async def on_listbox_click(self, event: Optional[Any] = None) -> None:
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

    async def add_repo(self, name_override: Optional[str] = None) -> None:
        """
        Method called when the button to add the github repository to assets is pressed.

        :param name_override: override passed when called by refresh_repo
        :return: None
        """
        repo_name: str = self.sv_repo_name.get() if name_override is None else name_override
        if repo_name == "":
            return

        repo_list: List[str] = list(self.lb_mods.get(0, END))

        if repo_name in repo_list and name_override is None:
            # skipping check if called by refresh_repo, as the name will be already in the list
            showwarning("Repository already in the assets", f"{repo_name} is already in the assets.")
            return

        gtnh_modpack: GTNHModpackManager = await self.get_gtnh_callback()
        try:
            await gtnh_modpack.add_github_mod(repo_name)
            gtnh_modpack.save_assets()

            if name_override is None:  # no need to readd the mod if this is called by refresh_repo
                repo_list += [repo_name]
                self.lb_mods.delete(0, END)
                self.lb_mods.insert(END, *sorted(repo_list))

                # not showing the info if this is called by refresh_mod
                showinfo("Repository added successfully", f"{repo_name} has been added successfully to the assets!")

        except RepoNotFoundException:
            showerror(
                "Error while adding the repository",
                f"{repo_name} is not a valid NH repository. A couple things to check:"
                "\n- Did you used the repository's url instead of its name?"
                "\n- Did you spelled it correctly?"
                "\n- Did you registered your token in DreamAssemblerXXL in case of a private repo?",
            )

    async def del_repo(self, verbose: bool = True) -> None:
        """
        Method called when the button to delete the highlighted github repository is pressed.

        :param verbose: if set to true show the error boxes
        :return: None
        """
        gtnh: GTNHModpackManager = await self.get_gtnh_callback()
        try:
            repo_name = self.lb_mods.get(self.lb_mods.curselection()[0])
        except IndexError:
            showerror("No repository name selected.", "Please select a repository before trying to edit it.")
            return

        if await gtnh.delete_github_mod(repo_name) and verbose:

            repo_list: List[str] = sorted([name for name in self.lb_mods.get(0, END) if name != repo_name])
            self.lb_mods.delete(0, END)
            self.lb_mods.insert(END, *repo_list)
            self.reset_mod_info_callback()

            showinfo("Repository successfully deleted", f"{repo_name} has been successfully deleted from assets.")

    async def refresh_repo(self) -> None:
        """
        Method to rebuild the assets for a specified repository.

        :return: None
        """
        try:
            repo_name = self.lb_mods.get(self.lb_mods.curselection()[0])
        except IndexError:
            showerror("No repository name selected.", "Please select a repository before trying to edit it.")
            return

        gtnh: GTNHModpackManager = await self.get_gtnh_callback()
        await gtnh.regen_github_repo_asset(repo_name)
        await self.on_listbox_click()
        showinfo("Repository refreshed successfully", f"{repo_name} has been refreshed successfully!")

    def _update_callback(self, delta_progress: float, msg: str) -> None:
        """
        callback used in refresh_all to update the progress bars.

        :param delta_progress: the progress to add to the progress bar
        :param msg: the message to display for the current task progress bar
        :return: None
        """
        self.update_global_progress_bar(delta_progress, "Regenerating github assets")
        self.update_current_task_progress_bar(delta_progress, msg)

    async def refresh_all(self) -> None:
        """
        Method used to refresh all the github mod assets.

        :return: None
        """
        self.reset_global_progress_bar()
        self.reset_current_task_progress_bar()

        gtnh: GTNHModpackManager = await self.get_gtnh_callback()
        await gtnh.regen_github_assets(callback=self._update_callback)
        showinfo("Github assets had been updated successfully", "All the github assets had been updated successfully!")


class GithubModFrame(LabelFrame):
    """
    Main frame widget for the github mods' management.
    """

    def __init__(
        self,
        master: Any,
        frame_name: str,
        callbacks: Dict[str, Any],
        width: Optional[int] = None,
        **kwargs: Any,
    ):
        """
        Constructor of the GithubModFrame class.

        :param master: the parent widget
        :param frame_name: the name displayed in the framebox
        :param callbacks: a dict of callbacks passed to this instance
        :param width: the width to harmonize widgets in characters
        :param kwargs: params to init the parent class
        """
        LabelFrame.__init__(self, master, text=frame_name, **kwargs)
        self.ypadding: int = 0
        self.xpadding: int = 0
        self.width: Optional[int] = width

        modpack_version_callbacks: Dict[str, Any] = {
            "set_modpack_version": callbacks["set_modpack_version"],
            "get_gtnh": callbacks["get_gtnh"],
        }

        self.modpack_version_frame: ModpackVersionFrame = ModpackVersionFrame(
            self, frame_name="Modpack version", callbacks=modpack_version_callbacks
        )

        mod_info_callbacks: Dict[str, Any] = {
            "set_mod_version": callbacks["set_github_mod_version"],
            "set_mod_side": callbacks["set_github_mod_side"],
        }

        self.mod_info_frame: ModInfoFrame = ModInfoFrame(
            self, frame_name="Github mod info", callbacks=mod_info_callbacks
        )

        github_mod_list_callbacks: Dict[str, Any] = {
            "mod_info": self.mod_info_frame.populate_data,
            "get_github_mods": callbacks["get_github_mods"],
            "get_gtnh": callbacks["get_gtnh"],
            "reset_mod_info": self.mod_info_frame.reset,
            "update_current_task_progress_bar": callbacks["update_current_task_progress_bar"],
            "update_global_progress_bar": callbacks["update_global_progress_bar"],
            "reset_current_task_progress_bar": callbacks["reset_current_task_progress_bar"],
            "reset_global_progress_bar": callbacks["reset_global_progress_bar"],
        }

        self.github_mod_list: GithubModList = GithubModList(
            self, frame_name="Github mod list", callbacks=github_mod_list_callbacks
        )

        if self.width is None:
            self.width = self.github_mod_list.get_width()
        else:
            self.github_mod_list.set_width(self.width)

        self.mod_info_frame.set_width(self.width)
        self.modpack_version_frame.set_width(self.width)

        self.update_widget()

    def configure_widgets(self) -> None:
        """
        Method to configure the widgets.

        :return: None
        """
        self.mod_info_frame.configure_widgets()
        self.modpack_version_frame.configure_widgets()
        self.github_mod_list.configure_widgets()

    def set_width(self, width: int) -> None:
        """
        Method to set the widgets' width.

        :param width: the new width
        :return: None
        """
        self.width = width
        self.mod_info_frame.set_width(self.width)
        self.modpack_version_frame.set_width(self.width)
        self.github_mod_list.set_width(self.width)

    def get_width(self) -> int:
        """
        Getter for self.width.

        :return: the width in character sizes of the normalised widgets
        """
        assert self.width  # can't be None because how it's defined in the constructor
        return self.width

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

        self.update_idletasks()

    def show(self) -> None:
        """
        Method used to display widgets and child widgets, as well as to configure the "responsiveness" of the widgets.

        :return: None
        """
        x: int = 0
        y: int = 0
        rows: int = 3
        columns: int = 1

        for i in range(rows):
            self.rowconfigure(i, weight=1, pad=self.xpadding)

        for i in range(columns):
            self.columnconfigure(i, weight=1, pad=self.ypadding)

        self.modpack_version_frame.grid(row=x, column=y, sticky=Position.HORIZONTAL)
        self.github_mod_list.grid(row=x + 1, column=y)  # ref widget
        self.mod_info_frame.grid(row=x + 2, column=y, sticky=Position.HORIZONTAL)

        self.modpack_version_frame.show()
        self.github_mod_list.show()
        self.mod_info_frame.show()

        self.update_idletasks()

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
        callbacks: Dict[str, Any],
        width: Optional[int] = None,
        **kwargs: Any,
    ):
        """
        Constructor of the ModpackVersionFrame.

        :param master: the parent widget
        :param frame_name: the name displayed in the framebox
        :param callbacks: a dict of callbacks passed to this instance
        :param width: the width to harmonize widgets in characters
        :param kwargs: params to init the parent class
        """
        LabelFrame.__init__(self, master, text=frame_name, **kwargs)
        self.ypadding: int = 0
        self.xpadding: int = 0
        modpack_version_text: str = "Modpack version:"
        refresh_modpack_text: str = "Refresh modpack assets"
        self.width: int = width if width is not None else max(len(modpack_version_text), len(refresh_modpack_text))
        self.label_modpack_version: Label = Label(self, text=modpack_version_text)
        self.sv_version: StringVar = StringVar(value="")
        self.cb_modpack_version: Combobox = Combobox(self, textvariable=self.sv_version, values=[])
        self.cb_modpack_version.bind(
            "<<ComboboxSelected>>", lambda event: callbacks["set_modpack_version"](self.sv_version.get())
        )
        self.btn_refresh: Button = Button(
            self, text=refresh_modpack_text, command=lambda: asyncio.ensure_future(self.refresh_modpack_assets())
        )
        self.get_gtnh_callback: Callable[[], Coroutine[Any, Any, GTNHModpackManager]] = callbacks["get_gtnh"]

    async def refresh_modpack_assets(self) -> None:
        """
        Method used to refresh assets for the modpack repository.

        :return: None
        """
        gtnh: GTNHModpackManager = await self.get_gtnh_callback()
        await gtnh.regen_config_assets()
        self.cb_modpack_version["values"] = [version.version_tag for version in gtnh.assets.config.versions]
        self.sv_version.set(gtnh.assets.config.latest_version)
        showinfo("Modpack assets refreshed", "Modpack assets refreshed successfully!")

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
        self.btn_refresh.grid_forget()

        self.update_idletasks()

    def show(self) -> None:
        """
        Method used to display widgets and child widgets, as well as to configure the "responsiveness" of the widgets.

        :return: None
        """
        x: int = 0
        y: int = 0
        rows: int = 2
        columns: int = 2

        for i in range(rows):
            self.rowconfigure(i, weight=1, pad=self.xpadding)

        for i in range(columns):
            self.columnconfigure(i, weight=1, pad=self.ypadding)

        self.label_modpack_version.grid(row=x, column=y)
        self.cb_modpack_version.grid(row=x, column=y + 1, sticky=Position.HORIZONTAL)
        self.btn_refresh.grid(row=x + 1, column=y + 1, sticky=Position.HORIZONTAL)

    def populate_data(self, data: Dict[str, Any]) -> None:
        """
        Method called by parent class to populate data in this class.

        :param data: the data to pass to this class
        :return: None
        """
        self.cb_modpack_version["values"] = data["combobox"]
        self.sv_version.set(data["stringvar"])
