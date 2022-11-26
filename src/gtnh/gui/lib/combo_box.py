from tkinter import Frame, Label, StringVar
from tkinter.ttk import Combobox
from typing import Any, Callable, List, Optional

from gtnh.defs import Position
from gtnh.gui.lib.custom_widget import CustomWidget


class CustomCombobox(Frame, CustomWidget):
    def __init__(
        self,
        master: Any,
        label_text: str,
        values: List[str] = [],
        hide_label: bool = False,
        on_selection: Optional[Callable[[Any], None]] = None,
        position_sticky_label: Optional[Position] = Position.HORIZONTAL,
        position_sticky_combobox: Optional[Position] = Position.HORIZONTAL,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        Frame.__init__(self, master, *args, *kwargs)
        CustomWidget.__init__(self, text=label_text)
        self.label: Label = Label(self, text=label_text)

        self.string_var: StringVar = StringVar(value="")

        self.combobox: Combobox = Combobox(self, textvariable=self.string_var, values=values)

        self.callback_on_selection: Optional[Callable[[Any], None]] = on_selection

        self.hide_label: bool = hide_label

        self.position_sticky_label: Position = (
            position_sticky_label if position_sticky_label is not None else Position.NONE
        )
        self.position_sticky_combobox: Position = (
            position_sticky_combobox if position_sticky_combobox is not None else Position.NONE
        )

        if self.callback_on_selection is not None:
            self.combobox.bind("<<ComboboxSelected>>", on_selection)

        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)

    def get_values(self) -> List[str]:
        return self.combobox["values"]  # type: ignore

    def set_values(self, values: List[str]) -> None:
        self.combobox["values"] = values

    def get(self) -> str:
        return self.combobox.get()

    def set(self, value: str) -> None:
        self.combobox.set(value)

    def set_on_selection_callback(self, callback: Callable[[Any], Any]) -> None:
        self.combobox.bind("<<ComboboxSelected>>", callback, False)

    def grid_forget(self, *args: Any, **kwargs: Any) -> None:
        self.label.grid_forget()
        self.combobox.grid_forget()
        super().grid_forget()

    def grid(self, *args: Any, **kwargs: Any) -> None:
        if not self.hide_label:
            self.label.grid(row=0, column=0, sticky=self.position_sticky_label)
            self.combobox.grid(row=0, column=1, sticky=self.position_sticky_combobox)
        else:
            self.combobox.grid(row=0, column=0, columnspan=2, sticky=self.position_sticky_combobox)

        super().grid(*args, **kwargs)

    def configure(self, *args: Any, **kwargs: Any) -> None:  # type: ignore
        if "width" in kwargs:
            self.label.configure(width=kwargs["width"])
            self.combobox.configure(
                width=kwargs["width"] + 3
            )  # +3 to compensate for the char losts because inner grid manager compared to outer grid manager
            del kwargs["width"]
        if "state" in kwargs:
            self.combobox.configure(state=kwargs["state"])
            del kwargs["state"]
        super().configure(*args, **kwargs)

    def reset(self) -> None:
        self.set("")
        self.set_values([])
