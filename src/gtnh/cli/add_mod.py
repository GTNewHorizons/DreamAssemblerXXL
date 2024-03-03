import asyncclick as click
import httpx

from gtnh.gtnh_logger import get_logger
from gtnh.modpack_manager import GTNHModpackManager

log = get_logger(__name__)


@click.command()
@click.argument("name")
async def add_mod(name: str) -> None:
    async with httpx.AsyncClient(http2=True) as client:
        log.info(f"Trying to add mod {name}")
        m = GTNHModpackManager(client)
        if await m.add_github_mod(name):
            m.save_assets()


if __name__ == "__main__":
    add_mod()
