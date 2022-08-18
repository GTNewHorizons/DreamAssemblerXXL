from tkinter import END, Button, Entry, Label, LabelFrame, Listbox, Scrollbar, StringVar
from tkinter.ttk import Progressbar
from typing import Any, Callable, Dict, List, Optional, Tuple

from gtnh.models.gtnh_release import GTNHRelease


class ModpackFrame(LabelFrame):
    """Main frame for managing the releases."""

    def __init__(
        self, master: Any, frame_name: str, callbacks: Dict[str, Any], width: Optional[int] = None, **kwargs: Any
    ) -> None:
        """
        Constructor of the ModpackFrame class.

        :param master: the parent widget
        :param frame_name: the name displayed in the framebox
        :param callbacks: a dict of callbacks passed to this instance
        :param width: the width to harmonize widgets in characters
        :param kwargs: params to init the parent class
        """
        LabelFrame.__init__(self, master, text=frame_name, **kwargs)
        self.xpadding: int = 0
        self.ypadding: int = 0
        self.width = width if width is not None else 20  # arbitrary value
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

    def configure_widgets(self) -> None:
        """
        Method to configure the widgets.

        :return: None
        """
        self.modpack_list.configure_widgets()
        self.action_frame.configure_widgets()

    def set_width(self, width: int) -> None:
        """
        Method to set the widgets' width.

        :param width: the new width
        :return: None
        """
        self.width = width
        self.modpack_list.set_width(self.width)
        self.action_frame.set_width(self.width)

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
        self.modpack_list.hide()
        self.action_frame.hide()

        self.update_idletasks()

    def show(self) -> None:
        """
        Method used to display widgets and child widgets, as well as to configure the "responsiveness" of the widgets.

        :return: None
        """
        self.columnconfigure(0, weight=1, pad=self.ypadding)
        self.columnconfigure(1, weight=1, pad=self.ypadding)
        self.rowconfigure(0, weight=1, pad=self.xpadding)

        self.modpack_list.grid(row=0, column=0, sticky="WENS")
        self.action_frame.grid(row=0, column=1, sticky="WENS")

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

    def __init__(
        self, master: Any, frame_name: str, callbacks: Dict[str, Any], width: Optional[int] = None, **kwargs: Any
    ) -> None:
        """
        Constructor of the ModpackList class.

        :param master: the parent widget
        :param frame_name: the name displayed in the framebox
        :param callbacks: a dict of callbacks passed to this instance
        :param width: the width to harmonize widgets in characters
        :param kwargs: params to init the parent class
        """
        LabelFrame.__init__(self, master, text=frame_name, **kwargs)
        self.xpadding: int = 0
        self.ypadding: int = 0

        self.btn_load_text: str = "Load version"
        self.btn_del_text: str = "Delete version"
        self.btn_add_text: str = "Add / Update"

        self.width: int = (
            width if width is not None else max(len(self.btn_del_text), len(self.btn_add_text), len(self.btn_load_text))
        )

        self.lb_modpack_versions: Listbox = Listbox(self, exportselection=False)
        self.lb_modpack_versions.bind("<<ListboxSelect>>", self.on_listbox_click)

        self.scrollbar: Scrollbar = Scrollbar(self)
        self.lb_modpack_versions.configure(yscrollcommand=self.scrollbar.set, height=19)
        self.scrollbar.configure(command=self.lb_modpack_versions.yview)

        self.btn_load: Button = Button(
            self, text=self.btn_load_text, command=lambda: self.btn_load_command(callbacks["load"])
        )
        self.btn_del: Button = Button(
            self, text=self.btn_del_text, command=lambda: self.btn_del_command(callbacks["delete"])
        )
        self.sv_entry: StringVar = StringVar(self)
        self.entry: Entry = Entry(self, textvariable=self.sv_entry)
        self.btn_add: Button = Button(
            self, text=self.btn_add_text, command=lambda: self.btn_add_command(callbacks["add"])
        )

        self.update_widget()

    def configure_widgets(self) -> None:
        """
        Method to configure the widgets.

        :return: None
        """
        self.btn_load.configure(width=self.width)
        self.btn_del.configure(width=self.width)
        self.entry.configure(width=self.width + 4)
        self.btn_add.configure(width=self.width)

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
        self.lb_modpack_versions.grid_forget()
        self.btn_load.grid_forget()
        self.btn_del.grid_forget()
        self.entry.grid_forget()
        self.btn_add.grid_forget()

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
        self.btn_load.grid(row=1, column=0, sticky="ES")
        self.btn_del.grid(row=1, column=1, columnspan=2, sticky="WS")
        self.entry.grid(row=2, column=0, sticky="EN")
        self.btn_add.grid(row=2, column=1, columnspan=2, sticky="WN")

        self.update_idletasks()

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

    def __init__(
        self, master: Any, frame_name: str, callbacks: Dict[str, Any], width: Optional[int] = None, **kwargs: Any
    ):
        """
        Constructor of the ActionFrame class.

        :param master: the parent widget
        :param frame_name: the name displayed in the framebox
        :param callbacks: a dict of callbacks passed to this instance
        :param width: the width to harmonize widgets in characters
        :param kwargs: params to init the parent class
        """
        LabelFrame.__init__(self, master, text=frame_name, **kwargs)
        self.xpadding: int = 0
        self.ypadding: int = 0
        client_archive_text: str = "client archive"
        server_archive_text: str = "server archive"
        generate_all_text: str = "Generate all archives"
        update_nightly_text: str = "Update nightly"
        update_assets_text: str = "Update assets"
        cf_text: str = "CurseForge"
        technic_text: str = "Technic"
        mr_text: str = "Modrinth"
        mmc_text: str = "MultiMC"
        self.width: int = (
            width
            if width is not None
            else max(
                len(client_archive_text),
                len(server_archive_text),
                len(generate_all_text),
                len(update_nightly_text),
                len(update_assets_text),
                len(cf_text),
                len(technic_text),
                len(mr_text),
                len(mmc_text),
            )
        )

        self.label_cf: Label = Label(self, text=cf_text)
        self.btn_client_cf: Button = Button(self, text=client_archive_text, command=callbacks["client_cf"])
        self.btn_server_cf: Button = Button(self, text=server_archive_text, command=callbacks["server_cf"])
        self.label_technic: Label = Label(self, text=technic_text)
        self.btn_client_technic: Button = Button(self, text=client_archive_text, command=callbacks["client_technic"])
        self.btn_server_technic: Button = Button(self, text=server_archive_text, command=callbacks["server_technic"])
        self.label_mmc: Label = Label(self, text=mmc_text)
        self.btn_client_mmc: Button = Button(self, text=client_archive_text, command=callbacks["client_mmc"])
        self.btn_server_mmc: Button = Button(self, text=server_archive_text, command=callbacks["server_mmc"])
        self.label_modrinth: Label = Label(self, text=mr_text)
        self.btn_client_modrinth: Button = Button(self, text=client_archive_text, command=callbacks["client_modrinth"])
        self.btn_server_modrinth: Button = Button(self, text=server_archive_text, command=callbacks["server_modrinth"])
        self.btn_generate_all: Button = Button(self, text="generate all", command=callbacks["generate_all"])
        self.btn_update_nightly: Button = Button(self, text="update nightly", command=callbacks["generate_nightly"])
        self.btn_update_assets: Button = Button(self, text="update assets", command=callbacks["update_assets"])

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

        self.update_widget()

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

        self.label_cf.grid(row=x + 4, column=y, sticky="S")
        self.label_technic.grid(row=x + 4, column=y + 1, sticky="S")
        self.label_modrinth.grid(row=x + 4, column=y + 2, sticky="S")
        self.label_mmc.grid(row=x + 4, column=y + 3, sticky="S")

        self.btn_client_cf.grid(row=x + 5, column=y, sticky="S")
        self.btn_client_technic.grid(row=x + 5, column=y + 1, sticky="S")
        self.btn_client_modrinth.grid(row=x + 5, column=y + 2, sticky="S")
        self.btn_client_mmc.grid(row=x + 5, column=y + 3, sticky="S")

        self.btn_server_cf.grid(row=x + 6, column=y, sticky="N")
        self.btn_server_technic.grid(row=x + 6, column=y + 1, sticky="N")
        self.btn_server_modrinth.grid(row=x + 6, column=y + 2, sticky="N")
        self.btn_server_mmc.grid(row=x + 6, column=y + 3, sticky="N")

        self.btn_generate_all.grid(row=x + 7, column=y + 1, columnspan=2, sticky="N")
        self.btn_update_nightly.grid(row=x + 7, column=y, columnspan=2, sticky="N")
        self.btn_update_assets.grid(row=x + 7, column=y + 2, columnspan=2, sticky="N")

        self.update_idletasks()

    def configure_widgets(self) -> None:
        """
        Method to configure the widgets.

        :return: None
        """

        self.label_cf.configure(width=self.width)
        self.btn_client_cf.configure(width=self.width)
        self.btn_server_cf.configure(width=self.width)
        self.label_technic.configure(width=self.width)
        self.btn_client_technic.configure(width=self.width)
        self.btn_server_technic.configure(width=self.width)
        self.label_modrinth.configure(width=self.width)
        self.btn_client_modrinth.configure(width=self.width)
        self.btn_server_modrinth.configure(width=self.width)
        self.label_mmc.configure(width=self.width)
        self.btn_client_mmc.configure(width=self.width)
        self.btn_server_mmc.configure(width=self.width)
        self.btn_generate_all.configure(width=self.width)
        self.btn_update_nightly.configure(width=self.width)
        self.btn_update_assets.configure(width=self.width)

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
        self.label_pb_global.grid_forget()
        self.pb_global.grid_forget()
        self.label_pb_current_task.grid_forget()
        self.pb_current_task.grid_forget()
        self.label_cf.grid_forget()
        self.btn_client_cf.grid_forget()
        self.btn_server_cf.grid_forget()
        self.label_technic.grid_forget()
        self.btn_client_technic.grid_forget()
        self.btn_server_technic.grid_forget()
        self.label_modrinth.grid_forget()
        self.btn_client_modrinth.grid_forget()
        self.btn_server_modrinth.grid_forget()
        self.label_mmc.grid_forget()
        self.btn_client_mmc.grid_forget()
        self.btn_server_mmc.grid_forget()
        self.btn_generate_all.grid_forget()
        self.btn_update_nightly.grid_forget()
        self.btn_update_assets.grid_forget()

        self.update_idletasks()
