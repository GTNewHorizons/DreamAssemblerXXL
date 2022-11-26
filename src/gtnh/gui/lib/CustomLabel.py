from tkinter import StringVar
from tkinter.ttk import Frame, Label
from typing import Any

from gtnh.defs import Position
from gtnh.gui.lib.custom_widget import CustomWidget


class CustomLabel(Frame, CustomWidget):
    def __init__(self, master: Any, label_text: str, value: str, *args: Any, **kwargs: Any) -> None:
        Frame.__init__(self, master, *args, *kwargs)
        CustomWidget.__init__(self, text=label_text)

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

    def configure(self, *args: Any, **kwargs: Any) -> None:  # type: ignore
        if "width" in kwargs:
            self.label.configure(width=kwargs["width"])
            self.var_label.configure(width=kwargs["width"])
            del kwargs["width"]
        super().configure(*args, **kwargs)

    def reset(self) -> None:
        self.set("")
