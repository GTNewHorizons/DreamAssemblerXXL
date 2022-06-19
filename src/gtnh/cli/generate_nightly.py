import click
from structlog import get_logger

from gtnh.mod_manager import GTNHModManager

log = get_logger(__name__)


@click.command()
@click.option("--update-available", default=False, is_flag=True)
def generate_nightly(update_available: bool) -> None:
    m = GTNHModManager()
    release = m.generate_release("nightly", update_available=update_available)
    if m.add_release(release, update=True):
        log.info("Release generated!")


if __name__ == "__main__":
    generate_nightly()
