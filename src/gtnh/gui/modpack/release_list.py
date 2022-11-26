from tkinter import END, Button, Entry, Label, LabelFrame, Listbox, Scrollbar, StringVar, simpledialog
from tkinter.messagebox import showerror
from typing import Any, Callable, Dict, List, Optional, Tuple

from gtnh.defs import Position
from gtnh.models.gtnh_release import GTNHRelease


class ReleaseList(LabelFrame):
    """Widget ruling the list of modpack versions"""

    def __init__(
        self, master: Any, frame_name: str, callbacks: Dict[str, Any], width: Optional[int] = None, **kwargs: Any
    ) -> None:
        """
        Constructor of the ReleaseList class.

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
