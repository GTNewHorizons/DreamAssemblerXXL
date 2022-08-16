import asyncclick as click
import httpx
from colorama import Fore
from structlog import get_logger

from gtnh.modpack_manager import GTNHModpackManager

log = get_logger(__name__)


@click.command()
@click.argument("mod_name")
@click.argument("version", required=False)
async def download_mod(mod_name: str, version: str | None = None) -> None:
    async with httpx.AsyncClient(http2=True) as client:
        m = GTNHModpackManager(client)
        log.info(
            f"Trying to Download mod `{Fore.CYAN}{mod_name}{Fore.RESET}:{Fore.YELLOW}{version or '<latest>'}{Fore.RESET}`"
        )
        mod = m.assets.get_github_mod(mod_name)
        if mod is not None:
            await m.download_asset(mod, version)


if __name__ == "__main__":
    download_mod()
