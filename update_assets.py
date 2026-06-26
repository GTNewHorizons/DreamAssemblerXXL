import asyncclick as click
import httpx
import orjson

from daxxl.modpack_manager import GTNHModpackManager


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
async def cleanup_maven_urls():
    async with httpx.AsyncClient(http2=True) as client:
        m = GTNHModpackManager(client)

    for mod in m.assets.mods:
        for v in mod.versions:
            if v.maven_url and "github.com" in v.maven_url:
                v.maven_url = None

    m.save_assets()


if __name__ == "__main__":
    # update_external_mods()
    cleanup_maven_urls()
