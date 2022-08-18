from tkinter import END, Button, Entry, LabelFrame, Listbox, Scrollbar, StringVar
from typing import Any, Callable, Dict, List, Optional, Tuple


class ExclusionFrame(LabelFrame):
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
        self.btn_add_text: str = "add new exclusion"
        self.btn_del_text: str = "remove highlighted"
        self.width: int = width if width is not None else max(len(self.btn_add_text), len(self.btn_del_text))
        self.listbox: Listbox = Listbox(self, exportselection=False, height=16)
        self.sv_entry: StringVar = StringVar(value="")
        self.entry: Entry = Entry(self, textvariable=self.sv_entry)
        self.btn_add: Button = Button(self, text=self.btn_add_text, command=self.add)
        self.btn_del: Button = Button(self, text=self.btn_del_text, command=self.delete)
        self.add_callback: Callable[[str], None] = callbacks["add"]
        self.del_callback: Callable[[str], None] = callbacks["del"]

        self.scrollbar: Scrollbar = Scrollbar(self)
        self.listbox.configure(yscrollcommand=self.scrollbar.set)
        self.scrollbar.configure(command=self.listbox.yview)

        self.update_widget()

    def add_to_list_sorted(self, elem: str) -> None:
        """
        Method used to insert an element into the listbox and sort the elements at the same time.

        :param elem: the element to add in the listbox
        :return: None
        """
        exclusions: List[str] = list(self.listbox.get(0, END))
        if elem in exclusions:
            return

        exclusions.append(elem)
        self.listbox.delete(0, END)
        self.listbox.insert(0, *(sorted(exclusions)))

    def add(self) -> None:
        """
        Callback of self.btn_add.

        :return: None
        """
        exclusion: str = self.sv_entry.get()
        if exclusion == "":
            return

        self.add_to_list_sorted(exclusion)
        self.add_callback(exclusion)

    def delete(self) -> None:
        """
        Callback of self.btn_del.

        :return: None
        """
        position: Tuple[int] = self.listbox.curselection()
        if position:
            exclusion: str = self.listbox.get(position[0])
            self.listbox.delete(position)
            self.del_callback(exclusion)

    def configure_widgets(self) -> None:
        """
        Method to configure the widgets.

        :return: None
        """

        self.entry.configure(width=2 * (self.width + 4))
        self.btn_add.configure(width=self.width)
        self.btn_del.configure(width=self.width)

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
        self.listbox.grid_forget()
        self.scrollbar.grid_forget()
        self.entry.grid_forget()
        self.btn_add.grid_forget()
        self.btn_del.grid_forget()

    def show(self) -> None:
        """
        Method used to display widgets and child widgets, as well as to configure the "responsiveness" of the widgets.

        :return: None
        """
        x: int = 0
        y: int = 0

        self.rowconfigure(0, weight=1, pad=self.xpadding)
        self.rowconfigure(1, weight=1, pad=self.xpadding)
        self.rowconfigure(2, weight=1, pad=self.xpadding)
        self.columnconfigure(0, weight=1, pad=self.ypadding)
        self.columnconfigure(1, weight=1, pad=self.ypadding)

        self.listbox.grid(row=x, column=y, columnspan=2, sticky="WE")
        self.scrollbar.grid(row=x, column=y + 2, columnspan=2, sticky="NS")
        self.entry.grid(row=x + 1, column=y, columnspan=3)
        self.btn_add.grid(row=x + 2, column=y, sticky="NE")
        self.btn_del.grid(row=x + 2, column=y + 1, columnspan=2, sticky="WN")

    def populate_data(self, data: Dict[str, Any]) -> None:
        """
        Method called by parent class to populate data in this class.

        :param data: the data to pass to this class
        :return: None
        """
        self.listbox.insert(END, *data["exclusions"])
