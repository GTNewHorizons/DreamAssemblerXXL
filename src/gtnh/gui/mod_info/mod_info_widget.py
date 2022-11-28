from tkinter import LabelFrame
from tkinter.ttk import LabelFrame as TtkLabelFrame
from typing import Any, Callable, Dict, List, Optional

from gtnh.defs import Position, Side
from gtnh.gui.lib.CustomLabel import CustomLabel
from gtnh.gui.lib.combo_box import CustomCombobox
from gtnh.gui.lib.custom_widget import CustomWidget


class ModInfoWidget(LabelFrame, TtkLabelFrame):  # type: ignore
    """
    Widget used to display info about a mod passed to it.
    """

    def __init__(
        self,
        master: Any,
        frame_name: str,
        callbacks: Dict[str, Callable[[str, str], None]],
        width: Optional[int] = None,
        themed: bool = False,
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
        self.callbacks: Dict[str, Any] = callbacks

        self.mod_name: CustomLabel = CustomLabel(self, label_text="Mod name:", value="", themed=self.themed)
        self.version: CustomCombobox = CustomCombobox(
            self, label_text="Mod version:", values=[], on_selection=self.set_mod_version, themed=self.themed
        )
        self.license: CustomLabel = CustomLabel(self, label_text="Mod license:", value="", themed=self.themed)
        self.side: CustomCombobox = CustomCombobox(
            self, label_text="Mod side:", values=[], on_selection=self.set_mod_side, themed=self.themed
        )

        self.widgets: List[CustomWidget] = [self.mod_name, self.version, self.license, self.side]
        self.width: int = (
            width if width is not None else max([widget.get_description_size() for widget in self.widgets])
        )

    def set_mod_side(self, event: Any) -> None:
        """
        Callback used when the user selects a mod side.

        :param event: the tkinter event passed by the tkinter in the Callback (unused)
        :return: None
        """
        mod_name: str = self.mod_name.get()
        if mod_name == "":
            raise ValueError("empty mod cannot have a side")
        side: str = self.side.get()
        self.callbacks["set_mod_side"](mod_name, side)

    def set_mod_version(self, event: Any) -> None:
        """
        Callback used when a mod version is being set by the user.

        :param event: the tkinter event passed by the tkinter in the Callback (unused)
        :return: None
        """
        if self.side.get() not in [
            "",
            Side.NONE,
        ]:  # preventing from adding versions to manifest if it's not init or disabled
            mod_name: str = self.mod_name.get()
            if mod_name == "":
                raise ValueError("empty mod cannot have a version")

            mod_version: str = self.version.get()
            self.callbacks["set_mod_version"](mod_name, mod_version)

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
        rows: int = 4
        columns: int = 1

        for i in range(rows):
            self.rowconfigure(i, weight=1, pad=self.xpadding)

        for i in range(columns):
            self.columnconfigure(i, weight=1, pad=self.ypadding)

        for i, widget in enumerate(self.widgets):
            widget.grid(row=i, column=0, sticky=Position.LEFT)

        self.update_idletasks()

    def populate_data(self, data: Any) -> None:
        """
        Method called by parent class to populate data in this class.

        :param data: the data to pass to this class
        :return: None
        """
        self.mod_name.set(data["name"])

        self.version.set_values(data["versions"])
        self.version.set(data["current_version"])

        self.license.set(data["license"])

        self.side.set_values([side.name for side in Side])
        self.side.set(data["side"])

    def reset(self) -> None:
        """
        Method to reset all the fields.

        :return: None
        """
        for widget in self.widgets:
            widget.reset()
