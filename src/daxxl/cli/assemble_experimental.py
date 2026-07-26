import asyncclick as click

from daxxl.cli._assemble import assemble_dev_release
from daxxl.defs import DevRelease


@click.command()
@click.option("--verbose", default=False, is_flag=True)
async def assemble_experimental(verbose: bool) -> None:
    await assemble_dev_release(DevRelease.EXPERIMENTAL, verbose)


if __name__ == "__main__":
    assemble_experimental()
