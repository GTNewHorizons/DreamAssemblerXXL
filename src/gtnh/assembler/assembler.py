from pathlib import Path
from typing import Callable, Dict, List, Optional

from structlog import get_logger

from gtnh.assembler.curse import CurseAssembler
from gtnh.assembler.modrinth import ModrinthAssembler
from gtnh.assembler.multi_poly import MMCAssembler
from gtnh.assembler.technic import TechnicAssembler
from gtnh.assembler.zip_assembler import ZipAssembler
from gtnh.defs import RELEASE_CHANGELOG_DIR, Archive, Side
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

    def assemble(self, side: Side, verbose: bool = False) -> None:
        """
        Method called to assemble the release for all the supports.

        :param side: the target side
        :param verbose: bool flag enabling verbose mod
        :return: None
        """

        if side not in {side.CLIENT, side.SERVER}:
            raise ValueError(f"Only valid sides are {Side.CLIENT} or {Side.SERVER}, got {side}")

        if self.current_task_reset_callback is not None:
            self.current_task_reset_callback()

        assemblers_client: Dict[str, Callable[[Side, bool], None]] = {
            Archive.ZIP: self.assemble_zip,
            Archive.MMC: self.assemble_mmc,
            Archive.TECHNIC: self.assemble_technic,
            Archive.CURSEFORGE: self.assemble_curse,
            Archive.MODRINTH: self.assemble_modrinth,
        }

        assemblers_server: Dict[str, Callable[[Side, bool], None]] = {Archive.ZIP: self.assemble_zip}

        assemblers: Dict[str, Callable[[Side, bool], None]] = (
            assemblers_client if side == Side.CLIENT else assemblers_server
        )

        for plateform, assembling in assemblers.items():
            if self.current_task_reset_callback is not None:
                self.current_task_reset_callback()

            if self.callback:
                self.callback(self.get_progress(), f"Assembling {side} {plateform} archive")  # type: ignore
            assembling(side, verbose)

    def assemble_zip(self, side: Side, verbose: bool = False) -> None:
        """
        Method called to assemble the zip archive.

        :param side: targetted side
        :param verbose: flag to control verbose mode
        :return: None
        """
        self.zip_assembler.assemble(side, verbose)

    def assemble_mmc(self, side: Side, verbose: bool = False) -> None:
        """
        Method called to assemble the zip archive.

        :param side: targetted side
        :param verbose: flag to control verbose mode
        :return: None
        """
        self.mmc_assembler.assemble(side, verbose)

    def assemble_curse(self, side: Side, verbose: bool = False) -> None:
        """
        Method called to assemble the curse archive.

        :param side: targetted side
        :param verbose: flag to control verbose mode
        :return: None
        """
        self.curse_assembler.assemble(side, verbose)

    def assemble_modrinth(self, side: Side, verbose: bool = False) -> None:
        """
        Method called to assemble the modrinth archive.

        :param side: targetted side
        :param verbose: flag to control verbose mode
        :return: None
        """
        self.modrinth_assembler.assemble(side, verbose)

    def assemble_technic(self, side: Side, verbose: bool = False) -> None:
        """
        Method called to assemble the technic archive.

        :param side: targetted side
        :param verbose: flag to control verbose mode
        :return: None
        """
        self.technic_assembler.assemble(side, verbose)

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

        changelog_path: Path = RELEASE_CHANGELOG_DIR / f"changelog from {previous_version} to {current_version}.md"

        with open(changelog_path, "w") as file:

            for mod, mod_changelog in changelog.items():
                for item in [mod] + mod_changelog:
                    if item in ["new_mods", "removed_mods"]:  # skipping useless lines
                        continue
                    try:
                        file.write(item + "\n")
                    except UnicodeEncodeError:
                        file.write((item + "\n").encode("ascii", "ignore").decode())

        return changelog_path
