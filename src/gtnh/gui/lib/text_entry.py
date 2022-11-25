from tkinter import Entry, Frame, Label, StringVar
from typing import Any

from gtnh.defs import Position


class TextEntry(Frame):
    def __init__(self, master: Any, label_text: str, *args: Any, **kwargs: Any):
        Frame.__init__(self, master, *args, **kwargs)
        self.label_text: str = label_text
        self.label: Label = Label(self, text=self.label_text)
        self.string_var: StringVar = StringVar(self)
        self.entry: Entry = Entry(self, textvariable=self.string_var)

    def set(self, value: str) -> None:
        self.string_var.set(value)

    def get(self) -> str:
        return self.string_var.get()

    def grid_forget(self, *args: Any, **kwargs: Any) -> None:
        self.label.grid_forget()
        self.entry.grid_forget()
        super().grid_forget()

    def grid(self, *args: Any, **kwargs: Any) -> None:
        self.label.grid(row=0, column=0, sticky=Position.LEFT)
        self.entry.grid(row=0, column=1, sticky=Position.HORIZONTAL)
        super().grid(*args, **kwargs)

    def configure(self, *args: Any, **kwargs: Any) -> None:
        if "width" in kwargs:
            self.label.configure(width=kwargs["width"])
            self.entry.configure(width=2 * kwargs["width"])
            del kwargs["width"]
        super().configure(*args, **kwargs)

    def get_description(self) -> str:
        return self.label_text

    def get_description_size(self) -> int:
        return len(self.label_text)

    def reset(self) -> None:
        self.set("")
