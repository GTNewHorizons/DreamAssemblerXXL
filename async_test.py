import asyncio

import gidgethub.httpx
import httpx
from structlog import get_logger

from gtnh.utils import get_token

log = get_logger(__name__)

BASE_URI = "https://api.github.com"
ORG = "GTNewHorizons"


async def get_repos(gh):
    # Make your requests, e.g. ...
    return [d async for d in gh.getiter(f"{BASE_URI}/orgs/{ORG}/repos")]


async def get_latest_release(gh, repo):
    return await gh.getitem(f"{BASE_URI}/repos/{ORG}/{repo}/releases/latest")


async def get_latest_releases(gh, repos):
    tasks = (get_latest_release(gh, repo["name"]) for repo in repos)
    releases = await asyncio.gather(*tasks, return_exceptions=True)
    return [r for r in releases]


async def get_all():
    async with httpx.AsyncClient() as client:
        gh = gidgethub.httpx.GitHubAPI(client, "mitchej123", oauth_token=get_token())

        log.info("Gathering all Repos")
        repos = await get_repos(gh)
        log.info("Gathering latest release for all repos")
        latest_releases = await get_latest_releases(gh, repos)
        log.info("Done!")

    return repos, latest_releases


async def get2(repos):
    async with httpx.AsyncClient() as client:
        gh = gidgethub.httpx.GitHubAPI(client, "mitchej123", oauth_token=get_token())
        log.info("Gathering latest release for all repos")
        latest_releases = await get_latest_releases(gh, repos)
        log.info("Done!")
    return latest_releases


if __name__ == "__main__":
    # repos, latest_releases = asyncio.run(get_all())
    latest_releases = asyncio.run(get2(repos))
