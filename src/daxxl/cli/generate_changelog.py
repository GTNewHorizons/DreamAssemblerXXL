import asyncclick as click
from httpx import AsyncClient

from daxxl.app_context import AppContext
from daxxl.gtnh_logger import get_logger

log = get_logger(__name__)


@click.command()
@click.argument("release_name")
@click.option("--previous-release-name", default=None)
def generate_changelog(release_name: str, previous_release_name: str | None) -> None:
    context = AppContext(AsyncClient(http2=True))
    release = context.release_service.get_release(release_name)
    if not release:
        raise Exception(f"Release not found {release_name}")

    log.debug(f"Release: {release_name}, Previous Release: {previous_release_name}")
    if not previous_release_name:
        previous_release_name = release.last_version if release.last_version else None
    previous_release = context.release_service.get_release(previous_release_name) if previous_release_name else None

    changelog = context.comparison.generate_changelog(release, previous_release=previous_release)

    for mod, mod_changelog in changelog.items():
        for change in mod_changelog:
            print(change)


if __name__ == "__main__":
    generate_changelog()
