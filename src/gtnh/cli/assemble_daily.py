import asyncclick as click
from colorama import Fore
from httpx import AsyncClient

from gtnh.assembler.assembler import ReleaseAssembler
from gtnh.defs import Side
from gtnh.gtnh_logger import get_logger
from gtnh.modpack_manager import GTNHModpackManager

log = get_logger(__name__)


@click.command()
@click.option("--verbose", default=False, is_flag=True)
async def assemble_daily(verbose: bool) -> None:
    release_name = "daily"
    modpack_manager = GTNHModpackManager(AsyncClient(http2=True))
    release = modpack_manager.get_release(release_name)
    if not release:
        log.error(
            f"Release `{Fore.LIGHTRED_EX}{release_name}{Fore.RESET}` not found! Error building the daily archive."
        )
        return

    await modpack_manager.download_release(
        release,
    )

    assembler = ReleaseAssembler(modpack_manager, release)
    await assembler.assemble_zip(Side.SERVER_JAVA9, verbose=verbose)
    await assembler.assemble_zip(Side.SERVER, verbose=verbose)
    await assembler.assemble_mmc(Side.CLIENT, verbose=verbose)
    await assembler.assemble_mmc(Side.CLIENT_JAVA9, verbose=verbose)

    modpack_manager.set_last_successful_daily_id(modpack_manager.get_daily_count())


if __name__ == "__main__":
    assemble_daily()
