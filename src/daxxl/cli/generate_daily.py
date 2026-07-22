import asyncclick as click
import httpx

from daxxl.defs import DevRelease
from daxxl.gtnh_logger import get_logger
from daxxl.modpack_manager import GTNHModpackManager


log = get_logger(__name__)


@click.command()
@click.option("--update-available", default=False, is_flag=True)
@click.option("--id", "new_id", type=int, help="Set numeric ID for new daily release")
async def generate_daily(update_available: bool, new_id: int | None) -> None:
    async with httpx.AsyncClient(http2=True) as client:
        m = GTNHModpackManager(client)
        if new_id:
            m.set_daily_id(new_id)
        else:
            m.increment_daily_count()  # assets need to be uploaded even if the build crashes, it tracks the build id
        _, update_errors = await m.update_rolling_release(DevRelease.DAILY.value, update_available=update_available)
        if update_errors:
            log.warn(f"{len(update_errors)} asset(s) failed to update, see errors above")
        m.save_assets()
        log.info("Release generated!")


if __name__ == "__main__":
    generate_daily()
