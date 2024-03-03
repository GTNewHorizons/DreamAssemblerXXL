import asyncclick as click
import httpx
from colorama import Fore

from gtnh.gtnh_logger import get_logger
from gtnh.modpack_manager import GTNHModpackManager

log = get_logger(__name__)


@click.command()
@click.argument("release-name")
async def do_download_release(release_name: str) -> None:
    async with httpx.AsyncClient(http2=True) as client:
        m = GTNHModpackManager(client)
        release = m.get_release(release_name)
        if release is None:
            log.error(f"Release `{Fore.LIGHTRED_EX}{release_name}{Fore.RESET}` not found!")
            return

        await m.download_release(release=release)


if __name__ == "__main__":
    do_download_release()
