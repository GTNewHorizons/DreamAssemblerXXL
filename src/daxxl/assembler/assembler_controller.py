from pathlib import Path
from typing import Awaitable, Callable, Optional

from daxxl.app_context import AppContext
from daxxl.assembler.platforms import CurseAssembler, ModrinthAssembler, PrismAssembler, TechnicAssembler, ZipAssembler
from daxxl.defs import (
    RELEASE_CHANGELOG_DAILY_BUILDS_DIR,
    RELEASE_CHANGELOG_DIR,
    RELEASE_CHANGELOG_EXPERIMENTAL_BUILDS_DIR,
    Archive,
    DevRelease,
    Side,
)
from daxxl.gtnh_logger import get_logger
from daxxl.models.gtnh_release import GTNHRelease

log = get_logger(__name__)


class ReleaseAssemblerController:
    """
    Main class to assemble a release.
    """

    def __init__(
        self,
        context: AppContext,
        release: GTNHRelease,
        task_callback: Optional[Callable[[float, str], None]] = None,
        global_callback: Optional[Callable[[float, str], None]] = None,
        current_task_reset_callback: Optional[Callable[[], None]] = None,
    ) -> None:
        """
        Constructor of the ReleaseAssemblerClass.

        :param context: the AppContext instance
        :param release: the target GTNHRelease
        :param global_progress_callback: the global_progress_callback to use to report progress
        :param current_task_reset_callback: the callback to reset the progress bar for the current task
        """
        self.context: AppContext = context
        self.release: GTNHRelease = release
        release.validate_release(context.assets)
        self.callback: Optional[Callable[[float, str], None]] = global_callback
        self.current_task_reset_callback = current_task_reset_callback

        changelog_path: Path = self.generate_changelog()

        self.zip_assembler: ZipAssembler = ZipAssembler(context, release, task_callback, changelog_path=changelog_path)
        self.prism_assembler: PrismAssembler = PrismAssembler(
            context, release, task_callback, changelog_path=changelog_path
        )
        self.curse_assembler: CurseAssembler = CurseAssembler(
            context, release, task_callback, changelog_path=changelog_path
        )
        self.technic_assembler: TechnicAssembler = TechnicAssembler(
            context,
            release,
            task_callback,
            changelog_path=changelog_path,
            current_task_reset_callback=current_task_reset_callback,
        )
        self.modrinth_assembler: ModrinthAssembler = ModrinthAssembler(
            context, release, task_callback, changelog_path=changelog_path
        )

        # computation of the progress per mod for the progressbar
        self.delta_progress: float = 0.0

    async def assemble(self, side: Side, verbose: bool = False) -> None:
        """
        Method called to assemble the release for all the supported platforms.

        :param side: the target side
        :param verbose: bool flag enabling verbose mod
        :return: None
        """

        if side not in {Side.CLIENT, Side.CLIENT_JAVA9, Side.SERVER, Side.SERVER_JAVA9}:
            raise ValueError(
                f"Only valid sides are {Side.CLIENT}/{Side.CLIENT_JAVA9} or {Side.SERVER}/{Side.SERVER_JAVA9}, got {side}"
            )

        if self.current_task_reset_callback is not None:
            self.current_task_reset_callback()

        assemblers_client: dict[Archive, Callable[[Side, bool], Awaitable[None]]] = {
            Archive.ZIP: self.assemble_zip,
            Archive.PRISM: self.assemble_prism,
            Archive.TECHNIC: self.assemble_technic,
            Archive.CURSEFORGE: self.assemble_curse,
            Archive.MODRINTH: self.assemble_modrinth,
        }

        assemblers_server: dict[Archive, Callable[[Side, bool], Awaitable[None]]] = {Archive.ZIP: self.assemble_zip}

        assemblers: dict[Archive, Callable[[Side, bool], Awaitable[None]]] = (
            assemblers_client if side.is_client() else assemblers_server
        )

        for platform, assembling in assemblers.items():
            if side.is_java9() and platform in [Archive.TECHNIC, Archive.CURSEFORGE]:
                # Java 9 is currently not supported on Technic and Curse
                continue

            if self.current_task_reset_callback is not None:
                self.current_task_reset_callback()

            if self.callback:
                self.callback(self.delta_progress, f"Assembling {side} {platform} archive")
            await assembling(side, verbose)

        # TODO: Remove when the maven urls are calculated on add, instead of in curse
        self.context.asset_service.save_assets()

    async def assemble_zip(self, side: Side, verbose: bool = False) -> None:
        """
        Method called to assemble the zip archive.

        :param side: targeted side
        :param verbose: flag to control verbose mode
        :return: None
        """
        await self.zip_assembler.assemble(side, verbose)

    async def assemble_prism(self, side: Side, verbose: bool = False) -> None:
        """
        Method called to assemble the zip archive.

        :param side: targeted side
        :param verbose: flag to control verbose mode
        :return: None
        """
        await self.prism_assembler.assemble(side, verbose)

    async def assemble_curse(self, side: Side, verbose: bool = False) -> None:
        """
        Method called to assemble the curse archive.

        :param side: targeted side
        :param verbose: flag to control verbose mode
        :return: None
        """
        await self.curse_assembler.assemble(side, verbose)

    async def assemble_modrinth(self, side: Side, verbose: bool = False) -> None:
        """
        Method called to assemble the modrinth archive.

        :param side: targeted side
        :param verbose: flag to control verbose mode
        :return: None
        """
        await self.modrinth_assembler.assemble(side, verbose)

    async def assemble_technic(
        self,
        side: Side,
        verbose: bool = False,
        global_step_callback: Optional[Callable[[str], None]] = None,
    ) -> None:
        """
        Method called to assemble the technic archive.

        :param side: targeted side
        :param verbose: flag to control verbose mode
        :param global_step_callback: callback to advance the global bar between internal phases
        :return: None
        """
        await self.technic_assembler.assemble(side, verbose, global_step_callback=global_step_callback)

    # Changes to this method may need updates to utils.compress_changelog()
    def generate_changelog(self) -> Path:
        """
        Method to generate the changelog of a release.

        :return: the path to the changelog
        """

        current_version: str = self.release.version
        previous_version: Optional[str] = self.release.last_version
        previous_release: Optional[GTNHRelease] = (
            None if previous_version is None else self.context.release_service.get_release(previous_version)
        )
        changelog: dict[str, list[str]] = self.context.comparison.generate_changelog(self.release, previous_release)
        changelog_path: Path
        release_type: DevRelease | None = None
        for dr in DevRelease:
            if dr.value in current_version:
                release_type = dr
                break
        if release_type is not None:
            changelog_dir = (
                RELEASE_CHANGELOG_EXPERIMENTAL_BUILDS_DIR
                if release_type is DevRelease.EXPERIMENTAL
                else RELEASE_CHANGELOG_DAILY_BUILDS_DIR
            )
            changelog_path = (
                changelog_dir / f"changelog from {release_type.value} "
                f"{self.context.counter.get_last_successful_dev_build_id(release_type)} to "
                f"{self.context.counter.get_dev_release_count(release_type)}.md"
            )
        else:
            changelog_path = RELEASE_CHANGELOG_DIR / f"changelog from {previous_version} to {current_version}.md"

        with open(changelog_path, "w") as f:
            for mod, mod_changelog in changelog.items():
                for item in mod_changelog:
                    try:
                        f.write(item + "\n")
                    except UnicodeEncodeError:
                        f.write((item + "\n").encode("ascii", "ignore").decode())

        return changelog_path
