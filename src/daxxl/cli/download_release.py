import asyncclick as click
import httpx
from colorama import Fore

from daxxl.gtnh_logger import get_logger
from daxxl.app_context import AppContext

log = get_logger(__name__)


@click.command()
@click.argument("release-name")
async def do_download_release(release_name: str) -> None:
    async with httpx.AsyncClient(http2=True) as client:
        context = AppContext(client)
        release = context.release_service.get_release(release_name)
        if release is None:
            log.error(f"Release `{Fore.LIGHTRED_EX}{release_name}{Fore.RESET}` not found!")
            return

        await context.downloader.download_release(release=release)


if __name__ == "__main__":
    do_download_release()
