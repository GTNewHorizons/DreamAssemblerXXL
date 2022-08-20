import click
from httpx import AsyncClient
from structlog import get_logger

from gtnh.modpack_manager import GTNHModpackManager

log = get_logger(__name__)


@click.command()
@click.argument("release_name")
@click.option("--previous-release-name", default=None)
def generate_changelog(release_name: str, previous_release_name: str | None) -> None:
    modpack_manager = GTNHModpackManager(AsyncClient(http2=True))
    release = modpack_manager.get_release(release_name)
    if not release:
        raise Exception(f"Release not found {release_name}")

    previous_release = modpack_manager.get_release(release_name) if previous_release_name else None

    changelog = modpack_manager.generate_changelog(release, previous_release=previous_release)

    for mod, mod_changelog in changelog.items():
        for change in mod_changelog:
            print(change)


if __name__ == "__main__":
    generate_changelog()
