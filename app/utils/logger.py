"""
Colored console logger for Amaya TFM.

Uses colorama — same pattern as the project's examen module.

Level → color mapping (traffic-light style):
  DEBUG    → cyan
  INFO     → green  (OK ✔)
  WARNING  → yellow (WARN ⚠)
  ERROR    → red    (ERR ✘)
  CRITICAL → bright magenta
"""

import logging

from colorama import Fore, Style, init

init(autoreset=True, strip=False)

_LEVEL_STYLES: dict[int, str] = {
    logging.DEBUG:    Fore.CYAN,
    logging.INFO:     Fore.GREEN,
    logging.WARNING:  Fore.YELLOW,
    logging.ERROR:    Fore.RED,
    logging.CRITICAL: Style.BRIGHT + Fore.MAGENTA,
}


class ColoredFormatter(logging.Formatter):
    """Formatter that colors the level name using colorama."""

    def format(self, record: logging.LogRecord) -> str:
        color = _LEVEL_STYLES.get(record.levelno, "")
        original_levelname = record.levelname
        record.levelname = f"{color}{Style.BRIGHT}{record.levelname}{Style.RESET_ALL}"
        formatted = super().format(record)
        record.levelname = original_levelname
        return formatted


def setup_logging(level: int = logging.INFO) -> None:
    """
    Configure the root logger with a colored console handler.

    Call this once at process startup (replaces logging.basicConfig).
    Subsequent calls are no-ops if the root logger already has handlers.
    """
    root = logging.getLogger()
    if root.handlers:
        return

    handler = logging.StreamHandler()
    handler.setFormatter(
        ColoredFormatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    root.setLevel(level)
    root.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    """Return a named logger. Always call setup_logging() first."""
    return logging.getLogger(name)
