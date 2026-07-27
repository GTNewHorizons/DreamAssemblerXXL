from dataclasses import dataclass
from tkinter import LabelFrame
from tkinter.ttk import LabelFrame as TtkLabelFrame
from typing import Any, Optional

from daxxl.defs import DevRelease, Position
from daxxl.gui.modpack.button_array import ButtonArray, ButtonArrayCallback
from daxxl.gui.modpack.release_list import ReleaseList, ReleaseListCallback
from daxxl.models.gtnh_release import GTNHRelease


@dataclass
class ModpackPanelCallback(ButtonArrayCallback, ReleaseListCallback):
    """
    The union of the button-array and release-list callbacks, with no members of its own.
    """


class ModpackPanel(LabelFrame, TtkLabelFrame):
    """Main frame for managing the releases."""

    def __init__(
        self,
        master: Any,
        frame_name: str,
        callbacks: ModpackPanelCallback,
        width: Optional[int] = None,
        themed: bool = False,
        **kwargs: Any,
    ) -> None:
        """
        Constructor of the ModpackPanel class.

        :param master: the parent widget
        :param frame_name: the name displayed in the framebox
        :param callbacks: a dict of callbacks passed to this instance
        :param width: the width to harmonize widgets in characters
        :param themed: for those who preferred themed versions of the widget. Default to false.
        :param kwargs: params to init the parent class
        """
        self.themed = themed
        if themed:
            TtkLabelFrame.__init__(self, master, text=frame_name, **kwargs)
        else:
            LabelFrame.__init__(self, master, text=frame_name, **kwargs)
        self.xpadding: int = 0
        self.ypadding: int = 0
        self._width: int = width if width is not None else 20  # arbitrary value

        self.callbacks: ModpackPanelCallback = callbacks

        self.action_frame: ButtonArray = ButtonArray(
            self,
            frame_name="Availiable tasks",
            callbacks=self.callbacks,
            update_experimental=self.update_experimental,
            update_daily=self.update_daily,
            themed=self.themed,
        )

        self.modpack_list: ReleaseList = ReleaseList(
            self, frame_name="Modpack Versions", callbacks=self.callbacks, themed=self.themed
        )

    def update_experimental(self) -> None:
        """
        Callback to generate/update the experimental builds.

        :return: None
        """
        self.callbacks.generate_experimental()
        data: list[str] = list(self.modpack_list.listbox.get_values())
        if DevRelease.EXPERIMENTAL.value not in data:
            data.insert(0, DevRelease.EXPERIMENTAL.value)
            self.modpack_list.listbox.set_values(data)

    def update_daily(self) -> None:
        """
        Callback to generate/update the daily builds.

        :return: None
        """
        self.callbacks.generate_daily()
        data: list[str] = list(self.modpack_list.listbox.get_values())
        if DevRelease.DAILY.value not in data:
            data.insert(0, DevRelease.DAILY.value)
            self.modpack_list.listbox.set_values(data)

    def configure_widgets(self) -> None:
        """
        Method to configure the widgets.

        :return: None
        """
        self.modpack_list.configure_widgets()
        self.action_frame.configure_widgets()

    @property
    def width(self) -> int:
        return self._width

    @width.setter
    def width(self, value: int) -> None:
        self._width = value
        self.modpack_list.width = self._width
        self.action_frame.width = self._width

    def update_widget(self) -> None:
        """
        Method to update the widget and update all its childs

        :return: None
        """
        self.hide()
        self.configure_widgets()
        self.show()

    def hide(self) -> None:
        """
        Method to hide the widget and update all its childs
        :return None:
        """
        self.modpack_list.hide()
        self.action_frame.hide()

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

    def populate_data(self, data: list[GTNHRelease]) -> None:
        """
        Method called by parent class to populate data in this class.

        :param data: the data to pass to this class
        :return: None
        """
        self.modpack_list.populate_data(data)
