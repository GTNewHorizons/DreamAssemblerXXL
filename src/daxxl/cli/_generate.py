import httpx

from daxxl.app_context import AppContext
from daxxl.defs import DevRelease
from daxxl.gtnh_logger import get_logger

log = get_logger(__name__)


async def generate_release(
    dev_release: DevRelease,
    update_available: bool,
    new_id: int | None,
) -> None:
    async with httpx.AsyncClient(http2=True) as client:
        context = AppContext(client)
        if new_id:
            context.counter.set_dev_release_id(dev_release, new_id)
        else:
            context.counter.increment_dev_build_id(
                dev_release
            )  # assets need to be uploaded even if the build crashes, it tracks the build id
        _, update_errors = await context.update_service.update_rolling_release(
            dev_release, update_available=update_available
        )
        if update_errors:
            log.warn(f"{len(update_errors)} asset(s) failed to update, see errors above")
        context.asset_service.save_assets()
        log.info("Release generated!")
