import json

from cache import AsyncLRU
from colorama import Fore, Style
from gidgethub import BadRequest
from gidgethub.httpx import GitHubAPI
from httpx import AsyncClient

from daxxl.defs import MAVEN_BASE_URL, OTHER, ROOT_DIR, UNKNOWN
from daxxl.exceptions import RepoNotFoundException
from daxxl.github.uri import latest_release_uri, org_repos_uri, repo_uri
from daxxl.gtnh_logger import get_logger
from daxxl.utils import AttributeDict, get_github_token

log = get_logger(__name__)


class GitHubClient:
    def __init__(self, client: AsyncClient, org: str = "GTNewHorizons") -> None:
        self.client = client
        self.org = org
        self.gh = GitHubAPI(self.client, "DreamAssemblerXXL", oauth_token=get_github_token())

    @AsyncLRU(maxsize=None)
    async def get_all_repos(self) -> dict[str, AttributeDict]:
        return {r["name"]: AttributeDict(r) async for r in self.gh.getiter(org_repos_uri(self.org))}

    @AsyncLRU(maxsize=None)
    async def get_repo(self, name: str) -> AttributeDict:
        try:
            return AttributeDict(await self.gh.getitem(repo_uri(self.org, name)))
        except BadRequest as error:
            raise RepoNotFoundException(f"Repo not found {name}") from error

    async def get_latest_github_release(self, repo: AttributeDict | str) -> AttributeDict | None:
        if isinstance(repo, str):
            try:
                latest_release = AttributeDict(await self.gh.getitem(latest_release_uri(self.org, repo)))
            except BadRequest:
                log.error(f"{Fore.RED}No latest release found for {Fore.CYAN}{repo}{Style.RESET_ALL}")
                latest_release = None
        else:
            try:
                latest_release = AttributeDict(await self.gh.getitem(latest_release_uri(self.org, repo.name)))
            except BadRequest:
                log.error(f"{Fore.RED}No latest release found for {Fore.CYAN}{repo.get('name')}{Style.RESET_ALL}")
                latest_release = None

        return latest_release

    async def get_license_from_repo(self, repo: AttributeDict, allow_fallback: bool = True) -> str | None:
        """
        Attempt to find a license for a mod, based on the repository; falling back to some manually collected licenses
        :param repo: Github Repository
        :return: License `str`
        """
        mod_license = None
        try:
            repo_license = repo.license
            if repo_license:
                mod_license = repo_license.name
                log.info(f"Found license `{Fore.YELLOW}{mod_license}{Fore.RESET}` from repo")
        except BadRequest:
            log.warn("No license found from repo")

        if mod_license in [None, UNKNOWN, OTHER] and allow_fallback:
            with open(ROOT_DIR / "licenses_from_boubou.json") as f:
                manual_licenses = json.loads(f.read())
                by_url = {v["url"]: v.get("license", None) for v in manual_licenses.values()}
                mod_license = by_url.get(repo.html_url, None)
                if mod_license:
                    log.info(f"Found fallback license {Fore.YELLOW}{mod_license}{Fore.RESET}.")

        if not mod_license:
            log.warn("No license found!")
            mod_license = "All Rights Reserved (fallback)"

        return mod_license

    async def get_maven(self, mod_name: str) -> str | None:
        """
        Get the maven URL for a `mod_name`, ensuring it exists
        :param mod_name: Mod Name
        :return: Maven URL, if found
        """
        maven_url = MAVEN_BASE_URL + mod_name + "/"
        response = await self.client.head(maven_url, follow_redirects=True)

        if response.status_code == 200:
            return maven_url
        elif response.status_code >= 500:
            raise Exception(f"Maven unreachable status: {response.status_code}")
        return None
