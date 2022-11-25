import asyncio
from tkinter import  Button, Label, LabelFrame, StringVar
from tkinter.messagebox import  showinfo
from tkinter.ttk import Combobox
from typing import Any, Callable, Coroutine, Dict, Optional

from gtnh.defs import Position
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
        modpack_version_text: str = "Modpack version:"
        refresh_modpack_text: str = "Refresh modpack assets"
        self.width: int = width if width is not None else max(len(modpack_version_text), len(refresh_modpack_text))
        self.label_modpack_version: Label = Label(self, text=modpack_version_text)
        self.sv_version: StringVar = StringVar(value="")
        self.cb_modpack_version: Combobox = Combobox(self, textvariable=self.sv_version, values=[])
        self.cb_modpack_version.bind(
            "<<ComboboxSelected>>", lambda event: callbacks["set_modpack_version"](self.sv_version.get())
        )
        self.btn_refresh: Button = Button(
            self, text=refresh_modpack_text, command=lambda: asyncio.ensure_future(self.refresh_modpack_assets())
        )
        self.get_gtnh_callback: Callable[[], Coroutine[Any, Any, GTNHModpackManager]] = callbacks["get_gtnh"]

    async def refresh_modpack_assets(self) -> None:
        """
        Method used to refresh assets for the modpack repository.

        :return: None
        """
        gtnh: GTNHModpackManager = await self.get_gtnh_callback()
        await gtnh.regen_config_assets()
        self.cb_modpack_version["values"] = [version.version_tag for version in gtnh.assets.config.versions]
        self.sv_version.set(gtnh.assets.config.latest_version)
        showinfo("Modpack assets refreshed", "Modpack assets refreshed successfully!")

    def configure_widgets(self) -> None:
        """
        Method to configure the widgets.

        :return: None
        """
        self.label_modpack_version.configure(width=self.width)
        self.cb_modpack_version.configure(width=self.width)

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
        self.label_modpack_version.grid_forget()
        self.cb_modpack_version.grid_forget()
        self.btn_refresh.grid_forget()

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

        self.label_modpack_version.grid(row=x, column=y)
        self.cb_modpack_version.grid(row=x, column=y + 1, sticky=Position.HORIZONTAL)
        self.btn_refresh.grid(row=x + 1, column=y + 1, sticky=Position.HORIZONTAL)

    def populate_data(self, data: Dict[str, Any]) -> None:
        """
        Method called by parent class to populate data in this class.

        :param data: the data to pass to this class
        :return: None
        """
        self.cb_modpack_version["values"] = data["combobox"]
        self.sv_version.set(data["stringvar"])
