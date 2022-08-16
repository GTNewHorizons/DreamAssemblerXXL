from tkinter import END, Button, Entry, Label, LabelFrame, Listbox, Scrollbar, StringVar
from tkinter.ttk import Progressbar
from typing import Any, Callable, Dict, List, Optional, Tuple

from gtnh.models.gtnh_release import GTNHRelease


class ModpackFrame(LabelFrame):
    """Main frame for managing the releases."""

    def __init__(self, master: Any, frame_name: str, callbacks: Dict[str, Any], **kwargs: Any) -> None:
        """
        Constructor of the ModpackFrame class.

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

        self.modpack_list.show()
        self.action_frame.show()

        self.update_idletasks()

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

        self.update_idletasks()

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

        self.update_idletasks()
