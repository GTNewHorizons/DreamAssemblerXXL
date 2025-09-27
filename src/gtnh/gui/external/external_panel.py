import asyncio
from asyncio import Task
from tkinter import LabelFrame, Toplevel
from tkinter.messagebox import showerror
from tkinter.ttk import LabelFrame as TtkLabelFrame
from typing import Any, Callable, Coroutine, Dict, List, Optional

from gtnh.defs import Position, Side
from gtnh.gui.external.mod_adder_window import ModAdderCallback, ModAdderWindow
from gtnh.gui.lib.button import CustomButton
from gtnh.gui.lib.custom_widget import CustomWidget
from gtnh.gui.lib.listbox import CustomListbox
from gtnh.gui.mod_info.mod_info_widget import ModInfoCallback, ModInfoWidget
from gtnh.models.gtnh_version import GTNHVersion
from gtnh.models.mod_info import GTNHModInfo
from gtnh.models.mod_version_info import ModVersionInfo
from gtnh.modpack_manager import GTNHModpackManager


class ExternalPanelCallback(ModInfoCallback):
    def __init__(
        self,
        set_mod_version: Callable[[str, str], None],
        set_mod_side: Callable[[str, Side], Task[None]],
        set_mod_side_default: Callable[[str, str], Task[None]],
        get_gtnh_callback: Callable[[], Coroutine[Any, Any, GTNHModpackManager]],
        get_external_mods_callback: Callable[[], Dict[str, ModVersionInfo]],
        toggle_freeze: Callable[[], None],
        add_mod_in_memory: Callable[[str, str], None],
        del_mod_in_memory: Callable[[str], None],
        refresh_external_modlist: Callable[[], Coroutine[Any, Any, None]],
    ):
        ModInfoCallback.__init__(
            self, set_mod_version=set_mod_version, set_mod_side=set_mod_side, set_mod_side_default=set_mod_side_default
        )
        self.get_gtnh_callback: Callable[[], Coroutine[Any, Any, GTNHModpackManager]] = get_gtnh_callback
        self.get_external_mods_callback: Callable[[], Dict[str, ModVersionInfo]] = get_external_mods_callback
        self.toggle_freeze: Callable[[], None] = toggle_freeze
        self.add_mod_in_memory: Callable[[str, str], None] = add_mod_in_memory
        self.del_mod_in_memory: Callable[[str], None] = del_mod_in_memory
        self.refresh_external_modlist: Callable[[], Coroutine[Any, Any, None]] = refresh_external_modlist


