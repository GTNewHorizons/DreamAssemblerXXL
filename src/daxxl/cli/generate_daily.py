import asyncclick as click

from daxxl.cli._generate import generate_release
from daxxl.defs import DevRelease


@click.command()
@click.option("--update-available", default=False, is_flag=True)
@click.option("--id", "new_id", type=int, help="Set numeric ID for new daily release")
async def generate_daily(update_available: bool, new_id: int | None) -> None:
    await generate_release(DevRelease.DAILY, update_available, new_id)


if __name__ == "__main__":
    generate_daily()
