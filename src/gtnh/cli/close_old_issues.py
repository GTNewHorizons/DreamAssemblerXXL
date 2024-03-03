import asyncio
from datetime import datetime

import asyncclick as click
import httpx
from dateutil.parser import parse as parse_date
from gidgethub.httpx import GitHubAPI

from gtnh.github.uri import API_BASE_URI, repo_issues_uri
from gtnh.gtnh_logger import get_logger
from gtnh.utils import AttributeDict, get_github_token

log = get_logger(__name__)


@click.command()
async def close_old_issues() -> None:
    async with httpx.AsyncClient(http2=True) as client:
        gh = GitHubAPI(client, "DreamAssemblerXXL", oauth_token=get_github_token())
        log.debug("Closing older issues")
        org = "GTNewHorizons"
        repo = "GT-New-Horizons-Modpack"
        issues = gh.getiter(repo_issues_uri(org, repo))
        tasks = []
        async for _i in issues:
            issue = AttributeDict(_i)
            if should_close_issue(issue):
                tasks.append(
                    gh.patch(
                        repo_issues_uri(org, repo, issue.number),
                        data={
                            "labels": list(
                                set(label.get("name") for label in issue.labels)
                                | {"Status: stale", "Comment to reopen"}
                            ),
                            "state": "closed",
                            "state_reason": "not_planned",
                        },
                    )
                )
        await asyncio.gather(*tasks, return_exceptions=True)


async def get_issue(num: int) -> AttributeDict:
    async with httpx.AsyncClient(http2=True) as client:
        gh = GitHubAPI(client, "DreamAssemblerXXL", oauth_token=get_github_token())
        log.debug(f"Getting issue {num}")
        return AttributeDict(
            await gh.getitem(f"{API_BASE_URI}/repos/GTNewHorizons/GT-New-Horizons-Modpack/issues/{num}")
        )


def display(issue: AttributeDict) -> str:
    return f"{issue.number} - {issue.title}"


def log_reason(issue: AttributeDict, should_close: bool, reason: str) -> None:
    log.debug(f""" {"Will" if should_close else "Won't"} close issue {display(issue)} - {reason}""")


def should_close_issue(issue: AttributeDict) -> bool:
    if issue.state != "open" or issue.closed_at is not None:
        # No reason to close an already closed issue
        return False

    if issue.milestone and issue.milestone.title == "Icebox":
        # Icebox is a lie, it'll never happen
        log_reason(issue, True, "It's in the Icebox")
        return True

    last_updated = datetime.now() - parse_date(issue.updated_at, ignoretz=True)
    if last_updated.days > 180:
        # It's been a long time since it's been updated
        log_reason(issue, True, f"It's been {last_updated.days} days since the issue was updated")
        return True

    return False


if __name__ == "__main__":
    close_old_issues()
