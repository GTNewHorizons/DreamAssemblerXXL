from tkinter import Label, LabelFrame, StringVar
from tkinter.ttk import Combobox
from typing import Any, Callable, Dict, Optional

from gtnh.defs import Side


class ModInfoFrame(LabelFrame):
    """
    Widget used to display info about a mod passed to it.
    """

    def __init__(
        self,
        master: Any,
        frame_name: str,
        callbacks: Dict[str, Callable[[str, str], None]],
        width: Optional[int] = None,
        **kwargs: Any,
    ) -> None:
        """
        Constructor of the ModInfoFrame class.

        :param master: the parent widget
        :param frame_name: the name displayed in the framebox
        :param callbacks: a dict of callbacks passed to this instance
        :param width: the width to harmonize widgets in characters
        :param kwargs: params to init the parent class
        """
        LabelFrame.__init__(self, master, text=frame_name, **kwargs)
        self.ypadding: int = 0
        self.xpadding: int = 0
        self.callbacks: Dict[str, Any] = callbacks

        self.label_mod_name_text: str = "Mod name:"
        self.label_version_text: str = "Mod version:"
        self.label_license_text: str = "Mod license:"
        self.label_size_text: str = "Mod side:"

        self.width: int = (
            width
            if width is not None
            else max(
                len(self.label_mod_name_text),
                len(self.label_version_text),
                len(self.label_license_text),
                len(self.label_size_text),
            )
        )
        self.label_mod_name: Label = Label(self, text=self.label_mod_name_text)
        self.label_version: Label = Label(self, text=self.label_version_text)
        self.label_license: Label = Label(self, text=self.label_license_text)
        self.label_side: Label = Label(self, text=self.label_size_text)

        self.sv_mod_name: StringVar = StringVar(self, value="")
        self.sv_version: StringVar = StringVar(self, value="")
        self.sv_license: StringVar = StringVar(self, value="")
        self.sv_side: StringVar = StringVar(self, value="")

        self.label_mod_name_value: Label = Label(self, textvariable=self.sv_mod_name)
        self.cb_version: Combobox = Combobox(self, textvariable=self.sv_version, values=[])
        self.cb_version.bind("<<ComboboxSelected>>", self.set_mod_version)

        self.label_license_value: Label = Label(self, textvariable=self.sv_license)
        self.cb_side: Combobox = Combobox(self, textvariable=self.sv_side, values=[])
        self.cb_side.bind("<<ComboboxSelected>>", self.set_mod_side)

    def set_mod_side(self, event: Any) -> None:
        """
        Callback used when the user selects a mod side.

        :param event: the tkinter event passed by the tkinter in the Callback (unused)
        :return: None
        """
        mod_name: str = self.sv_mod_name.get()
        if mod_name == "":
            raise ValueError("empty mod cannot have a side")
        side: str = self.sv_side.get()
        self.callbacks["set_mod_side"](mod_name, side)

    def set_mod_version(self, event: Any) -> None:
        """
        Callback used when a mod version is being set by the user.

        :param event: the tkinter event passed by the tkinter in the Callback (unused)
        :return: None
        """
        if self.sv_side.get() not in [
            "",
            Side.NONE,
        ]:  # preventing from adding versions to manifest if it's not init or disabled
            mod_name: str = self.sv_mod_name.get()
            if mod_name == "":
                raise ValueError("empty mod cannot have a version")

            mod_version: str = self.sv_version.get()
            self.callbacks["set_mod_version"](mod_name, mod_version)

    def configure_widgets(self) -> None:
        """
        Method to configure the widgets.

        :return: None
        """
        self.label_mod_name.configure(width=self.width)
        self.label_version.configure(width=self.width)
        self.label_license.configure(width=self.width)
        self.label_side.configure(width=self.width)
        self.label_mod_name_value.configure(width=self.width)
        self.cb_version.configure(width=self.width)
        self.label_license_value.configure(width=self.width)
        self.cb_side.configure(width=self.width)

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
        self.label_mod_name.grid_forget()
        self.label_mod_name_value.grid_forget()
        self.label_version.grid_forget()
        self.cb_version.grid_forget()
        self.label_license.grid_forget()
        self.label_license_value.grid_forget()
        self.label_side.grid_forget()
        self.cb_side.grid_forget()

        self.update_idletasks()

    def show(self) -> None:
        """
        Method used to display widgets and child widgets, as well as to configure the "responsiveness" of the widgets.

        :return: None
        """
        x: int = 0
        y: int = 0
        rows: int = 4
        columns: int = 2

        for i in range(rows):
            self.rowconfigure(i, weight=1, pad=self.xpadding)

        for i in range(columns):
            self.columnconfigure(i, weight=1, pad=self.ypadding)

        self.label_mod_name.grid(row=x, column=y)
        self.label_mod_name_value.grid(row=x, column=y + 1)
        self.label_version.grid(row=x + 1, column=y)
        self.cb_version.grid(row=x + 1, column=y + 1)
        self.label_license.grid(row=x + 2, column=y)
        self.label_license_value.grid(row=x + 2, column=y + 1)
        self.label_side.grid(row=x + 3, column=y)
        self.cb_side.grid(row=x + 3, column=y + 1)

        self.update_idletasks()

    def populate_data(self, data: Any) -> None:
        """
        Method called by parent class to populate data in this class.

        :param data: the data to pass to this class
        :return: None
        """
        self.sv_mod_name.set(data["name"])
        self.cb_version["values"] = data["versions"]
        self.cb_side["values"] = [side.name for side in Side]
        self.cb_version.set(data["current_version"])
        self.sv_license.set(data["license"])
        self.cb_side.set(data["side"])

    def reset(self) -> None:
        """
        Method to reset all the fields.

        :return: None
        """

        self.sv_mod_name.set("")
        self.cb_version["values"] = []
        self.cb_side["values"] = []
        self.cb_version.set("")
        self.sv_license.set("")
        self.cb_side.set("")
