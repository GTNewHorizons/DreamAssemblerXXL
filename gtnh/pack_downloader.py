import os
from github import Github
from github.GitRelease import GitRelease
from github.Organization import Organization
from retry import retry
import requests

from mod_info import GTNHMods, load_gtnh_mod_info

CACHE_DIR = "cache"


class NoReleasesException(Exception):
    pass


def get_latest_releases(gtnh_mod_info: GTNHMods) -> None:
    g = Github(get_token())
    o = g.get_organization("GTNewHorizons")

    for mod_name, mod_info in gtnh_mod_info.mods.items():
        download_mod(g, o, mod_name)


@retry(delay=5, tries=3)
def download_mod(g: Github, o: Organization, mod_name: str) -> None:
    print("***********************************************************")
    print(f"Looking for release information for {mod_name}")

    repo = o.get_repo(mod_name)
    latest_release: GitRelease = repo.get_latest_release()
    if not latest_release:
        print(f"*** No latest release found for {mod_name}")
        return

    print(f"Found release {latest_release.tag_name}")

    release_assets = latest_release.get_assets()
    for asset in release_assets:
        if not asset.name.endswith(".jar") or asset.name.endswith("dev.jar") or asset.name.endswith("sources.jar") or asset.name.endswith("api.jar"):
            continue

        print(f"Found Release at {asset.browser_download_url}")
        cache_dir = ensure_cache_dir()
        mod_filename = cache_dir + "/" + asset.name
        if os.path.exists(mod_filename):
            print(f"Skipping re-redownload of {asset.name}")
            continue

        print(f"Downloading {asset.name} to {mod_filename}")

        headers = {'Authorization': f'token {get_token()}', 'Accept': 'application/octet-stream'}

        if repo.private:
            print(f"Private Repo!")

        with requests.get(asset.url, stream=True, headers=headers) as r:
            r.raise_for_status()
            with open(mod_filename, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        print("Download successful")


def ensure_cache_dir() -> str:
    cache_dir = os.getcwd() + "/" + CACHE_DIR
    os.makedirs(cache_dir, exist_ok=True)

    return cache_dir


def get_token():
    if os.getenv("GITHUB_TOKEN", None) is None:
        token_file = os.path.expanduser('~/.github_personal_token')
        if os.path.exists(token_file):
            with open(token_file) as f:
                token = f.readline()[:-1]
                os.environ["GITHUB_TOKEN"] = token
        else:
            raise Exception("No token ENV and no token file")

    return os.getenv("GITHUB_TOKEN")


if __name__ == '__main__':
    github_mods = load_gtnh_mod_info()
    get_latest_releases(github_mods)
