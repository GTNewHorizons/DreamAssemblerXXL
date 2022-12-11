import asyncclick as click
import orjson

from gtnh.defs import ModSource
from gtnh.modpack_manager import GTNHModpackManager
import httpx


def update_external_mods():
    with open("gtnh-assets.json") as f:
        blah = f.read()
    assets = orjson.loads(blah)

    for mod in assets["external_mods"]:
        if mod.get("source", None) == "other":
            continue

        project = mod.get("project_id")
        if not project:
            continue

        versions = mod.get("versions")
        if not versions:
            continue

        for version in versions:
            browser_download_url = version.get("browser_download_url")
            if not browser_download_url:
                continue

            try:
                file_no = int(browser_download_url.split("/")[-1])
            except ValueError:
                continue
            version["curse_file"] = {"project_no": project, "file_no": file_no}
            print(f"Added curse file for {project}: {browser_download_url}")
    with open("gtnh-assets.json", "wb") as f:
        f.write(orjson.dumps(assets))
    return assets


@click.command()
async def update_to_mod():
    async with httpx.AsyncClient(http2=True) as client:
        m = GTNHModpackManager(client)

    for mod in m.assets.github_mods:
        if mod.name in ["DummyCore"]:
            continue
        m.assets.add_mod(mod)

    for mod in m.assets.external_mods:
        if m.assets.has_mod(mod.name):
            print(f"Skipping duplicate external mod {mod.name}")
            continue
        mod.source = ModSource.curse
        m.assets.add_mod(mod)

    del m.assets.github_mods
    del m.assets.external_mods

    m.save_assets()


if __name__ == "__main__":
    # update_external_mods()
    m = update_to_mod()
