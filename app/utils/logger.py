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

Additional highlights applied to every log line:
  • Logger name column   → colored by subsystem (third-party dimmed, own modules accented)
  • HTTP methods         → bright cyan  (GET POST PUT DELETE PATCH)
  • HTTP 2xx codes       → green
  • HTTP 4xx codes       → yellow
  • HTTP 5xx codes       → red
  • Agent / service tags → bright blue
"""

import logging
import re

from colorama import Fore, Style, init

init(autoreset=True, strip=False)

# ---------------------------------------------------------------------------
# Custom log level: USER — incoming user messages (between INFO=20 and WARNING=30)
# ---------------------------------------------------------------------------
USER_MSG = 25
logging.addLevelName(USER_MSG, "USER")

# ---------------------------------------------------------------------------
# Level → color
# ---------------------------------------------------------------------------
_LEVEL_STYLES: dict[int, str] = {
    logging.DEBUG:    Fore.CYAN,
    logging.INFO:     Fore.GREEN,
    USER_MSG:         Style.BRIGHT + Fore.MAGENTA,
    logging.WARNING:  Fore.YELLOW,
    logging.ERROR:    Fore.RED,
    logging.CRITICAL: Style.BRIGHT + Fore.RED,
}

# ---------------------------------------------------------------------------
# Logger-name → color  (prefix-matched, first match wins)
# ---------------------------------------------------------------------------
_NAME_STYLES: list[tuple[str, str]] = [
    # Third-party noise → dimmed so it doesn't compete with app logs
    ("httpx",             Style.DIM + Fore.WHITE),
    ("uvicorn",           Style.DIM + Fore.WHITE),
    ("telegram",          Style.DIM + Fore.WHITE),
    ("openai",            Style.DIM + Fore.WHITE),
    ("langsmith",         Style.DIM + Fore.WHITE),
    ("langchain",         Style.DIM + Fore.WHITE),
    # MCP servers
    ("finance_server",    Style.BRIGHT + Fore.BLUE),
    ("reminder_server",   Style.BRIGHT + Fore.BLUE),
    # Own subsystems
    ("app.agents",        Fore.BLUE),
    ("app.services",      Fore.CYAN),
    ("app.connectors",    Fore.CYAN),
    ("app.api",           Fore.WHITE),
    ("app.",              Fore.GREEN),
]

# ---------------------------------------------------------------------------
# Message body highlight rules  (applied in order, ANSI-safe)
# ---------------------------------------------------------------------------
_HTTP_METHOD   = re.compile(r'\b(GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS)\b')
_STATUS_2XX    = re.compile(r'\b(2\d\d)\b')
_STATUS_4XX    = re.compile(r'\b(4\d\d)\b')
_STATUS_5XX    = re.compile(r'\b(5\d\d)\b')
_AGENT_TAGS    = re.compile(
    r'\b(orchestrator|supervisor|finance_server|reminder_server'
    r'|TravelAgentOrchestrator|guardrail|RAG|rag)\b'
)

def _highlight_message(text: str) -> str:
    text = _HTTP_METHOD.sub(
        lambda m: f"{Style.BRIGHT}{Fore.CYAN}{m.group()}{Style.RESET_ALL}", text
    )
    text = _STATUS_2XX.sub(
        lambda m: f"{Fore.GREEN}{m.group()}{Style.RESET_ALL}", text
    )
    text = _STATUS_4XX.sub(
        lambda m: f"{Fore.YELLOW}{m.group()}{Style.RESET_ALL}", text
    )
    text = _STATUS_5XX.sub(
        lambda m: f"{Style.BRIGHT}{Fore.RED}{m.group()}{Style.RESET_ALL}", text
    )
    text = _AGENT_TAGS.sub(
        lambda m: f"{Style.BRIGHT}{Fore.BLUE}{m.group()}{Style.RESET_ALL}", text
    )
    return text


def _name_color(name: str) -> str:
    for prefix, color in _NAME_STYLES:
        if name.startswith(prefix):
            return color
    return ""


# ---------------------------------------------------------------------------
# Formatter
# ---------------------------------------------------------------------------
class ColoredFormatter(logging.Formatter):
    """Formatter that colors levels, logger names, and highlights message bodies."""

    def format(self, record: logging.LogRecord) -> str:
        # --- level name ---
        level_color = _LEVEL_STYLES.get(record.levelno, "")
        original_levelname = record.levelname
        record.levelname = f"{level_color}{Style.BRIGHT}{record.levelname}{Style.RESET_ALL}"

        # --- logger name ---
        name_color = _name_color(record.name)
        original_name = record.name
        if name_color:
            record.name = f"{name_color}{record.name}{Style.RESET_ALL}"

        formatted = super().format(record)

        # Restore originals (record objects are reused by the logging machinery)
        record.levelname = original_levelname
        record.name = original_name

        # --- message body highlights ---
        formatted = _highlight_message(formatted)

        # --- USER messages: paint the whole line ---
        if record.levelno == USER_MSG:
            formatted = f"{Style.BRIGHT}{Fore.MAGENTA}{formatted}{Style.RESET_ALL}"

        return formatted


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
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
    """Log an incoming user message at the USER level (bright magenta, full line)."""
    if logger.isEnabledFor(USER_MSG):
        logger.log(USER_MSG, message, *args, **kwargs)
