import asyncio
from asyncio import Task
from tkinter import LabelFrame, Toplevel
from tkinter.messagebox import showerror
from tkinter.ttk import LabelFrame as TtkLabelFrame
from typing import Any, Callable, List, Optional

from gtnh.defs import Side
from gtnh.gui.external.mod_adder_window import ModAdderCallback, ModAdderWindow
from gtnh.gui.lib.CustomLabel import CustomLabel
from gtnh.gui.lib.button import CustomButton
from gtnh.gui.lib.combo_box import CustomCombobox
from gtnh.gui.lib.custom_widget import CustomWidget
from gtnh.gui.lib.listbox import CustomListbox

USE_DEFAULT = "NOT SET"


class ModInfoCallback:
    def __init__(
        self,
        set_mod_version: Callable[[str, str], None],
        set_mod_side: Callable[[str, Side], Task[None]],
        set_mod_side_default: Callable[[str, str], Task[None]],
    ):
        self.set_mod_version: Callable[[str, str], None] = set_mod_version
        self.set_mod_side: Callable[[str, Side], Task[None]] = set_mod_side
        self.set_mod_side_default: Callable[[str, str], Task[None]] = set_mod_side_default
        self.has_listbox_selection: CustomListbox = None  # type: ignore

    def attach_listbox_object(self, listbox: CustomListbox) -> None:
        self.listbox = listbox


