import asyncclick as click
import httpx

from gtnh.exceptions import ReleaseNotFoundException
from gtnh.gtnh_logger import get_logger
from gtnh.modpack_manager import GTNHModpackManager

log = get_logger(__name__)


@click.command()
@click.option("--update-available", default=False, is_flag=True)
async def generate_nightly(update_available: bool) -> None:
    async with httpx.AsyncClient(http2=True) as client:
        m = GTNHModpackManager(client)
        existing_release = m.get_release("nightly")
        m.increment_nightly_count()  # assets need to be uploaded even if the build crashes, it tracks the build id
        if not existing_release:
            raise ReleaseNotFoundException("Nightly release not found")

        previous_nightly_release_name = "previous_nightly"

        release = await m.update_release(
            "nightly",
            existing_release=existing_release,
            update_available=update_available,
            last_version=previous_nightly_release_name,
        )

        if m.add_release(release, update=True):
            log.info("Release generated!")

            # saving the previous_nightly for changelog generation
            existing_release.version = previous_nightly_release_name
            m.add_release(existing_release, update=True)

            m.save_assets()
            m.save_modpack()


if __name__ == "__main__":
    generate_nightly()
