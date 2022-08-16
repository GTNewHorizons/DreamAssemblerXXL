import asyncio
from tkinter import Button, Tk
from tkinter.messagebox import showerror, showinfo
from typing import Any, Dict, List, Optional, Union

import httpx

from gtnh.assembler.assembler import ReleaseAssembler
from gtnh.defs import Side
from gtnh.gui.exclusion_frame import ExclusionFrame
from gtnh.gui.external_mod_frame import ExternalModFrame
from gtnh.gui.github_mod_frame import GithubModFrame
from gtnh.gui.modpack_frame import ModpackFrame
from gtnh.models.gtnh_config import GTNHConfig
from gtnh.models.gtnh_release import GTNHRelease
from gtnh.modpack_manager import GTNHModpackManager

ASYNC_SLEEP = 0.05


class App:
    """
    Wrapper class to start the GUI.
    """

    def __init__(self) -> None:
        self.instance: Window = Window()

    async def exec(self) -> None:
        """
        Coroutine used to run all the stuff.
        """
        await self.instance.run()


class Window(Tk):
    """
    Main class for the GUI.
    """

    def __init__(self) -> None:
        """
        Constructor of the Window class.
        """
        Tk.__init__(self)
        self._client: Optional[httpx.AsyncClient] = None
        self._modpack_manager: Optional[GTNHModpackManager] = None
        self._run: bool = True

        self.github_mods: Dict[str, str] = {}  # name <-> version of github mods mappings for the current release
        self.gtnh_config: str = ""  # modpack asset version
        self.external_mods: Dict[str, str] = {}  # name <-> version of external mods mappings for the current release
        self.version: str = ""  # modpack release name

        self.init: bool = False
        self.protocol("WM_DELETE_WINDOW", lambda: asyncio.ensure_future(self.close_app()))

        # frame for the github mods
        github_frame_callbacks: Dict[str, Any] = {
            "get_gtnh": self._get_modpack_manager,
            "get_github_mods": self.get_github_mods,
            "set_github_mod_version": self.set_github_mod_version,
            "set_github_mod_side": lambda name, side: asyncio.ensure_future(self.set_github_mod_side(name, side)),
            "set_modpack_version": self.set_modpack_version,
        }

        self.github_mod_frame: GithubModFrame = GithubModFrame(
            self, frame_name="github mods data", callbacks=github_frame_callbacks
        )

        # frame for the external mods

        external_frame_callbacks: Dict[str, Any] = {
            "set_external_mod_version": self.set_external_mod_version,
            "set_external_mod_side": lambda name, side: None,
        }
        self.external_mod_frame: ExternalModFrame = ExternalModFrame(
            self, frame_name="external mod data", callbacks=external_frame_callbacks
        )

        # frame for the modpack handling
        modpack_list_callbacks: Dict[str, Any] = {
            "load": lambda release_name: asyncio.ensure_future(self.load_gtnh_version(release_name)),
            "add": lambda release_name: asyncio.ensure_future(self.add_gtnh_version(release_name)),
            "delete": lambda release_name: asyncio.ensure_future(self.delete_gtnh_version(release_name)),
            "update_assets": lambda: asyncio.ensure_future(self.update_assets()),
            "generate_nightly": lambda: asyncio.ensure_future(self.generate_nightly()),
            "client_mmc": lambda: asyncio.ensure_future(self.assemble_mmc_release("CLIENT")),
            "server_mmc": lambda: asyncio.ensure_future(self.assemble_mmc_release("SERVER")),
        }

        self.modpack_list_frame: ModpackFrame = ModpackFrame(
            self, frame_name="modpack release actions", callbacks=modpack_list_callbacks
        )

        exclusion_client_callbacks: Dict[str, Any] = {
            "add": lambda exclusion: asyncio.ensure_future(self.add_exclusion("client", exclusion)),
            "del": lambda exclusion: asyncio.ensure_future(self.del_exclusion("client", exclusion)),
        }

        # frame for the client file exclusions
        self.exclusion_frame_client: ExclusionFrame = ExclusionFrame(
            self, "client exclusions", callbacks=exclusion_client_callbacks
        )

        exclusion_server_callbacks: Dict[str, Any] = {
            "add": lambda exclusion: asyncio.ensure_future(self.add_exclusion("server", exclusion)),
            "del": lambda exclusion: asyncio.ensure_future(self.del_exclusion("server", exclusion)),
        }

        # frame for the server side exclusions
        self.exclusion_frame_server: ExclusionFrame = ExclusionFrame(
            self, "server exclusions", callbacks=exclusion_server_callbacks
        )

        self.btn_debug = Button(text="update", command=self.github_mod_frame.update_widget)

    async def assemble_mmc_release(self, side: str) -> None:
        """
        Method used to trigger the assembling of the mmc pack archive corresponding to the provided side.

        :param side: side of the modpack
        :return: None
        """
        gtnh: GTNHModpackManager = await self._get_modpack_manager()
        release: GTNHRelease = GTNHRelease(
            version=self.version,
            config=self.gtnh_config,
            github_mods=self.github_mods,
            external_mods=self.external_mods,
        )
        await gtnh.download_release(
            release, callback=self.modpack_list_frame.action_frame.update_current_task_progress_bar
        )
        ReleaseAssembler(gtnh, release).assemble(Side[side], verbose=True)

    async def add_exclusion(self, side: str, exclusion: str) -> None:
        """
        Method used to add an file exclusion to the corresponding side's exclusion list.

        :param side: side of the modpack
        :param exclusion: the string corresponding to the file exclusion
        :return: None
        """
        gtnh: GTNHModpackManager = await self._get_modpack_manager()
        gtnh.add_exclusion(side, exclusion)
        gtnh.save_modpack()

    async def del_exclusion(self, side: str, exclusion: str) -> None:
        """
        Method used to add an file exclusion to the corresponding side's exclusion list.

        :param side: side of the modpack
        :param exclusion: the string corresponding to the file exclusion
        :return: None
        """
        gtnh: GTNHModpackManager = await self._get_modpack_manager()
        gtnh.delete_exclusion(side, exclusion)
        gtnh.save_modpack()

    async def get_modpack_exclusions(self, side: str) -> List[str]:
        """
        Method used to gather the file exclusion list of the modpack corresponding to the provided side.

        :param side: side of the pack
        :return: list of strings corresponding to the file exclusions
        """
        gtnh: GTNHModpackManager = await self._get_modpack_manager()
        if side == "client":
            return sorted([exclusion for exclusion in gtnh.mod_pack.client_exclusions])
        elif side == "server":
            return sorted([exclusion for exclusion in gtnh.mod_pack.server_exclusions])
        else:
            raise ValueError(f"side {side} is an invalid side")

    async def set_github_mod_side(self, mod_name: str, side: str) -> None:
        """
        Method used to set the side of a github mod.

        :param mod_name: the mod name
        :param side: side of the pack
        :return: None
        """
        gtnh: GTNHModpackManager = await self._get_modpack_manager()
        if not gtnh.set_github_mod_side(mod_name, side):
            showerror(
                "Error setting up the side of the mod",
                f"Error during the process of setting up {mod_name}'s side to {side}. Check the logs for more details",
            )

    def set_github_mod_version(self, github_mod_name: str, mod_version: str) -> None:
        """
        Callback used when a github mod version is selected.

        :param github_mod_name: mod name
        :param mod_version: mod version
        :return: None
        """
        self.github_mods[github_mod_name] = mod_version

    def set_external_mod_version(self, external_mod_name: str, mod_version: str) -> None:
        """
        Callback used when an external mod version is selected.

        :param external_mod_name: mod name
        :param mod_version: mod version
        :return: None
        """
        self.external_mods[external_mod_name] = mod_version

    def set_modpack_version(self, modpack_version: str) -> None:
        """
        Callback used when a modpack version is selected.

        :param modpack_version: modpack version
        :return: None
        """
        self.gtnh_config = modpack_version

    async def get_repos(self) -> List[str]:
        """
        Method to grab all the repo names known.

        :return: a list of github mod names
        """
        gtnh: GTNHModpackManager = await self._get_modpack_manager()
        return [x.name for x in gtnh.assets.github_mods]

    def get_github_mods(self) -> Dict[str, str]:
        """
        Getter for self.github_mods.

        :return: self.github_mods
        """
        return self.github_mods

    async def _get_client(self) -> httpx.AsyncClient:
        """
        Internal getter for the httpx client instance, creating it if it doesn't exist.

        :return: the httpx client instance
        """
        if self._client is None:
            self._client = httpx.AsyncClient(http2=True)
        return self._client

    async def _get_modpack_manager(self) -> GTNHModpackManager:
        """
        Internal getter for the modpack manager instance, creating it if it doesn't exist.

        :return: the modpack manager instance
        """
        if self._modpack_manager is None:
            self._modpack_manager = GTNHModpackManager(await self._get_client())
        return self._modpack_manager

    async def update_assets(self) -> None:
        """
        Callback to update all the availiable assets.

        :return: None
        """
        gtnh: GTNHModpackManager = await self._get_modpack_manager()
        await gtnh.update_all()
        showinfo("assets updated successfully!", "all the assets have been updated correctly!")

    async def generate_nightly(self) -> None:
        """
        Callback used to generate/update the nightly build.

        :return: None
        """
        gtnh: GTNHModpackManager = await self._get_modpack_manager()
        release: GTNHRelease = await gtnh.generate_release("nightly", update_available=True)
        gtnh.add_release(release, update=True)
        gtnh.save_modpack()
        showinfo("updated the nightly release metadata", "The nightly release metadata had been updated!")

    async def get_releases(self) -> List[GTNHRelease]:
        """
        Method used to return a list of known releases with valid metadata.
        The list is sorted in ascending order (from oldest to the latest).

        :return: a sorted list of all the gtnh releases availiable
        """
        gtnh: GTNHModpackManager = await self._get_modpack_manager()

        releases: List[GTNHRelease] = []

        # if there is any release, chose last
        if len(gtnh.mod_pack.releases) > 0:
            # gtnh.mod_pack.releases is actually a set of the release names
            for release_name in gtnh.mod_pack.releases:
                release: Optional[GTNHRelease] = gtnh.get_release(release_name)

                # discarding all the None releases, as it means the json data couldn't be loaded
                if release is not None:
                    releases.append(release)

            # sorting releases by date
            releases = sorted(releases, key=lambda release: release.last_updated)

        return releases

    async def load_gtnh_version(self, release: Union[GTNHRelease, str], init: bool = False) -> None:
        """
        Callback to load in memory a pack release.

        :param release: either a release object or a release name
        :param init: bool indicating if this is done manually or at init
        :return: None
        """

        if isinstance(release, str):
            gtnh: GTNHModpackManager = await self._get_modpack_manager()
            release_object = gtnh.get_release(release)
        else:
            release_object = release

        if release_object is not None:
            self.github_mods = release_object.github_mods
            self.gtnh_config = release_object.config
            self.external_mods = release_object.external_mods
            self.version = release_object.version
        else:
            showerror("incorrect version detected", f"modpack version {release} doesn't exist")
            return

        if not init:
            showinfo("version loaded successfully!", f"modpack version {release_object.version} loaded successfully!")

    async def add_gtnh_version(self, release_name: str) -> None:
        """
        Callback to add a new modpack version.

        :param release_name: the name of the release
        :return: None
        """

        gtnh: GTNHModpackManager = await self._get_modpack_manager()
        release: GTNHRelease = GTNHRelease(
            version=release_name,
            config=self.gtnh_config,
            github_mods=self.github_mods,
            external_mods=self.external_mods,
        )

        if gtnh.add_release(release, update=True):
            gtnh.save_modpack()
            showinfo("release successfully generated", f"modpack version {release_name} successfully generated!")

    async def delete_gtnh_version(self, release_name: str) -> None:
        """
        Callback used to delete a modpack version.

        :param release_name: name of the release
        :return: None
        """
        gtnh: GTNHModpackManager = await self._get_modpack_manager()
        gtnh.delete_release(release_name)
        showinfo("release successfully deleted", f"modpack version {release_name} successfully deleted!")

    def show(self) -> None:
        """
        Method used to display widgets and child widgets, as well as to configure the "responsiveness" of the widgets.

        :return: None
        """

        # auto resize config
        for i in range(3):
            self.columnconfigure(i, weight=1)
            self.rowconfigure(i, weight=1)

        # display child widgets
        self.github_mod_frame.grid(row=0, column=0)
        self.external_mod_frame.grid(row=2, column=0)
        self.modpack_list_frame.grid(row=0, column=1, columnspan=2, sticky="WENS")
        self.exclusion_frame_client.grid(row=1, column=1, sticky="WENS", rowspan=3)
        self.exclusion_frame_server.grid(row=1, column=2, sticky="WENS", rowspan=2)

        self.btn_debug.grid(row=10, column=10)

        # child widget's inner display
        self.github_mod_frame.show()
        self.external_mod_frame.show()
        self.modpack_list_frame.show()
        self.exclusion_frame_client.show()
        self.exclusion_frame_server.show()

    async def get_modpack_versions(self) -> List[str]:
        """
        Method used to gather all the version of the GT-New-Horizons-Modpack repo.

        :return: a list of all the versions availiable.
        """
        gtnh: GTNHModpackManager = await self._get_modpack_manager()
        modpack_config: GTNHConfig = gtnh.assets.config
        return [version.version_tag for version in modpack_config.versions]

    async def run(self) -> None:
        """
        async entrypoint to trigger the mainloop

        :return: None
        """
        self.show()
        await self.update_widget()

    async def update_widget(self) -> None:
        """
        Method handling the loop of the gui.

        :return: None
        """
        if not self.init:
            self.init = True
            # load last gtnh version if there is any:
            releases: List[GTNHRelease] = await self.get_releases()
            if len(releases) > 0:
                await self.load_gtnh_version(releases[-1], init=True)
            data = {
                "github_mod_list": await self.get_repos(),
                "modpack_version_frame": {"combobox": await self.get_modpack_versions(), "stringvar": self.gtnh_config},
            }

            self.github_mod_frame.populate_data(data)
            self.modpack_list_frame.populate_data(await self.get_releases())
            self.exclusion_frame_server.populate_data({"exclusions": await self.get_modpack_exclusions("server")})
            self.exclusion_frame_client.populate_data({"exclusions": await self.get_modpack_exclusions("client")})
        while self._run:
            self.update()
            self.update_idletasks()
            await asyncio.sleep(ASYNC_SLEEP)

    async def close_app(self) -> None:
        """
        Callback used when the app is closed.

        :return: None
        """
        if self._client is not None:
            await self._client.aclose()
            self._run = False
        self.destroy()


if __name__ == "__main__":
    asyncio.run(App().exec())
