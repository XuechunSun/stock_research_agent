"""Logging setup; does not log secrets."""

from __future__ import annotations

import logging
import os


def get_logger(name: str) -> logging.Logger:
    """Return a module logger; level from LOG_LEVEL env (default INFO)."""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    level_name = os.environ.get("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    logger.setLevel(level)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
    logger.addHandler(handler)
    return logger
