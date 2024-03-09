import asyncclick as click
import httpx
from colorama import Fore

from gtnh.gtnh_logger import get_logger
from gtnh.modpack_manager import GTNHModpackManager

log = get_logger(__name__)


@click.command()
@click.argument("mod_name")
@click.option("--local", is_flag=True, help="Use local mod list instead")
@click.argument("version", required=False)
async def download_mod(mod_name: str, local: bool, version: str | None = None) -> None:
    async with httpx.AsyncClient(http2=True) as client:
        m = GTNHModpackManager(client)
        log.info(
            f"Trying to Download mod `{Fore.CYAN}{mod_name}{Fore.RESET}:{Fore.YELLOW}{version or '<latest>'}"
            f"{Fore.RESET}`"
        )
        mod = (m.local_assets if local is True else m.assets).get_mod(mod_name)
        if mod is not None:
            await m.download_asset(mod, version)


if __name__ == "__main__":
    download_mod()
