from tkinter import Button
from tkinter.ttk import Button as TtkButton
from typing import Any

from gtnh.gui.lib.custom_widget import CustomWidget


class CustomButton(Button, TtkButton, CustomWidget):  # type: ignore
    def __init__(self, *args: Any, themed: bool = False, **kwargs: Any):
        self.themed = themed
        if themed:
            TtkButton.__init__(self, *args, **kwargs)
        else:
            Button.__init__(self, *args, **kwargs)
        CustomWidget.__init__(self, text=self["text"])

    def configure(self, *args, **kwargs) -> None:  # type: ignore
        Button.configure(self, *args, **kwargs)

    def grid_forget(self) -> None:
        return Button.grid_forget(self)

    def grid(self, *args, **kwargs) -> None:  # type: ignore
        return Button.grid(self, *args, **kwargs)

    def reset(self) -> None:
        pass
