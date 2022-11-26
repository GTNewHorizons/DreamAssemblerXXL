from tkinter.ttk import Button
from typing import Any

from gtnh.gui.lib.custom_widget import CustomWidget


class CustomButton(Button, CustomWidget):
    def __init__(self, *args: Any, **kwargs: Any):
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
