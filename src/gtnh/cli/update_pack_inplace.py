import asyncclick as click
import httpx

from gtnh.defs import Side
from gtnh.exceptions import ReleaseNotFoundException
from gtnh.gtnh_logger import get_logger
from gtnh.modpack_manager import GTNHModpackManager

log = get_logger(__name__)


@click.command()
@click.argument("side", type=click.Choice([Side.CLIENT, Side.SERVER, Side.CLIENT_JAVA9, Side.SERVER_JAVA9]))
@click.argument("minecraft_dir", type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.option("--use-symlink", is_flag=True, help="Use symlinks instead of copying files")
async def update_pack_inplace(side: Side, minecraft_dir: str, use_symlink: bool = False) -> None:
    async with httpx.AsyncClient(http2=True) as client:
        m = GTNHModpackManager(client)
        release = m.get_release("nightly")
        if not release:
            raise ReleaseNotFoundException("Nightly release not found")

        await m.download_release(release, ignore_translations=True)

        await m.update_pack_inplace(release, side, minecraft_dir, use_symlink)


if __name__ == "__main__":
    update_pack_inplace()
