import httpx

from daxxl.defs import DevRelease
from daxxl.gtnh_logger import get_logger
from daxxl.modpack_manager import AppContext

log = get_logger(__name__)


async def generate_release(
    dev_release: DevRelease,
    update_available: bool,
    new_id: int | None,
) -> None:
    async with httpx.AsyncClient(http2=True) as client:
        m = AppContext(client)
        if new_id:
            m.counter.set_dev_release_id(dev_release, new_id)
        else:
            m.counter.increment_dev_build_id(dev_release)
        _, update_errors = await m.update_service.update_rolling_release(
            dev_release, update_available=update_available
        )
        if update_errors:
            log.warn(f"{len(update_errors)} asset(s) failed to update, see errors above")
        m.asset_service.save_assets()
        log.info("Release generated!")
