from tkinter import LabelFrame
from typing import Any, Callable, Dict, List, Optional

from gtnh.defs import Position
from gtnh.gui.modpack.button_array import ButtonArray
from gtnh.gui.modpack.release_list import ReleaseList


class ModpackPanel(LabelFrame):
    """Main frame for managing the releases."""

    def __init__(
        self, master: Any, frame_name: str, callbacks: Dict[str, Any], width: Optional[int] = None, **kwargs: Any
    ) -> None:
        """
        Constructor of the ModpackPanel class.

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
        self.action_frame: ButtonArray = ButtonArray(self, frame_name="Availiable tasks", callbacks=action_callbacks)

        modpack_list_callbacks: Dict[str, Any] = {
            "load": callbacks["load"],
            "delete": callbacks["delete"],
            "add": callbacks["add"],
        }

        self.modpack_list: ReleaseList = ReleaseList(
            self, frame_name="Modpack Versions", callbacks=modpack_list_callbacks
        )

    def update_nightly(self) -> None:
        """
        Callback to generate/update the nightly builds.

        :return: None
        """
        self.generate_nightly_callback()
        data: List[str] = list(self.modpack_list.listbox.get_values())
        if "nightly" not in data:
            data.insert(0, "nightly")
            self.modpack_list.listbox.set_values(data)

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
