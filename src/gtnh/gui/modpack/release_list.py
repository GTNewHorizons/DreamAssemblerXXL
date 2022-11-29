from tkinter import LabelFrame, simpledialog
from tkinter.messagebox import showerror
from tkinter.ttk import LabelFrame as TtkLabelFrame
from typing import Any, Callable, Dict, List, Optional

from gtnh.defs import Position
from gtnh.gui.lib.CustomLabel import CustomLabel
from gtnh.gui.lib.button import CustomButton
from gtnh.gui.lib.custom_widget import CustomWidget
from gtnh.gui.lib.listbox import CustomListbox
from gtnh.gui.lib.text_entry import TextEntry
from gtnh.models.gtnh_release import GTNHRelease


class ReleaseList(LabelFrame, TtkLabelFrame):  # type: ignore
    """Widget ruling the list of modpack versions"""

    def __init__(
        self,
        master: Any,
        frame_name: str,
        callbacks: Dict[str, Any],
        width: Optional[int] = None,
        themed: bool = False,
        **kwargs: Any,
    ) -> None:
        """
        Constructor of the ReleaseList class.

        :param master: the parent widget
        :param frame_name: the name displayed in the framebox
        :param callbacks: a dict of callbacks passed to this instance
        :param width: the width to harmonize widgets in characters
        :param themed: for those who prefered themed versions of the widget. Default to false.
        :param kwargs: params to init the parent class
        """
        self.themed = themed
        if themed:
            TtkLabelFrame.__init__(self, master, text=frame_name, **kwargs)
        else:
            LabelFrame.__init__(self, master, text=frame_name, **kwargs)
        self.xpadding: int = 0
        self.ypadding: int = 0

        self.listbox: CustomListbox = CustomListbox(
            self,
            label_text="Modpack versions:",
            exportselection=False,
            on_selection=self.on_listbox_click,
            themed=self.themed,
        )

        self.btn_load: CustomButton = CustomButton(
            self, text="Load version", command=lambda: self.btn_load_command(callbacks["load"]), themed=self.themed
        )
        self.btn_del: CustomButton = CustomButton(
            self, text="Delete version", command=lambda: self.btn_del_command(callbacks["delete"]), themed=self.themed
        )
        self.btn_add: CustomButton = CustomButton(
            self, text="Add / Update", command=lambda: self.btn_add_command(callbacks["add"]), themed=self.themed
        )

        self.modpack: TextEntry = TextEntry(self, "", hide_label=True, themed=self.themed)

        self.loaded_version: CustomLabel = CustomLabel(
            self, label_text="Loaded version: {0}", value="", themed=self.themed
        )

        self.widgets: List[CustomWidget] = [
            self.listbox,
            self.btn_add,
            self.btn_load,
            self.btn_del,
            self.modpack,
            self.loaded_version,
        ]

        self.width: int = (
            width if width is not None else max([widget.get_description_size() for widget in self.widgets])
        )

        self.update_widget()

    def set_loaded_version(self, version: str) -> None:
        self.loaded_version.set(version)

    def configure_widgets(self) -> None:
        """
        Method to configure the widgets.

        :return: None
        """
        for widget in self.widgets:
            widget.configure(width=self.width)

        print(f"internal width: {self.width}, entry width: {self.modpack.entry['width']}")

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
        rows: int = 1
        columns: int = 2

        for i in range(columns):
            self.columnconfigure(i, weight=1, pad=self.ypadding)

        for i in range(rows):
            self.rowconfigure(i, weight=1, pad=self.xpadding)

        self.listbox.grid(row=x, column=y, columnspan=2, sticky=Position.ALL)
        self.loaded_version.grid(row=x + 1, column=y)
        self.btn_load.grid(row=x + 2, column=y)
        self.btn_del.grid(row=x + 2, column=y + 1)
        self.modpack.grid(row=x + 3, column=y)
        self.btn_add.grid(row=x + 3, column=y + 1)

        self.update_idletasks()

    def on_listbox_click(self, _: Any) -> None:
        """
        Callback used to fill the entry widget when a modpack version is selected.

        :param _: the tkinter event passed by the tkinter in the Callback (unused)
        :return: None
        """
        if self.listbox.has_selection():
            index: int = self.listbox.get()
            self.modpack.set(self.listbox.get_value_at_index(index))

    def btn_load_command(self, callback: Optional[Callable[[str], None]] = None) -> None:
        """
        Callback for the button self.btn_load.

        :param callback: external call back to process added release name.
        :return: None
        """
        if self.listbox.has_selection():
            index: int = self.listbox.get()
            release_name: str = self.listbox.get_value_at_index(index)

            if callback is not None:
                callback(release_name)

            self.set_loaded_version(release_name)

    def btn_add_command(self, callback: Optional[Callable[[str, str], None]] = None) -> None:
        """
        Callback for the button self.btn_add.

        :param callback: external call back to process added release name.
        :return: None
        """
        release_name: str = self.modpack.get()
        listbox_entries: List[str] = self.listbox.get_values()
        if release_name != "":
            previous_release: Optional[str] = simpledialog.askstring(
                title="Enter the previous modpack version", prompt="Please enter the previous modpack version:"
            )
            if previous_release is None:  # pressed cancel
                return

            # invalid input
            if previous_release not in listbox_entries or previous_release == release_name:
                showerror(
                    "Invalid previous version",
                    "You must provide a valid version corresponding to the previous pack version.",
                )
                return

            if callback is not None:
                callback(release_name, previous_release)

        if release_name not in listbox_entries:
            self.listbox.insert(-1, release_name)

        self.set_loaded_version(release_name)

    def btn_del_command(self, callback: Optional[Callable[[str], None]] = None) -> None:
        """
        Callback for the button self.btn_del.

        :param callback: external call back to process deleted release name.
        :return: None
        """

        if self.listbox.has_selection():
            index: int = self.listbox.get()
            release_name: str = self.listbox.get_value_at_index(index)
            self.listbox.del_value_at_index(index)
            if callback is not None:
                callback(release_name)

    def populate_data(self, data: List[GTNHRelease]) -> None:
        """
        Method called by parent class to populate data in this class.

        :param data: the data to pass to this class
        :return: None
        """
        self.listbox.set_values([release.version for release in data])
