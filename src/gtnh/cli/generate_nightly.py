import asyncclick as click
import httpx
from structlog import get_logger

from gtnh.modpack_manager import GTNHModpackManager

log = get_logger(__name__)


@click.command()
@click.option("--update-available", default=False, is_flag=True)
async def generate_nightly(update_available: bool) -> None:
    async with httpx.AsyncClient(http2=True) as client:
        m = GTNHModpackManager(client)
        release = await m.generate_release("nightly", update_available=update_available)
        if m.add_release(release, update=True):
            log.info("Release generated!")


if __name__ == "__main__":
    generate_nightly()
