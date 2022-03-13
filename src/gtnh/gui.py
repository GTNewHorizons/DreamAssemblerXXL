import tkinter as tk
from tkinter.messagebox import showinfo, showerror, showwarning
from src.gtnh.add_mod import get_repo, new_mod_from_repo
from src.gtnh.utils import load_gtnh_manifest, sort_and_write_modpack, LatestReleaseNotFound
from exceptions import RepoNotFoundException, LatestReleaseNotFound

class MainFrame(tk.Tk):
    def __init__(self):
        tk.Tk.__init__(self)
        self.title("DreamAssemblerXXL")

        # state control vars
        self.is_new_repo_popup_open = False

        self.btn_add_repo = tk.Button(self, text="add a new repository", command=self.open_new_repo_popup)
        self.btn_update_dep = tk.Button(self, text="update dependencies", command=self.handle_dependencies_update)

        self.btn_add_repo.pack()
        self.btn_update_dep.pack()

        # refs to popup toplevel widgets
        self.repo_popup = None

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

if __name__ == "__main__":
    m = MainFrame()
    m.mainloop()


