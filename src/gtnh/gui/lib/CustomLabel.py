from tkinter import Frame, Label, StringVar
from tkinter.ttk import Frame as TtkFrame, Label as TtkLabel
from typing import Any, Union

from gtnh.gui.lib.custom_widget import CustomWidget


class CustomLabel(Frame, TtkFrame, CustomWidget):  # type: ignore
    def __init__(
        self, master: Any, label_text: str, value: str, themed: bool = False, *args: Any, **kwargs: Any
    ) -> None:
        self.themed = themed
        if themed:
            TtkFrame.__init__(self, master, *args, *kwargs)
        else:
            Frame.__init__(self, master, *args, *kwargs)

        CustomWidget.__init__(self, text=label_text)

        self.string_var: StringVar = StringVar(value=value)
        self.var_label: Union[Label, TtkLabel] = (
            TtkLabel(self, textvariable=self.string_var) if themed else Label(self, textvariable=self.string_var)
        )

    def get(self) -> str:
        return self.string_var.get()

    def set(self, value: str) -> None:
        self.string_var.set(self.label_text.format(value))

    def grid_forget(self, *args: Any, **kwargs: Any) -> None:
        self.var_label.grid_forget()
        super().grid_forget()

    def grid(self, *args: Any, **kwargs: Any) -> None:
        self.var_label.grid(row=0, column=0)
        super().grid(*args, **kwargs)

    def configure(self, *args: Any, **kwargs: Any) -> None:  # type: ignore
        if "width" in kwargs:
            self.var_label.configure(width=kwargs["width"])
            del kwargs["width"]
        super().configure(*args, **kwargs)

    def reset(self) -> None:
        self.set("")
