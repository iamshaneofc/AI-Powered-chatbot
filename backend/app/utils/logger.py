"""
utils/logger.py — Centralised logging configuration.

Usage:
    from app.utils.logger import get_logger
    logger = get_logger(__name__)
    logger.info("Something happened")

Features:
  - Human-readable coloured output in development
  - ISO-8601 timestamps
  - Log level controlled by LOG_LEVEL env var (default: INFO)
"""

import logging
import os
import sys

_COLOURS = {
    "DEBUG":    "\033[36m",   # cyan
    "INFO":     "\033[32m",   # green
    "WARNING":  "\033[33m",   # yellow
    "ERROR":    "\033[31m",   # red
    "CRITICAL": "\033[35m",   # magenta
}
_RESET = "\033[0m"


class _ColouredFormatter(logging.Formatter):
    """Adds ANSI colour to the level-name when writing to a TTY."""

    def format(self, record: logging.LogRecord) -> str:
        colour = _COLOURS.get(record.levelname, "")
        if sys.stderr.isatty():
            record.levelname = f"{colour}{record.levelname:<8}{_RESET}"
        return super().format(record)


def get_logger(name: str) -> logging.Logger:
    """Return a module-level logger, configuring the root logger on first call."""
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()

    logger = logging.getLogger(name)

    # Only configure handlers once (on the root logger)
    root = logging.getLogger()
    if not root.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(
            _ColouredFormatter(
                fmt="%(asctime)s  %(levelname)s  %(name)s — %(message)s",
                datefmt="%Y-%m-%dT%H:%M:%S",
            )
        )
        root.addHandler(handler)
        root.setLevel(log_level)

    logger.setLevel(log_level)
    return logger
