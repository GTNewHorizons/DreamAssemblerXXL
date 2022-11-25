import asyncio
from tkinter import LabelFrame
from tkinter.messagebox import showerror, showinfo, showwarning
from typing import Any, Callable, Coroutine, Dict, List, Optional

from gtnh.defs import Position
from gtnh.exceptions import RepoNotFoundException
from gtnh.gui.lib.button import CustomButton
from gtnh.gui.lib.listbox import CustomListbox
from gtnh.gui.lib.text_entry import TextEntry
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

        self.add_mod_to_memory: Callable[[str, str], None] = callbacks["add_mod_in_memory"]
        self.del_mod_from_memory: Callable[[str], None] = callbacks["del_mod_in_memory"]

        self.ypadding: int = 0
        self.xpadding: int = 0

        self.mod_info_callback: Callable[[Any], None] = callbacks["mod_info"]
        self.reset_mod_info_callback: Callable[[], None] = callbacks["reset_mod_info"]

        self.repository: TextEntry = TextEntry(self, label_text="Enter the new repo here")

        self.btn_add: CustomButton = CustomButton(
            self, text="Add repository", command=lambda: asyncio.ensure_future(self.add_repo())
        )
        self.btn_rem: CustomButton = CustomButton(
            self, text="Delete highlighted", command=lambda: asyncio.ensure_future(self.del_repo())
        )
        self.btn_refresh: CustomButton = CustomButton(
            self, text="Refresh repository data", command=lambda: asyncio.ensure_future(self.refresh_repo())
        )
        self.btn_refresh_all: CustomButton = CustomButton(
            self, text="Refresh all the repositories", command=lambda: asyncio.ensure_future(self.refresh_all())
        )

        self.listbox: CustomListbox = CustomListbox(
            self,
            "List of availiable github mods:",
            exportselection=False,
            on_selection=lambda event: asyncio.ensure_future(self.on_listbox_click(event)),
        )

        self.widgets = [
            self.repository,
            self.btn_add,
            self.btn_rem,
            self.btn_refresh,
            self.btn_refresh_all,
            self.listbox,
        ]

        self.width: int = (
            width if width is not None else max([widget.get_description_size() for widget in self.widgets])
        )

    def configure_widgets(self) -> None:
        """
        Method to configure the widgets.

        :return: None
        """
        self.repository.configure(width=self.width - 8)  # magic number don't ask it just fits well with 8

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
        for widget in self.widgets:
            widget.grid_forget()

        self.update_idletasks()

    def show(self) -> None:
        """
        Method used to display widgets and child widgets, as well as to configure the "responsiveness" of the widgets.

        :return: None
        """
        x: int = 0
        y: int = 0
        rows: int = 11
        columns: int = 2

        for i in range(rows):
            self.rowconfigure(i, weight=1, pad=self.xpadding)

        for i in range(columns):
            self.columnconfigure(i, weight=1, pad=self.ypadding)

        self.listbox.grid(row=x, column=y, columnspan=2, sticky=Position.HORIZONTAL)

        self.repository.grid(row=x + 1, column=y, columnspan=2)

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
        self.listbox.set_values(data)

    async def on_listbox_click(self, _: Optional[Any] = None) -> None:
        """
        Callback used when the user clicks on the github mods' listbox.

        :param _: the tkinter event passed by the tkinter in the Callback (unused)
        :return: None
        """
        if not self.listbox.has_selection():
            return

        index: int = self.listbox.get()
        gtnh: GTNHModpackManager = await self.get_gtnh_callback()
        mod_info: GTNHModInfo = gtnh.assets.get_github_mod(self.listbox.get_value_at_index(index))
        name: str = mod_info.name
        mod_versions: list[GTNHVersion] = mod_info.versions
        latest_version: Optional[GTNHVersion] = mod_info.get_latest_version()
        assert latest_version
        current_version: str = (
            self.get_github_mods_callback()[name]
            if name in self.get_github_mods_callback()
            else latest_version.version_tag
        )
        mod_license: str = mod_info.license or "No license detected"
        side: str = mod_info.side

        data = {
            "name": name,
            "versions": [version.version_tag for version in mod_versions],
            "current_version": current_version,
            "license": mod_license,
            "side": side,
        }

        self.mod_info_callback(data)

    async def add_repo(self, name_override: Optional[str] = None) -> None:
        """
        Method called when the button to add the github repository to assets is pressed.

        :param name_override: override passed when called by refresh_repo
        :return: None
        """
        repo_name: str = self.repository.get() if name_override is None else name_override
        if repo_name == "":
            return

        repo_list: List[str] = self.listbox.get_values()

        if repo_name in repo_list and name_override is None:
            # skipping check if called by refresh_repo, as the name will be already in the list
            showwarning("Repository already in the assets", f"{repo_name} is already in the assets.")
            return

        gtnh_modpack: GTNHModpackManager = await self.get_gtnh_callback()
        try:
            await gtnh_modpack.add_github_mod(repo_name)
            gtnh_modpack.save_assets()
            repo = await gtnh_modpack.get_latest_github_release(repo_name)
            assert repo
            version = repo.tag_name
            self.add_mod_to_memory(repo_name, version)

            if name_override is None:  # no need to readd the mod if this is called by refresh_repo
                repo_list += [repo_name]
                self.listbox.set_values(sorted(repo_list))

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
        if self.listbox.has_selection():
            repo_name = self.listbox.get_value_at_index(self.listbox.get())
        else:
            showerror("No repository name selected.", "Please select a repository before trying to edit it.")
            return

        repo_list: List[str] = sorted([name for name in self.listbox.get_values() if name != repo_name])
        self.listbox.set_values(repo_list)
        self.reset_mod_info_callback()

        self.del_mod_from_memory(repo_name)

        if await gtnh.delete_github_mod(repo_name) and verbose:
            showinfo("Repository successfully deleted", f"{repo_name} has been successfully deleted from assets.")

    async def refresh_repo(self) -> None:
        """
        Method to rebuild the assets for a specified repository.

        :return: None
        """
        if self.listbox.has_selection():
            repo_name = self.listbox.get_value_at_index(self.listbox.get())
        else:
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
