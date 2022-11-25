from tkinter import END, Frame, Label, Listbox, Scrollbar
from typing import Any, Callable, List, Optional

from gtnh.defs import Position


class CustomListbox(Frame):
    def __init__(
        self,
        master,
        label_text,
        exportselection=False,
        on_selection: Optional[Callable[[Any], Any]] = None,
        *args,
        **kwargs,
    ):
        Frame.__init__(self, master, *args, **kwargs)

        self.label_text: str = label_text
        self.label: Label = Label(self, text=label_text)

        self.listbox: Listbox = Listbox(self, exportselection=exportselection)

        self.callback_on_selection: Callable[[Any], None] = on_selection
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
        return self.listbox.get(0, END)

    def set_values(self, values: List[str]) -> None:
        self.listbox.delete(0, END)
        self.listbox.insert(0, *values)

    def get(self) -> int:
        return self.listbox.curselection()[0]  # no quard against listboxes with no selection

    def set(self, value: int) -> None:
        self.listbox.select_set(value)

    def has_selection(self) -> bool:
        return self.listbox.curselection() != ()

    def get_value_at_index(self, index) -> str:
        return self.listbox.get(index)

    def set_on_selection_callback(self, callback: Callable[[None], None]) -> None:
        self.listbox.bind("<<ListboxSelect>>", callback, False)

    def grid_forget(self, *args: Any, **kwargs: Any) -> None:
        self.label.grid_forget()
        self.listbox.grid_forget()
        self.scrollbar.grid_forget()
        super().grid_forget()

    def grid(self, *args: Any, **kwargs: Any) -> None:
        self.label.grid(row=0, column=0, sticky=Position.LEFT)
        self.listbox.grid(row=1, column=0, columnspan=2, sticky=Position.HORIZONTAL)
        self.scrollbar.grid(row=1, column=2, sticky=Position.VERTICAL)
        super().grid(*args, **kwargs)

    def configure(self, *args: Any, **kwargs: Any) -> None:
        if "width" in kwargs:
            self.label.configure(width=kwargs["width"])
            self.listbox.configure(width=kwargs["width"])
            del kwargs["width"]
        super().configure(*args, **kwargs)

    def get_description(self) -> str:
        return self.label_text

    def get_description_size(self) -> int:
        return len(self.label_text)

    def reset(self):
        self.set(0)
        self.set_values([])
