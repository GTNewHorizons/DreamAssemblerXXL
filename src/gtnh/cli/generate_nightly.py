import asyncclick as click
import httpx

from gtnh.exceptions import ReleaseNotFoundException
from gtnh.gtnh_logger import get_logger
from gtnh.modpack_manager import GTNHModpackManager

log = get_logger(__name__)


@click.command()
@click.option("--update-available", default=False, is_flag=True)
@click.option("--id", "new_id", type=int, help="Set numeric ID for new experimental release")
async def generate_experimental(update_available: bool, new_id: int) -> None:
    async with httpx.AsyncClient(http2=True) as client:
        m = GTNHModpackManager(client)
        existing_release = m.get_release("experimental")
        if new_id:
            m.set_experimental_id(new_id)
        else:
            m.increment_experimental_count()  # assets need to be uploaded even if the build crashes, it tracks the build id
        if not existing_release:
            raise ReleaseNotFoundException("Experimental release not found")

        previous_experimental_release_name = "previous_experimental"

        release = await m.update_release(
            "experimental",
            existing_release=existing_release,
            update_available=update_available,
            last_version=previous_experimental_release_name,
        )

        if m.add_release(release, update=True):
            log.info("Release generated!")

            # saving the previous_experimental for changelog generation
            existing_release.version = previous_experimental_release_name
            m.add_release(existing_release, update=True)

            m.save_assets()
            m.save_modpack()


if __name__ == "__main__":
    generate_experimental()
