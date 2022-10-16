import asyncio
from tkinter import END, Button, LabelFrame, Listbox, Scrollbar, StringVar, Toplevel, Label, IntVar, Radiobutton, Entry
from tkinter.messagebox import showerror, showinfo
from typing import Any, Callable, Coroutine, Dict, List, Optional

from gtnh.defs import Position
from gtnh.gui.mod_info_frame import ModInfoFrame
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

        self.width: int = width if width is not None else max(len(self.btn_add_text), len(self.btn_rem_text), len(self.btn_add_version_text))

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
        pass

    async def del_external_mod(self) -> None:
        """
        Method called when the button to delete the highlighted external mod is pressed.

        :return: None
        """
        showerror("Feature not yet implemented", "The removal of external mods from assets is not yet implemented.")
        # don't forget to use self.del_mod_from_memory when implementing this

    async def add_external_mod(self) -> None:
        """
        Method called when the button to add an external mod is pressed.

        :return: None
        """
        # showerror("Feature not yet implemented", "The addition of external mods to the assets is not yet implemented.")
        # don't forget to use self.add_mod_in_memory when implementing this
        self.toggle_freeze()
        top_level: Toplevel = Toplevel(self)
        callbacks = {
            "freeze": self.toggle_freeze
        }
        mod_addition_frame: ModAdditionFrame = ModAdditionFrame(top_level, "external mod adder", callbacks=callbacks)
        mod_addition_frame.grid()
        mod_addition_frame.update_widget()
        top_level.title("External mod addition")

    def populate_data(self, data: Any) -> None:
        """
        Method called by parent class to populate data in this class.

        :param data: the data to pass to this class
        :return: None
        """

        self.lb_mods.insert(END, *sorted(data))

    async def on_listbox_click(self, event: Any) -> None:
        """
        Callback used when the user clicks on the external mods' listbox.

        :param event: the tkinter event passed by the tkinter in the Callback (unused)
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

        license: str = mod_info.license or "No license detected"
        side: str = mod_info.side

        data = {
            "name": name,
            "versions": [version.version_tag for version in mod_versions],
            "current_version": current_version,
            "license": license,
            "side": side,
        }
        self.mod_info_callback(data)


class ExternalModFrame(LabelFrame):
    """Main frame widget for the external mods' management."""

    def __init__(
        self, master: Any, frame_name: str, callbacks: Dict[str, Any], width: Optional[int] = None, **kwargs: Any
    ):
        """
        Constructor of the ExternalModFrame class.

        :param master: the parent widget
        :param frame_name: the name displayed in the framebox
        :param callbacks: a dict of callbacks passed to this instance
        :param width: the width to harmonize widgets in characters
        :param kwargs: params to init the parent class
        """
        self.ypadding: int = 0
        self.xpadding: int = 0
        LabelFrame.__init__(self, master, text=frame_name, **kwargs)

        self.width: Optional[int] = width

        mod_info_callbacks: Dict[str, Any] = {
            "set_mod_version": callbacks["set_external_mod_version"],
            "set_mod_side": callbacks["set_external_mod_side"],
        }
        self.mod_info_frame: ModInfoFrame = ModInfoFrame(
            self, frame_name="External mod info", callbacks=mod_info_callbacks
        )

        external_mod_list_callbacks: Dict[str, Any] = {
            "get_gtnh": callbacks["get_gtnh"],
            "get_external_mods": callbacks["get_external_mods"],
            "mod_info": self.mod_info_frame.populate_data,
            "add_mod_in_memory": callbacks["add_mod_in_memory"],
            "del_mod_in_memory": callbacks["del_mod_in_memory"],
            "freeze": callbacks["freeze"]
        }

        self.external_mod_list: ExternalModList = ExternalModList(
            self, frame_name="External mod list", callbacks=external_mod_list_callbacks
        )

        if self.width is None:
            self.width = self.external_mod_list.get_width()
            self.mod_info_frame.set_width(self.width)
            self.update_widget()

        else:
            self.mod_info_frame.set_width(self.width)
            self.external_mod_list.set_width(self.width)

    def configure_widgets(self) -> None:
        """
        Method to configure the widgets.

        :return: None
        """
        self.mod_info_frame.configure_widgets()
        self.external_mod_list.configure_widgets()

    def set_width(self, width: int) -> None:
        """
        Method to set the widgets' width.

        :param width: the new width
        :return: None
        """
        self.width = width
        self.mod_info_frame.set_width(self.width)
        self.external_mod_list.set_width(self.width)

    def get_width(self) -> int:
        """
        Getter for self.width.

        :return: the width in character sizes of the normalised widgets
        """
        assert self.width  # can't be None because how it's defined in the constructor
        return self.width

    def update_widget(self) -> None:
        """
        Method to update the widget and all its childs

        :return: None
        """
        self.hide()
        self.configure_widgets()
        self.show()

        self.external_mod_list.update_widget()
        self.mod_info_frame.update_widget()

    def hide(self) -> None:
        """
        Method to hide the widget and all its childs
        :return None:
        """
        self.external_mod_list.grid_forget()
        self.mod_info_frame.grid_forget()

        self.external_mod_list.hide()
        self.mod_info_frame.hide()

        self.update_idletasks()

    def show(self) -> None:
        """
        Method used to display widgets and child widgets, as well as to configure the "responsiveness" of the widgets.

        :return: None
        """
        x: int = 0
        y: int = 0
        rows: int = 2
        columns: int = 1

        for i in range(rows):
            self.rowconfigure(i, weight=1, pad=self.xpadding)

        for i in range(columns):
            self.columnconfigure(i, weight=1, pad=self.ypadding)

        self.external_mod_list.grid(row=x, column=y)
        self.mod_info_frame.grid(row=x + 1, column=y)

        self.external_mod_list.show()
        self.mod_info_frame.show()

        self.update_idletasks()

    def populate_data(self, data: Any) -> None:
        """
        Method called by parent class to populate data in this class.

        :param data: the data to pass to this class
        :return: None
        """
        mod_list: List[str] = data["external_mod_list"]
        self.external_mod_list.populate_data(mod_list)

