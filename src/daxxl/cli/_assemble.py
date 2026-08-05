from colorama import Fore
from httpx import AsyncClient

from daxxl.app_context import AppContext
from daxxl.assembler.assembler_controller import ReleaseAssemblerController
from daxxl.defs import RELEASE_MANIFEST_DIR, DevRelease, Side
from daxxl.fullpack_manifest import write_fullpack_manifest
from daxxl.gtnh_logger import get_logger

log = get_logger(__name__)


async def assemble_dev_release(dev_release: DevRelease, verbose: bool) -> None:
    release_name = dev_release.value
    context = AppContext(AsyncClient(http2=True))
    release = context.release_service.get_release(release_name)
    if not release:
        log.error(f"Release `{Fore.LIGHTRED_EX}{release_name}{Fore.RESET}` not found! Error building the {release_name} archive.")
        return

    await context.downloader.download_release(release)

    assembler = ReleaseAssemblerController(context, release)
    write_fullpack_manifest(RELEASE_MANIFEST_DIR / f"{release_name}.json", assembler.zip_assembler)
    await assembler.assemble_zip(Side.SERVER_JAVA9, verbose=verbose)
    await assembler.assemble_zip(Side.SERVER, verbose=verbose)
    await assembler.assemble_prism(Side.CLIENT, verbose=verbose)
    await assembler.assemble_prism(Side.CLIENT_JAVA9, verbose=verbose)

    context.counter.set_last_successful_dev_build_id(dev_release, context.counter.get_dev_release_count(dev_release))
