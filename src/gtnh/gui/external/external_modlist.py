import asyncio
from tkinter import END, Button, LabelFrame, Listbox, Scrollbar, StringVar, Toplevel
from tkinter.messagebox import showerror
from typing import Any, Callable, Coroutine, Dict, Optional

from gtnh.defs import Position
from gtnh.gui.external.mod_adder_window import ModAdderWindow
from gtnh.models.gtnh_version import GTNHVersion
from gtnh.models.mod_info import ExternalModInfo
from gtnh.modpack_manager import GTNHModpackManager


class ExternalModList(LabelFrame):
    """Widget handling the list of external mods."""

    def __init__(
        self, master: Any, frame_name: str, callbacks: Dict[str, Any], width: Optional[int] = None, **kwargs: Any
    ):
        """
        Constructor of the ExternalModList class.

        :param master: the parent widget
        :param frame_name: the name displayed in the framebox
        :param callbacks: a dict of callbacks passed to this instance
        :param width: the width to harmonize widgets in characters
        :param kwargs: params to init the parent class
        """
        LabelFrame.__init__(self, master, text=frame_name, **kwargs)
        self.ypadding: int = 0
        self.xpadding: int = 0

        self.btn_add_text: str = "Add new mod"
        self.btn_add_version_text: str = "Add new version to highlighted"
        self.btn_rem_text: str = "Delete highlighted"

        self.get_gtnh_callback: Callable[[], Coroutine[Any, Any, GTNHModpackManager]] = callbacks["get_gtnh"]
        self.get_external_mods_callback: Callable[[], Dict[str, str]] = callbacks["get_external_mods"]
        self.toggle_freeze: Callable[[], None] = callbacks["freeze"]
        self.mod_info_callback: Callable[[Any], None] = callbacks["mod_info"]
        self.add_mod_to_memory: Callable[[str, str], None] = callbacks["add_mod_in_memory"]
        self.del_mod_from_memory: Callable[[str], None] = callbacks["del_mod_in_memory"]
        self.refresh_external_modlist: Callable[[], None] = callbacks["refresh_external_mods"]

        self.width: int = (
            width
            if width is not None
            else max(len(self.btn_add_text), len(self.btn_rem_text), len(self.btn_add_version_text))
        )

        self.sv_repo_name: StringVar = StringVar(self, value="")

        self.lb_mods: Listbox = Listbox(self, exportselection=False)
        self.lb_mods.bind("<<ListboxSelect>>", lambda event: asyncio.ensure_future(self.on_listbox_click(event)))

        self.btn_add: Button = Button(
            self, text=self.btn_add_text, command=lambda: asyncio.ensure_future(self.add_external_mod())
        )

        self.btn_add_version: Button = Button(
            self, text=self.btn_add_version_text, command=lambda: asyncio.ensure_future(self.add_new_version())
        )

        self.btn_rem: Button = Button(
            self, text=self.btn_rem_text, command=lambda: asyncio.ensure_future(self.del_external_mod())
        )

        self.scrollbar: Scrollbar = Scrollbar(self)
        self.lb_mods.configure(yscrollcommand=self.scrollbar.set)
        self.scrollbar.configure(command=self.lb_mods.yview)

    def configure_widgets(self) -> None:
        """
        Method to configure the widgets.

        :return: None
        """
        self.btn_add.configure(width=self.width)
        self.btn_add_version.configure(width=self.width)
        self.btn_rem.configure(width=self.width)

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
        self.lb_mods.grid_forget()
        self.scrollbar.grid_forget()
        self.btn_add.grid_forget()
        self.btn_add_version.grid_forget()
        self.btn_rem.grid_forget()

        self.update_idletasks()

    def show(self) -> None:
        """
        Method used to display widgets and child widgets, as well as to configure the "responsiveness" of the widgets.

        :return: None
        """
        x: int = 0
        y: int = 0
        rows: int = 4
        columns: int = 2

        for i in range(rows):
            self.rowconfigure(i, weight=1, pad=self.xpadding)

        for i in range(columns):
            self.columnconfigure(i, weight=1, pad=self.ypadding)

        self.lb_mods.grid(row=x, column=y, columnspan=2, sticky=Position.HORIZONTAL)
        self.scrollbar.grid(row=x, column=y + 2, sticky=Position.VERTICAL)
        self.btn_add.grid(row=x + 1, column=y)
        self.btn_rem.grid(row=x + 1, column=y + 1, columnspan=2)
        self.btn_add_version.grid(row=x + 2, column=y)

        self.update_idletasks()

    async def add_new_version(self) -> None:
        """
        Method called when the button to add a new version to an external mod is pressed.

        :return: None
        """
        try:
            index: int = self.lb_mods.curselection()[0]
            mod_name: str = self.lb_mods.get(index)
            self.toggle_freeze()
            top_level: Toplevel = Toplevel(self)

            def close(event: Any = None) -> None:
                """
                Method called when toplevel is destroyed.

                :return: None
                """
                if event.widget is top_level:
                    self.toggle_freeze()
                    asyncio.ensure_future(self.refresh_external_modlist())  # type: ignore

            top_level.bind("<Destroy>", close)
            callbacks = {
                "get_gtnh": self.get_gtnh_callback,
                "add_mod_in_memory": self.add_mod_to_memory,
                "del_mod_from_memory": self.del_mod_from_memory,
            }
            mod_addition_frame: ModAdderWindow = ModAdderWindow(
                top_level, "external version adder", callbacks=callbacks, mod_name=mod_name
            )
            mod_addition_frame.grid()
            mod_addition_frame.update_widget()
            top_level.title("External mod addition")
        except IndexError:
            showerror(
                "No curseforge mod selected",
                "In order to add a new version to a curseforge mod, you must select one first",
            )
            return

    async def del_external_mod(self) -> None:
        """
        Method called when the button to delete the highlighted external mod is pressed.

        :return: None
        """
        # showerror("Feature not yet implemented", "The removal of external mods from assets is not yet implemented.")
        # don't forget to use self.del_mod_from_memory when implementing this
        try:
            index: int = self.lb_mods.curselection()[0]
            mod_name: str = self.lb_mods.get(index)
            gtnh: GTNHModpackManager = await self.get_gtnh_callback()
            self.lb_mods.delete(index)
            await gtnh.delete_external_mod(mod_name)
        except IndexError:
            showerror(
                "No curseforge mod selected",
                "In order to add a new version to a curseforge mod, you must select one first",
            )
            return

    async def add_external_mod(self) -> None:
        """
        Method called when the button to add an external mod is pressed.

        :return: None
        """

        # showerror("Feature not yet implemented", "The addition of external mods to the assets is not yet implemented.")
        # don't forget to use self.add_mod_in_memory when implementing this
        self.toggle_freeze()
        top_level: Toplevel = Toplevel(self)

        def close(event: Any = None) -> None:
            """
            Method called when toplevel is destroyed.

            :return: None
            """
            if event.widget is top_level:
                self.toggle_freeze()
                asyncio.ensure_future(self.refresh_external_modlist())  # type: ignore

        top_level.bind("<Destroy>", close)
        callbacks = {
            "get_gtnh": self.get_gtnh_callback,
            "add_mod_in_memory": self.add_mod_to_memory,
            "del_mod_from_memory": self.del_mod_from_memory,
        }
        mod_addition_frame: ModAdderWindow = ModAdderWindow(top_level, "external mod adder", callbacks=callbacks)
        mod_addition_frame.grid()
        mod_addition_frame.update_widget()
        top_level.title("External mod addition")

    def populate_data(self, data: Any) -> None:
        """
        Method called by parent class to populate data in this class.

        :param data: the data to pass to this class
        :return: None
        """
        self.lb_mods.delete(0, END)
        self.lb_mods.insert(END, *sorted(data))

    async def on_listbox_click(self, _: Any) -> None:
        """
        Callback used when the user clicks on the external mods' listbox.

        :param _: the tkinter event passed by the tkinter in the Callback (unused)
        :return: None
        """

        index: int = self.lb_mods.curselection()[0]
        gtnh: GTNHModpackManager = await self.get_gtnh_callback()
        mod_info: ExternalModInfo = gtnh.assets.get_external_mod(self.lb_mods.get(index))
        name: str = mod_info.name
        mod_versions: list[GTNHVersion] = mod_info.versions
        latest_version: Optional[GTNHVersion] = mod_info.get_latest_version()
        assert latest_version
        external_mods: Dict[str, str] = self.get_external_mods_callback()
        current_version: str = external_mods[name] if name in external_mods else latest_version.version_tag

        _license: str = mod_info.license or "No license detected"
        side: str = mod_info.side

        data = {
            "name": name,
            "versions": [version.version_tag for version in mod_versions],
            "current_version": current_version,
            "license": _license,
            "side": side,
        }
        self.mod_info_callback(data)
