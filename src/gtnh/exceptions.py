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


class MissingModFileException(Exception):
    pass


class InvalidReleaseException(Exception):
    pass


class ReleaseNotFoundException(Exception):
    pass


class InvalidNightlyIdException(Exception):
    pass


class InvalidDailyIdException(Exception):
    pass
