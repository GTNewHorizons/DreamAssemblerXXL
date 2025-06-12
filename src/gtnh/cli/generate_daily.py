import asyncclick as click
import httpx

from gtnh.exceptions import ReleaseNotFoundException
from gtnh.gtnh_logger import get_logger
from gtnh.modpack_manager import GTNHModpackManager

log = get_logger(__name__)


@click.command()
@click.option("--update-available", default=False, is_flag=True)
@click.option("--id", "new_id", type=int, help="Set numeric ID for new daily release")
async def generate_daily(update_available: bool, new_id: int) -> None:
    async with httpx.AsyncClient(http2=True) as client:
        m = GTNHModpackManager(client)
        existing_release = m.get_release("daily")
        if new_id:
            m.set_daily_id(new_id)
        else:
            m.increment_daily_count()  # assets need to be uploaded even if the build crashes, it tracks the build id
        if not existing_release:
            raise ReleaseNotFoundException("Daily release not found")

        previous_daily_release_name = "previous_daily"
        # copy the current assets
        previous_assets = m.assets.copy(deep=True)

        release = await m.update_release(
            "daily",
            existing_release=existing_release,
            update_available=update_available,
            last_version=previous_daily_release_name,
        )

        if m.add_release(release, update=True):
            log.info("Release generated!")

            # saving the daily for changelog generation
            existing_release.version = previous_daily_release_name
            m.add_release(existing_release, update=True)
            # restore the previous assets minus the 2 daily tracking fields as to not interfere with the nightly runs
            # (was resetting the latest_version for each mod)
            new_latest_daily = m.assets.latest_daily
            new_latest_successful_daily = m.assets.latest_successful_daily
            m.assets = previous_assets
            m.assets.latest_daily = new_latest_daily
            m.assets.latest_successful_daily = new_latest_successful_daily

            m.save_assets()
            m.save_modpack()


if __name__ == "__main__":
    generate_daily()
