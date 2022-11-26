from tkinter import Entry, Frame, Label, StringVar
from typing import Any, Optional

from gtnh.defs import Position
from gtnh.gui.lib.custom_widget import CustomWidget


class TextEntry(Frame, CustomWidget):
    def __init__(
        self,
        master: Any,
        label_text: str,
        hide_label: bool = False,
        position_sticky_label: Optional[Position] = Position.HORIZONTAL,
        position_sticky_entry: Optional[Position] = Position.HORIZONTAL,
        *args: Any,
        **kwargs: Any,
    ):
        Frame.__init__(self, master, *args, **kwargs)
        CustomWidget.__init__(self, text=label_text)
        self.hide_label: bool = hide_label
        self.position_sticky_label: Position = (
            position_sticky_label if position_sticky_label is not None else Position.NONE
        )
        self.position_sticky_entry: Position = (
            position_sticky_entry if position_sticky_entry is not None else Position.NONE
        )
        self.label: Label = Label(self, text=self.label_text)
        self.string_var: StringVar = StringVar(self)
        self.entry: Entry = Entry(self, textvariable=self.string_var)

        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)

    def set(self, value: str) -> None:
        self.string_var.set(value)

    def get(self) -> str:
        return self.string_var.get()

    def grid_forget(self) -> None:
        if not self.hide_label:
            self.label.grid_forget()
        self.entry.grid_forget()
        super().grid_forget()

    def grid(self, *args: Any, **kwargs: Any) -> None:  # type: ignore
        if not self.hide_label:
            self.label.grid(row=0, column=0, sticky=self.position_sticky_label)
            self.entry.grid(row=0, column=1, sticky=self.position_sticky_entry)
        else:
            self.entry.grid(row=0, column=0, columnspan=2, sticky=self.position_sticky_entry)

        super().grid(*args, **kwargs)

    def configure(self, *args: Any, **kwargs: Any) -> None:  # type: ignore
        if "width" in kwargs:
            if not self.hide_label:
                self.label.configure(width=kwargs["width"])
                self.entry.configure(
                    width=kwargs["width"] + 6
                )  # +6 to compensate for the char losts because inner grid manager compared to outer grid manager
            else:
                self.entry.configure(width=kwargs["width"])
            del kwargs["width"]
        if "state" in kwargs:
            self.entry.configure(state=kwargs["state"])
            del kwargs["state"]
        super().configure(*args, **kwargs)

    def reset(self) -> None:
        self.set("")
