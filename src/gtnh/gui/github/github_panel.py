from tkinter import LabelFrame
from typing import Any, Dict, Optional

from gtnh.defs import Position
from gtnh.gui.github.github_modlist import GithubModList
from gtnh.gui.github.modpack_version import ModpackVersion
from gtnh.gui.mod_info_frame import ModInfoFrame


class GithubPanel(LabelFrame):
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

        self.modpack_version_frame: ModpackVersion = ModpackVersion(
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
            "add_mod_in_memory": callbacks["add_mod_in_memory"],
            "del_mod_in_memory": callbacks["del_mod_in_memory"],
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
