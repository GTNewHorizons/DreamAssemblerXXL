import click
from colorama import Fore
from httpx import AsyncClient
from structlog import get_logger

from gtnh.assembler.assembler import ReleaseAssembler
from gtnh.defs import Side
from gtnh.modpack_manager import GTNHModpackManager

log = get_logger(__name__)


@click.command()
@click.argument("side", type=click.Choice([Side.CLIENT, Side.SERVER]))
@click.argument("release_name")
@click.option("--verbose", default=False, is_flag=True)
def assemble_release(side: Side, release_name: str, verbose: bool) -> None:
    modpack_manager = GTNHModpackManager(AsyncClient(http2=True))
    release = modpack_manager.get_release(release_name)
    if not release:
        log.error(f"Release `{Fore.LIGHTRED_EX}{release_name}{Fore.RESET}` not found! Error building {Fore.YELLOW}{side.value}{Fore.RESET} archive.")
        return

    ReleaseAssembler(modpack_manager, release, verbose=verbose).assemble(side)


if __name__ == "__main__":
    assemble_release()
