from pathlib import Path

from daxxl.defs import GTNH_MODPACK_FILE, ROOT_DIR
from daxxl.gtnh_logger import get_logger
from daxxl.models.gtnh_modpack import GTNHModpack
from daxxl.utils import atomic_write_text

log = get_logger(__name__)


class ModpackPersistenceService:
    def __init__(self) -> None:
        self.manifest_path: Path = ROOT_DIR / GTNH_MODPACK_FILE

    def load(self) -> GTNHModpack:
        log.debug(f"Loading GTNH Modpack from {self.manifest_path}")
        with open(self.manifest_path, encoding="utf-8") as f:
            return GTNHModpack.parse_raw(f.read())

    def save(self, mod_pack: GTNHModpack) -> None:
        log.debug(f"Saving modpack asset to {self.manifest_path}")
        dumped = mod_pack.json(by_alias=True, exclude_unset=True, exclude_none=True, exclude_defaults=True)
        if dumped:
            atomic_write_text(self.manifest_path, dumped)
        else:
            log.error("Save aborted, empty save result")
