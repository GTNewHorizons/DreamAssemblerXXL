from colorama import Fore
from httpx import AsyncClient

from daxxl.assembler.assembler_controller import ReleaseAssemblerController
from daxxl.defs import DevRelease, Side
from daxxl.gtnh_logger import get_logger
from daxxl.modpack_manager import AppContext

log = get_logger(__name__)


async def assemble_dev_release(dev_release: DevRelease, verbose: bool) -> None:
    release_name = dev_release.value
    modpack_manager = AppContext(AsyncClient(http2=True))
    release = modpack_manager.release_service.get_release(release_name)
    if not release:
        log.error(
            f"Release `{Fore.LIGHTRED_EX}{release_name}{Fore.RESET}` not found! Error building the {release_name} archive."
        )
        return

    await modpack_manager.downloader.download_release(release)

    assembler = ReleaseAssemblerController(modpack_manager, release)
    await assembler.assemble_zip(Side.SERVER_JAVA9, verbose=verbose)
    await assembler.assemble_zip(Side.SERVER, verbose=verbose)
    await assembler.assemble_prism(Side.CLIENT, verbose=verbose)
    await assembler.assemble_prism(Side.CLIENT_JAVA9, verbose=verbose)

    modpack_manager.counter.set_last_successful_dev_build_id(dev_release, modpack_manager.counter.get_dev_release_count(dev_release))