class ExternalPanel(LabelFrame, TtkLabelFrame):  # type: ignore
    """Main frame widget for the external mods' management."""

    def __init__(
        self,
        master: Any,
        frame_name: str,
        callbacks: ExternalPanelCallback,
        width: Optional[int] = None,
        themed: bool = False,
        **kwargs: Any,
    ):
        """
        Constructor of the ExternalPanel class.

        :param master: the parent widget
        :param frame_name: the name displayed in the framebox
        :param callbacks: a dict of callbacks passed to this instance
        :param width: the width to harmonize widgets in characters
        :param themed: for those who prefered themed versions of the widget. Default to false.
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
        self.get_gtnh_callback: Callable[[], Coroutine[Any, Any, GTNHModpackManager]] = callbacks.get_gtnh_callback
        self.get_external_mods_callback: Callable[[], Dict[str, ModVersionInfo]] = callbacks.get_external_mods_callback
        self.toggle_freeze: Callable[[], None] = callbacks.toggle_freeze
        self.add_mod_to_memory: Callable[[str, str], None] = callbacks.add_mod_in_memory
        self.del_mod_from_memory: Callable[[str], None] = callbacks.del_mod_in_memory
        self.refresh_external_modlist: Callable[[], Coroutine[Any, Any, None]] = callbacks.refresh_external_modlist


        self.mod_adder_callbacks: ModAdderCallback = ModAdderCallback(
            get_gtnh_callback=self.get_gtnh_callback,
            add_mod_to_memory=self.add_mod_to_memory,
            del_mod_from_memory=self.del_mod_from_memory,
        )
        self.callbacks = callbacks

        self.mod_info_frame: ModInfoWidget = ModInfoWidget(self, frame_name="External mod info", callbacks=callbacks,
                                                           external_mods=True, mod_adder_callbacks=self.mod_adder_callbacks)
        self.mod_info_callback: Callable[[Any], None] = self.mod_info_frame.populate_data

        self.listbox: CustomListbox = CustomListbox(
            self,
            label_text="External mods:",
            exportselection=False,
            on_selection=lambda event: asyncio.ensure_future(self.on_listbox_click(event)),
            display_horizontal_scrollbar=False,
            themed=self.themed,
        )

        self.callbacks.attach_listbox_object(self.listbox)

        self.btn_add: CustomButton = CustomButton(
            self, text="Add new mod", command=lambda: asyncio.ensure_future(self.add_external_mod()), themed=self.themed
        )

        self.btn_add_version: CustomButton = CustomButton(
            self,
            text="Add new version to highlighted",
            command=lambda: asyncio.ensure_future(self.add_new_version()),
            themed=self.themed,
        )

        self.btn_rem: CustomButton = CustomButton(
            self,
            text="Delete highlighted",
            command=lambda: asyncio.ensure_future(self.del_external_mod()),
            themed=self.themed,
        )

        self.widgets: List[CustomWidget] = [self.btn_add, self.btn_rem, self.btn_add_version, self.listbox]
        self.width: int = (
            width if width is not None else max([widget.get_description_size() for widget in self.widgets])
        )

        if width is None:
            self.mod_info_frame.set_width(self.width)
            self.update_widget()

        else:
            self.mod_info_frame.set_width(self.width)
            self.update_widget()

    def configure_widgets(self) -> None:
        """
        Method to configure the widgets.

        :return: None
        """
        self.mod_info_frame.configure_widgets()
        for widget in self.widgets:
            widget.configure(width=self.width)

    def set_width(self, width: int) -> None:
        """
        Method to set the widgets' width.

        :param width: the new width
        :return: None
        """
        self.width = width
        self.mod_info_frame.set_width(self.width)
        self.configure_widgets()

    def get_width(self) -> int:
        """
        Getter for self.width.

        :return: the width in character sizes of the normalised widgets
        """
        return self.width

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

        self.listbox.grid(row=x, column=y, columnspan=2, sticky=Position.HORIZONTAL)
        self.btn_add.grid(row=x + 1, column=y, sticky=Position.HORIZONTAL)
        self.btn_rem.grid(row=x + 1, column=y + 1, sticky=Position.HORIZONTAL)
        self.btn_add_version.grid(row=x + 2, column=y, sticky=Position.HORIZONTAL)

        self.mod_info_frame.grid(row=x + 3, column=y, columnspan=2)

        self.mod_info_frame.show()

        self.update_idletasks()

    def populate_data(self, data: Any) -> None:
        """
        Method called by parent class to populate data in this class.

        :param data: the data to pass to this class
        :return: None
        """
        mod_list: List[str] = data["external_mod_list"]
        self.listbox.set_values(sorted(mod_list))

    async def on_listbox_click(self, _: Any) -> None:
        """
        Callback used when the user clicks on the external mods' listbox.

        :param _: the tkinter event passed by the tkinter in the Callback (unused)
        :return: None
        """
        if not self.listbox.has_selection():
            return

        index: int = self.listbox.get()
        gtnh: GTNHModpackManager = await self.get_gtnh_callback()
        mod_info: GTNHModInfo = gtnh.assets.get_mod(self.listbox.get_value_at_index(index))
        name: str = mod_info.name
        mod_versions: list[GTNHVersion] = mod_info.versions
        latest_version: Optional[GTNHVersion] = mod_info.get_latest_version()
        assert latest_version
        external_mods: Dict[str, ModVersionInfo] = self.get_external_mods_callback()
        current_version: str = external_mods[name].version if name in external_mods else latest_version.version_tag

        _license: str = mod_info.license or "No license detected"
        side: str = external_mods[name].side if name in external_mods else Side.NONE  # type: ignore
        side_default: str = mod_info.side

        data = {
            "name": name,
            "versions": [version.version_tag for version in mod_versions],
            "current_version": current_version,
            "license": _license,
            "side": side,
            "side_default": side_default,
        }
        self.mod_info_callback(data)

    async def add_external_mod(self) -> None:
        """
        Method called when the button to add an external mod is pressed.

        :return: None
        """

        # showerror("Feature not yet implemented", "The addition of external mods to the assets is not yet implemented.")
        # don't forget to use self.add_mod_in_memory when implementing this
        self.toggle_freeze()
        top_level: Toplevel = Toplevel(self)

        def close(event: Any = None) -> None:
            """
            Method called when toplevel is destroyed.

            :return: None
            """
            if event.widget is top_level:
                self.toggle_freeze()
                asyncio.ensure_future(self.refresh_external_modlist())  # type: ignore

        top_level.bind("<Destroy>", close)

        mod_addition_frame: ModAdderWindow = ModAdderWindow(
            master=top_level, frame_name="external mod adder", callbacks=self.mod_adder_callbacks, width=None,
            mod_name=None, themed=self.themed
        )
        mod_addition_frame.populate_data(mod=None)

        mod_addition_frame.grid()
        mod_addition_frame.update_widget()
        top_level.title("External mod addition")

    async def del_external_mod(self) -> None:
        """
        Method called when the button to delete the highlighted external mod is pressed.

        :return: None
        """
        # showerror("Feature not yet implemented", "The removal of external mods from assets is not yet implemented.")
        # don't forget to use self.del_mod_from_memory when implementing this
        if not self.listbox.has_selection():
            showerror(
                "No curseforge mod selected",
                "In order to add a new version to a curseforge mod, you must select one first",
            )
            return

        index: int = self.listbox.get()
        mod_name: str = self.listbox.get_value_at_index(index)
        gtnh: GTNHModpackManager = await self.get_gtnh_callback()
        self.listbox.del_value_at_index(index)
        await gtnh.delete_mod(mod_name)


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
                asyncio.ensure_future(self.refresh_external_modlist())  # type: ignore

        top_level.bind("<Destroy>", close)

        mod_addition_frame: ModAdderWindow = ModAdderWindow(
            top_level,
            "external version adder",
            callbacks=self.mod_adder_callbacks,
            mod_name=mod_name,
            themed=self.themed,
        )
        gtnh = await self.get_gtnh_callback()
        data = gtnh.assets.get_mod(mod_name)
        mod_addition_frame.populate_data(mod=data)
        mod_addition_frame.grid()
        mod_addition_frame.update_widget()
        top_level.title("New version")

