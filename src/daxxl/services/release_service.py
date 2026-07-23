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
        release = self.get_release(release_name)
        if release:
            manifest_path = RELEASE_MANIFEST_DIR / (release.version + ".json")
            manifest_path.unlink(missing_ok=True)  # file deletion
            self.mod_pack.releases.remove(release_name)
