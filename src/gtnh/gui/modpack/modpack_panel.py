from asyncio import Task
from tkinter import LabelFrame
from tkinter.ttk import LabelFrame as TtkLabelFrame
from typing import Any, Callable, List, Optional

from gtnh.defs import Position
from gtnh.gui.modpack.button_array import ButtonArray, ButtonArrayCallback
from gtnh.gui.modpack.release_list import ReleaseList, ReleaseListCallback


class ModpackPanelCallback(ButtonArrayCallback, ReleaseListCallback):
    def __init__(
        self,
        update_asset: Callable[[], Task[None]],
        generate_experimental: Callable[[], Task[None]],
        generate_daily: Callable[[], Task[None]],
        client_mmc: Callable[[], Task[None]],
        client_mmc_j9: Callable[[], Task[None]],
        client_zip: Callable[[], Task[None]],
        server_zip: Callable[[], Task[None]],
        server_zip_j9: Callable[[], Task[None]],
        client_curse: Callable[[], Task[None]],
        client_modrinth: Callable[[], Task[None]],
        client_technic: Callable[[], Task[None]],
        update_all: Callable[[], Task[None]],
        update_beta: Callable[[], Task[None]],
        generate_changelog: Callable[[], Task[None]],
        generate_cf_files: Callable[[], Task[None]],
        load: Callable[[str], Task[None]],
        delete: Callable[[str], Task[None]],
        add: Callable[[str, str], Task[None]],
    ):
        ButtonArrayCallback.__init__(
            self,
            update_asset=update_asset,
            generate_experimental=generate_experimental,
            generate_daily=generate_daily,
            client_mmc=client_mmc,
            client_mmc_j9=client_mmc_j9,
            client_zip=client_zip,
            server_zip=server_zip,
            server_zip_j9=server_zip_j9,
            client_curse=client_curse,
            client_modrinth=client_modrinth,
            client_technic=client_technic,
            update_all=update_all,
            update_beta=update_beta,
            generate_changelog=generate_changelog,
            generate_intermediate_cf_files=generate_cf_files,
        )

        ReleaseListCallback.__init__(self, load=load, delete=delete, add=add)


class ModpackPanel(LabelFrame, TtkLabelFrame):  # type: ignore
    """Main frame for managing the releases."""

    def __init__(
        self,
        master: Any,
        frame_name: str,
        callbacks: ModpackPanelCallback,
        width: Optional[int] = None,
        themed: bool = False,
        **kwargs: Any,
    ) -> None:
        """
        Constructor of the ModpackPanel class.

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
        self.width: int = width if width is not None else 20  # arbitrary value

        self.callbacks: ModpackPanelCallback = callbacks

        self.action_frame: ButtonArray = ButtonArray(
            self,
            frame_name="Availiable tasks",
            callbacks=self.callbacks,
            update_experimental=self.update_experimental,
            update_daily=self.update_daily,
            themed=self.themed,
        )

        self.modpack_list: ReleaseList = ReleaseList(
            self, frame_name="Modpack Versions", callbacks=self.callbacks, themed=self.themed
        )

    def update_experimental(self) -> None:
        """
        Callback to generate/update the experimental builds.

        :return: None
        """
        self.callbacks.generate_experimental()
        data: List[str] = list(self.modpack_list.listbox.get_values())
        if "experimental" not in data:
            data.insert(0, "experimental")
            self.modpack_list.listbox.set_values(data)

    def update_daily(self) -> None:
        """
        Callback to generate/update the daily builds.

        :return: None
        """
        self.callbacks.generate_daily()
        data: List[str] = list(self.modpack_list.listbox.get_values())
        if "daily" not in data:
            data.insert(0, "daily")
            self.modpack_list.listbox.set_values(data)

    def configure_widgets(self) -> None:
        """
        Method to configure the widgets.

        :return: None
        """
        self.modpack_list.configure_widgets()
        self.action_frame.configure_widgets()

    def set_width(self, width: int) -> None:
        """
        Method to set the widgets' width.

        :param width: the new width
        :return: None
        """
        self.width = width
        self.modpack_list.set_width(self.width)
        self.action_frame.set_width(self.width)

    def get_width(self) -> int:
        """
        Getter for self.width.

        :return: the width in character sizes of the normalised widgets
        """
        return self.width

    def update_widget(self) -> None:
        """
        Method to update the widget and update all its childs

        :return: None
        """
        self.hide()
        self.configure_widgets()
        self.show()

    def hide(self) -> None:
        """
        Method to hide the widget and update all its childs
        :return None:
        """
        self.modpack_list.hide()
        self.action_frame.hide()

        self.update_idletasks()

    def show(self) -> None:
        """
        Method used to display widgets and child widgets, as well as to configure the "responsiveness" of the widgets.

        :return: None
        """
        x: int = 0
        y: int = 0
        rows: int = 1
        columns: int = 2

        for i in range(rows):
            self.rowconfigure(i, weight=1, pad=self.xpadding)

        for i in range(columns):
            self.columnconfigure(i, weight=1, pad=self.ypadding)

        self.modpack_list.grid(row=x, column=y, sticky=Position.ALL)
        self.action_frame.grid(row=x, column=y + 1, sticky=Position.ALL)

        self.modpack_list.show()
        self.action_frame.show()

        self.update_idletasks()

    def populate_data(self, data: Any) -> None:
        """
        Method called by parent class to populate data in this class.

        :param data: the data to pass to this class
        :return: None
        """
        self.modpack_list.populate_data(data)
