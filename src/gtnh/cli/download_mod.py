import click
from colorama import Fore
from structlog import get_logger

from gtnh.assembler.downloader import download_github_mod
from gtnh.modpack_manager import GTNHModpackManager

log = get_logger(__name__)


@click.command()
@click.argument("mod_name")
@click.argument("version", required=False)
def download_mod(mod_name: str, version: str | None = None) -> None:
    m = GTNHModpackManager()
    log.info(f"Trying to Download mod `{Fore.CYAN}{mod_name}{Fore.RESET}:{Fore.YELLOW}{version or '<latest>'}{Fore.RESET}`")
    mod = m.assets.get_github_mod(mod_name)
    if mod is not None:
        download_github_mod(mod, version)


if __name__ == "__main__":
    download_mod()
