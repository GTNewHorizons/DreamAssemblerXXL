import itertools
import os
from bisect import bisect_left
from functools import cache
from pathlib import Path
import re
from shutil import copy, rmtree
from typing import Any, Iterable, Iterator, List
from urllib import parse

from gtnh.defs import CLIENT_WORKING_DIR, SERVER_WORKING_DIR, ModEntry


class AttributeDict(dict):  # type: ignore
    def __getattr__(self, name: str) -> Any:
        res = self.get(name)
        if isinstance(res, dict):
            return AttributeDict(res)
        return res

    def __setattr__(self, name: str, val: Any) -> Any:
        self[name] = val


def grouper(n: int, iterable: Iterable[Any]) -> Iterator[Any]:
    iterable = iter(iterable)
    return iter(lambda: list(itertools.islice(iterable, n)), [])


@cache
def get_github_token() -> str:
    return _get_token("Github", "GITHUB_TOKEN", "~/.github_personal_token")


@cache
def get_curse_token() -> str:
    return _get_token("Curse", "CURSE_TOKEN", "~/.curse_token")


def _get_token(token_name: str, token_env: str, token_path: str) -> str:
    if os.getenv(token_name, None) is None:
        token_file = os.path.expanduser(token_path)
        if os.path.exists(token_file):
            with open(token_file) as f:
                token = f.readline().rstrip()
                os.environ[token_name] = token
        else:
            raise Exception(f"Token '{token_name}' not found in '{token_env}' or '{token_file}'")
    return os.getenv(token_name, "<unset>")


def copy_file_to_folder(path_list: List[Path], source_root: Path, destination_root: Path) -> None:
    """
    Function used to move files from the source folder to the destination folder, while keeping the relative path.

    :param path_list: the list of files to move.
    :param source_root: the root folder of the files to move. It is assumed that path_list has files comming from the
                        same root folder.
    :param destination_root: the root folder for the destination.
    :return: None
    """
    for file in path_list:
        dst = destination_root / file.relative_to(source_root)
        if not dst.parent.is_dir():
            os.makedirs(dst.parent)
        copy(file, dst)


def crawl(path: Path) -> List[Path]:
    """
    Function that will recursively list all the files of a folder.

    :param path: The folder to scan
    :return: The list of all the files contained in that folder
    """
    files = [x for x in path.iterdir() if x.is_file()]
    for folder in [x for x in path.iterdir() if x.is_dir()]:
        files.extend(crawl(folder))
    return files


def move_mods(client_paths: List[Path], server_paths: List[Path]) -> None:
    """
    Method used to move the mods in their correct archive folder after they have been downloaded.

    :param client_paths: the paths for the mods clientside
    :param server_paths: the paths for the mods serverside
    :return: None
    """
    client_folder = CLIENT_WORKING_DIR
    server_folder = SERVER_WORKING_DIR
    source_root = Path(__file__).parent / "cache"

    if client_folder.exists():
        rmtree(client_folder)
        os.makedirs(client_folder)

    if server_folder.exists():
        rmtree(server_folder)
        os.makedirs(server_folder)

    copy_file_to_folder(client_paths, source_root, client_folder)
    copy_file_to_folder(server_paths, source_root, server_folder)


def verify_url(url: str) -> bool:
    """
    Url validator.

    :param url: the url to be checked
    :return: if yes or no it's valid
    """
    parse_result = parse.urlparse(url)
    return parse_result.scheme in ["https", "http"] and parse_result.netloc != ""


def index(elements_list: List[Any], element: Any) -> int:
    """
    Locate the leftmost value exactly equal to element in element_list.

    :param elements_list: the list of element looked into
    :param element: the element looked for
    :return: the position of element in elements_list
    """
    i = bisect_left(elements_list, element)
    if i != len(elements_list) and elements_list[i] == element:
        return i
    raise ValueError


def blockquote(input_str: str) -> str:
    return "\n".join(f">{s}" for s in input_str.split("\n"))


def compress_changelog(file_path):
    """
    Compress the changelog matching the given changelog path.

    :param file_path: the path of the file
    :return: none
    """
    currentEntry = None
    inChangesMode = False
    currentVersion = ""
    entries = []
    initialLines = []
    with open(file_path, "r") as file:
        data = file.readlines()
        for line in data:
            line = line.strip()
            if line.startswith("# New Mod - "):
                m = re.search("^# New Mod - (.*?):(.*?)$", line)
                name = m.group(1)
                version = m.group(2)
                currentEntry = ModEntry(name, version, True)
                inChangesMode = False
                entries.append(currentEntry)
            elif line.startswith("# Updated - "):
                m = re.search("^# Updated - (.*?) - (.*?) -->(.*?)$", line)
                name = m.group(1)
                versionFrom = m.group(2)
                versionTo = m.group(3)
                version = versionFrom + "..." + versionTo
                currentEntry = ModEntry(name, version, False)
                inChangesMode = False
                entries.append(currentEntry)
            elif currentEntry != None:
                if line == ">## What's Changed":
                    inChangesMode = True
                elif line == ">## New Contributors":
                    inChangesMode = False
                elif line.startswith("## *"):
                    currentVersion = line[4: -1]
                elif line.startswith(">* "):
                    if inChangesMode:
                        currentEntry.changes.append(line[3:] + " (" + currentVersion + ")")
                    else:
                        currentEntry.newContributors.append(line[3:] + " (" + currentVersion + ")")
                elif line.startswith(">**Full Changelog**: "):
                    m = re.search("(compare|commits)/(.*?)(\.\.\.(.*))?$", line)
                    if m.group(1) == "compare":
                        currentEntry.oldestLinkVersion = m.group(2)
                        if currentEntry.newestLinkVersion == "":
                            currentEntry.newestLinkVersion = m.group(4)
                    else:
                        currentEntry.oldestLinkVersion = m.group(2)
            else:
                initialLines.append(line)

    with open(file_path, "w") as file:
        for line in initialLines:
            file.write(line + "\n")

        for ent in entries:
            if ent.isNew:
                file.write("# New Mod - " + ent.name + " (" + ent.version + ")\n")
            else:
                file.write(
                    "# Updated " + ent.name + " (" + re.sub('^(.*)\.\.\.(.*)$', r'\1 --> \2', ent.version) + ")\n")

            if ent.isNew or ent.newestLinkVersion == "":
                file.write("**Full Changelog**: https://github.com/GTNewHorizons/" + ent.name + "/commits/" + (
                    ent.newestLinkVersion if ent.newestLinkVersion != "" else (
                        ent.oldestLinkVersion if ent.oldestLinkVersion != "" else ent.version)) + "\n")
            else:
                file.write(
                    "**Full Changelog**: https://github.com/GTNewHorizons/" + ent.name + "/compare/" + ent.oldestLinkVersion + "..." + ent.newestLinkVersion + "\n")

            if ent.changes:
                file.write(">## What's Changed\n")
                for ch in ent.changes:
                    file.write("> * " + ch + "\n")
                file.write(">\n")

            if ent.newContributors:
                file.write(">## New Contributors\n")
                for nc in ent.newContributors:
                    file.write("> * " + nc + "\n")
                file.write(">\n")

            file.write("\n")

