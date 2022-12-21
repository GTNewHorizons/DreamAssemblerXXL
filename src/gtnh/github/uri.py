"""Module providing functions to get various github uri."""

API_BASE_URI = "https://api.github.com"


def org_repos_uri(org: str) -> str:
    """
    Return the org repo uri for the provided org.

    Parameters
    ----------
    org: str
        The given org.

    Returns
    -------
    The corresponding org uri.
    """
    return f"{API_BASE_URI}/orgs/{org}/repos"


def repo_uri(org: str, repo: str) -> str:
    """
    Return the repository uri for the provided org and repository name.

    Parameters
    ----------
    org: str
        The given org.

    repo: str
        The given repository name.

    Returns
    -------
    The corresponding repository uri.
    """
    return f"{API_BASE_URI}/repos/{org}/{repo}"


def latest_release_uri(org: str, repo: str) -> str:
    """
    Return the latest release uri for a given organisation and a given repository.

    Parameters
    ----------
    org: str
        The given organisation.

    repo: str
        The given repository.

    Returns
    -------
    The corresponding latest release uri.
    """
    return f"{API_BASE_URI}/repos/{org}/{repo}/releases/latest"


def repo_releases_uri(org: str, repo: str) -> str:
    """
    Return the releases uri for a given organisation and a given repository.

    Parameters
    ----------
    org: str
        The given organisation.

    repo: str
        The given repository.

    Returns
    -------
    The corresponding releases uri.
    """
    return f"{API_BASE_URI}/repos/{org}/{repo}/releases"


def repo_license_uri(org: str, repo: str) -> str:
    """
    Return the license uri for a given organisation and a given repository.

    Parameters
    ----------
    org: str
        The given organisation.

    repo: str
        The given repository.

    Returns
    -------
    The corresponding license uri.
    """
    return f"{API_BASE_URI}/repos/{org}/{repo}/license"


def repo_issues_uri(org: str, repo: str, issue_num: int | None = None) -> str:
    """
    Return the repository issues uri for a given organisation and a given repository.

    Parameters
    ----------
    org: str
        The given organisation.

    repo: str
        The given repository.

    Returns
    -------
    The corresponding repository issues uri.
    """
    return f"{API_BASE_URI}/repos/{org}/{repo}/issues" + (f"/{issue_num}" if issue_num is not None else "")
