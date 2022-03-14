class LatestReleaseNotFound(Exception):
    pass


class NoReleasesException(Exception):
    pass


class RepoNotFoundException(Exception):
    pass


class ModAlreadyExistsException(Exception):
    pass


class NoModAssetFound(Exception):
    pass


class PackingInterruptException(Exception):
    pass
