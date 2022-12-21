"""Module handling the Modrinth pack releases."""
from pathlib import Path
from typing import Callable, Optional

from gtnh.assembler.generic_assembler import GenericAssembler
from gtnh.defs import RELEASE_MODRINTH_DIR, Side
from gtnh.models.gtnh_release import GTNHRelease
from gtnh.modpack_manager import GTNHModpackManager


class ModrinthAssembler(GenericAssembler):
    """Modrinth assembler class. Allows for the assembling of modrinth archives."""

    def __init__(
        self,
        gtnh_modpack: GTNHModpackManager,
        release: GTNHRelease,
        task_progress_callback: Optional[Callable[[float, str], None]] = None,
        global_progress_callback: Optional[Callable[[float, str], None]] = None,
        changelog_path: Optional[Path] = None,
    ):
        """
        Construct the ModrinthAssembler class.

        Parameters
        ----------
        gtnh_modpack: GTNHModpackManager
            The modpack manager instance.

        release: GTNHRelease
            The targetted release.

        task_progress_callback: Optional[Callable[[float, str], None]]
            The callback used to report progress within the task process.

        global_progress_callback: Optional[Callable[[float, str], None]]
            The callback used to report total progress.

        changelog_path: Optional[Path]
            The path of the changelog.
        """
        GenericAssembler.__init__(
            self,
            gtnh_modpack=gtnh_modpack,
            release=release,
            task_progress_callback=task_progress_callback,
            global_progress_callback=global_progress_callback,
            changelog_path=changelog_path,
        )

    async def assemble(self, side: Side, verbose: bool = False) -> None:
        """
        Assemble the release.

        Parameters
        ----------
        side : Side
            The side of the archive being assembled.

        verbose : bool
            Boolean controlling if yes or no the assembling process should be verbose.

        Returns
        -------
        None.
        """
        raise NotImplementedError

    def get_archive_path(self, side: Side) -> Path:
        """
        Get the archive path for the release.

        Parameters
        ----------
        side : Side
            The side of the archive being assembled.

        Returns
        -------
        A Path object representing the archive's path.
        """
        return RELEASE_MODRINTH_DIR / f"GT_New_Horizons_{side}_{self.release.version}.zip"
