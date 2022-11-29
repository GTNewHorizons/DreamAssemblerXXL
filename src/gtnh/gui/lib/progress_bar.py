from tkinter import Frame, Label, StringVar
from tkinter.ttk import Label as TtkLabel, Progressbar
from typing import Any, Union

from gtnh.gui.lib.custom_widget import CustomWidget


class CustomProgressBar(Frame, CustomWidget):
    def __init__(
        self,
        master: Any,
        label_text: str,
        progress_bar_length: int = 500,
        themed: bool = False,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        if themed:
            pass
        else:
            Frame.__init__(self, master, *args, **kwargs)

        CustomWidget.__init__(self, text=label_text)

        self.progress_bar_length: int = progress_bar_length

        self.progress_bar: Progressbar = Progressbar(
            self, orient="horizontal", mode="determinate", length=progress_bar_length
        )

        self.stringvar: StringVar = StringVar(self, value="")

        self.label: Union[Label, TtkLabel] = (
            TtkLabel(self, textvariable=self.stringvar, width=100)
            if themed
            else Label(self, textvariable=self.stringvar, width=100)
        )

        rows: int = 2
        columns: int = 1

        for i in range(rows):
            self.rowconfigure(i, weight=1)

        for i in range(columns):
            self.columnconfigure(i, weight=1)

    def add_progress(self, progress: float, data: str) -> None:
        """
        Callback to update the bar showing the progress.

        :param progress: value to add to the progress
        :param data: what is currently done
        :return: None
        """
        self.progress_bar["value"] += progress
        self.stringvar.set(data)
        self.update_idletasks()

    def reset(self) -> None:
        """
        Callback to reset the progress bar for the current task.

        :return: None
        """
        self.progress_bar["value"] = 0
        self.stringvar.set("")
        self.update_idletasks()

    def grid(self, *args: Any, **kwargs: Any) -> None:
        x: int = 0
        y: int = 0
        self.progress_bar.grid(row=x, column=y)
        self.label.grid(row=x + 1, column=y)
        super().grid(*args, **kwargs)

    def grid_forget(self) -> None:
        self.progress_bar.grid_forget()
        self.label.grid_forget()

    def configure(self, *args: Any, **kwargs: Any) -> None:  # type: ignore
        if "width" in kwargs:
            self.label.configure(width=kwargs["width"])
            del kwargs["width"]
        super().configure(*args, **kwargs)
