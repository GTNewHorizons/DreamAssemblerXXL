from colorama import Fore
from httpx import AsyncClient
from structlog import get_logger

from gtnh.defs import Side
from gtnh.modpack_manager import GTNHModpackManager

log = get_logger(__name__)


async def update_pack_inplace(side: Side, minecraft_dir: str, verbose: bool = False) -> None:
    modpack_manager = GTNHModpackManager(AsyncClient(http2=True))
    release = modpack_manager.get_release("nightly")
    if not release:
        log.error(f"Release `{Fore.LIGHTRED_EX}nightly{Fore.RESET}` not found! Error building the nightly archive.")
        return

    await modpack_manager.update_pack_inplace(side, minecraft_dir, verbose)
