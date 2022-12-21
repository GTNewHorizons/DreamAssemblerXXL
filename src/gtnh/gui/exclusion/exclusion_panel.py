"""Module providing a widget to handle file exclusions."""
from asyncio import Task
from tkinter import LabelFrame
from tkinter.ttk import LabelFrame as TtkLabelFrame
from typing import Any, Callable, Dict, List, Optional

from gtnh.defs import Position
from gtnh.gui.lib.button import CustomButton
from gtnh.gui.lib.custom_widget import CustomWidget
from gtnh.gui.lib.listbox import CustomListbox
from gtnh.gui.lib.text_entry import TextEntry


class ExclusionPanelCallback:
    """Exclusion Panel Callback class. The goal of this class is to provide a type for the ExclusionPanel callbacks."""

    def __init__(self, add: Callable[[str], Task[None]], delete: Callable[[str], Task[None]]):
        """
        Construct the ExclusionPanelCallback class.

        Parameters
        ----------
        add: Callable[[str], Task[None]]
            Callback used when a new exclusion is entered in the GUI.

        delete: Callable[[str], Task[None]]
            Callback used when the user wants to delete the highlighted exclusion in the listbox.
        """
        self.add: Callable[[str], Task[None]] = add
        self.delete: Callable[[str], Task[None]] = delete


class ExclusionPanel(LabelFrame, TtkLabelFrame):  # type: ignore
    """Widget managing an exclusion list."""

    def __init__(
        self,
        master: Any,
        frame_name: str,
        callbacks: ExclusionPanelCallback,
        width: Optional[int] = None,
        themed: bool = False,
        **kwargs: Any,
    ) -> None:
        """
        Construct of the ExclusionFrame class.

        Parameters
        ----------
        master: Any
            The master widget.

        frame_name: str
            The name of the frame.

        callbacks: ExclusionPanelCallback
            The callbacks used within this class.

        width: Optional[int]
            If provided, set the width of the subwidgets.

        themed: bool
            If yes, use the themed version of ttk.

        kwargs: Any
            Other keywords arguments that will be passed to the LabelFrame init.
        """
        self.themed = themed
        if themed:
            LabelFrame.__init__(self, master, text=frame_name, **kwargs)
        else:
            TtkLabelFrame.__init__(self, master, text=frame_name, **kwargs)
        self.xpadding: int = 0
        self.ypadding: int = 0
        self.add_callback: Callable[[str], Task[None]] = callbacks.add
        self.del_callback: Callable[[str], Task[None]] = callbacks.delete

        self.listbox: CustomListbox = CustomListbox(
            self,
            label_text=frame_name,
            exportselection=False,
            height=12,
            display_horizontal_scrollbar=True,
            themed=self.themed,
        )

        self.exclusion: TextEntry = TextEntry(self, label_text="", hide_label=True, themed=self.themed)

        self.btn_add: CustomButton = CustomButton(self, text="Add new exclusion", command=self.add, themed=self.themed)
        self.btn_del: CustomButton = CustomButton(
            self, text="Remove highlighted", command=self.delete, themed=self.themed
        )

        self.widgets: List[CustomWidget] = [self.btn_add, self.btn_del, self.listbox]

        self.width: int = (
            width if width is not None else max([widget.get_description_size() for widget in self.widgets])
        )

        self.rowconfigure(0, weight=1)

        self.columnconfigure(0, weight=1, pad=self.ypadding)
        self.columnconfigure(1, weight=1, pad=self.ypadding)

        # no rowconfigure to avoid space between elements

        self.update_widget()

    def add_to_list_sorted(self, elem: str) -> None:
        """
        Insert an element into the listbox and sort the elements at the same time.

        Parameters
        ----------
        elem: str
            The element to add in the listbox.

        Returns
        -------
        None.
        """
        exclusions: List[str] = self.listbox.get_values()
        if elem in exclusions:
            return

        exclusions.append(elem)
        self.listbox.set_values(sorted(exclusions))

    def add(self) -> None:
        """
        Add the exclusion typed in the GUI to the listbox.

        Returns
        -------
        None.
        """
        exclusion: str = self.exclusion.get()
        if exclusion == "":
            return

        self.add_to_list_sorted(exclusion)
        self.add_callback(exclusion)

    def delete(self) -> None:
        """
        Delete the exclusion highlighted in the listbox.

        Returns
        -------
        None.
        """
        if self.listbox.has_selection():
            position: int = self.listbox.get()
            exclusion: str = self.listbox.get_value_at_index(position)
            self.listbox.del_value_at_index(position)
            self.del_callback(exclusion)

    def configure_widgets(self) -> None:
        """
        Configure the widgets.

        Returns
        -------
        None.
        """
        for widget in self.widgets:
            widget.configure(width=self.width)

        # overriding exclusion widget to get proper size
        # self.exclusion.configure(width=2 * (self.width + 6))

    def set_width(self, width: int) -> None:
        """
        Set the widgets' width.

        Parameters
        ----------
        width: int
            The new width to apply.

        Returns
        -------
        None.
        """
        self.width = width
        self.configure_widgets()

    def get_width(self) -> int:
        """
        Get self.width, the width applied to all the widgets.

        Returns
        -------
        The width applied to the widgets.
        """
        return self.width

    def update_widget(self) -> None:
        """
        Update the widget and all its childs.

        Returns
        -------
        None.
        """
        self.hide()
        self.configure_widgets()
        self.show()

    def hide(self) -> None:
        """
        Hide the widget and all its childs.

        Returns
        -------
        None.
        """
        for widget in self.widgets:
            widget.grid_forget()

    def show(self) -> None:
        """
        Display the widgets and its child widgets, as well as configuring the "responsiveness" of the widgets.

        Returns
        -------
        None.
        """
        x: int = 0
        y: int = 0

        self.listbox.grid(row=x, column=y, columnspan=2, sticky=Position.ALL)
        self.exclusion.grid(row=x + 1, column=y, columnspan=2, stick=Position.HORIZONTAL)
        self.btn_add.grid(row=x + 2, column=y, sticky=Position.HORIZONTAL)
        self.btn_del.grid(row=x + 2, column=y + 1, sticky=Position.HORIZONTAL)

    def populate_data(self, data: Dict[str, Any]) -> None:
        """
        Populate data in this instance.

        Called by the parent class.

        Parameters
        ----------
        data: Dict[str, Any]
            The data used to populate the instance of the class.

        Returns
        -------
        None.
        """
        self.listbox.set_values(data["exclusions"])
