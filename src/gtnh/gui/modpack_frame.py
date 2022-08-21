from tkinter import END, Button, Entry, Frame, Label, LabelFrame, Listbox, Scrollbar, StringVar, simpledialog
from tkinter.messagebox import showerror
from tkinter.ttk import Progressbar
from typing import Any, Callable, Dict, List, Optional, Tuple

from gtnh.defs import Position
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
        self.width: int = width if width is not None else 20  # arbitrary value
        self.generate_nightly_callback: Callable[[], None] = callbacks["generate_nightly"]
        action_callbacks: Dict[str, Any] = {
            "client_cf": callbacks["client_curse"],
            "client_modrinth": callbacks["client_modrinth"],
            "client_mmc": callbacks["client_mmc"],
            "client_technic": callbacks["client_technic"],
            "client_zip": callbacks["client_zip"],
            "server_zip": callbacks["server_zip"],
            "generate_all": callbacks["all"],
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
        x: int = 0
        y: int = 0
        rows: int = 1
        columns: int = 2

        for i in range(rows):
            self.rowconfigure(i, weight=1, pad=self.xpadding)

        for i in range(columns):
            self.columnconfigure(i, weight=1, pad=self.ypadding)

        self.modpack_list.grid(row=x, column=y, sticky=Position.ALL)
        self.action_frame.grid(row=x, column=y + 1, sticky=Position.ALL)

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

        self.text_loaded_version = "Loaded version: {0}"
        self.sv_loaded_version: StringVar = StringVar(self)
        self.sv_loaded_version.set(self.text_loaded_version.format(""))
        self.label_loaded_version: Label = Label(self, textvariable=self.sv_loaded_version)

        self.update_widget()

    def set_loaded_version(self, version: str) -> None:
        self.sv_loaded_version.set(self.text_loaded_version.format(version))

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
        self.label_loaded_version.grid_forget()

        self.update_idletasks()

    def show(self) -> None:
        """
        Method used to display widgets and child widgets, as well as to configure the "responsiveness" of the widgets.

        :return: None
        """
        x: int = 0
        y: int = 0
        rows: int = 3
        columns: int = 2

        for i in range(columns):
            self.columnconfigure(i, weight=1, pad=self.ypadding)

        for i in range(rows):
            self.rowconfigure(i, weight=1, pad=self.xpadding)

        self.lb_modpack_versions.grid(row=x, column=y, columnspan=2, sticky=Position.HORIZONTAL)
        self.scrollbar.grid(row=x, column=y + 2, columnspan=2, sticky=Position.VERTICAL)
        self.label_loaded_version.grid(row=x + 1, column=y, columnspan=3, sticky=Position.LEFT)
        self.btn_load.grid(row=x + 2, column=y, sticky=Position.DOWN_RIGHT)
        self.btn_del.grid(row=x + 2, column=y + 1, columnspan=2, sticky=Position.DOWN_LEFT)
        self.entry.grid(row=x + 3, column=y, sticky=Position.UP_RIGHT)
        self.btn_add.grid(row=x + 3, column=y + 1, columnspan=2, sticky=Position.UP_LEFT)

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
            release_name: str = self.lb_modpack_versions.get(index)

            if callback is not None:
                callback(release_name)

            self.set_loaded_version(release_name)

    def btn_add_command(self, callback: Optional[Callable[[str, str], None]] = None) -> None:
        """
        Callback for the button self.btn_add.

        :param callback: external call back to process added release name.
        :return: None
        """
        release_name: str = self.sv_entry.get()
        if release_name != "":
            previous_release: Optional[str] = simpledialog.askstring(
                title="Enter the previous modpack version", prompt="Please enter the previous modpack version:"
            )
            if previous_release is None:  # pressed cancel
                return

            # invalid input
            if previous_release not in self.lb_modpack_versions.get(0, END) or previous_release == release_name:
                showerror(
                    "Invalid previous version",
                    "You must provide a valid version corresponding to the previous pack version.",
                )
                return

            if callback is not None:
                callback(release_name, previous_release)

        if release_name not in self.lb_modpack_versions.get(0, END):
            self.lb_modpack_versions.insert(END, release_name)

        self.set_loaded_version(release_name)

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

        generate_all_text: str = "Generate all archives"
        update_nightly_text: str = "Update nightly"
        update_assets_text: str = "Update assets"

        client_cf_text: str = "CurseForge client archive"
        client_technic_text: str = "Technic client archive"
        client_mr_text: str = "Modrinth client archive"
        client_mmc_text: str = "MultiMC client archive"
        client_zip_text: str = "Zip client archive"
        server_zip_text: str = "Zip server archive"

        self.width: int = (
            width
            if width is not None
            else max(
                len(generate_all_text),
                len(update_nightly_text),
                len(update_assets_text),
                len(server_zip_text),
                len(client_cf_text),
                len(client_mr_text),
                len(client_mmc_text),
                len(client_technic_text),
                len(client_zip_text),
            )
        )

        self.frame_btn: Frame = Frame(self)

        self.btn_client_cf: Button = Button(self.frame_btn, text=client_cf_text, command=callbacks["client_cf"])
        self.btn_client_technic: Button = Button(
            self.frame_btn, text=client_technic_text, command=callbacks["client_technic"]
        )
        self.btn_client_mmc: Button = Button(self.frame_btn, text=client_mmc_text, command=callbacks["client_mmc"])
        self.btn_client_modrinth: Button = Button(
            self.frame_btn, text=client_mr_text, command=callbacks["client_modrinth"]
        )
        self.btn_generate_all: Button = Button(
            self.frame_btn, text=generate_all_text, command=callbacks["generate_all"]
        )
        self.btn_update_nightly: Button = Button(
            self.frame_btn, text=update_nightly_text, command=callbacks["generate_nightly"]
        )
        self.btn_update_assets: Button = Button(
            self.frame_btn, text=update_assets_text, command=callbacks["update_assets"]
        )
        self.btn_client_zip: Button = Button(self.frame_btn, text=client_zip_text, command=callbacks["client_zip"])
        self.btn_server_zip: Button = Button(self.frame_btn, text=server_zip_text, command=callbacks["server_zip"])

        self.label_spacer: Label = Label(self, text="")

        progress_bar_length: int = 500

        self.pb_global: Progressbar = Progressbar(
            self, orient="horizontal", mode="determinate", length=progress_bar_length
        )
        self.sv_pb_global: StringVar = StringVar(self, value="")
        self.label_pb_global: Label = Label(self, textvariable=self.sv_pb_global, width=100)

        self.pb_current_task: Progressbar = Progressbar(
            self, orient="horizontal", mode="determinate", length=progress_bar_length
        )
        self.sv_pb_current_task: StringVar = StringVar(self, value="")
        self.label_pb_current_task: Label = Label(self, textvariable=self.sv_pb_current_task, width=100)

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

    def reset_current_task_progress_bar(self) -> None:
        """
        Callback to reset the progress bar for the current task.

        :return: None
        """
        self.pb_current_task["value"] = 0
        self.sv_pb_current_task.set("")
        self.update_idletasks()

    def update_global_progress_bar(self, progress: float, data: str) -> None:
        """
        Callback to update the task bar showing the global progress.

        :param progress: value to add to the progress
        :param data: what is currently done
        :return: None
        """
        self.pb_global["value"] += progress
        self.sv_pb_global.set(data)
        self.update_idletasks()

    def reset_global_progress_bar(self) -> None:
        """
        Callback to reset the progress bar for the global progress.

        :return: None
        """
        self.pb_global["value"] = 0
        self.sv_pb_global.set("")
        self.update_idletasks()

    def show(self) -> None:
        """
        Method used to display widgets and child widgets, as well as to configure the "responsiveness" of the widgets.

        :return: None
        """
        x: int = 0
        y: int = 0
        rows: int = 5
        columns: int = 1

        for i in range(rows):
            self.rowconfigure(i, weight=1, pad=self.xpadding)

        self.rowconfigure(rows + 1, weight=3)  # allocate more space for the btn frame

        for i in range(columns):
            self.columnconfigure(i, weight=1, pad=self.ypadding)

        self.label_pb_global.grid(row=x, column=y)
        self.pb_global.grid(row=x + 1, column=y)
        self.label_pb_current_task.grid(row=x + 2, column=y)
        self.pb_current_task.grid(row=x + 3, column=y)

        self.label_spacer.grid(row=x + 4, column=y)

        self.frame_btn.grid(row=x + 5, column=y, sticky=Position.UP)

        # grid withing the self.fram_btn
        pad: int = 3
        frame_rows: int = 3
        frame_columns: int = 3
        for i in range(frame_rows):
            self.frame_btn.rowconfigure(i, weight=1, pad=pad)

        for i in range(frame_columns):
            self.frame_btn.columnconfigure(i, weight=1, pad=pad)

        self.btn_client_cf.grid(row=0, column=0)
        self.btn_client_zip.grid(row=0, column=1)
        self.btn_client_technic.grid(row=0, column=2)

        self.btn_client_modrinth.grid(row=1, column=0)
        self.btn_server_zip.grid(row=1, column=1)
        self.btn_client_mmc.grid(row=1, column=2)

        self.btn_update_nightly.grid(row=2, column=0)
        self.btn_generate_all.grid(row=2, column=1)
        self.btn_update_assets.grid(row=2, column=2)

        self.update_idletasks()

    def configure_widgets(self) -> None:
        """
        Method to configure the widgets.

        :return: None
        """

        self.btn_client_cf.configure(width=self.width)
        self.btn_client_technic.configure(width=self.width)
        self.btn_client_modrinth.configure(width=self.width)
        self.btn_client_mmc.configure(width=self.width)
        self.btn_generate_all.configure(width=self.width)
        self.btn_update_nightly.configure(width=self.width)
        self.btn_update_assets.configure(width=self.width)
        self.btn_client_zip.configure(width=self.width)
        self.btn_server_zip.configure(width=self.width)

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
        self.label_spacer.grid_forget()
        self.btn_client_cf.grid_forget()
        self.btn_client_technic.grid_forget()
        self.btn_client_modrinth.grid_forget()
        self.btn_client_mmc.grid_forget()
        self.btn_generate_all.grid_forget()
        self.btn_update_nightly.grid_forget()
        self.btn_update_assets.grid_forget()
        self.btn_client_zip.grid_forget()
        self.btn_server_zip.grid_forget()

        self.update_idletasks()
