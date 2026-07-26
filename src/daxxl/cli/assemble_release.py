import asyncclick as click
from colorama import Fore
from httpx import AsyncClient

from daxxl.assembler.assembler_controller import ReleaseAssemblerController
from daxxl.defs import Side
from daxxl.gtnh_logger import get_logger
from daxxl.app_context import AppContext

log = get_logger(__name__)


@click.command()
@click.argument("side", type=click.Choice([Side.CLIENT, Side.CLIENT_JAVA9, Side.SERVER, Side.SERVER_JAVA9]))
@click.argument("release_name")
@click.option("--verbose", default=False, is_flag=True)
async def assemble_release(side: Side, release_name: str, verbose: bool) -> None:
    context = AppContext(AsyncClient(http2=True))
    release = context.release_service.get_release(release_name)
    if not release:
        log.error(
            f"Release `{Fore.LIGHTRED_EX}{release_name}{Fore.RESET}` not found! Error building {Fore.YELLOW}"
            f"{side.value}{Fore.RESET} archive."
        )
        return

    await ReleaseAssemblerController(context, release).assemble(side, verbose=verbose)


if __name__ == "__main__":
    assemble_release()
