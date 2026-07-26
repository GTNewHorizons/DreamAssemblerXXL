from gidgethub.httpx import GitHubAPI
from httpx import AsyncClient

from daxxl.gtnh_logger import get_logger
from daxxl.models.gtnh_modpack import GTNHModpack
from daxxl.services.asset_service import AssetService
from daxxl.services.comparison_service import ComparisonService
from daxxl.services.counter_service import CounterService
from daxxl.services.download_service import DownloadService
from daxxl.services.github_client import GitHubClient
from daxxl.services.modpack_persistence import ModpackPersistenceService
from daxxl.services.release_service import ReleaseService
from daxxl.services.update_orchestrator import AssetUpdateOrchestrator
from daxxl.services.update_service import UpdateService
from daxxl.utils import get_github_token

log = get_logger(__name__)


class AppContext:
    def __init__(self, client: AsyncClient) -> None:
        self.org = "GTNewHorizons"
        self.client = client
        self.gh = GitHubAPI(self.client, "DreamAssemblerXXL", oauth_token=get_github_token())
        self.gh_client = GitHubClient(self.client, self.org)
        self.persistence = ModpackPersistenceService()
        self.asset_service = AssetService(self.gh_client, self.gh, self.org)
        self.assets = self.asset_service.assets
        self.mod_pack: GTNHModpack = self.persistence.load()
        self.blacklisted_repos = self.asset_service.load_blacklisted_repos()
        self.counter = CounterService(self.assets, self.asset_service.save_assets)
        self.downloader = DownloadService(self.client, self.assets)
        self.release_service = ReleaseService(self.mod_pack)
        self.comparison = ComparisonService(self.assets)
        self.update_orchestrator = AssetUpdateOrchestrator(self.gh_client, self.asset_service, self.assets)
        self.update_service = UpdateService(
            self.assets,
            self.release_service,
            self.update_orchestrator.update_all,
            lambda: self.persistence.save(self.mod_pack),
        )
