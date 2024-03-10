import asyncclick as click
import httpx

from gtnh.exceptions import ReleaseNotFoundException
from gtnh.gtnh_logger import get_logger
from gtnh.models.gtnh_release import load_local_extras
from gtnh.modpack_manager import GTNHModpackManager

log = get_logger(__name__)


@click.command()
@click.option("--update-available", default=False, is_flag=True)
@click.option("--local", is_flag=True, help="Add the local mod list as well")
async def generate_nightly(update_available: bool, local: bool = False) -> None:
    async with httpx.AsyncClient(http2=True) as client:
        m = GTNHModpackManager(client)
        existing_release = m.get_release("nightly")
        if not existing_release:
            raise ReleaseNotFoundException("Nightly release not found")

        if local is True:
            tmp = load_local_extras()
            if tmp is not None:
                existing_release.github_mods |= tmp.github_mods
                existing_release.external_mods |= tmp.external_mods

        release = await m.update_release(
            "nightly-local" if local else "nightly", existing_release=existing_release, update_available=update_available, local=local
        )

        if m.add_release(release, update=True):
            log.info("Release generated!")
            m.save_assets()
            if local:
                m.save_local_assets()
            m.save_modpack()


if __name__ == "__main__":
    generate_nightly()
