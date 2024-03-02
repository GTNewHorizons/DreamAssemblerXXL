import asyncclick as click
import httpx
from colorama import Fore
from httpx import AsyncClient
from structlog import get_logger

from gtnh.defs import Side
from gtnh.exceptions import ReleaseNotFoundException
from gtnh.modpack_manager import GTNHModpackManager

log = get_logger(__name__)

@click.command()
@click.argument("side", type=click.Choice([Side.CLIENT, Side.SERVER, Side.CLIENT_JAVA9, Side.SERVER_JAVA9]))
@click.argument("minecraft_dir", type=click.Path(exists=True, file_okay=False, dir_okay=True))
async def update_pack_inplace(side: Side, minecraft_dir: str) -> None:
    async with httpx.AsyncClient(http2=True) as client:
        m = GTNHModpackManager(client)
        existing_release = m.get_release("nightly")
        if not existing_release:
            raise ReleaseNotFoundException("Nightly release not found")

        release = await m.update_release(
            "nightly", existing_release=existing_release, update_available=True
        )

        if m.add_release(release, update=True):
            log.info("Release generated!")
            m.save_assets()
            m.save_modpack()

        await m.download_release(release)

        await m.update_pack_inplace(side, minecraft_dir)

if __name__ == "__main__":
    update_pack_inplace()