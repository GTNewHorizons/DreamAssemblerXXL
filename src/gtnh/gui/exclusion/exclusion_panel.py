from tkinter.ttk import LabelFrame
from typing import Any, Callable, Dict, List, Optional

from gtnh.defs import Position
from gtnh.gui.lib.button import CustomButton
from gtnh.gui.lib.custom_widget import CustomWidget
from gtnh.gui.lib.listbox import CustomListbox
from gtnh.gui.lib.text_entry import TextEntry


class ExclusionPanel(LabelFrame):
    """Widget managing an exclusion list."""

    def __init__(
        self, master: Any, frame_name: str, callbacks: Dict[str, Any], width: Optional[int] = None, **kwargs: Any
    ) -> None:
        """
        Constructor of the ExclusionFrame class.

        :param master: the parent widget
        :param frame_name: the name displayed in the framebox
        :param callbacks: a dict of callbacks passed to this instance
        :param width: the width to harmonize widgets in characters
        :param kwargs: params to init the parent class
        """
        LabelFrame.__init__(self, master, text=frame_name, **kwargs)
        self.xpadding: int = 0
        self.ypadding: int = 0
        self.add_callback: Callable[[str], None] = callbacks["add"]
        self.del_callback: Callable[[str], None] = callbacks["del"]

        self.listbox: CustomListbox = CustomListbox(
            self, label_text=frame_name, exportselection=False, height=12, display_horizontal_scrollbar=True
        )

        self.exclusion: TextEntry = TextEntry(self, label_text="", hide_label=True)

        self.btn_add: CustomButton = CustomButton(self, text="Add new exclusion", command=self.add)
        self.btn_del: CustomButton = CustomButton(self, text="Remove highlighted", command=self.delete)

        self.widgets: List[CustomWidget] = [self.btn_add, self.btn_del, self.listbox]

        self.width: int = (
            width if width is not None else max([widget.get_description_size() for widget in self.widgets])
        )

        self.columnconfigure(0, weight=1, pad=self.ypadding)
        self.columnconfigure(1, weight=1, pad=self.ypadding)

        # no rowconfigure to avoid space between elements

        self.update_widget()

    def add_to_list_sorted(self, elem: str) -> None:
        """
        Method used to insert an element into the listbox and sort the elements at the same time.

        :param elem: the element to add in the listbox
        :return: None
        """
        exclusions: List[str] = self.listbox.get_values()
        if elem in exclusions:
            return

        exclusions.append(elem)
        self.listbox.set_values(sorted(exclusions))

    def add(self) -> None:
        """
        Callback of self.btn_add.

        :return: None
        """
        exclusion: str = self.exclusion.get()
        if exclusion == "":
            return

        self.add_to_list_sorted(exclusion)
        self.add_callback(exclusion)

    def delete(self) -> None:
        """
        Callback of self.btn_del.

        :return: None
        """
        if self.listbox.has_selection():
            position: int = self.listbox.get()
            exclusion: str = self.listbox.get_value_at_index(position)
            self.listbox.del_value_at_index(position)
            self.del_callback(exclusion)

    def configure_widgets(self) -> None:
        """
        Method to configure the widgets.

        :return: None
        """
        for widget in self.widgets:
            widget.configure(width=self.width)

        # overriding exclusion widget to get proper size
        # self.exclusion.configure(width=2 * (self.width + 6))

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

    def show(self) -> None:
        """
        Method used to display widgets and child widgets, as well as to configure the "responsiveness" of the widgets.

        :return: None
        """
        x: int = 0
        y: int = 0

        self.listbox.grid(row=x, column=y, columnspan=2, sticky=Position.HORIZONTAL)
        self.exclusion.grid(row=x + 1, column=y, columnspan=2, stick=Position.HORIZONTAL)
        self.btn_add.grid(row=x + 2, column=y, sticky=Position.HORIZONTAL)
        self.btn_del.grid(row=x + 2, column=y + 1, sticky=Position.HORIZONTAL)

    def populate_data(self, data: Dict[str, Any]) -> None:
        """
        Method called by parent class to populate data in this class.

        :param data: the data to pass to this class
        :return: None
        """
        self.listbox.set_values(data["exclusions"])
