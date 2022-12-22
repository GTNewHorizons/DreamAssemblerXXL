"""Module providing a widget for the external mod management in DAXXL."""
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
    """ModAdderCallback class. The goal of this class is to provide a type for the ExternalPanel callbacks."""

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
        """
        Construct the ExternalPanelCallback class.

        Parameters
        ----------
        set_mod_version: Callable[[str, str], None]
            Callback used to set the version of a mod in the current release.

        set_mod_side: Callable[[str, Side], Task[None]]
            Callback used to set the side of a mod.

        set_mod_side_default: Callable[[str, str], Task[None]]
            Callback used to set the default side for a mod.

        get_gtnh_callback: Callable[[], Coroutine[Any, Any, GTNHModpackManager]]
            Callback used to retrieve the modpack manager instance.

        get_external_mods_callback: Callable[[], Dict[str, ModVersionInfo]]
            Callback used to retrieve the external mods from the assets.

        toggle_freeze: Callable[[], None]
            Callback used to (un)freeze the GUI to prevent any interaction in the GUI while performing a task.

        add_mod_to_memory: Callable[[str, str], None]
            Callback used to add a mod in DAXXL's memory.

        del_mod_from_memory: Callable[[str], None]
            Callback used to delete a mod from DAXXL's memory.

        refresh_external_modlist: Callable[[], Coroutine[Any, Any, None]]
            Callback used to refresh the external modlist.
        """
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
        Construct the ExternalPanel class.

        Parameters
        ----------
        master: Any
            The parent widget.

        frame_name: str
            The name displayed in the framebox.

        callbacks: ExternalPanelCallback
            The callbacks passed to this instance.

        width: Optional[int]
            If provided, the width used to harmonize the child widgets.

        themed: bool
            If True, use the themed ttk widgets. Use normal widgets otherwise.

        kwargs: Any
            Keyword parameters passed to the constructor of the parent class.
        """
        self.themed: bool = themed
        self.ypadding: int = 0
        self.xpadding: int = 0
        if themed:
            LabelFrame.__init__(self, master, text=frame_name, **kwargs)
        else:
            TtkLabelFrame.__init__(self, master, text=frame_name, **kwargs)

        self.callbacks = callbacks

        self.mod_info_frame: ModInfoWidget = ModInfoWidget(self, frame_name="External mod info", callbacks=callbacks)

        # start
        self.get_gtnh_callback: Callable[[], Coroutine[Any, Any, GTNHModpackManager]] = callbacks.get_gtnh_callback
        self.get_external_mods_callback: Callable[[], Dict[str, ModVersionInfo]] = callbacks.get_external_mods_callback
        self.toggle_freeze: Callable[[], None] = callbacks.toggle_freeze
        self.add_mod_to_memory: Callable[[str, str], None] = callbacks.add_mod_in_memory
        self.del_mod_from_memory: Callable[[str], None] = callbacks.del_mod_in_memory
        self.refresh_external_modlist: Callable[[], Coroutine[Any, Any, None]] = callbacks.refresh_external_modlist

        self.mod_info_callback: Callable[[Any], None] = self.mod_info_frame.populate_data

        self.mod_adder_callbacks: ModAdderCallback = ModAdderCallback(
            get_gtnh_callback=self.get_gtnh_callback,
            add_mod_to_memory=self.add_mod_to_memory,
            del_mod_from_memory=self.del_mod_from_memory,
        )

        self.listbox: CustomListbox = CustomListbox(
            self,
            label_text="External mods:",
            exportselection=False,
            on_selection=lambda event: asyncio.ensure_future(self.on_listbox_click(event)),
            display_horizontal_scrollbar=False,
            themed=self.themed,
        )

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
        Configure the widgets.

        Returns
        -------
        None.
        """
        self.mod_info_frame.configure_widgets()
        for widget in self.widgets:
            widget.configure(width=self.width)

    def set_width(self, width: int) -> None:
        """
        Set the widgets' width.

        Parameters
        ----------
        width: int
            The new width to apply.

        Returns
        -------
        None.
        """
        self.width = width
        self.mod_info_frame.set_width(self.width)
        self.configure_widgets()

    def get_width(self) -> int:
        """
        Get self.width, the width applied to all the widgets.

        Returns
        -------
        The width applied to the widgets.
        """
        return self.width

    def update_widget(self) -> None:
        """
        Update the widget and all its childs.

        Returns
        -------
        None.
        """
        self.hide()
        self.configure_widgets()
        self.show()

        self.mod_info_frame.update_widget()

    def hide(self) -> None:
        """
        Hide the widget and all its childs.

        Returns
        -------
        None.
        """
        for widget in self.widgets:
            widget.grid_forget()
        self.mod_info_frame.grid_forget()

        self.mod_info_frame.hide()

        self.update_idletasks()

    def show(self) -> None:
        """
        Display the widgets and its child widgets, as well as configuring the "responsiveness" of the widgets.

        Returns
        -------
        None.
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
        Populate data in this instance.

        Called by the parent class.

        Parameters
        ----------
        data: Any
            The data used to populate the instance of the class.

        Returns
        -------
        None.
        """
        mod_list: List[str] = data["external_mod_list"]
        self.listbox.set_values(sorted(mod_list))

    async def on_listbox_click(self, _: Any) -> None:
        """
        React to the user's clicks on the external mods' listbox.

        Parameters
        ----------
        _: Any
            The event passed. Unused.

        Returns
        -------
        None.
        """
        if self.listbox.has_selection():
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
        Add an external mod when the button is pressed.

        Returns
        -------
        None.
        """
        # showerror("Feature not yet implemented", "The addition of external mods to the assets is not yet implemented.")
        # don't forget to use self.add_mod_in_memory when implementing this
        self.toggle_freeze()
        top_level: Toplevel = Toplevel(self)

        def close(event: Any = None) -> None:
            """
            React when the toplevel is destroyed.

            Parameters
            ----------
            event: Optional[None]
                The event triggering this function.

            Returns
            -------
            None.
            """
            if event.widget is top_level:
                self.toggle_freeze()
                asyncio.ensure_future(self.refresh_external_modlist())  # type: ignore

        top_level.bind("<Destroy>", close)

        mod_addition_frame: ModAdderWindow = ModAdderWindow(
            top_level, "external mod adder", callbacks=self.mod_adder_callbacks, themed=self.themed
        )
        mod_addition_frame.grid()
        mod_addition_frame.update_widget()
        top_level.title("External mod addition")

    async def del_external_mod(self) -> None:
        """
        Delete the highlighted external mod when the user click on the associated button.

        Returns
        -------
        None.
        """
        # showerror("Feature not yet implemented", "The removal of external mods from assets is not yet implemented.")
        # don't forget to use self.del_mod_from_memory when implementing this
        if self.listbox.has_selection():
            index: int = self.listbox.get()
            mod_name: str = self.listbox.get_value_at_index(index)
            gtnh: GTNHModpackManager = await self.get_gtnh_callback()
            self.listbox.del_value_at_index(index)
            await gtnh.delete_mod(mod_name)
        else:
            showerror(
                "No curseforge mod selected",
                "In order to add a new version to a curseforge mod, you must select one first",
            )
            return

    async def add_new_version(self) -> None:
        """
        Add a new version to an external mod when the associated button is pressed.

        Returns
        -------
        None.
        """
        if self.listbox.has_selection():
            index: int = self.listbox.get()
            mod_name: str = self.listbox.get_value_at_index(index)
            self.toggle_freeze()
            top_level: Toplevel = Toplevel(self)

            def close(event: Any = None) -> None:
                """
                React when the toplevel is destroyed.

                Parameters
                ----------
                event: Optional[None]
                    The event triggering this function.

                Returns
                -------
                None.
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
            mod_addition_frame.grid()
            mod_addition_frame.update_widget()
            top_level.title("External mod addition")
        else:
            showerror(
                "No curseforge mod selected",
                "In order to add a new version to a curseforge mod, you must select one first",
            )
            return