class ModInfoWidget(LabelFrame, TtkLabelFrame):  # type: ignore
    """
    Widget used to display info about a mod passed to it.
    """

    def __init__(
        self,
        master: Any,
        frame_name: str,
        callbacks: ModInfoCallback,
        width: Optional[int] = None,
        themed: bool = False,
        external_mods: bool = False,
        mod_adder_callbacks: Optional[ModAdderCallback] = None,
        **kwargs: Any,
    ) -> None:
        """
        Constructor of the ModInfoWidget class.

        :param master: the parent widget
        :param frame_name: the name displayed in the framebox
        :param callbacks: a dict of callbacks passed to this instance
        :param width: the width to harmonize widgets in characters
        :param themed: for those who prefered themed versions of the widget. Default to false.
        :param kwargs: params to init the parent class
        """
        self.themed = themed
        if themed:
            TtkLabelFrame.__init__(self, master, text=frame_name, **kwargs)
        else:
            LabelFrame.__init__(self, master, text=frame_name, **kwargs)
        self.ypadding: int = 0
        self.xpadding: int = 0
        self.callbacks: ModInfoCallback = callbacks
        self._set_mod_side: Callable[[str, Side], Task[None]] = callbacks.set_mod_side
        self._set_mod_side_default: Callable[[str, str], Task[None]] = callbacks.set_mod_side_default
        self._set_mod_version: Callable[[str, str], None] = callbacks.set_mod_version

        self.mod_name: CustomLabel = CustomLabel(self, label_text="Mod name: {0}", value="", themed=self.themed)
        self.version: CustomCombobox = CustomCombobox(
            self, label_text="Mod version:", values=[], on_selection=self.set_mod_version, themed=self.themed
        )
        self.license: CustomLabel = CustomLabel(self, label_text="Mod license: {0}", value="", themed=self.themed)
        self.side: CustomCombobox = CustomCombobox(
            self, label_text="Mod side this release:", values=[], on_selection=self.set_mod_side, themed=self.themed
        )
        self.side_default: CustomCombobox = CustomCombobox(
            self, label_text="Mod side default:", values=[], on_selection=self.set_mod_side_default, themed=self.themed
        )
        self.current_mod_name = ""

        self.edit_button: CustomButton = CustomButton(
            self,
            text="edit version",
            command=lambda: asyncio.ensure_future(self.edit_version()),
            themed=self.themed,
        )

        self.mod_adder_callbacks = mod_adder_callbacks
        self.widgets: List[CustomWidget]
        if external_mods:
            self.widgets = [
                self.mod_name,
                self.version,
                self.edit_button,
                self.license,
                self.side,
                self.side_default,
            ]
        else:
            self.widgets = [self.mod_name, self.version, self.license, self.side, self.side_default]
        self.width: int = width if width is not None else max([widget.get_description_size() for widget in self.widgets])  # type: ignore

    async def edit_version(self) -> None:
        if not self.callbacks.listbox.has_selection():
            showerror(
                "No external mod selected",
                "In order to add a new version to a external mod, you must select one first",
            )
            return

        if not self.version.combobox.get():
            showerror(
                "No mod version selected",
                "In order to add a new version to a external mod, you must select one first",
            )
            return

        version = self.version.get()

        top_level: Toplevel = Toplevel(self)
        mod_name: str = self.callbacks.listbox.get_value_at_index(self.callbacks.listbox.get())
        mod_addition_frame: ModAdderWindow = ModAdderWindow(
            top_level,
            "external version adder",
            callbacks=self.mod_adder_callbacks,  # type: ignore
            mod_name=mod_name,
            themed=self.themed,
            edit_version_mode=True,
        )
        gtnh = await self.mod_adder_callbacks.get_gtnh_callback()  # type: ignore
        data = gtnh.assets.get_mod(mod_name)
        version = data.get_version(version)
        mod_addition_frame.populate_data(mod=data, version=version)  # type: ignore
        mod_addition_frame.grid()
        mod_addition_frame.update_widget()
        top_level.title("Edit new version")

    def set_mod_side(self, _: Any) -> None:
        """
        Callback used when the user selects a mod side.

        :param _: the tkinter event passed by the tkinter in the Callback (unused)
        :return: None
        """
        mod_name: str = self.current_mod_name
        if mod_name == "":
            raise ValueError("empty mod cannot have a side")
        side: Side = Side(self.side.get())
        if side == USE_DEFAULT:
            raise ValueError("cannot set to USE_DEFAULT")
        assert side
        self._set_mod_side(mod_name, side)

    def set_mod_side_default(self, _: Any) -> None:
        """
        Callback used when the user selects a mod side.

        :param _: the tkinter event passed by the tkinter in the Callback (unused)
        :return: None
        """
        mod_name: str = self.current_mod_name
        if mod_name == "":
            raise ValueError("empty mod cannot have a side")
        side: str = self.side_default.get()
        self._set_mod_side_default(mod_name, side)

    def set_mod_version(self, _: Any) -> None:
        """
        Callback used when a mod version is being set by the user.

        :param _: the tkinter event passed by the tkinter in the Callback (unused)
        :return: None
        """
        if self.side.get() not in [
            "",
            Side.NONE,
        ]:  # preventing from adding versions to manifest if it's not init or disabled
            mod_name: str = self.current_mod_name
            if mod_name == "":
                raise ValueError("empty mod cannot have a version")

            mod_version: str = self.version.get()
            self._set_mod_version(mod_name, mod_version)

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
        for widget in self.widgets:
            widget.grid_forget()

        self.update_idletasks()

    def show(self) -> None:
        """
        Method used to display widgets and child widgets, as well as to configure the "responsiveness" of the widgets.

        :return: None
        """
        rows: int = len(self.widgets)
        columns: int = 1

        for i in range(rows):
            self.rowconfigure(i, weight=1, pad=self.xpadding)

        for i in range(columns):
            self.columnconfigure(i, weight=1, pad=self.ypadding)

        for i, widget in enumerate(self.widgets):
            widget.grid(row=i, column=0)

        self.update_idletasks()

    def populate_data(self, data: Any) -> None:
        """
        Method called by parent class to populate data in this class.

        :param data: the data to pass to this class
        :return: None
        """
        self.mod_name.set(data["name"])
        self.current_mod_name = data["name"]

        self.version.set_values(data["versions"])
        self.version.set(data["current_version"])

        self.license.set(data["license"])

        self.side.set_values([side.name for side in Side])
        self.side.set(data["side"] or USE_DEFAULT)

        self.side_default.set_values([side.name for side in Side])
        self.side_default.set(data["side_default"])

    def reset(self) -> None:
        """
        Method to reset all the fields.

        :return: None
        """
        for widget in self.widgets:
            widget.reset()
