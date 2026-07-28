"""
Colored console logger for Amaya TFM.

Uses colorama — same pattern as the project's examen module.

Level → color mapping (traffic-light style):
  DEBUG    → cyan
  INFO     → green  (OK ✔)
  USER     → bright magenta / lilac  (incoming user message)
  WARNING  → yellow (WARN ⚠)
  ERROR    → red    (ERR ✘)
  CRITICAL → bright red
"""

import logging

from colorama import Fore, Style, init

init(autoreset=True, strip=False)

# Custom level for incoming user messages (between INFO=20 and WARNING=30)
USER_MSG = 25
logging.addLevelName(USER_MSG, "USER")

_LEVEL_STYLES: dict[int, str] = {
    logging.DEBUG: Fore.CYAN,
    logging.INFO:  Fore.GREEN,
    USER_MSG:      Style.BRIGHT + Fore.MAGENTA,
    logging.WARNING:  Fore.YELLOW,
    logging.ERROR:    Fore.RED,
    logging.CRITICAL: Style.BRIGHT + Fore.RED,
}


class ColoredFormatter(logging.Formatter):
    """Formatter that colors the level name and the full line for USER messages."""

    def format(self, record: logging.LogRecord) -> str:
        color = _LEVEL_STYLES.get(record.levelno, "")
        original_levelname = record.levelname
        record.levelname = f"{color}{Style.BRIGHT}{record.levelname}{Style.RESET_ALL}"
        formatted = super().format(record)
        record.levelname = original_levelname

        # For USER messages, paint the entire line so it stands out at a glance
        if record.levelno == USER_MSG:
            formatted = f"{Style.BRIGHT}{Fore.MAGENTA}{formatted}{Style.RESET_ALL}"

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


def log_user_message(logger: logging.Logger, message: str, *args, **kwargs) -> None:
    """Log an incoming user message at the USER level (bright magenta)."""
    if logger.isEnabledFor(USER_MSG):
        logger.log(USER_MSG, message, *args, **kwargs)
