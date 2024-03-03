import asyncclick as click
from colorama import Fore
from httpx import AsyncClient

from gtnh.assembler.assembler import ReleaseAssembler
from gtnh.defs import Side
from gtnh.gtnh_logger import get_logger
from gtnh.modpack_manager import GTNHModpackManager

log = get_logger(__name__)


@click.command()
@click.argument("side", type=click.Choice([Side.CLIENT, Side.SERVER]))
@click.argument("release_name")
@click.option("--verbose", default=False, is_flag=True)
async def assemble_release(side: Side, release_name: str, verbose: bool) -> None:
    modpack_manager = GTNHModpackManager(AsyncClient(http2=True))
    release = modpack_manager.get_release(release_name)
    if not release:
        log.error(
            f"Release `{Fore.LIGHTRED_EX}{release_name}{Fore.RESET}` not found! Error building {Fore.YELLOW}"
            f"{side.value}{Fore.RESET} archive."
        )
        return

    await ReleaseAssembler(modpack_manager, release).assemble(side, verbose=verbose)


if __name__ == "__main__":
    assemble_release()
