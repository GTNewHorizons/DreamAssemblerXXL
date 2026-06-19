import logging
import os
import typing

import structlog


def get_logger(name: str) -> structlog.BoundLogger:
    if not structlog.is_configured():
        LOG_LEVEL = getattr(logging, os.environ.get("LOG_LEVEL", "INFO").upper())
        structlog.configure(wrapper_class=structlog.make_filtering_bound_logger(LOG_LEVEL))
    return typing.cast(structlog.BoundLogger, structlog.get_logger(name))
