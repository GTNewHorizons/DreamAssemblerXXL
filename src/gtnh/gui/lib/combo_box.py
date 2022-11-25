from tkinter import Frame, Label, StringVar
from tkinter.ttk import Combobox
from typing import Any, Callable, List, Optional

from gtnh.defs import Position


class CustomCombobox(Frame):
    def __init__(
        self,
        master: Any,
        label_text: str,
        values: List[str] = [],
        on_selection: Optional[Callable[[Any], None]] = None,
        *args,
        **kwargs,
    ) -> None:
        Frame.__init__(self, master, *args, *kwargs)
        self.label_text: str = label_text
        self.label: Label = Label(self, text=label_text)
        self.string_var: StringVar = StringVar(value="")
        self.combobox: Combobox = Combobox(self, textvariable=self.string_var, values=values)
        self.callback_on_selection: Callable[[Any], None] = on_selection
        if self.callback_on_selection is not None:
            self.combobox.bind("<<ComboboxSelected>>", on_selection)

    def get_values(self) -> List[str]:
        return self.combobox["values"]

    def set_values(self, values: List[str]) -> None:
        self.combobox["values"] = values

    def get(self) -> str:
        return self.combobox.get()

    def set(self, value: str) -> None:
        self.combobox.set(value)

    def set_on_selection_callback(self, callback: Callable[[None], None]) -> None:
        self.combobox.bind("<<ComboboxSelected>>", callback, False)

    def grid_forget(self, *args: Any, **kwargs: Any) -> None:
        self.label.grid_forget()
        self.combobox.grid_forget()
        super().grid_forget()

    def grid(self, *args: Any, **kwargs: Any) -> None:
        self.label.grid(row=0, column=0, sticky=Position.LEFT)
        self.combobox.grid(row=0, column=1, sticky=Position.HORIZONTAL)
        super().grid(*args, **kwargs)

    def configure(self, *args: Any, **kwargs: Any) -> None:
        if "width" in kwargs:
            self.label.configure(width=kwargs["width"])
            self.combobox.configure(width=kwargs["width"])
            del kwargs["width"]
        super().configure(*args, **kwargs)

    def get_description(self) -> str:
        return self.label_text

    def get_description_size(self) -> int:
        return len(self.label_text)

    def reset(self):
        self.set("")
        self.set_values([])
