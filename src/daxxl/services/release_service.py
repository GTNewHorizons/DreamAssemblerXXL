from colorama import Fore

from daxxl.defs import RELEASE_MANIFEST_DIR
from daxxl.gtnh_logger import get_logger
from daxxl.models.gtnh_modpack import GTNHModpack
from daxxl.models.gtnh_release import GTNHRelease, load_release, save_release

log = get_logger(__name__)


class ReleaseService:
    def __init__(self, mod_pack: GTNHModpack) -> None:
        self.mod_pack = mod_pack

    def add_release(self, release: GTNHRelease, update: bool = False) -> bool:
        log.info(f"Adding Release `{Fore.GREEN}{release.version}{Fore.RESET}`")
        if not update and release.version in self.mod_pack.releases:
            log.error(f"Release `{Fore.RED}{release.version}{Fore.RESET} already exists, and update was not specified!")
            return False
        self.mod_pack.releases.add(release.version)
        return save_release(release, update=update)

    def get_release(self, release_name: str) -> GTNHRelease | None:
        if release_name in self.mod_pack.releases:
            return load_release(release_name)
        return None

    def delete_release(self, release_name: str) -> None:
        """
        Delete a release's manifest and drop it from the modpack.

        The name is dropped whether or not the manifest could be read, so a corrupt or already
        deleted manifest doesn't leave behind an entry that can never be removed.

        :param release_name: name of the release to delete
        :return: None
        """
        (RELEASE_MANIFEST_DIR / f"{release_name}.json").unlink(missing_ok=True)
        self.mod_pack.releases.discard(release_name)
        log.info(f"Deleted Release `{Fore.GREEN}{release_name}{Fore.RESET}`")
