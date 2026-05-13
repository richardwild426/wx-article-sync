from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


LOGGER_NAME = "wx_article_sync"
LOG_FILE_MAX_BYTES = 2 * 1024 * 1024
DEFAULT_LOG_PATH = Path("logs/wx-article-sync.log")
LOG_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"


logging.getLogger(LOGGER_NAME).addHandler(logging.NullHandler())


def get_logger(name: str | None = None) -> logging.Logger:
    if not name:
        return logging.getLogger(LOGGER_NAME)
    return logging.getLogger(f"{LOGGER_NAME}.{name}")


def configure_logging(level: str, *, log_path: str | Path = DEFAULT_LOG_PATH) -> None:
    resolved_log_path = Path(log_path).expanduser()
    resolved_log_path.parent.mkdir(parents=True, exist_ok=True)
    formatter = logging.Formatter(LOG_FORMAT)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    file_handler = RotatingFileHandler(
        resolved_log_path,
        maxBytes=LOG_FILE_MAX_BYTES,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    logging.basicConfig(
        level=getattr(logging, level),
        handlers=[console_handler, file_handler],
        force=True,
    )


def redact_url(url: str) -> str:
    parts = urlsplit(url)
    redacted_query = []
    for key, value in parse_qsl(parts.query, keep_blank_values=True):
        if key.lower() in {"url"}:
            redacted_query.append((key, _redact_value(value)))
        else:
            redacted_query.append((key, value))
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(redacted_query), parts.fragment))


def _redact_value(value: str) -> str:
    if len(value) <= 16:
        return "<redacted>"
    return f"{value[:12]}...{value[-6:]}"
