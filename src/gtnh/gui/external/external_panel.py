from tkinter import LabelFrame
from typing import Any, Dict, List, Optional

from gtnh.gui.external.external_modlist import ExternalModList
from gtnh.gui.mod_info.mod_info_widget import ModInfoWidget


class ExternalPanel(LabelFrame):
    """Main frame widget for the external mods' management."""

    def __init__(
        self, master: Any, frame_name: str, callbacks: Dict[str, Any], width: Optional[int] = None, **kwargs: Any
    ):
        """
        Constructor of the ExternalPanel class.

        :param master: the parent widget
        :param frame_name: the name displayed in the framebox
        :param callbacks: a dict of callbacks passed to this instance
        :param width: the width to harmonize widgets in characters
        :param kwargs: params to init the parent class
        """
        self.ypadding: int = 0
        self.xpadding: int = 0
        LabelFrame.__init__(self, master, text=frame_name, **kwargs)

        self.width: Optional[int] = width

        mod_info_callbacks: Dict[str, Any] = {
            "set_mod_version": callbacks["set_external_mod_version"],
            "set_mod_side": callbacks["set_external_mod_side"],
        }
        self.mod_info_frame: ModInfoWidget = ModInfoWidget(
            self, frame_name="External mod info", callbacks=mod_info_callbacks
        )

        external_mod_list_callbacks: Dict[str, Any] = {
            "get_gtnh": callbacks["get_gtnh"],
            "get_external_mods": callbacks["get_external_mods"],
            "mod_info": self.mod_info_frame.populate_data,
            "add_mod_in_memory": callbacks["add_mod_in_memory"],
            "del_mod_in_memory": callbacks["del_mod_in_memory"],
            "freeze": callbacks["freeze"],
            "refresh_external_mods": callbacks["refresh_external_mods"],
        }

        self.external_mod_list: ExternalModList = ExternalModList(
            self, frame_name="External mod list", callbacks=external_mod_list_callbacks
        )

        if self.width is None:
            self.width = self.external_mod_list.get_width()
            self.mod_info_frame.set_width(self.width)
            self.update_widget()

        else:
            self.mod_info_frame.set_width(self.width)
            self.external_mod_list.set_width(self.width)

    def configure_widgets(self) -> None:
        """
        Method to configure the widgets.

        :return: None
        """
        self.mod_info_frame.configure_widgets()
        self.external_mod_list.configure_widgets()

    def set_width(self, width: int) -> None:
        """
        Method to set the widgets' width.

        :param width: the new width
        :return: None
        """
        self.width = width
        self.mod_info_frame.set_width(self.width)
        self.external_mod_list.set_width(self.width)

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

        self.external_mod_list.update_widget()
        self.mod_info_frame.update_widget()

    def hide(self) -> None:
        """
        Method to hide the widget and all its childs
        :return None:
        """
        self.external_mod_list.grid_forget()
        self.mod_info_frame.grid_forget()

        self.external_mod_list.hide()
        self.mod_info_frame.hide()

        self.update_idletasks()

    def show(self) -> None:
        """
        Method used to display widgets and child widgets, as well as to configure the "responsiveness" of the widgets.

        :return: None
        """
        x: int = 0
        y: int = 0
        rows: int = 2
        columns: int = 1

        for i in range(rows):
            self.rowconfigure(i, weight=1, pad=self.xpadding)

        for i in range(columns):
            self.columnconfigure(i, weight=1, pad=self.ypadding)

        self.external_mod_list.grid(row=x, column=y)
        self.mod_info_frame.grid(row=x + 1, column=y)

        self.external_mod_list.show()
        self.mod_info_frame.show()

        self.update_idletasks()

    def populate_data(self, data: Any) -> None:
        """
        Method called by parent class to populate data in this class.

        :param data: the data to pass to this class
        :return: None
        """
        mod_list: List[str] = data["external_mod_list"]
        self.external_mod_list.populate_data(mod_list)
