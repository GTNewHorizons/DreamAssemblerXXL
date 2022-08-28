import asyncio
from tkinter import Button, LabelFrame, Listbox, Scrollbar, StringVar, END
from tkinter.messagebox import showerror
from typing import Any, Callable, Coroutine, Dict, Optional, List

from gtnh.defs import Position
from gtnh.gui.mod_info_frame import ModInfoFrame
from gtnh.models.gtnh_version import GTNHVersion
from gtnh.models.mod_info import GTNHModInfo, ExternalModInfo
from gtnh.modpack_manager import GTNHModpackManager


class ExternalModList(LabelFrame):
    """Widget handling the list of external mods."""

    def __init__(
        self, master: Any, frame_name: str, callbacks: Dict[str, Any], width: Optional[int] = None, **kwargs: Any
    ):
        """
        Constructor of the ExternalModList class.

        :param master: the parent widget
        :param frame_name: the name displayed in the framebox
        :param callbacks: a dict of callbacks passed to this instance
        :param width: the width to harmonize widgets in characters
        :param kwargs: params to init the parent class
        """
        LabelFrame.__init__(self, master, text=frame_name, **kwargs)
        self.ypadding: int = 0
        self.xpadding: int = 0

        self.btn_add_text: str = "add new"
        self.btn_rem_text: str = "delete highlighted"

        self.get_gtnh_callback: Callable[[], Coroutine[Any, Any, GTNHModpackManager]] = callbacks["get_gtnh"]
        self.get_external_mods_callback: Callable[[], Dict[str, str]] = callbacks["get_external_mods"]
        self.mod_info_callback: Callable[[Any], None] = callbacks["mod_info"]

        self.width: int = width if width is not None else max(len(self.btn_add_text), len(self.btn_rem_text))

        self.sv_repo_name: StringVar = StringVar(self, value="")

        self.lb_mods: Listbox = Listbox(self, exportselection=False)
        self.lb_mods.bind("<<ListboxSelect>>", lambda event: asyncio.ensure_future(self.on_listbox_click(event)))

        self.btn_add: Button = Button(
            self, text="add new", command=lambda: asyncio.ensure_future(self.add_external_mod())
        )

        self.btn_rem: Button = Button(
            self, text="delete highlighted", command=lambda: asyncio.ensure_future(self.del_external_mod())
        )

        self.scrollbar: Scrollbar = Scrollbar(self)
        self.lb_mods.configure(yscrollcommand=self.scrollbar.set)
        self.scrollbar.configure(command=self.lb_mods.yview)

    def configure_widgets(self) -> None:
        """
        Method to configure the widgets.

        :return: None
        """
        self.btn_add.configure(width=self.width)
        self.btn_rem.configure(width=self.width)

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
        self.lb_mods.grid_forget()
        self.scrollbar.grid_forget()
        self.btn_add.grid_forget()
        self.btn_rem.grid_forget()

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

        for i in range(rows):
            self.rowconfigure(i, weight=1, pad=self.xpadding)

        for i in range(columns):
            self.columnconfigure(i, weight=1, pad=self.ypadding)

        self.lb_mods.grid(row=x, column=y, columnspan=2, sticky=Position.HORIZONTAL)
        self.scrollbar.grid(row=x, column=y + 2, sticky=Position.VERTICAL)
        self.btn_add.grid(row=x + 1, column=y)
        self.btn_rem.grid(row=x + 1, column=y + 1, columnspan=2)

        self.update_idletasks()

    async def del_external_mod(self) -> None:
        """
        Method called when the button to delete the highlighted external mod is pressed.

        :return: None
        """
        showerror("Feature not yet implemented", "The removal of external mods from assets is not yet implemented.")

    async def add_external_mod(self) -> None:
        """
        Method called when the button to add an external mod is pressed.

        :return: None
        """
        showerror("Feature not yet implemented", "The addition of external mods to the assets is not yet implemented.")

    def populate_data(self, data: Any) -> None:
        """
        Method called by parent class to populate data in this class.

        :param data: the data to pass to this class
        :return: None
        """

        self.lb_mods.insert(END, *sorted(data))

    async def on_listbox_click(self, event):
        """
        Callback used when the user clicks on the external mods' listbox.

        :param event: the tkinter event passed by the tkinter in the Callback (unused)
        :return: None
        """

        index: int = self.lb_mods.curselection()[0]
        gtnh: GTNHModpackManager = await self.get_gtnh_callback()
        mod_info: ExternalModInfo = gtnh.assets.get_external_mod(self.lb_mods.get(index))
        name: str = mod_info.name
        mod_versions: list[GTNHVersion] = mod_info.versions
        latest_version: Optional[GTNHVersion] = mod_info.get_latest_version()
        assert latest_version
        current_version: str = (
            self.get_external_mods_callback()[name]
            if name in self.get_external_mods_callback()
            else latest_version.version_tag
        )
        license: str = mod_info.license or "No license detected"
        side: str = mod_info.side

        data = {
            "name": name,
            "versions": [version.version_tag for version in mod_versions],
            "current_version": current_version,
            "license": license,
            "side": side,
        }
        self.mod_info_callback(data)


class ExternalModFrame(LabelFrame):
    """Main frame widget for the external mods' management."""

    def __init__(
        self, master: Any, frame_name: str, callbacks: Dict[str, Any], width: Optional[int] = None, **kwargs: Any
    ):
        """
        Constructor of the ExternalModFrame class.

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
        self.mod_info_frame: ModInfoFrame = ModInfoFrame(
            self, frame_name="external mod info", callbacks=mod_info_callbacks
        )

        external_mod_list_callbacks: Dict[str, Any] = {
            "get_gtnh": callbacks["get_gtnh"],
            "get_external_mods": callbacks["get_external_mods"],
            "mod_info": self.mod_info_frame.populate_data
        }

        self.external_mod_list: ExternalModList = ExternalModList(
            self, frame_name="external mod list", callbacks=external_mod_list_callbacks
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

