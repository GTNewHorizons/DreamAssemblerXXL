#!/usr/bin/env python3
import click
from colorama import Fore, Style, init
from structlog import get_logger

from gtnh.mod_manager import GTNHModManager
from gtnh.models.mod_info import update_github_mod_from_repo

log = get_logger(__name__)

init(autoreset=True)


class NoReleasesException(Exception):
    pass


@click.option(
    "--mods",
    is_flag=False,
    metavar="<mods>",
    type=click.types.STRING,
)
@click.command()
def update_check(mods: str | None = None) -> None:
    mods_to_update = [m.strip() for m in mods.split(",")] if mods else None
    if mods_to_update:
        log.info(f"Attemting to update mod(s): `{mods_to_update}`")

    m = GTNHModManager()

    log.info("Grabbing all repository information...")
    all_repos = m.get_all_repos()
    updated = False

    for mod in m.mods.github_mods:
        if mods_to_update and mod.name not in mods_to_update:
            continue

        log.info(f"Checking for updates for {Fore.CYAN}{mod.name}{Fore.RESET}.")
        repo = all_repos.get(mod.name)
        if not repo:
            log.error(f"{Fore.RED}Missing repo for {Fore.CYAN}{mod.name}{Fore.RED}, skipping update check.{Fore.RESET}")
            continue

        updated |= update_github_mod_from_repo(mod, repo)

    if updated:
        m.save_mods()

    missing_repos = m.get_missing_repos(all_repos)
    if len(missing_repos):
        log.info(f"{Fore.RED}****** Missing Mods:{Style.RESET_ALL} {', '.join(sorted(missing_repos))}")

    missing_maven = m.get_missing_mavens()
    if len(missing_maven):
        log.info(f"{Fore.RED}****** Missing Maven:{Style.RESET_ALL} {', '.join(sorted(missing_maven))}")


if __name__ == "__main__":
    update_check()
