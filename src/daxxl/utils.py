import os
import stat
from functools import cache
from pathlib import Path
from typing import Any
from zipfile import ZipFile


class AttributeDict(dict):
    def __getattr__(self, name: str) -> Any:
        res = self.get(name)
        if isinstance(res, dict):
            return AttributeDict(res)
        return res

    def __setattr__(self, name: str, val: Any) -> Any:
        self[name] = val


@cache
def get_github_token() -> str:
    return _get_token("Github", "GITHUB_TOKEN", "~/.github_personal_token")


def _get_token(token_name: str, token_env: str, token_path: str) -> str:
    if os.getenv(token_env, None) is None:
        token_file = os.path.expanduser(token_path)
        if os.path.exists(token_file):
            with open(token_file) as f:
                token = f.readline().rstrip()
                os.environ[token_env] = token
        else:
            raise Exception(f"Token '{token_name}' not found in '{token_env}' or '{token_file}'")
    return os.getenv(token_env, "<unset>")


def normalize_archive_permissions(archive: ZipFile) -> None:
    """
    Normalize a ZipFile with canonical unix permissions.
    Directories become 0o777 and files 0o644 (Or 0o755 if file is flagged as executable).
    If a file was flagged as executable it's

    :param archive: the ZipFile object to be normalized
    :return: None
    """
    for zinfo in archive.infolist():
        source_perm = (zinfo.external_attr >> 16) & 0o777
        if zinfo.is_dir():
            zinfo.external_attr = ((stat.S_IFDIR | 0o755) << 16) | 0x10
        else:
            perm = 0o755 if source_perm & 0o111 else 0o644
            zinfo.external_attr = (stat.S_IFREG | perm) << 16


def atomic_write_text(path: Path, data: str) -> None:
    temporary = path.with_name(f"{path.name}.tmp")
    try:
        with open(temporary, "w", encoding="utf-8") as file:
            file.write(data)
            file.flush()
            os.fsync(file.fileno())
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)
