from tkinter import Frame, Label, LabelFrame, StringVar
from tkinter.ttk import Frame as TtkFrame, Label as TtkLabel, LabelFrame as TtkLabelFrame, Progressbar
from typing import Any, Dict, List, Optional, Union

from gtnh.defs import Position
from gtnh.gui.lib.button import CustomButton
from gtnh.gui.lib.custom_widget import CustomWidget


class ButtonArray(LabelFrame, TtkLabelFrame):  # type: ignore
    """
    Widget managing all the buttons related to pack assembling.
    """

    def __init__(
        self,
        master: Any,
        frame_name: str,
        callbacks: Dict[str, Any],
        width: Optional[int] = None,
        themed: bool = False,
        **kwargs: Any,
    ):
        """
        Constructor of the ButtonArray class.

        :param master: the parent widget
        :param frame_name: the name displayed in the framebox
        :param callbacks: a dict of callbacks passed to this instance
        :param width: the width to harmonize widgets in characters
        :param themed: for those who prefered themed versions of the widget. Default to false.
        :param kwargs: params to init the parent class
        """
        self.themed = themed
        if themed:
            TtkLabelFrame.__init__(self, master, text=frame_name, **kwargs)
        else:
            LabelFrame.__init__(self, master, text=frame_name, **kwargs)
        self.xpadding: int = 0
        self.ypadding: int = 0

        self.frame_btn: Union[Frame, TtkFrame] = TtkFrame(self) if themed else Frame(self)

        self.btn_client_cf: CustomButton = CustomButton(
            self.frame_btn, text="CurseForge client archive", command=callbacks["client_cf"], themed=self.themed
        )
        self.btn_client_technic: CustomButton = CustomButton(
            self.frame_btn, text="Technic client archive", command=callbacks["client_technic"], themed=self.themed
        )
        self.btn_client_mmc: CustomButton = CustomButton(
            self.frame_btn, text="MultiMC client archive", command=callbacks["client_mmc"], themed=self.themed
        )
        self.btn_client_modrinth: CustomButton = CustomButton(
            self.frame_btn, text="Modrinth client archive", command=callbacks["client_modrinth"], themed=self.themed
        )
        self.btn_generate_all: CustomButton = CustomButton(
            self.frame_btn, text="Generate all archives", command=callbacks["generate_all"], themed=self.themed
        )
        self.btn_update_nightly: CustomButton = CustomButton(
            self.frame_btn, text="Update nightly", command=callbacks["generate_nightly"], themed=self.themed
        )
        self.btn_update_assets: CustomButton = CustomButton(
            self.frame_btn, text="Update assets", command=callbacks["update_assets"], themed=self.themed
        )
        self.btn_client_zip: CustomButton = CustomButton(
            self.frame_btn, text="Zip client archive", command=callbacks["client_zip"], themed=self.themed
        )
        self.btn_server_zip: CustomButton = CustomButton(
            self.frame_btn, text="Zip server archive", command=callbacks["server_zip"], themed=self.themed
        )

        self.label_spacer: Union[Label, TtkLabel] = TtkLabel(self, text="") if themed else Label(self, text="")

        progress_bar_length: int = 500

        self.pb_global: Progressbar = Progressbar(
            self, orient="horizontal", mode="determinate", length=progress_bar_length
        )
        self.sv_pb_global: StringVar = StringVar(self, value="")
        self.label_pb_global: Union[Label, TtkLabel] = (
            TtkLabel(self, textvariable=self.sv_pb_global, width=100)
            if themed
            else Label(self, textvariable=self.sv_pb_global, width=100)
        )

        self.pb_current_task: Progressbar = Progressbar(
            self, orient="horizontal", mode="determinate", length=progress_bar_length
        )
        self.sv_pb_current_task: StringVar = StringVar(self, value="")
        self.label_pb_current_task: Union[Label, TtkLabel] = (
            TtkLabel(self, textvariable=self.sv_pb_current_task, width=100)
            if themed
            else Label(self, textvariable=self.sv_pb_current_task, width=100)
        )

        self.widgets: List[CustomWidget] = [
            self.btn_client_cf,
            self.btn_client_technic,
            self.btn_client_modrinth,
            self.btn_client_mmc,
            self.btn_update_assets,
            self.btn_update_nightly,
            self.btn_generate_all,
            self.btn_client_zip,
            self.btn_server_zip,
        ]
        self.width: int = (
            width if width is not None else max([widget.get_description_size() for widget in self.widgets])
        )

        self.update_widget()

    def populate_data(self, data: Any) -> None:
        """
        Method called by parent class to populate data in this class.

        :param data: the data to pass to this class
        :return: None
        """
        pass

    def update_current_task_progress_bar(self, progress: float, data: str) -> None:
        """
        Callback to update the task bar showing the current task's progress.

        :param progress: value to add to the progress
        :param data: what is currently done
        :return: None
        """
        self.pb_current_task["value"] += progress
        self.sv_pb_current_task.set(data)
        self.update_idletasks()

    def reset_current_task_progress_bar(self) -> None:
        """
        Callback to reset the progress bar for the current task.

        :return: None
        """
        self.pb_current_task["value"] = 0
        self.sv_pb_current_task.set("")
        self.update_idletasks()

    def update_global_progress_bar(self, progress: float, data: str) -> None:
        """
        Callback to update the task bar showing the global progress.

        :param progress: value to add to the progress
        :param data: what is currently done
        :return: None
        """
        self.pb_global["value"] += progress
        self.sv_pb_global.set(data)
        self.update_idletasks()

    def reset_global_progress_bar(self) -> None:
        """
        Callback to reset the progress bar for the global progress.

        :return: None
        """
        self.pb_global["value"] = 0
        self.sv_pb_global.set("")
        self.update_idletasks()

    def show(self) -> None:
        """
        Method used to display widgets and child widgets, as well as to configure the "responsiveness" of the widgets.

        :return: None
        """
        x: int = 0
        y: int = 0
        rows: int = 5
        columns: int = 1

        for i in range(rows):
            self.rowconfigure(i, weight=1, pad=self.xpadding)

        self.rowconfigure(rows + 1, weight=3)  # allocate more space for the btn frame

        for i in range(columns):
            self.columnconfigure(i, weight=1, pad=self.ypadding)

        self.label_pb_global.grid(row=x, column=y)
        self.pb_global.grid(row=x + 1, column=y)
        self.label_pb_current_task.grid(row=x + 2, column=y)
        self.pb_current_task.grid(row=x + 3, column=y)

        self.label_spacer.grid(row=x + 4, column=y)

        self.frame_btn.grid(row=x + 5, column=y, sticky=Position.UP)

        # grid withing the self.fram_btn
        pad: int = 3
        frame_rows: int = 3
        frame_columns: int = 3
        for i in range(frame_rows):
            self.frame_btn.rowconfigure(i, weight=1, pad=pad)

        for i in range(frame_columns):
            self.frame_btn.columnconfigure(i, weight=1, pad=pad)

        self.btn_client_cf.grid(row=0, column=0)
        self.btn_client_zip.grid(row=0, column=1)
        self.btn_client_technic.grid(row=0, column=2)

        self.btn_client_modrinth.grid(row=1, column=0)
        self.btn_server_zip.grid(row=1, column=1)
        self.btn_client_mmc.grid(row=1, column=2)

        self.btn_update_nightly.grid(row=2, column=0)
        self.btn_generate_all.grid(row=2, column=1)
        self.btn_update_assets.grid(row=2, column=2)

        self.update_idletasks()

    def configure_widgets(self) -> None:
        """
        Method to configure the widgets.

        :return: None
        """
        for widget in self.widgets:
            widget.configure(width=self.width)

    def set_width(self, width: int) -> None:
        """
        Method to set the widgets' width.

        :param width: the new width
        :return: None
        """
        self.width = width
        self.configure_widgets()

    def get_width(self) -> int:
        """
        Getter for self.width.

        :return: the width in character sizes of the normalised widgets
        """
        return self.width

    def update_widget(self) -> None:
        """
        Method to update the widget and all its childs

        :return: None
        """
        self.hide()
        self.configure_widgets()
        self.show()

    def hide(self) -> None:
        """
        Method to hide the widget and all its childs
        :return None:
        """
        for widget in self.widgets:
            widget.grid_forget()

        self.update_idletasks()
