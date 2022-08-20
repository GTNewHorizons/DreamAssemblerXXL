from typing import Callable, Optional

from structlog import get_logger

from gtnh.assembler.multi_poly import MMCAssembler
from gtnh.assembler.zip_assembler import ZipAssembler
from gtnh.defs import Side
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
    ) -> None:
        """
        Constructor of the ReleaseAssemblerClass.

        :param mod_manager: the GTNHModpackManager instance
        :param release: the target GTNHRelease
        :param callback: the callback to use to report progress
        """
        self.mod_manager: GTNHModpackManager = mod_manager
        self.release: GTNHRelease = release
        self.callback: Optional[Callable[[float, str], None]] = global_callback

        self.zip_assembler: ZipAssembler = ZipAssembler(mod_manager, release, task_callback)
        self.mmc_assembler: MMCAssembler = MMCAssembler(mod_manager, release, task_callback)

        # computation of the progress per mod for the progressbar
        self.count: float = 0.0
        self.progress: float = 0.0
        self.delta_progress: float = 0.0

    def assemble(self, side: Side, verbose: bool = False) -> None:
        """
        Method called to assemble the release.

        :param side: the target side
        :param verbose: bool flag enabling verbose mod
        :return: None
        """

        self.assemble_zip(side, verbose)
        self.assemble_mmc(side, verbose)

    def assemble_zip(self, side: Side, verbose: bool = False) -> None:
        self.zip_assembler.assemble(side, verbose)

    def assemble_mmc(self, side: Side, verbose: bool = False) -> None:
        self.mmc_assembler.assemble(side, verbose)
