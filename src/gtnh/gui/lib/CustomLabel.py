from tkinter import Frame, Label, StringVar
from typing import Any, List

from gtnh.defs import Position


class CustomLabel(Frame):
    def __init__(self, master: Any, label_text: str, value: str, *args, **kwargs) -> None:
        Frame.__init__(self, master, *args, *kwargs)
        self.label_text: str = label_text
        self.label: Label = Label(self, text=label_text)
        self.string_var: StringVar = StringVar(value=value)
        self.var_label: Label = Label(self, textvariable=self.string_var)

    def get(self) -> str:
        return self.string_var.get()

    def set(self, value: str) -> None:
        self.string_var.set(value)

    def grid_forget(self, *args: Any, **kwargs: Any) -> None:
        self.label.grid_forget()
        self.var_label.grid_forget()
        super().grid_forget()

    def grid(self, *args: Any, **kwargs: Any) -> None:
        self.label.grid(row=0, column=0, sticky=Position.LEFT)
        self.var_label.grid(row=0, column=1, sticky=Position.HORIZONTAL)
        super().grid(*args, **kwargs)

    def configure(self, *args: Any, **kwargs: Any) -> None:
        if "width" in kwargs:
            self.label.configure(width=kwargs["width"])
            self.var_label.configure(width=kwargs["width"])
            del kwargs["width"]
        super().configure(*args, **kwargs)

    def get_description(self) -> str:
        return self.label_text

    def get_description_size(self) -> int:
        return len(self.label_text)

    def reset(self) -> None:
        self.set("")
