from tkinter import Frame, IntVar, Label, Radiobutton
from typing import Any, Callable, Dict, List

from gtnh.defs import Position
from gtnh.gui.lib.custom_widget import CustomWidget


class RadioChoice(Frame, CustomWidget):
    def __init__(
        self,
        master: Any,
        label_text: str,
        update_command: Callable[[], None],
        choices: Dict[str, int],
        default_value: int = 0,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        Frame.__init__(self, master, *args, **kwargs)
        CustomWidget.__init__(self, text=label_text)

        self.default_value = default_value
        self.int_var: IntVar = IntVar()
        self.int_var.set(default_value)

        self.label: Label = Label(self, text=label_text)
        self.update_command = update_command

        if not len(choices):
            raise ValueError("Choice dict cannot be empty")

        self.choice_list: List[Radiobutton] = [
            Radiobutton(self, text=choice_name, variable=self.int_var, value=choice_value, command=update_command)
            for choice_name, choice_value in choices.items()
        ]

    def get(self) -> int:
        return self.int_var.get()

    def set(self, value: int) -> None:
        self.int_var.set(value)

    def grid_forget(self, *args: Any, **kwargs: Any) -> None:
        self.label.grid_forget()
        for widget in self.choice_list:
            widget.grid_forget()
        super().grid_forget()

    def grid(self, *args: Any, **kwargs: Any) -> None:
        self.label.grid(row=0, column=0, sticky=Position.HORIZONTAL)
        for i, widget in enumerate(self.choice_list):
            widget.grid(row=0, column=i + 1)
        super().grid(*args, **kwargs)

    def configure(self, *args: Any, **kwargs: Any) -> None:  # type: ignore
        if "width" in kwargs:
            width = kwargs["width"]
            self.label.configure(width=width)
            for widget in self.choice_list:
                widget.configure(width=width)
            del kwargs["width"]
        super().configure(*args, **kwargs)

    def reset(self) -> None:
        pass
