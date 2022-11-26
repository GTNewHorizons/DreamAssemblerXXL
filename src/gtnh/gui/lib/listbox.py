from tkinter import END, Frame, Label, Listbox, Scrollbar
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
        *args: Any,
        **kwargs: Any,
    ) -> None:
        Frame.__init__(self, master, *args, **kwargs)
        CustomWidget.__init__(self, text=label_text)

        self.label: Label = Label(self, text=label_text)

        self.listbox: Listbox = Listbox(self, exportselection=exportselection, height=height)

        self.callback_on_selection: Optional[Callable[[Any], None]] = on_selection
        if self.callback_on_selection is not None:
            self.listbox.bind("<<ListboxSelect>>", on_selection)

        self.scrollbar: Scrollbar = Scrollbar(self)
        self.listbox.configure(yscrollcommand=self.scrollbar.set)
        self.scrollbar.configure(command=self.listbox.yview)

        rows: int = 2
        columns: int = 2  # not resizing the scrollbar column on demand

        for i in range(rows):
            self.rowconfigure(i, weight=1, pad=0)

        for i in range(columns):
            self.columnconfigure(i, weight=1, pad=0)

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
        self.scrollbar.grid_forget()
        super().grid_forget()

    def grid(self, *args: Any, **kwargs: Any) -> None:  # type: ignore
        self.label.grid(row=0, column=0, sticky=Position.LEFT)
        self.listbox.grid(row=1, column=0, columnspan=2, sticky=Position.HORIZONTAL)
        self.scrollbar.grid(row=1, column=2, sticky=Position.VERTICAL)
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
