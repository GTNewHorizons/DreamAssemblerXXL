from colorama import Fore
from httpx import AsyncClient

from daxxl.assembler.assembler_controller import ReleaseAssemblerController
from daxxl.defs import DevRelease, Side
from daxxl.gtnh_logger import get_logger
from daxxl.app_context import AppContext

log = get_logger(__name__)


async def assemble_dev_release(dev_release: DevRelease, verbose: bool) -> None:
    release_name = dev_release.value
    context = AppContext(AsyncClient(http2=True))
    release = context.release_service.get_release(release_name)
    if not release:
        log.error(
            f"Release `{Fore.LIGHTRED_EX}{release_name}{Fore.RESET}` not found! Error building the {release_name} archive."
        )
        return

    await context.downloader.download_release(release)

    assembler = ReleaseAssemblerController(context, release)
    await assembler.assemble_zip(Side.SERVER_JAVA9, verbose=verbose)
    await assembler.assemble_zip(Side.SERVER, verbose=verbose)
    await assembler.assemble_prism(Side.CLIENT, verbose=verbose)
    await assembler.assemble_prism(Side.CLIENT_JAVA9, verbose=verbose)

    context.counter.set_last_successful_dev_build_id(
        dev_release, context.counter.get_dev_release_count(dev_release)
    )
