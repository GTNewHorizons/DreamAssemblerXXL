import asyncio
from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from tkinter import LabelFrame, Toplevel
from tkinter.messagebox import showerror
from tkinter.ttk import LabelFrame as TtkLabelFrame
from typing import Any

from daxxl.app_context import AppContext
from daxxl.defs import Position, Side
from daxxl.exceptions import InvalidModVersionException
from daxxl.gui.external.mod_adder_window import ModAdderCallback, ModAdderWindow
from daxxl.gui.lib.button import CustomButton
from daxxl.gui.lib.custom_widget import CustomWidget
from daxxl.gui.lib.listbox import CustomListbox
from daxxl.gui.mod_info.mod_info_widget import ModInfoCallback, ModInfoData, ModInfoWidget
from daxxl.models.gtnh_version import GTNHVersion
from daxxl.models.mod_info import GTNHModInfo
from daxxl.models.mod_version_info import ModVersionInfo


@dataclass
class ExternalPanelCallback(ModInfoCallback):
    get_context_callback: Callable[[], Coroutine[Any, Any, AppContext]]
    get_external_mods_callback: Callable[[], dict[str, ModVersionInfo]]
    toggle_freeze: Callable[[], None]
    add_mod_in_memory: Callable[[str, str], None]
    delete_mod_in_memory: Callable[[str], None]
    refresh_external_modlist: Callable[[], Coroutine[Any, Any, None]]


