import asyncio
from tkinter import LabelFrame
from tkinter.messagebox import showinfo
from typing import Any, Callable, Coroutine, Dict, Optional

from gtnh.defs import Position
from gtnh.gui.lib.button import CustomButton
from gtnh.gui.lib.combo_box import CustomCombobox
from gtnh.modpack_manager import GTNHModpackManager


class ModpackVersion(LabelFrame):
    """
    Frame to chose the gtnh modpack repo assets' version.
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
        Constructor of the ModpackVersionFrame.

        :param master: the parent widget
        :param frame_name: the name displayed in the framebox
        :param callbacks: a dict of callbacks passed to this instance
        :param width: the width to harmonize widgets in characters
        :param kwargs: params to init the parent class
        """
        LabelFrame.__init__(self, master, text=frame_name, **kwargs)
        self.ypadding: int = 0
        self.xpadding: int = 0

        self.modpack_version: CustomCombobox = CustomCombobox(self, label_text="Modpack version:", values=[])
        self.modpack_version.set_on_selection_callback(lambda event: callbacks["set_modpack_version"](self.modpack_version.get()))

        self.btn_refresh: CustomButton = CustomButton(
            self, text="Refresh modpack assets", command=lambda: asyncio.ensure_future(self.refresh_modpack_assets())
        )
        self.widgets = [self.modpack_version, self.btn_refresh]

        self.width: int = width if width is not None else max([widget.get_description_size() for widget in self.widgets])

        self.get_gtnh_callback: Callable[[], Coroutine[Any, Any, GTNHModpackManager]] = callbacks["get_gtnh"]

    async def refresh_modpack_assets(self) -> None:
        """
        Method used to refresh assets for the modpack repository.

        :return: None
        """
        gtnh: GTNHModpackManager = await self.get_gtnh_callback()
        await gtnh.regen_config_assets()
        self.modpack_version.set_values([version.version_tag for version in gtnh.assets.config.versions])
        self.modpack_version.set(gtnh.assets.config.latest_version)

        showinfo("Modpack assets refreshed", "Modpack assets refreshed successfully!")

    def configure_widgets(self) -> None:
        """
        Method to configure the widgets.

        :return: None
        """
        for widget in self.widgets:
            widget.configure(width=self.width)

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
        rows: int = 2
        columns: int = 2

        for i in range(rows):
            self.rowconfigure(i, weight=1, pad=self.xpadding)

        for i in range(columns):
            self.columnconfigure(i, weight=1, pad=self.ypadding)

        self.modpack_version.grid(row=x, column=y, columnspan=2, sticky=Position.HORIZONTAL)
        self.btn_refresh.grid(row=x + 1, column=y + 1, sticky=Position.HORIZONTAL)

    def populate_data(self, data: Dict[str, Any]) -> None:
        """
        Method called by parent class to populate data in this class.

        :param data: the data to pass to this class
        :return: None
        """
        self.modpack_version.set_values(data["combobox"])
        self.modpack_version.set(data["stringvar"])
