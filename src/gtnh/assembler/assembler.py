"""Module handling all the assemblers."""
from pathlib import Path
from typing import Awaitable, Callable, Dict, List, Optional

from structlog import get_logger

from gtnh.assembler.curse import CurseAssembler
from gtnh.assembler.modrinth import ModrinthAssembler
from gtnh.assembler.multi_poly import MMCAssembler
from gtnh.assembler.technic import TechnicAssembler
from gtnh.assembler.zip_assembler import ZipAssembler
from gtnh.defs import RELEASE_CHANGELOG_DIR, Archive, Side
from gtnh.models.gtnh_release import GTNHRelease
from gtnh.modpack_manager import GTNHModpackManager
from gtnh.utils import compress_changelog

log = get_logger(__name__)


class ReleaseAssembler:
    """Main class to assemble a release."""

    def __init__(
        self,
        mod_manager: GTNHModpackManager,
        release: GTNHRelease,
        task_callback: Optional[Callable[[float, str], None]] = None,
        global_callback: Optional[Callable[[float, str], None]] = None,
        current_task_reset_callback: Optional[Callable[[], None]] = None,
    ) -> None:
        """
        Construct the ReleaseAssemblerClass.

        Parameters
        ----------
        mod_manager: GTNHModpackManager
            The GTNHModpackManager instance.

        release: GTNHRelease
            The target GTNHRelease.

        task_callback: Optional[Callable[[float, str], None]]
            The callback used to report progress within the task process.

        global_callback: Optional[Callable[[float, str], None]]
            The callback used to report total progress.

        current_task_reset_callback: Optional[Callable[[], None]]
            The callback to reset the progress bar for the current task.
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
        Set the value of self.delta_progress.

        Parameters
        ----------
        progress: float
            The new delta progress.

        Returns
        -------
        None
        """
        self.delta_progress = progress

    def get_progress(self) -> float:
        """
        Get the value of self.delta_progress.

        Returns
        -------
        A float corresponding to the value of self.delta_progress.
        """
        return self.delta_progress

    async def assemble(self, side: Side, verbose: bool = False) -> None:
        """
        Assemble the release for all the supports.

        Parameters
        ----------
        side: Side
            The side of the archive being assembled.

        verbose: bool
            If True, show more detailled logs.

        Returns
        -------
        None
        """
        if side not in {side.CLIENT, side.SERVER}:
            raise ValueError(f"Only valid sides are {Side.CLIENT} or {Side.SERVER}, got {side}")

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
            assemblers_client if side == Side.CLIENT else assemblers_server
        )

        for plateform, assembling in assemblers.items():
            if self.current_task_reset_callback is not None:
                self.current_task_reset_callback()

            if self.callback:
                self.callback(self.get_progress(), f"Assembling {side} {plateform} archive")  # type: ignore
            await assembling(side, verbose)

        # TODO: Remove when the maven urls are calculated on add, instead of in curse
        self.mod_manager.save_assets()

    async def assemble_zip(self, side: Side, verbose: bool = False) -> None:
        """
        Assemble the zip archive.

        Parameters
        ----------
        side: Side
            The side of the zip archive to be assembled.

        verbose: bool
            If True, show more detailled logs.

        Returns
        -------
        None
        """
        await self.zip_assembler.assemble(side, verbose)

    async def assemble_mmc(self, side: Side, verbose: bool = False) -> None:
        """
        Assemble the mmc archive.

        Parameters
        ----------
        side: Side
            The side of the zip archive to be assembled.

        verbose: bool
            If True, show more detailled logs.

        Returns
        -------
        None
        """
        await self.mmc_assembler.assemble(side, verbose)

    async def assemble_curse(self, side: Side, verbose: bool = False) -> None:
        """
        Assemble the curseforge archive.

        Parameters
        ----------
        side: Side
            The side of the zip archive to be assembled.

        verbose: bool
            If True, show more detailled logs.

        Returns
        -------
        None
        """
        await self.curse_assembler.assemble(side, verbose)

    async def assemble_modrinth(self, side: Side, verbose: bool = False) -> None:
        """
        Assemble the Modrinth archive.

        Parameters
        ----------
        side: Side
            The side of the zip archive to be assembled.

        verbose: bool
            If True, show more detailled logs.

        Returns
        -------
        None
        """
        await self.modrinth_assembler.assemble(side, verbose)

    async def assemble_technic(self, side: Side, verbose: bool = False) -> None:
        """
        Assemble the Technic archive.

        Parameters
        ----------
        side: Side
            The side of the zip archive to be assembled.

        verbose: bool
            If True, show more detailled logs.

        Returns
        -------
        None
        """
        await self.technic_assembler.assemble(side, verbose)

    def generate_changelog(self) -> Path:
        """
        Generate the changelog of a release.

        Returns
        -------
        A Path object pointing to the changelog file.
        """
        current_version: str = self.release.version
        previous_version: Optional[str] = self.release.last_version
        previous_release: Optional[GTNHRelease] = (
            None if previous_version is None else self.mod_manager.get_release(previous_version)
        )
        changelog: Dict[str, List[str]] = self.mod_manager.generate_changelog(self.release, previous_release)

        changelog_path: Path = RELEASE_CHANGELOG_DIR / f"changelog from {previous_version} to {current_version}.md"

        with open(changelog_path, "w") as file:

            for mod, mod_changelog in changelog.items():
                for item in mod_changelog:
                    try:
                        file.write(item + "\n")
                    except UnicodeEncodeError:
                        file.write((item + "\n").encode("ascii", "ignore").decode())

        compress_changelog(changelog_path)

        return changelog_path