class ExternalPanel(LabelFrame, TtkLabelFrame):
    """Main frame widget for the external mods' management."""

    def __init__(
        self,
        master: Any,
        frame_name: str,
        callbacks: ExternalPanelCallback,
        width: int | None = None,
        themed: bool = False,
        **kwargs: Any,
    ):
        """
        Constructor of the ExternalPanel class.

        :param master: the parent widget
        :param frame_name: the name displayed in the framebox
        :param callbacks: a dict of callbacks passed to this instance
        :param width: the width to harmonize widgets in characters
        :param themed: for those who preferred themed versions of the widget. Default to false.
        :param kwargs: params to init the parent class
        """
        self.themed: bool = themed
        self.ypadding: int = 0
        self.xpadding: int = 0
        if themed:
            LabelFrame.__init__(self, master, text=frame_name, **kwargs)
        else:
            TtkLabelFrame.__init__(self, master, text=frame_name, **kwargs)

        # start
        self.get_context_callback: Callable[[], Coroutine[Any, Any, AppContext]] = callbacks.get_context_callback
        self.get_external_mods_callback: Callable[[], dict[str, ModVersionInfo]] = callbacks.get_external_mods_callback
        self.toggle_freeze: Callable[[], None] = callbacks.toggle_freeze
        self.add_mod_to_memory: Callable[[str, str], None] = callbacks.add_mod_in_memory
        self.delete_mod_from_memory: Callable[[str], None] = callbacks.delete_mod_in_memory
        self.refresh_external_modlist: Callable[[], Coroutine[Any, Any, None]] = callbacks.refresh_external_modlist

        self.mod_adder_callbacks: ModAdderCallback = ModAdderCallback(
            get_context_callback=self.get_context_callback,
            add_mod_to_memory=self.add_mod_to_memory,
            delete_mod_from_memory=self.delete_mod_from_memory,
        )
        self.callbacks = callbacks

        self.mod_info_frame: ModInfoWidget = ModInfoWidget(
            self,
            frame_name="External mod info",
            callbacks=callbacks,
            external_mods=True,
            mod_adder_callbacks=self.mod_adder_callbacks,
        )
        self.mod_info_callback: Callable[[ModInfoData], None] = self.mod_info_frame.populate_data

        self.listbox: CustomListbox = CustomListbox(
            self,
            label_text="External mods:",
            exportselection=False,
            on_selection=lambda event: asyncio.ensure_future(self.on_listbox_click(event)),
            display_horizontal_scrollbar=False,
            themed=self.themed,
        )

        self.callbacks.attach_listbox_object(self.listbox)

        self.btn_add: CustomButton = CustomButton(self, text="Add new mod", command=lambda: asyncio.ensure_future(self.add_external_mod()), themed=self.themed)

        self.btn_add_version: CustomButton = CustomButton(
            self,
            text="Add new version to highlighted",
            command=lambda: asyncio.ensure_future(self.add_new_version()),
            themed=self.themed,
        )

        self.btn_rem: CustomButton = CustomButton(
            self,
            text="Delete highlighted",
            command=lambda: asyncio.ensure_future(self.delete_external_mod()),
            themed=self.themed,
        )

        self.widgets: list[CustomWidget] = [self.btn_add, self.btn_rem, self.btn_add_version, self.listbox]
        self._width: int = width if width is not None else max([widget.description_size for widget in self.widgets])

        self.mod_info_frame.width = self._width
        self.update_widget()

    def configure_widgets(self) -> None:
        """
        Method to configure the widgets.

        :return: None
        """
        self.mod_info_frame.configure_widgets()
        for widget in self.widgets:
            widget.configure(width=self._width)

    @property
    def width(self) -> int:
        return self._width

    @width.setter
    def width(self, value: int) -> None:
        self._width = value
        self.mod_info_frame.width = self._width
        self.configure_widgets()

    def update_widget(self) -> None:
        """
        Method to update the widget and update all its childs

        :return: None
        """
        self.hide()
        self.configure_widgets()
        self.show()

        self.mod_info_frame.update_widget()

    def hide(self) -> None:
        """
        Method to hide the widget and update all its childs
        :return None:
        """
        for widget in self.widgets:
            widget.grid_forget()
        self.mod_info_frame.grid_forget()

        self.mod_info_frame.hide()

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

        self.listbox.grid(row=x, column=y, columnspan=2, sticky=Position.HORIZONTAL)
        self.btn_add.grid(row=x + 1, column=y, sticky=Position.HORIZONTAL)
        self.btn_rem.grid(row=x + 1, column=y + 1, sticky=Position.HORIZONTAL)
        self.btn_add_version.grid(row=x + 2, column=y, sticky=Position.HORIZONTAL)

        self.mod_info_frame.grid(row=x + 3, column=y, columnspan=2)

        self.mod_info_frame.show()

    def populate_data(self, external_mod_list: list[str]) -> None:
        """
        Method called by parent class to populate data in this class.

        :param external_mod_list: the names of the external mods known to the assets
        :return: None
        """
        self.listbox.set_values(sorted(external_mod_list))

    async def on_listbox_click(self, _: Any) -> None:
        """
        Callback used when the user clicks on the external mods' listbox.

        :param _: the tkinter event passed by the tkinter in the Callback (unused)
        :return: None
        """
        if not self.listbox.has_selection():
            return

        index: int = self.listbox.get()
        context: AppContext = await self.get_context_callback()
        mod_info: GTNHModInfo = context.assets.get_mod(self.listbox.get_value_at_index(index))
        name: str = mod_info.name
        mod_versions: list[GTNHVersion] = mod_info.versions
        latest_version: GTNHVersion | None = mod_info.get_latest_version()
        if latest_version is None:
            raise InvalidModVersionException
        external_mods: dict[str, ModVersionInfo] = self.get_external_mods_callback()
        current_version: str = external_mods[name].version if name in external_mods else latest_version.version_tag

        _license: str = mod_info.license or "No license detected"
        side: Side | None = external_mods[name].side if name in external_mods else Side.NONE
        side_default: Side = mod_info.side

        data = ModInfoData(
            name=name,
            versions=[version.version_tag for version in mod_versions],
            current_version=current_version,
            license=_license,
            side=side,
            side_default=side_default,
        )
        self.mod_info_callback(data)

    async def add_external_mod(self) -> None:
        """
        Method called when the button to add an external mod is pressed.

        :return: None
        """
        self.toggle_freeze()
        top_level: Toplevel = Toplevel(self)

        def close(event: Any = None) -> None:
            """
            Method called when toplevel is destroyed.

            :return: None
            """
            if event.widget is top_level:
                self.toggle_freeze()
                asyncio.ensure_future(self.refresh_external_modlist())

        top_level.bind("<Destroy>", close)

        mod_addition_frame: ModAdderWindow = ModAdderWindow(
            master=top_level,
            frame_name="external mod adder",
            callbacks=self.mod_adder_callbacks,
            width=None,
            mod_name=None,
            themed=self.themed,
        )
        mod_addition_frame.populate_data(mod=None)

        mod_addition_frame.grid()
        mod_addition_frame.update_widget()
        top_level.title("External mod addition")

    async def delete_external_mod(self) -> None:
        """
        Method called when the button to delete the highlighted external mod is pressed.

        :return: None
        """
        if not self.listbox.has_selection():
            showerror(
                "No curseforge mod selected",
                "In order to add a new version to a curseforge mod, you must select one first",
            )
            return

        index: int = self.listbox.get()
        mod_name: str = self.listbox.get_value_at_index(index)
        context: AppContext = await self.get_context_callback()
        self.listbox.delete_value_at_index(index)
        await context.asset_service.delete_mod(mod_name)

    async def add_new_version(self) -> None:
        """
        Method called when the button to add a new version to an external mod is pressed.

        :return: None
        """
        if not self.listbox.has_selection():
            showerror(
                "No curseforge mod selected",
                "In order to add a new version to a curseforge mod, you must select one first",
            )
            return

        index: int = self.listbox.get()
        mod_name: str = self.listbox.get_value_at_index(index)
        self.toggle_freeze()
        top_level: Toplevel = Toplevel(self)

        def close(event: Any = None) -> None:
            """
            Method called when toplevel is destroyed.

            :return: None
            """
            if event.widget is top_level:
                self.toggle_freeze()
                asyncio.ensure_future(self.refresh_external_modlist())

        top_level.bind("<Destroy>", close)

        mod_addition_frame: ModAdderWindow = ModAdderWindow(
            top_level,
            "external version adder",
            callbacks=self.mod_adder_callbacks,
            mod_name=mod_name,
            themed=self.themed,
        )
        context = await self.get_context_callback()
        data = context.assets.get_mod(mod_name)
        mod_addition_frame.populate_data(mod=data)
        mod_addition_frame.grid()
        mod_addition_frame.update_widget()
        top_level.title("New version")
