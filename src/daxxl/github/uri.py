class GitHubURI:
    BASE = "https://api.github.com"

    def __init__(self, org: str) -> None:
        self.org = org

    @property
    def org_repos(self) -> str:
        return f"{self.BASE}/orgs/{self.org}/repos"

    def repo(self, name: str) -> str:
        return f"{self.BASE}/repos/{self.org}/{name}"

    def latest_release(self, repo: str) -> str:
        return f"{self.BASE}/repos/{self.org}/{repo}/releases/latest"

    def releases(self, repo: str) -> str:
        return f"{self.BASE}/repos/{self.org}/{repo}/releases"

    def license(self, repo: str) -> str:
        return f"{self.BASE}/repos/{self.org}/{repo}/license"

    def issues(self, repo: str, issue_num: int | None = None) -> str:
        base = f"{self.BASE}/repos/{self.org}/{repo}/issues"
        return f"{base}/{issue_num}" if issue_num is not None else base
