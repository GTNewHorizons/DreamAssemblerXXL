class LatestReleaseNotFound(Exception):
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


class InvalidConfigException(Exception):
    pass


class InvalidModVersionException(Exception):
    pass


class ReleaseNotFoundException(Exception):
    pass


class InvalidExperimentalIdException(Exception):
    pass


class InvalidDailyIdException(Exception):
    pass


class SideAlreadySetException(Exception):
    pass
