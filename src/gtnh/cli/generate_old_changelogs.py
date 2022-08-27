import asyncclick as click
import gidgethub
import httpx
from gidgethub.httpx import GitHubAPI
from structlog import get_logger

from gtnh.github.uri import repo_releases_uri
from gtnh.modpack_manager import GTNHModpackManager
from gtnh.utils import get_github_token

log = get_logger(__name__)


@click.command()
async def generate_old_changelogs() -> None:
    async with httpx.AsyncClient(http2=True) as client:
        gh = GitHubAPI(client, "DreamAssemblerXXL", oauth_token=get_github_token())
        log.info("Generating Old Changelogs")
        m = GTNHModpackManager(client)
        for mod in m.assets.github_mods:
            last_version = None
            for version in mod.versions:
                if "-dev" in version.version_tag or "-pre" in version.version_tag:
                    version.prerelease = True

                if version.changelog:
                    last_version = version.version_tag
                    continue
                release_uri = repo_releases_uri(m.org, mod.name)

                try:
                    existing_release = await gh.getitem(f"{release_uri}/tags/{version.version_tag}")
                except gidgethub.BadRequest:
                    log.debug(f"Existing release {version.version_tag} not found!")
                    continue
                changelog = None
                if existing_release.get("body"):
                    changelog = existing_release["body"]
                else:
                    gh_changelog = await gh.post(
                        f"{release_uri}/generate-notes",
                        data={
                            "tag_name": version.version_tag,
                            "previous_tag_name": last_version or "",
                        },
                    )
                    if gh_changelog and gh_changelog.get("body"):
                        changelog = gh_changelog.get("body")

                if changelog:
                    # Update the local version
                    version.changelog = changelog

                    # Update GH
                    if not existing_release.get("body"):
                        release_id = existing_release.get("id")
                        await gh.patch(
                            f"{release_uri}/{release_id}",
                            data={
                                "body": version.changelog,
                                "prerelease": version.prerelease,
                            },
                        )

                    print(f"Updated - {mod.name} - {version.version_tag} - {version.prerelease} - {last_version}")

                # Set the last version
                last_version = version.version_tag

    m.save_assets()


if __name__ == "__main__":
    generate_old_changelogs()
