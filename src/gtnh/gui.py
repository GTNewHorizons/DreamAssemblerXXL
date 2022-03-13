import tkinter as tk
from tkinter.ttk import Progressbar
from tkinter.messagebox import showinfo, showerror, showwarning
from github import Github
from src.gtnh.add_mod import get_repo, new_mod_from_repo
from src.gtnh.pack_downloader import download_mod, ensure_cache_dir
from src.gtnh.utils import load_gtnh_manifest, sort_and_write_modpack, get_token
from exceptions import RepoNotFoundException, LatestReleaseNotFound
from zipfile import ZipFile
import os
from pathlib import Path


class MainFrame(tk.Tk):
    def __init__(self):
        tk.Tk.__init__(self)
        self.title("DreamAssemblerXXL")

        # state control vars
        self.is_new_repo_popup_open = False
        self.is_archive_popup_open = False

        self.btn_add_repo = tk.Button(self, text="add a new repository", command=self.open_new_repo_popup)
        self.btn_update_dep = tk.Button(self, text="update dependencies", command=self.handle_dependencies_update)
        self.btn_download = tk.Button(self, text="build archive", command=self.open_archive_popup)

        self.btn_add_repo.pack()
        self.btn_update_dep.pack()
        self.btn_download.pack()

        # refs to popup toplevel widgets
        self.repo_popup = None
        self.archive_popup = None

    def open_new_repo_popup(self):
        # clean the popup on destroy event
        def _unlock_popup(_):
            self.is_new_repo_popup_open = False
            self.repo_popup = None

        # prevent the popup from appearing more than once
        if not self.is_new_repo_popup_open:
            self.is_new_repo_popup_open = True
            self.repo_popup = AddRepoPopup()
            self.repo_popup.bind("<Destroy>", _unlock_popup)

    def handle_dependencies_update(self):
        pass

    def open_archive_popup(self):
        # clean the popup on destroy event
        def _unlock_popup(_):
            self.is_archive_popup_open = False
            self.archive_popup = None

        # prevent the popup from appearing more than once
        if not self.is_archive_popup_open:
            self.is_archive_popup_open = True
            self.archive_popup = ArchivePopup()
            self.archive_popup.bind("<Destroy>", _unlock_popup)


class AddRepoPopup(tk.Toplevel):
    def __init__(self):
        tk.Toplevel.__init__(self)
        self.label_name_repo = tk.Label(self, text="Add the new repository below")
        self.stringvar_name_repo = tk.StringVar(self)
        self.entry_name_repo = tk.Entry(self, textvariable=self.stringvar_name_repo, width=30)
        self.btn_validate = tk.Button(self, text="validate", command=self.validate)

        # grid manager
        self.label_name_repo.pack()
        self.entry_name_repo.pack()
        self.btn_validate.pack()

        # state control vars
        self.is_messagebox_open = False

    def validate(self):
        if not self.is_messagebox_open:
            self.is_messagebox_open = True

            # resolving the name from the widget
            name = self.stringvar_name_repo.get()

            # checking the repo on github
            try:
                new_repo = get_repo(name)

            except RepoNotFoundException:
                showerror("repository not found", f"the repository {name} was not found on github.")

            else:
                # checking if the repo is already added
                gtnh = load_gtnh_manifest()
                if gtnh.get_github_mod(new_repo.name):
                    showwarning("repository already added", f"the repository {name} is already added.")

                # adding the repo
                else:
                    try:
                        new_mod = new_mod_from_repo(new_repo)
                        gtnh.github_mods.append(new_mod)
                        sort_and_write_modpack(gtnh)
                        showinfo("repository added successfully", f"the repo {name} was added successfully!")

                    except LatestReleaseNotFound:
                        showerror("no release availiable on the repository",
                                  f"the repository {name} has no release, aborting")

            self.is_messagebox_open = False


class ArchivePopup(tk.Toplevel):
    def __init__(self):
        tk.Toplevel.__init__(self)

        self.progress_bar = Progressbar(self, orient="horizontal", mode="determinate", length=500)
        self.progress_label = tk.Label(self, text="")
        self.btn_start = tk.Button(self, text="start", command=self.start)

        self.progress_bar.pack()
        self.progress_label.pack()
        self.btn_start.pack()

    def start(self):
        github = Github(get_token())
        organization = github.get_organization("GTNewHorizons")
        gtnh_modpack = load_gtnh_manifest()
        client_paths, server_paths = self.download_mods(gtnh_modpack, github, organization)
        self.handle_pack_extra_files()
        self.pack_client(client_paths)
        self.pack_server(server_paths)
        self.pack_technic()
        self.make_deploader_json()
        self.pack_curse()

    def download_mods(self, gtnh_modpack, github, organization):
        amount_of_mods = len(gtnh_modpack.github_mods)
        delta_progress = 100 / amount_of_mods
        client_paths = []
        server_paths = []
        for mod in gtnh_modpack.github_mods:
            # update progress bar
            self.progress_bar["value"] += delta_progress
            self.progress_bar["value"] = min(100.0, float(format(self.progress_bar["value"], ".2f")))
            self.progress_label["text"] = f"downloading mods. Progress: {self.progress_bar['value']}%"
            # self.update_idletasks()
            self.update()

            # do the actual work
            paths = download_mod(github, organization, mod)
            if mod.side == "BOTH":
                client_paths.extend(paths)
                server_paths.extend(paths)
            elif mod.side == "CLIENT":
                client_paths.extend(paths)
            elif mod.side == "SERVER":
                server_paths.extend(paths)

        return client_paths, server_paths

    def pack_client(self, client_paths):
        delta_progress = 100 / len(client_paths)
        cwd = os.getcwd()
        cache_dir = Path(ensure_cache_dir())
        os.chdir(cache_dir)

        if os.path.exists("client.zip"):
            os.remove("client.zip")
            print("previous client archive deleted")

        with ZipFile("client.zip", "w") as client_archive:
            for mod_path in client_paths:
                # updating the progress bar
                self.progress_bar["value"] += delta_progress
                self.progress_bar["value"] = min(100.0, float(format(self.progress_bar["value"], ".2f")))
                self.progress_label["text"] = f"Packing client archive: {mod_path.name}." \
                                              f"Progress: {self.progress_bar['value']}%"
                #self.update_idletasks()
                self.update()

                client_archive.write(mod_path, mod_path.relative_to(cache_dir))

        os.chdir(cwd)

    def pack_server(self, server_paths):
        delta_progress = 100 / len(server_paths)
        cwd = os.getcwd()
        cache_dir = Path(ensure_cache_dir())
        os.chdir(cache_dir)

        if os.path.exists("server.zip"):
            os.remove("server.zip")
            print("previous server archive deleted")

        with ZipFile("server.zip", "w") as server_archive:
            for mod_path in server_paths:
                # updating the progress bar
                self.progress_bar["value"] += delta_progress
                self.progress_bar["value"] = min(100.0, float(format(self.progress_bar["value"], ".2f")))
                self.progress_label["text"] = f"Packing server archive: {mod_path.name}." \
                                              f"Progress: {self.progress_bar['value']}%"
                # self.update_idletasks()
                self.update()

                server_archive.write(mod_path, Path("mods") / mod_path.name)
        os.chdir(cwd)

    def handle_pack_extra_files(self):
        pass

    def make_deploader_json(self):
        pass
    
    def pack_curse(self):
        pass

    def pack_technic(self):
        pass



if __name__ == "__main__":
    m = MainFrame()
    m.mainloop()
