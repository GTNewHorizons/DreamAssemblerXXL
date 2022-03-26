import tkinter as tk
from pathlib import Path
from tkinter.messagebox import showerror, showinfo, showwarning
from tkinter.ttk import Combobox, Progressbar
from typing import Any, List, Optional, Tuple, Union
from urllib import parse

import pydantic
from github import Github
from github.Organization import Organization

from gtnh.add_mod import get_repo, new_mod_from_repo
from gtnh.defs import Side
from gtnh.exceptions import LatestReleaseNotFound, NoModAssetFound, PackingInterruptException, RepoNotFoundException
from gtnh.mod_info import GTNHModpack, ModInfo
from gtnh.pack_assembler import handle_pack_extra_files, pack_clientpack, pack_serverpack
from gtnh.pack_downloader import download_mods, ensure_cache_dir
from gtnh.utils import crawl, get_token, load_gtnh_manifest, move_mods, save_gtnh_manifest, verify_url


class MainFrame(tk.Tk):
    """
    Main windows of DreamAssemblerXXL. Lets you select what you want to do with it via the buttons. Each button spawns
    a new window allowing you to do the selected task(s).
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """
        Constructor of the MainFrame class.

        :return: None
        """
        tk.Tk.__init__(self, *args, **kwargs)
        self.title("DreamAssemblerXXL")

        # setting up a gtnh metadata instance
        self.gtnh_modpack = load_gtnh_manifest()

        # setting up the icon of the window
        imgicon = tk.PhotoImage(file=Path(__file__).parent / "icon.png")
        self.iconphoto(True, imgicon)

        # widgets in the window
        self.repo_popup: AddRepoFrame = AddRepoFrame(self)
        self.archive_popup: ArchiveFrame = ArchiveFrame(self, length=300)
        self.exclusion_popup: HandleFileExclusionFrame = HandleFileExclusionFrame(self)
        # self.dependencies_popup: HandleDepUpdateFrame = HandleDepUpdateFrame(self)
        self.curse_popup: AddCurseModFrame = AddCurseModFrame(self)

        # grid manager
        self.repo_popup.grid(row=0, column=0, sticky="WNS")
        self.curse_popup.grid(row=0, column=1, sticky="WENS")
        self.archive_popup.grid(row=0, column=2, sticky="WENS")
        self.exclusion_popup.grid(row=1, column=0, columnspan=2, sticky="WNS")
        # self.dependencies_popup.grid(row=1, column=1, sticky="WENS")


class BaseFrame(tk.LabelFrame):
    """
    Base popup class.
    """

    def __init__(self, root: MainFrame, popup_name: str = "DreamAssemblerXXL", *args: Any, **kwargs: Any) -> None:
        """
        Constructor of the BaseFrame class.

        :param root: the MainFrame widget.
        :param popup_name: Name of the popup window
        :param window_width: width in pixel of the window by default
        :param window_height: height in pixel of the window by default
        :param enforce_window_size: activate windows size setup or not
        :param args:
        :param kwargs:
        :return: None
        """
        tk.LabelFrame.__init__(self, root, text=popup_name, *args, **kwargs)
        self.root = root

    def reload_gtnh_metadata(self) -> None:
        """
        Method to reload the metadata from disk.

        :return: None
        """
        self.root.gtnh_modpack = load_gtnh_manifest()
        print("metadata loaded!")

    def save_gtnh_metadata(self) -> None:
        """
        Method to save the metadata to disk.

        :return: None
        """
        save_gtnh_manifest(self.root.gtnh_modpack)
        print("metadata saved!")


class AddRepoFrame(BaseFrame):
    """
    Frame allowing you to manage repositories in the github list contained in DreamAssemblerXXL.
    When adding a new Repository, the following things can happen:
    - Will raise you a tkinter error messagebox when the repository is not found.
    - Will raise you a tkinter warning messagebox when the repository is already added.
    - Will raise you a tkinter info messagebox when the repository is successfully added to the list.
    """

    def __init__(self, root: MainFrame) -> None:
        """
        Constructor of the AddRepoFrame class.

        :param root: the MainFrame instance
        :return: None
        """
        BaseFrame.__init__(self, root, popup_name="Repository adder")

        # ModInfo memory
        self.curr_mod: Union[ModInfo, None] = None

        # widgets in the window
        self.custom_frame = CustomLabelFrame(self, self.get_repos(), False, add_callback=self.validate_callback)
        self.combobox_side = Combobox(self, values=["CLIENT", "SERVER", "BOTH", "NONE"])
        self.combobox_side.bind("<<ComboboxSelected>>", self.update_mod)
        self.label_mod = tk.Label(self, text="current selected mod: ")

        # dirty hack to reshape the custom label frame without making a new class
        self.custom_frame.listbox.configure(height=20)
        self.custom_frame.listbox.bind("<<ListboxSelect>>", self.fill_fields)

        # grid manager
        self.custom_frame.grid(row=0, column=0, columnspan=2)
        self.label_mod.grid(row=1, column=0)
        self.combobox_side.grid(row=1, column=1, sticky="E")

        # state control vars
        self.is_messagebox_open = False

    def get_repos(self) -> List[str]:
        """
        Method to get a list of all the repository names in the metadata.

        :return: the list of all the repository names.
        """
        return [repo.name for repo in self.root.gtnh_modpack.github_mods]

    def validate_callback(self, repo_name: str) -> bool:
        """
        Method executed when self.btn_validate is pressed by the user.

        :return: if the repo was added or not.
        """
        repo_added = False

        # if no messagebox had been opened
        if not self.is_messagebox_open:
            self.is_messagebox_open = True

            # checking the repo on github
            try:
                new_repo = get_repo(repo_name)

            # let the user know that the repository doesn't exist
            except RepoNotFoundException:
                showerror("repository not found", f"the repository {repo_name} was not found on github.")

            else:
                # let the user know that the repository is already added
                if self.root.gtnh_modpack.has_github_mod(new_repo.name):
                    showwarning("repository already added", f"the repository {repo_name} is already added.")

                # adding the repo
                else:
                    try:
                        new_mod = new_mod_from_repo(new_repo)
                        self.root.gtnh_modpack.github_mods.append(new_mod)
                        self.save_gtnh_metadata()
                        self.reload_gtnh_metadata()
                        showinfo("repository added successfully", f"the repo {repo_name} was added successfully!")
                        repo_added = True

                    # let the user know that the repository has no release, therefore it won't be added to the list
                    except LatestReleaseNotFound:
                        showerror("no release availiable on the repository", f"the repository {repo_name} has no release, aborting")

                    # if no mod asset found:
                    except NoModAssetFound:
                        showwarning(
                            "no asset found", f"the repository {repo_name} has no asset found. This usually means it has no jar file in the release. Aborting."
                        )

            # releasing the blocking
            self.is_messagebox_open = False
        return repo_added

    def fill_fields(self, *args: Any) -> None:
        """
        Method used to populate the combobox representing the side of the github mod when it's name is clicked in the
        listbox.

        :param args:
        :return: None
        """

        listbox = self.custom_frame.listbox

        # catch weird edge cases of listbox selection
        try:
            name = listbox.get(listbox.curselection()[0])
        except IndexError:
            return

        self.curr_mod = self.root.gtnh_modpack.get_github_mod(name)
        self.label_mod.configure(text=f"current selected mod: {name}")
        self.combobox_side.set(self.curr_mod.side)

    def update_mod(self, *args: Any) -> None:
        """
        Method called when a side in the combobox is selected.

        :param args:
        :return: None
        """

        if self.curr_mod is None:
            return

        self.curr_mod.side = Side(self.combobox_side.get())
        github_mods = [mod for mod in self.root.gtnh_modpack.github_mods if mod.name != self.curr_mod.name]
        github_mods.append(self.curr_mod)
        self.root.gtnh_modpack.github_mods = github_mods
        self.save_gtnh_metadata()
        self.reload_gtnh_metadata()


class AddCurseModFrame(BaseFrame):
    """
    Frame allowing you to add a curse mod in the metadata.
    """

    def __init__(self, root: MainFrame) -> None:
        """
        Constructor of the AddCurseModFrame class.

        :param root: the MainFrame instance
        :return: None
        """
        BaseFrame.__init__(self, root, popup_name="Curse mods management")

        # widgets
        self.label_name = tk.Label(self, text="mod name")
        self.label_page_url = tk.Label(self, text="project url")
        self.label_license = tk.Label(self, text="license")
        self.label_version = tk.Label(self, text="mod version")
        self.label_browser_url = tk.Label(self, text="url of the download page")
        self.label_download_url = tk.Label(self, text="direct download url of the mod file")
        self.label_release_date = tk.Label(self, text="release date")
        self.label_maven_url = tk.Label(self, text="maven url")
        self.label_side = tk.Label(self, text="client/server side")

        self.sv_name = tk.StringVar(self)
        self.sv_page_url = tk.StringVar(self)
        self.sv_license = tk.StringVar(self)
        self.sv_version = tk.StringVar(self)
        self.sv_browser_url = tk.StringVar(self)
        self.sv_download_url = tk.StringVar(self)
        self.sv_release_date = tk.StringVar(self)
        self.sv_maven_url = tk.StringVar(self)

        self.entry_name = tk.Entry(self, textvariable=self.sv_name)
        self.entry_page_url = tk.Entry(self, textvariable=self.sv_page_url)
        self.entry_license = tk.Entry(self, textvariable=self.sv_license)
        self.entry_version = tk.Entry(self, textvariable=self.sv_version)
        self.entry_browser_url = tk.Entry(self, textvariable=self.sv_browser_url)
        self.entry_download_url = tk.Entry(self, textvariable=self.sv_download_url)
        self.entry_release_date = tk.Entry(self, textvariable=self.sv_release_date)
        self.entry_maven_url = tk.Entry(self, textvariable=self.sv_maven_url)

        self.combo_box_sides = Combobox(self, values=["CLIENT", "SERVER", "BOTH", "NONE"])
        self.combo_box_sides.current(2)

        self.custom_label_frame = CustomLabelFrame(self, [x.name for x in self.root.gtnh_modpack.external_mods], False, delete_callback=self.delete_callback)

        self.btn_add = tk.Button(self, text="add/update", command=self.add)

        # dirty hack to reshape the custom label frame without making a new class
        self.custom_label_frame.listbox.configure(height=21)
        self.custom_label_frame.btn_add.grid_forget()
        self.custom_label_frame.btn_remove.grid_forget()
        self.custom_label_frame.entry.grid_forget()
        self.custom_label_frame.btn_remove.grid(row=3, column=0, columnspan=2, sticky="WE")
        self.custom_label_frame.listbox.bind("<<ListboxSelect>>", self.fill_fields)

        # grid manager
        self.custom_label_frame.grid(row=0, column=0, rowspan=21, sticky="NS")
        self.label_name.grid(row=0, column=1, sticky="WE")
        self.entry_name.grid(row=1, column=1, sticky="WE")
        self.label_page_url.grid(row=2, column=1, sticky="WE")
        self.entry_page_url.grid(row=3, column=1, sticky="WE")
        self.label_license.grid(row=4, column=1, sticky="WE")
        self.entry_license.grid(row=5, column=1, sticky="WE")
        self.label_version.grid(row=6, column=1, sticky="WE")
        self.entry_version.grid(row=7, column=1, sticky="WE")
        self.label_browser_url.grid(row=8, column=1, sticky="WE")
        self.entry_browser_url.grid(row=9, column=1, sticky="WE")
        self.label_download_url.grid(row=10, column=1, sticky="WE")
        self.entry_download_url.grid(row=11, column=1, sticky="WE")
        self.label_release_date.grid(row=12, column=1, sticky="WE")
        self.entry_release_date.grid(row=13, column=1, sticky="WE")
        self.label_maven_url.grid(row=16, column=1, sticky="WE")
        self.entry_maven_url.grid(row=17, column=1, sticky="WE")
        self.label_side.grid(row=18, column=1, sticky="WE")
        self.combo_box_sides.grid(row=19, column=1, sticky="WE")
        self.btn_add.grid(row=20, column=1, sticky="WE")

    def add(self) -> None:
        """
        Method used to parse all the data to add a new external mod.

        :return: None
        """
        try:
            errored_url = [
                label["text"]
                for label, stringvar in [
                    (self.label_page_url, self.sv_page_url),
                    (self.label_browser_url, self.sv_browser_url),
                    (self.label_download_url, self.sv_browser_url),
                ]
                if not verify_url(stringvar.get())
            ]

            if len(errored_url) > 0:
                showerror("invalid url detected", f"""{",".join(errored_url)} are invalid. Please check.""")
                return

            filename = parse.unquote_plus(Path(parse.urlparse(self.sv_download_url.get()).path).name)

            if not (filename.endswith(".jar") or filename.endswith(".zip")):
                showerror("wrong download url", "the url for the download doesn't end up with .zip or .jar. Please check")
                return

            new_mod = ModInfo(
                name=self.sv_name.get(),
                repo_url=self.sv_page_url.get(),
                license=self.sv_license.get(),
                version=self.sv_version.get(),
                browser_download_url=self.sv_browser_url.get(),
                download_url=self.sv_download_url.get(),
                tagged_at=self.sv_release_date.get(),
                filename=filename,
                maven=self.sv_maven_url.get(),
                side=self.combo_box_sides.get(),
            )

        # catching datetime format errors
        except pydantic.error_wrappers.ValidationError:
            showerror("invalid date format", f"{self.sv_release_date.get()} is an invalid date format. It must be written as: YYYY-MM-DD hh:mm:ss")
            return

        # refreshing the modlist in case the mod is already in the list
        external_mods = [mod for mod in self.root.gtnh_modpack.external_mods if not mod.name == new_mod.name]
        external_mods.append(new_mod)
        self.root.gtnh_modpack.external_mods = external_mods

        # save/reload because the cached properties doesn't update otherwise
        self.save_gtnh_metadata()
        self.reload_gtnh_metadata()

        content = self.custom_label_frame.get_listbox_content()
        content.append(new_mod.name)
        content = list(set(content))
        self.custom_label_frame.listbox.delete(0, tk.END)
        self.custom_label_frame.listbox.insert(tk.END, *sorted(content, key=lambda x: x.lower()))

    def fill_fields(self, *args: Any) -> None:
        """
        Method used to populate the fields of an external mod when it's name is clicked in the listbox.

        :param args:
        :return: None
        """

        listbox = self.custom_label_frame.listbox

        # catch weird edge cases of listbox selection
        try:
            name = listbox.get(listbox.curselection()[0])
        except IndexError:
            return

        modinfo = self.root.gtnh_modpack.get_external_mod(name)
        bindings = (
            ("name", self.sv_name),
            ("repo_url", self.sv_page_url),
            ("license", self.sv_license),
            ("version", self.sv_version),
            ("browser_download_url", self.sv_browser_url),
            ("download_url", self.sv_download_url),
            ("tagged_at", self.sv_release_date),
            # ("filename", self.sv_file_name),
            ("maven", self.sv_maven_url),
        )

        # filling the fields
        for modinfo_field, stringvar in bindings:
            stringvar.set(getattr(modinfo, modinfo_field))
        self.combo_box_sides.set(modinfo.side)

    def delete_callback(self, mod_name: str) -> bool:
        """
        Method called when the selected mod in the listbox is deleted.

        :param mod_name: the name of the deleted mod.
        :return: True
        """
        self.root.gtnh_modpack.external_mods = [mod for mod in self.root.gtnh_modpack.external_mods if not mod.name == mod_name]
        self.save_gtnh_metadata()
        self.reload_gtnh_metadata()
        return True


class ArchiveFrame(BaseFrame):
    """
    Window allowing you to pack the archives for all the supported plateforms.
    """

    def __init__(self, root: MainFrame, length: int = 500) -> None:
        """
        Constructor of the ArchiveFrame class.

        :param root: the MainFrame instance
        :param length: size of the progress bars
        :return: None
        """
        BaseFrame.__init__(self, root, popup_name="Archive packager")

        # widgets on the window
        self.progress_bar = Progressbar(self, orient="horizontal", mode="determinate", length=length)
        self.progress_bar_global = Progressbar(self, orient="horizontal", mode="determinate", length=length)
        self.progress_label_global = tk.Label(self, text="")
        self.progress_label = tk.Label(self, text="")
        self.label_pack_version = tk.Label(self, text="pack_version")
        self.sv_pack_version = tk.StringVar(self, value=self.root.gtnh_modpack.modpack_version)
        self.entry_pack_version = tk.Entry(self, textvariable=self.sv_pack_version)
        self.btn_start = tk.Button(self, text="start", command=self.start, width=20)

        # grid manager
        self.progress_bar_global.grid(row=0, column=0)
        self.progress_label_global.grid(row=1, column=0)
        self.progress_bar.grid(row=2, column=0)
        self.progress_label.grid(row=3, column=0)
        self.label_pack_version.grid(row=4, column=0)
        self.entry_pack_version.grid(row=5, column=0)
        self.btn_start.grid(row=6, column=0)

    def start(self) -> None:
        """
        Method called when self.btn_start is pressed by the user. It starts the packaging process.

        :return: None
        """
        # rudimentary version parser
        if self.sv_pack_version.get() == "" or "." not in self.sv_pack_version.get():
            showerror("incorrect versionning", f"{self.sv_pack_version.get()} is incorrect: it must not be empty and have dots (ie 2.1.2.0) in it.")
            return

        # update pack_version
        self.root.gtnh_modpack.modpack_version = self.sv_pack_version.get()
        self.save_gtnh_metadata()
        self.reload_gtnh_metadata()

        # disabling the entry during the whole process
        self.entry_pack_version.config(state=tk.DISABLED)

        github = Github(get_token())
        organization = github.get_organization("GTNewHorizons")
        client_folder = Path(__file__).parent / "cache" / "client_archive"
        server_folder = Path(__file__).parent / "cache" / "server_archive"

        def error_callback_handle_extra_files() -> None:
            showerror("release not found", "The gtnh modpack repo has no release. Aborting.")

        try:
            self.progress_bar["value"] = 0
            self.progress_bar_global["value"] = 0
            delta_progress_global = 100 / 8

            self._progress_callback(delta_progress_global, "dowloading mods", self.progress_bar_global, self.progress_label_global)
            client_paths, server_paths = self.download_mods_client(self.root.gtnh_modpack, github, organization)

            self.progress_bar["value"] = 0
            self._progress_callback(delta_progress_global, "sort client/server side mods", self.progress_bar_global, self.progress_label_global)
            move_mods(client_paths, server_paths)

            self.progress_bar["value"] = 0
            self._progress_callback(delta_progress_global, "adding extra files", self.progress_bar_global, self.progress_label_global)
            handle_pack_extra_files(error_callback=error_callback_handle_extra_files)

            self.progress_bar["value"] = 0
            self._progress_callback(delta_progress_global, "generating client archive", self.progress_bar_global, self.progress_label_global)
            self.pack_clientpack_client(crawl(client_folder), self.root.gtnh_modpack.modpack_version)

            self.progress_bar["value"] = 0
            self._progress_callback(delta_progress_global, "generating server archive", self.progress_bar_global, self.progress_label_global)
            self.pack_serverpack_client(crawl(server_folder), self.root.gtnh_modpack.modpack_version)

            self.progress_bar["value"] = 0
            self._progress_callback(delta_progress_global, "generating technic assets", self.progress_bar_global, self.progress_label_global)
            self.pack_technic()

            self.progress_bar["value"] = 0
            self._progress_callback(delta_progress_global, "generating deploader for curse", self.progress_bar_global, self.progress_label_global)
            self.make_deploader_json()

            self.progress_bar["value"] = 0
            self._progress_callback(delta_progress_global, "generating curse archive", self.progress_bar_global, self.progress_label_global)
            self.pack_curse()

            showinfo(
                f"packing of version {self.root.gtnh_modpack.modpack_version} successful", f"client pack and server pack are availiable in {ensure_cache_dir()}"
            )
        except PackingInterruptException:
            pass

        self.entry_pack_version.config(state=tk.NORMAL)

    def _progress_callback(self, delta_progress: float, label: str, progress_bar_w: Optional[Progressbar] = None, label_w: Optional[tk.Label] = None) -> None:
        """
        Method used to update a progress bar.

        :param delta_progress: progress to add
        :param label: text to display
        :param progress_bar_w: the progress bar widget
        :param label_w: the label widget
        :return: None
        """
        progress_bar_widget = self.progress_bar if progress_bar_w is None else progress_bar_w
        label_widget = self.progress_label if label_w is None else label_w

        # updating the progress bar
        progress_bar_widget["value"] += delta_progress
        progress_bar_widget["value"] = min(100.0, float(format(progress_bar_widget["value"], ".2f")))
        label_widget["text"] = label.format(progress_bar_widget["value"])
        self.update()

    def download_mods_client(self, gtnh_modpack: GTNHModpack, github: Github, organization: Organization) -> Tuple[List[Path], List[Path]]:
        """
        client version of download_mods.

        :param gtnh_modpack: GTNHModpack object. Represents the metadata of the modpack.
        :param github: Github object.
        :param organization: Organization object. Represent the GTNH organization.
        :return: a list holding all the paths to the clientside mods and a list holding all the paths to the serverside
                mod.
        """
        return download_mods(gtnh_modpack, github, organization, self._progress_callback)

    def pack_clientpack_client(self, client_paths: List[Path], pack_version: str) -> None:
        """
        Client version of pack_clientpack.

        :param client_paths: a list containing all the Path objects refering to the files needed client side.
        :param pack_version: the pack version.
        :return: None
        """
        pack_clientpack(client_paths, pack_version, self._progress_callback)

    def pack_serverpack_client(self, server_paths: List[Path], pack_version: str) -> None:
        """
        Client version of pack_serverpack

        :param server_paths: a list containing all the Path objects refering to the files needed server side.
        :param pack_version: the pack version.
        :return: None
        """
        pack_serverpack(server_paths, pack_version, self._progress_callback)

    def make_deploader_json(self) -> None:
        """
        Method used to update the deploader config for curse archives.

        :return: None
        """
        pass

    def pack_curse(self) -> None:
        """
        Method used to generate the curse client and server archives.

        :return: None
        """
        pass

    def pack_technic(self) -> None:
        """
        Method used to generate all the zips needed for solder to update the pack on technic.

        :return: None
        """
        pass


class HandleDepUpdateFrame(BaseFrame):
    """
    Window allowing you to update the dependencies.
    """

    def __init__(self, root: MainFrame) -> None:
        """
        Constructor of HandleDepUpdateFrame class.

        :param root: the MainFrame instance
        :return: None
        """
        BaseFrame.__init__(self, root, popup_name="gradle updater")


class HandleFileExclusionFrame(BaseFrame):
    """
    Window allowing you to update the files dedicated to clientside or serverside.
    """

    def __init__(self, root: MainFrame) -> None:
        """
        Constructor of HandleFileExclusionFrame class.

        :param root: the MainFrame instance
        :return: None
        """

        BaseFrame.__init__(self, root, popup_name="Exclusions editor")

        # widgets
        self.exclusion_frame_client = CustomLabelFrame(
            self, self.root.gtnh_modpack.client_exclusions, True, text="client entries", add_callback=self.add_client, delete_callback=self.del_client
        )
        self.exclusion_frame_server = CustomLabelFrame(
            self, self.root.gtnh_modpack.server_exclusions, True, text="server entries", add_callback=self.add_server, delete_callback=self.del_server
        )

        # grid manager
        self.exclusion_frame_client.grid(row=0, column=0)
        self.exclusion_frame_server.grid(row=0, column=1)

    def save(self, entry: str, side: str = "client", mode: str = "add", *args: Any, **kwargs: Any) -> bool:
        """
        Method called to save the metadata.

        :return: true
        """
        if side == "client":
            exclusions = self.exclusion_frame_client.get_listbox_content()
            if mode == "add":
                exclusions.append(entry)
            else:
                exclusions = [exclusion for exclusion in exclusions if exclusion != entry]
            self.root.gtnh_modpack.client_exclusions = sorted(list(set(exclusions)))

        elif side == "server":
            exclusions = self.exclusion_frame_server.get_listbox_content()
            if mode == "add":
                exclusions.append(entry)
            else:
                exclusions = [exclusion for exclusion in exclusions if exclusion != entry]
            self.root.gtnh_modpack.server_exclusions = sorted(list(set(exclusions)))

        self.save_gtnh_metadata()
        self.reload_gtnh_metadata()
        return True

    def add_client(self, entry: str, *args: Any, **kwargs: Any) -> bool:
        """
        called when the button add of the client exclusion list is called.
        :param entry: the new exclusion
        :param args:
        :param kwargs:
        :return: true
        """
        return self.save(entry, "client", "add", *args, **kwargs)

    def add_server(self, entry: str, *args: Any, **kwargs: Any) -> bool:
        """
        called when the button add of the server exclusion list is called.
        :param entry: the new exclusion
        :param args:
        :param kwargs:
        :return: true
        """
        return self.save(entry, "server", "add", *args, **kwargs)

    def del_client(self, entry: str, *args: Any, **kwargs: Any) -> bool:
        """
        called when the button remove of the client exclusion list is called.
        :param entry: the deleted exclusion
        :param args:
        :param kwargs:
        :return: true
        """
        return self.save(entry, "client", "remove", *args, **kwargs)

    def del_server(self, entry: str, *args: Any, **kwargs: Any) -> bool:
        """
        called when the button remove of the server exclusion list is called.
        :param entry: the deleted exclusion
        :param args:
        :param kwargs:
        :return: true
        """
        return self.save(entry, "server", "remove", *args, **kwargs)


class CustomLabelFrame(tk.LabelFrame):
    """
    Widget providing a basic set of subwidgets to make an editable listbox.
    """

    def __init__(self, master: Any, entries: List[str], framed: bool, add_callback: Any = None, delete_callback: Any = None, *args: Any, **kwargs: Any) -> None:
        """
        Constructor of CustomLabelFrame class.
        """
        # select the appropriate frame
        if framed:
            tk.LabelFrame.__init__(self, master, *args, **kwargs)
        else:
            tk.LabelFrame.__init__(self, master, relief="flat", *args, **kwargs)

        # callback memory
        self.add_callback = add_callback
        self.delete_callback = delete_callback

        # widgets
        self.listbox = tk.Listbox(self, width=80)
        self.scrollbar_vertical = tk.Scrollbar(self)
        self.scrollbar_horizontal = tk.Scrollbar(self, orient=tk.HORIZONTAL)
        self.stringvar = tk.StringVar(self, value="")
        self.entry = tk.Entry(self, textvariable=self.stringvar)
        self.btn_add = tk.Button(self, text="add", command=self.add)
        self.btn_remove = tk.Button(self, text="remove", command=self.remove)

        # bind the scrollbars
        self.scrollbar_vertical.config(command=self.listbox.yview)
        self.listbox.config(yscrollcommand=self.scrollbar_vertical.set)

        self.scrollbar_horizontal.config(command=self.listbox.xview)
        self.listbox.config(xscrollcommand=self.scrollbar_horizontal.set)

        # populate the listbox
        self.listbox.insert(tk.END, *sorted(entries, key=lambda x: x.lower()))

        # grid manager
        self.listbox.grid(row=0, column=0, columnspan=2, sticky="WE")
        self.scrollbar_vertical.grid(row=0, column=2, sticky="NS")
        self.scrollbar_horizontal.grid(row=1, column=0, columnspan=2, sticky="WE")
        self.entry.grid(row=2, column=0, columnspan=2, sticky="WE")
        self.btn_add.grid(row=3, column=0, sticky="WE")
        self.btn_remove.grid(row=3, column=1, sticky="WE")

    def add(self) -> None:
        """
        Method bound to self.btn_add. Let the user add the text in the entry in the listbox.

        :return: None
        """
        # duplicate handling is supposed to be made in the callback
        if self.add_callback is not None:
            if self.add_callback(self.entry.get()):
                self.listbox.insert(tk.END, self.entry.get())
        else:
            self.listbox.insert(tk.END, self.entry.get())

        entries = self.get_listbox_content()
        entries.sort(key=lambda x: x.lower())
        self.listbox.delete(0, tk.END)
        self.listbox.insert(tk.END, *entries)

    def remove(self) -> None:
        """
        Method bound to self.btn_remove. Let the user remove the selected entry in the listbox. Does nothing if no entry
        had been selected in the listbox.

        :return: None
        """
        # ignoring errors if the delete button had been pressed without selecting an item in the listbox
        try:
            index = self.listbox.curselection()[0]
            if self.delete_callback is not None:
                if self.delete_callback(self.listbox.get(index)):
                    self.listbox.delete(index)
            else:
                self.listbox.delete(index)
        except IndexError:
            pass

    def get_listbox_content(self) -> List[str]:
        """
        Method to return the list of the entries contained in the listbox.

        :return: the list of entries contained in the listbox.
        """
        return [str(item) for item in self.listbox.get(0, tk.END)]


if __name__ == "__main__":
    m = MainFrame()
    m.mainloop()