class ModAdditionFrame(LabelFrame):
    """
    Class handling the widgets for the toplevel window about the mod addition.
    """


    def __init__(
            self, master: Any, frame_name: str, callbacks: Dict[str, Any], width: Optional[int] = None,
            **kwargs: Any
    ):
        """
        Constructor of the ModAdditionFrame class.

        :param master: the parent widget
        :param frame_name: the name displayed in the framebox
        :param callbacks: a dict of callbacks passed to this instance
        :param width: the width to harmonize widgets in characters
        :param kwargs: params to init the parent class
        """
        self.ypadding: int = 0
        self.xpadding: int = 0
        LabelFrame.__init__(self, master, text=frame_name, **kwargs)

        self.width: int = width or 50

        self.label_source_text:str = "Choose a source type for the mod"
        self.btn_src_other_text:str = "Other"
        self.btn_src_curse_text:str = "CurseForge"

        self.int_var_src:IntVar = IntVar()
        self.int_var_src.set(1)

        self.label_source:Label = Label(self, text = self.label_source_text)
        self.btn_src_other:Radiobutton = Radiobutton(self, text=self.btn_src_other_text, variable=self.int_var_src, value=2, command=self.update_widget)
        self.btn_src_curse:Radiobutton = Radiobutton(self, text=self.btn_src_curse_text, variable=self.int_var_src, value=1, command=self.update_widget)

        self.label_download_link_text:str = "Download link\n(check your download history to get it)"
        self.label_download_link:Label = Label(self, text=self.label_download_link_text)


        self.label_cf_project_id_text:str = "project ID"
        self.label_cf_project_id:Label = Label(self, text=self.label_cf_project_id_text)

        self.sv_cf_project_id:StringVar = StringVar()
        self.entry_cf_project_id:Entry = Entry(self, textvariable=self.sv_cf_project_id)

        self.label_cf_browser_url_text:str = "browser download page url\n(page where you can download the file)"
        self.label_cf_browser_url: Label = Label(self, text=self.label_cf_browser_url_text)

        self.sv_cf_browser_url: StringVar = StringVar()
        self.entry_cf_browser_url: Entry = Entry(self, textvariable=self.sv_cf_browser_url)

        self.sv_download_link:StringVar = StringVar(self)
        self.entry_download_link:Entry = Entry(self, textvariable=self.sv_download_link)

        self.btn_add_text:str = "Add external mod to DreamAssemblerXXL"
        self.btn_add:Button = Button(self, text=self.btn_add_text, command=self.add_mod)
        self.exit_func = callbacks["freeze"]

    def add_mod(self):
        """
        Method to add an external mod to DAXXL.

        :return: None
        """
        valid_download_url: bool = False
        valid_project_id: bool = False
        valid_browser_url: bool = False

        download_url:str = self.entry_download_link.get()
        if download_url.endswith(".jar") and (download_url.startswith("http://") or download_url.startswith("https://")):
            valid_download_url = True

        if self.int_var_src.get() != 1: # not curse
            if valid_download_url:
                showinfo("Operation successful", "The mod was added successfully to DreamAssemblerXXL")
            else:
                showerror("Error", "The download url isn't a valid http(s) link or isn't ending with '.jar'. Make sure you use the correct download link")
            return

        project_id = self.entry_cf_project_id.get()
        try:
            int(project_id)
            valid_project_id = True
        except ValueError:
            pass

        browser_url = self.entry_cf_browser_url.get()
        try:
            int(browser_url.split("/")[-1])
            valid_browser_url = True
        except ValueError:
            pass
        if not (download_url.startswith("http://") or download_url.startswith("https://")):
            valid_browser_url = False

        if valid_download_url and valid_project_id and valid_browser_url:
            showinfo("Operation successful", "The mod was added successfully to DreamAssemblerXXL")
        else:
            error_list: list = []
            if not valid_download_url:
                error_list.append("The download url isn't a valid http(s) link or isn't ending with '.jar'. Make sure you use the correct download link")
            if not valid_project_id:
                error_list.append("The project id contains other characters than numbers")
            if not valid_browser_url:
                error_list.append("The browser download page link isn't a valid http(s) link or doesn't terminate by a number. Make sure you use the correct link.")

            showerror("Error", f"The following error(s) occured:\n"+'\n'.join(error_list))

        return



    def configure_widgets(self) -> None:
        """
        Method to configure the widgets.

        :return: None
        """
        self.label_source.configure(width=self.width)
        self.btn_src_other.configure(width=self.width)
        self.btn_src_curse.configure(width=self.width)
        self.label_download_link.configure(width=self.width)
        self.entry_download_link.configure(width=2*self.width)

        self.label_cf_project_id.configure(width=self.width)
        self.entry_cf_project_id.configure(width=2*self.width)
        self.label_cf_browser_url.configure(width=self.width)
        self.entry_cf_browser_url.configure(width=2*self.width)
        self.btn_add.configure(width=self.width)





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
        self.label_source.grid_forget()
        self.btn_src_curse.grid_forget()
        self.btn_src_other.grid_forget()
        self.entry_download_link.grid_forget()
        self.label_download_link.grid_forget()

        self.label_cf_project_id.grid_forget()
        self.entry_cf_project_id.grid_forget()
        self.label_cf_browser_url.grid_forget()
        self.entry_cf_browser_url.grid_forget()

        self.btn_add.grid_forget()

        self.update_idletasks()

    def show(self) -> None:
        """
        Method used to display widgets and child widgets, as well as to configure the "responsiveness" of the widgets.

        :return: None
        """
        x: int = 0
        y: int = 0
        rows: int = 5
        columns: int = 3

        for i in range(rows+1):
            self.rowconfigure(i, weight=1, pad=self.xpadding)

        for i in range(columns+1):
            self.columnconfigure(i, weight=1, pad=self.ypadding)

        self.label_source.grid(row=x, column=y)
        self.btn_src_curse.grid(row=x, column=y+1)
        self.btn_src_other.grid(row=x, column=y+2)
        self.label_download_link.grid(row=x+1, column=y)
        self.entry_download_link.grid(row=x+1, column=y+1, columnspan=2)

        if self.int_var_src.get() == 1: # for curse mods
            self.label_cf_project_id.grid(row=x+2, column=y)
            self.entry_cf_project_id.grid(row=x+2, column=y+1, columnspan=2)
            self.label_cf_browser_url.grid(row=x+3, column=y)
            self.entry_cf_browser_url.grid(row=x+3, column=y+1, columnspan=2)

        self.btn_add.grid(row=x+4, column=1)

        self.update_idletasks()

    def populate_data(self, data: Any) -> None:
        """
        Method called by parent class to populate data in this class.

        :param data: the data to pass to this class
        :return: None
        """
        pass