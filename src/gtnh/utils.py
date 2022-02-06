import os
from functools import cache

from github.Organization import Organization


@cache
def get_token():
    if os.getenv("GITHUB_TOKEN", None) is None:
        token_file = os.path.expanduser("~/.github_personal_token")
        if os.path.exists(token_file):
            with open(token_file) as f:
                token = f.readline()[:-1]
                os.environ["GITHUB_TOKEN"] = token
        else:
            raise Exception("No token ENV and no token file")

    return os.getenv("GITHUB_TOKEN")


@cache
def get_all_repos(o: Organization):
    return {r.name: r for r in o.get_repos()}
