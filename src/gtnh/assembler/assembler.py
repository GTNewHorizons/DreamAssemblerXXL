from pathlib import Path
from typing import Awaitable, Callable, Dict, List, Optional

from gtnh.assembler.curse import CurseAssembler
from gtnh.assembler.modrinth import ModrinthAssembler
from gtnh.assembler.multi_poly import MMCAssembler
from gtnh.assembler.technic import TechnicAssembler
from gtnh.assembler.zip_assembler import ZipAssembler
from gtnh.defs import (
    RELEASE_CHANGELOG_DAILY_BUILDS_DIR,
    RELEASE_CHANGELOG_DIR,
    RELEASE_CHANGELOG_EXPERIMENTAL_BUILDS_DIR,
    Archive,
    Side,
)
from gtnh.gtnh_logger import get_logger
from gtnh.models.gtnh_release import GTNHRelease
from gtnh.modpack_manager import GTNHModpackManager

log = get_logger(__name__)


class ReleaseAssembler:
    """
    Main class to assemble a release.
    """

    def __init__(
        self,
        mod_manager: GTNHModpackManager,
        release: GTNHRelease,
        task_callback: Optional[Callable[[float, str], None]] = None,
        global_callback: Optional[Callable[[float, str], None]] = None,
        current_task_reset_callback: Optional[Callable[[], None]] = None,
    ) -> None:
        """
        Constructor of the ReleaseAssemblerClass.

        :param mod_manager: the GTNHModpackManager instance
        :param release: the target GTNHRelease
        :param global_progress_callback: the global_progress_callback to use to report progress
        :param current_task_reset_callback: the callback to reset the progress bar for the current task
        """
        self.mod_manager: GTNHModpackManager = mod_manager
        self.release: GTNHRelease = release
        self.callback: Optional[Callable[[float, str], None]] = global_callback
        self.current_task_reset_callback = current_task_reset_callback

        changelog_path: Path = self.generate_changelog()

        self.zip_assembler: ZipAssembler = ZipAssembler(
            mod_manager, release, task_callback, changelog_path=changelog_path
        )
        self.mmc_assembler: MMCAssembler = MMCAssembler(
            mod_manager, release, task_callback, changelog_path=changelog_path
        )
        self.curse_assembler: CurseAssembler = CurseAssembler(
            mod_manager, release, task_callback, changelog_path=changelog_path
        )
        self.technic_assembler: TechnicAssembler = TechnicAssembler(
            mod_manager, release, task_callback, changelog_path=changelog_path
        )
        self.modrinth_assembler: ModrinthAssembler = ModrinthAssembler(
            mod_manager, release, task_callback, changelog_path=changelog_path
        )

        # computation of the progress per mod for the progressbar
        self.delta_progress: float = 0.0

    def set_progress(self, progress: float) -> None:
        """
        Setter for self.delta_progress.

        :param progress: new delta progress
        :return: None
        """
        self.delta_progress = progress

    def get_progress(self) -> float:
        """
        Getter for self.delta_progress.

        :return: the delta progress
        """
        return self.delta_progress

    async def assemble(self, side: Side, verbose: bool = False) -> None:
        """
        Method called to assemble the release for all the supported platforms.

        :param side: the target side
        :param verbose: bool flag enabling verbose mod
        :return: None
        """

        if side not in {side.CLIENT, side.CLIENT_JAVA9, side.SERVER, side.SERVER_JAVA9}:
            raise ValueError(
                f"Only valid sides are {Side.CLIENT}/{Side.CLIENT_JAVA9} or {Side.SERVER}/{Side.SERVER_JAVA9}, got {side}"
            )

        if self.current_task_reset_callback is not None:
            self.current_task_reset_callback()

        assemblers_client: Dict[str, Callable[[Side, bool], Awaitable[None]]] = {
            Archive.ZIP: self.assemble_zip,
            Archive.MMC: self.assemble_mmc,
            Archive.TECHNIC: self.assemble_technic,
            Archive.CURSEFORGE: self.assemble_curse,
            Archive.MODRINTH: self.assemble_modrinth,
        }

        assemblers_server: Dict[str, Callable[[Side, bool], Awaitable[None]]] = {Archive.ZIP: self.assemble_zip}

        assemblers: Dict[str, Callable[[Side, bool], Awaitable[None]]] = (
            assemblers_client if side.is_client() else assemblers_server
        )

        for platform, assembling in assemblers.items():
            if side.is_java9() and platform in [Archive.TECHNIC, Archive.CURSEFORGE]:
                # Java 9 is currently not supported on Technic and Curse
                continue

            if self.current_task_reset_callback is not None:
                self.current_task_reset_callback()

            if self.callback:
                self.callback(self.get_progress(), f"Assembling {side} {platform} archive")  # type: ignore
            await assembling(side, verbose)

        # TODO: Remove when the maven urls are calculated on add, instead of in curse
        self.mod_manager.save_assets()

    async def assemble_zip(self, side: Side, verbose: bool = False) -> None:
        """
        Method called to assemble the zip archive.

        :param side: targetted side
        :param verbose: flag to control verbose mode
        :return: None
        """
        await self.zip_assembler.assemble(side, verbose)

    async def assemble_mmc(self, side: Side, verbose: bool = False) -> None:
        """
        Method called to assemble the zip archive.

        :param side: targetted side
        :param verbose: flag to control verbose mode
        :return: None
        """
        await self.mmc_assembler.assemble(side, verbose)

    async def assemble_curse(self, side: Side, verbose: bool = False) -> None:
        """
        Method called to assemble the curse archive.

        :param side: targetted side
        :param verbose: flag to control verbose mode
        :return: None
        """
        await self.curse_assembler.assemble(side, verbose)

    async def assemble_modrinth(self, side: Side, verbose: bool = False) -> None:
        """
        Method called to assemble the modrinth archive.

        :param side: targetted side
        :param verbose: flag to control verbose mode
        :return: None
        """
        await self.modrinth_assembler.assemble(side, verbose)

    async def assemble_technic(self, side: Side, verbose: bool = False) -> None:
        """
        Method called to assemble the technic archive.

        :param side: targetted side
        :param verbose: flag to control verbose mode
        :return: None
        """
        await self.technic_assembler.assemble(side, verbose)

    # Changes to this method may need updates to utils.compress_changelog()
    def generate_changelog(self) -> Path:
        """
        Method to generate the changelog of a release.

        :return: the path to the changelog
        """

        current_version: str = self.release.version
        previous_version: Optional[str] = self.release.last_version
        previous_release: Optional[GTNHRelease] = (
            None if previous_version is None else self.mod_manager.get_release(previous_version)
        )
        changelog: Dict[str, List[str]] = self.mod_manager.generate_changelog(self.release, previous_release)
        changelog_path: Path
        if "experimental" in current_version:
            changelog_path = (
                RELEASE_CHANGELOG_EXPERIMENTAL_BUILDS_DIR / f"changelog from experimental "
                f"{self.mod_manager.get_last_successful_experimental()} to "
                f"{self.mod_manager.get_experimental_count()}.md"
            )
        elif "daily" in current_version:
            changelog_path = (
                RELEASE_CHANGELOG_DAILY_BUILDS_DIR / f"changelog from daily "
                f"{self.mod_manager.get_last_successful_daily()} to "
                f"{self.mod_manager.get_daily_count()}.md"
            )
        else:
            changelog_path = RELEASE_CHANGELOG_DIR / f"changelog from {previous_version} to {current_version}.md"

        with open(changelog_path, "w") as file:

            for mod, mod_changelog in changelog.items():
                for item in mod_changelog:
                    try:
                        file.write(item + "\n")
                    except UnicodeEncodeError:
                        file.write((item + "\n").encode("ascii", "ignore").decode())

        return changelog_path
