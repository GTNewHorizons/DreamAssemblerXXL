#!/usr/bin/env python3
import asyncclick as click
import httpx
from colorama import init
from structlog import get_logger

from gtnh.modpack_manager import GTNHModpackManager

log = get_logger(__name__)

init(autoreset=True)


class NoReleasesException(Exception):
    pass


@click.argument("version_tag", type=click.types.STRING)
@click.argument("mod_name", type=click.types.STRING)
@click.command()
async def remove_version(mod_name: str, version_tag: str) -> None:
    async with httpx.AsyncClient(http2=True) as client:
        log.info(f"Attemting to remove {version_tag} from {mod_name}")

        m = GTNHModpackManager(client)

        mod = m.assets.get_mod(mod_name)
        if not mod:
            log.error(f"Mod not found {mod_name}")
            return

        version_reset = mod.remove_version_tag(version_tag) or mod.reset_latest()

        if not version_reset:
            log.warn(f"Version tag {version_tag} not found")
        else:
            log.info(f"Version tag {version_tag} removed, latest version is: {mod.latest_version}")
            m.save_assets()


if __name__ == "__main__":
    remove_version()
