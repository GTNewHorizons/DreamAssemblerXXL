API_BASE_URI = "https://api.github.com"


def org_repos_uri(org: str) -> str:
    return f"{API_BASE_URI}/orgs/{org}/repos"


def repo_uri(org: str, repo: str) -> str:
    return f"{API_BASE_URI}/repos/{org}/{repo}"


def latest_release_uri(org: str, repo: str) -> str:
    return f"{API_BASE_URI}/repos/{org}/{repo}/releases/latest"


def repo_releases_uri(org: str, repo: str) -> str:
    return f"{API_BASE_URI}/repos/{org}/{repo}/releases"


def repo_license_uri(org: str, repo: str) -> str:
    return f"{API_BASE_URI}/repos/{org}/{repo}/license"


def repo_issues_uri(org: str, repo: str, issue_num: int | None = None) -> str:
    return f"{API_BASE_URI}/repos/{org}/{repo}/issues" + (f"/{issue_num}" if issue_num is not None else "")
