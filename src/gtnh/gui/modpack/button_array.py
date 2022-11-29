from tkinter import Frame, LabelFrame
from tkinter.ttk import Frame as TtkFrame, LabelFrame as TtkLabelFrame
from typing import Any, Callable, List, Optional, Union

from gtnh.gui.lib.button import CustomButton
from gtnh.gui.lib.custom_widget import CustomWidget
from gtnh.gui.lib.progress_bar import CustomProgressBar


class ButtonArrayCallback:
    def __init__(
        self,
        update_asset: Callable[[], None],
        generate_nightly: Callable[[], None],
        client_mmc: Callable[[], None],
        client_zip: Callable[[], None],
        server_zip: Callable[[], None],
        client_curse: Callable[[], None],
        client_modrinth: Callable[[], None],
        client_technic: Callable[[], None],
        update_all: Callable[[], None],
    ) -> None:
        self.update_assets: Callable[[], None] = update_asset
        self.generate_nightly: Callable[[], None] = generate_nightly
        self.client_mmc: Callable[[], None] = client_mmc
        self.client_zip: Callable[[], None] = client_zip
        self.server_zip: Callable[[], None] = server_zip
        self.client_curse: Callable[[], None] = client_curse
        self.client_modrinth: Callable[[], None] = client_modrinth
        self.client_technic: Callable[[], None] = client_technic
        self.all: Callable[[], None] = update_all


class ButtonArray(LabelFrame, TtkLabelFrame):  # type: ignore
    """
    Widget managing update_all the buttons related to pack assembling.
    """

    def __init__(
        self,
        master: Any,
        frame_name: str,
        callbacks: ButtonArrayCallback,
        update_nightly: Callable[[], None],
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

        self.update_nightly: Callable[[], None] = update_nightly
        self.callbacks: ButtonArrayCallback = callbacks

        self.btn_client_cf: CustomButton = CustomButton(
            self.frame_btn, text="CurseForge client archive", command=callbacks.client_curse, themed=self.themed
        )
        self.btn_client_technic: CustomButton = CustomButton(
            self.frame_btn, text="Technic client archive", command=callbacks.client_technic, themed=self.themed
        )
        self.btn_client_mmc: CustomButton = CustomButton(
            self.frame_btn, text="MultiMC client archive", command=callbacks.client_mmc, themed=self.themed
        )
        self.btn_client_modrinth: CustomButton = CustomButton(
            self.frame_btn, text="Modrinth client archive", command=callbacks.client_modrinth, themed=self.themed
        )
        self.btn_generate_all: CustomButton = CustomButton(
            self.frame_btn, text="Generate update_all archives", command=callbacks.all, themed=self.themed
        )
        self.btn_update_nightly: CustomButton = CustomButton(
            self.frame_btn, text="Update nightly", command=update_nightly, themed=self.themed
        )
        self.btn_update_assets: CustomButton = CustomButton(
            self.frame_btn, text="Update assets", command=callbacks.update_assets, themed=self.themed
        )
        self.btn_client_zip: CustomButton = CustomButton(
            self.frame_btn, text="Zip client archive", command=callbacks.client_zip, themed=self.themed
        )
        self.btn_server_zip: CustomButton = CustomButton(
            self.frame_btn, text="Zip server archive", command=callbacks.server_zip, themed=self.themed
        )

        progress_bar_length: int = 500

        self.progress_bar_global = CustomProgressBar(
            self, label_text="test global", progress_bar_length=progress_bar_length
        )

        self.progress_bar_current_task = CustomProgressBar(
            self, label_text="test current task", progress_bar_length=progress_bar_length
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
            self.progress_bar_global,
            self.progress_bar_current_task,
        ]
        self.width: int = (
            width if width is not None else max([widget.get_description_size() for widget in self.widgets])
        )

        rows: int = 5

        for i in range(rows):
            self.rowconfigure(i, weight=1, pad=self.xpadding)

        self.columnconfigure(0, weight=1, pad=self.ypadding)

        self.update_widget()

    def populate_data(self, data: Any) -> None:
        """
        Method called by parent class to populate data in this class.

        :param data: the data to pass to this class
        :return: None
        """
        pass

    def show(self) -> None:
        """
        Method used to display widgets and child widgets, as well as to configure the "responsiveness" of the widgets.

        :return: None
        """
        x: int = 0
        y: int = 0

        self.progress_bar_global.grid(row=x, column=y)
        self.progress_bar_current_task.grid(row=x + 2, column=y)

        self.frame_btn.grid(row=x + 4, column=y)

        # grid withing the self.fram_btn
        pad: int = 3
        frame_columns: int = 3

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

        # manual override
        length_coef: int = 4  # coef used arbitrarily to demultiply the length of the labels for progress bars
        self.progress_bar_global.configure(width=length_coef * self.width)
        self.progress_bar_current_task.configure(width=length_coef * self.width)

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
        Method to update the widget and update_all its childs

        :return: None
        """
        self.hide()
        self.configure_widgets()
        self.show()

    def hide(self) -> None:
        """
        Method to hide the widget and update_all its childs
        :return None:
        """
        for widget in self.widgets:
            widget.grid_forget()

        self.update_idletasks()
