import asyncclick as click
import httpx
from colorama import Fore

from daxxl.app_context import AppContext
from daxxl.gtnh_logger import get_logger

log = get_logger(__name__)


@click.command()
@click.argument("mod_name")
@click.argument("version", required=False)
async def download_mod(mod_name: str, version: str | None = None) -> None:
    async with httpx.AsyncClient(http2=True) as client:
        context = AppContext(client)
        log.info(
            f"Trying to Download mod `{Fore.CYAN}{mod_name}{Fore.RESET}:{Fore.YELLOW}{version or '<latest>'}"
            f"{Fore.RESET}`"
        )
        mod = context.assets.get_mod(mod_name)
        if mod is not None:
            await context.downloader.download_asset(mod, version)


if __name__ == "__main__":
    download_mod()
