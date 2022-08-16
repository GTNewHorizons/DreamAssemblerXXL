from tkinter import Button, LabelFrame, Listbox, Scrollbar, StringVar
from typing import Any, Dict

from gtnh.gui.mod_info_frame import ModInfoFrame


class ExternalModList(LabelFrame):
    """Widget handling the list of external mods."""

    def __init__(self, master: Any, frame_name: str, callbacks: Dict[str, Any], **kwargs: Any):
        """
        Constructor of the ExternalModList class.

        :param master: the parent widget
        :param frame_name: the name displayed in the framebox
        :param callbacks: a dict of callbacks passed to this instance
        :param kwargs: params to init the parent class
        """
        LabelFrame.__init__(self, master, text=frame_name, **kwargs)
        self.ypadding: int = 20  # todo: tune this
        self.xpadding: int = 0  # todo: tune this
        self.sv_repo_name: StringVar = StringVar(self, value="")

        self.lb_mods: Listbox = Listbox(self, exportselection=False)

        self.btn_add: Button = Button(self, text="add new")
        self.btn_rem: Button = Button(self, text="delete highlighted")

        self.scrollbar: Scrollbar = Scrollbar(self)
        self.lb_mods.configure(yscrollcommand=self.scrollbar.set)
        self.scrollbar.configure(command=self.lb_mods.yview)

    def show(self) -> None:
        """
        Method used to display widgets and child widgets, as well as to configure the "responsiveness" of the widgets.

        :return: None
        """
        x: int = 0
        y: int = 0

        self.columnconfigure(0, weight=1, pad=self.ypadding)
        self.rowconfigure(0, weight=1, pad=self.xpadding)
        self.rowconfigure(1, weight=1, pad=self.xpadding)
        self.rowconfigure(2, weight=1, pad=self.xpadding)

        self.lb_mods.grid(row=x, column=y, columnspan=2, sticky="WE")
        self.scrollbar.grid(row=x, column=y + 2, columnspan=2, sticky="NS")
        self.btn_add.grid(row=x + 1, column=y, sticky="WE")
        self.btn_rem.grid(row=x + 1, column=y + 1, sticky="WE")

    def populate_data(self, data: Any) -> None:
        """
        Method called by parent class to populate data in this class.

        :param data: the data to pass to this class
        :return: None
        """
        pass


class ExternalModFrame(LabelFrame):
    """Main frame widget for the external mods' management."""

    def __init__(self, master: Any, frame_name: str, callbacks: Dict[str, Any], **kwargs: Any):
        """
        Constructor of the ExternalModFrame class.

        :param master: the parent widget
        :param frame_name: the name displayed in the framebox
        :param callbacks: a dict of callbacks passed to this instance
        :param kwargs: params to init the parent class
        """
        self.ypadding: int = 20  # todo:tune this
        self.xpadding: int = 0  # todo: tune this
        LabelFrame.__init__(self, master, text=frame_name, **kwargs)

        mod_info_callbacks: Dict[str, Any] = {
            "set_mod_version": callbacks["set_external_mod_version"],
            "set_mod_side": callbacks["set_external_mod_side"],
        }
        self.mod_info_frame: ModInfoFrame = ModInfoFrame(
            self, frame_name="external mod info", callbacks=mod_info_callbacks
        )
        self.external_mod_list: ExternalModList = ExternalModList(self, frame_name="external mod list", callbacks={})

    def show(self) -> None:
        """
        Method used to display widgets and child widgets, as well as to configure the "responsiveness" of the widgets.

        :return: None
        """
        self.columnconfigure(0, weight=1, pad=self.ypadding)
        self.rowconfigure(0, weight=1, pad=self.xpadding)
        self.rowconfigure(1, weight=1, pad=self.xpadding)

        self.external_mod_list.grid(row=0, column=0, sticky="WE")
        self.mod_info_frame.grid(row=1, column=0, sticky="WE")

        self.master.update_idletasks()

        self.external_mod_list.show()
        self.mod_info_frame.show()

    def populate_data(self, data: Any) -> None:
        """
        Method called by parent class to populate data in this class.

        :param data: the data to pass to this class
        :return: None
        """
        pass
