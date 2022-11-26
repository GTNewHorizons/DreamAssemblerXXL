from tkinter import END, HORIZONTAL, VERTICAL, Frame, Label, Listbox, Scrollbar
from typing import Any, Callable, List, Optional, Tuple

from gtnh.defs import Position
from gtnh.gui.lib.custom_widget import CustomWidget


class CustomListbox(Frame, CustomWidget):
    def __init__(
        self,
        master: Any,
        label_text: str,
        exportselection: bool = False,
        on_selection: Optional[Callable[[Any], Any]] = None,
        height: int = 11,
        display_horizontal_scrollbar: bool = False,
        display_vertical_scrollbar: bool = True,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        Frame.__init__(self, master, *args, **kwargs)
        CustomWidget.__init__(self, text=label_text)

        self.display_horizontal_scrollbar: bool = display_horizontal_scrollbar
        self.display_vertical_scrollbar: bool = display_vertical_scrollbar

        self.label: Label = Label(self, text=label_text)

        self.listbox: Listbox = Listbox(self, exportselection=exportselection, height=height)

        self.callback_on_selection: Optional[Callable[[Any], None]] = on_selection
        if self.callback_on_selection is not None:
            self.listbox.bind("<<ListboxSelect>>", on_selection)

        self.scrollbar_horizontal: Scrollbar = Scrollbar(self, orient=HORIZONTAL)
        self.listbox.configure(xscrollcommand=self.scrollbar_horizontal.set)
        self.scrollbar_horizontal.configure(command=self.listbox.xview)

        self.scrollbar_vertical: Scrollbar = Scrollbar(self, orient=VERTICAL)
        self.listbox.configure(yscrollcommand=self.scrollbar_vertical.set)
        self.scrollbar_vertical.configure(command=self.listbox.yview)

        self.rowconfigure(0, weight=1, pad=0)
        self.rowconfigure(1, weight=10, pad=0)

        self.columnconfigure(0, weight=1, pad=0)
        # no resizing of the vertical scrollbar, hence the only columnconfigure

    def get_values(self) -> List[str]:
        return self.listbox.get(0, END)  # type: ignore

    def set_values(self, values: List[str]) -> None:
        self.listbox.delete(0, END)
        self.listbox.insert(0, *values)

    def get(self) -> int:
        if not self.has_selection():
            raise IndexError("The listbox has no selection but was asked one")
        selection: Tuple[int] = self.listbox.curselection()
        return selection[0]

    def set(self, value: int) -> None:
        self.listbox.select_set(value)

    def insert(self, position: int, value: str) -> None:
        if position == -1:
            self.listbox.insert(END, value)
        else:
            self.listbox.insert(position, value)

    def has_selection(self) -> bool:
        return self.listbox.curselection() != ()  # type: ignore

    def get_value_at_index(self, index: int) -> str:
        return self.listbox.get(index)  # type: ignore

    def del_value_at_index(self, index: int) -> None:
        self.listbox.delete(index)

    def set_on_selection_callback(self, callback: Callable[[Any], Any]) -> None:
        self.listbox.bind("<<ListboxSelect>>", callback, False)

    def grid_forget(self) -> None:
        self.label.grid_forget()
        self.listbox.grid_forget()
        self.scrollbar_horizontal.grid_forget()
        self.scrollbar_vertical.grid_forget()
        super().grid_forget()

    def grid(self, *args: Any, **kwargs: Any) -> None:  # type: ignore
        x = 0
        y = 0
        self.label.grid(row=x + 0, column=y + 0, sticky=Position.LEFT)
        self.listbox.grid(row=x + 1, column=y + 0, columnspan=1, sticky=Position.HORIZONTAL)
        if self.display_horizontal_scrollbar:
            self.scrollbar_horizontal.grid(row=x + 2, column=y + 0, sticky=Position.HORIZONTAL)
        if self.display_vertical_scrollbar:
            self.scrollbar_vertical.grid(row=x + 1, column=y + 1, sticky=Position.VERTICAL)

        super().grid(*args, **kwargs)

    def configure(self, *args: Any, **kwargs: Any) -> None:  # type: ignore
        if "width" in kwargs:
            self.label.configure(width=kwargs["width"])
            self.listbox.configure(width=kwargs["width"])
            del kwargs["width"]
        if "state" in kwargs:
            self.listbox.configure(state=kwargs["state"])
            del kwargs["state"]
        super().configure(*args, **kwargs)

    def reset(self) -> None:
        self.set(0)
        self.set_values([])
