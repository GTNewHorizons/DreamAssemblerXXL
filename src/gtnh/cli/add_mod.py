import click
from structlog import get_logger

from gtnh.mod_manager import GTNHModManager

log = get_logger(__name__)


@click.command()
@click.argument("name")
def add_mod(name: str) -> None:
    log.info(f"Trying to add mod {name}")
    m = GTNHModManager()
    if m.add_github_mod(name):
        m.save_mods()


if __name__ == "__main__":
    add_mod()
