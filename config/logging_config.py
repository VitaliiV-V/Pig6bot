"""Shared logging setup: never emit Telegram bot tokens or configured API secrets."""

import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import re
import sys
from urllib.parse import quote


_TOKEN_PATTERN = re.compile(r"\d{5,}(?::|%3[aA])[A-Za-z0-9_-]{20,}")
_SECRET_NAMES = (
    "TOKEN", "JUDGMENT_DAY_TOKEN", "LOGS_TOKEN", "AI_TOKEN",
    "GEMINI_API_KEY",
)
_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
_installed = False


def redact_secrets(text):
    text = str(text)
    # Read the environment at emission time: dotenv may load after logging setup.
    for name in _SECRET_NAMES:
        secret = os.environ.get(name)
        if secret:
            text = text.replace(secret, "[REDACTED]")
            text = text.replace(quote(secret, safe=""), "[REDACTED]")
    return _TOKEN_PATTERN.sub("[REDACTED]", text)


def _redact_value(value):
    if isinstance(value, str):
        return redact_secrets(value)
    if isinstance(value, tuple):
        return tuple(_redact_value(item) for item in value)
    if isinstance(value, list):
        return [_redact_value(item) for item in value]
    if isinstance(value, dict):
        return {key: _redact_value(item) for key, item in value.items()}
    # Preserve numbers and other objects unless their string form contains a secret.
    text = str(value)
    redacted = redact_secrets(text)
    return redacted if redacted != text else value


def configure_logging(log_file=None):
    global _installed
    if not _installed:
        previous_factory = logging.getLogRecordFactory()

        def safe_record_factory(*args, **kwargs):
            record = previous_factory(*args, **kwargs)
            record.msg = _redact_value(record.msg)
            # Keep the argument tuple intact for Uvicorn's access formatter.
            record.args = _redact_value(record.args)
            if record.exc_info:
                record.exc_text = redact_secrets(
                    logging.Formatter().formatException(record.exc_info)
                )
            if record.stack_info:
                record.stack_info = redact_secrets(record.stack_info)
            return record

        logging.setLogRecordFactory(safe_record_factory)

        def safe_excepthook(exc_type, exc, traceback):
            logging.getLogger("uncaught").critical(
                "Unhandled exception", exc_info=(exc_type, exc, traceback)
            )

        # Supervisor captures stderr too, including otherwise unfiltered crashes.
        sys.excepthook = safe_excepthook
        _installed = True

    logging.basicConfig(level=logging.INFO, format=_FORMAT)
    # Request URLs contain bot credentials; suppress verbose HTTP/Telegram traces.
    for name in ("httpx", "httpcore", "telegram"):
        logging.getLogger(name).setLevel(logging.WARNING)

    if log_file:
        path = Path(log_file).resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        root = logging.getLogger()
        if not any(
            isinstance(handler, logging.FileHandler) and handler.baseFilename == str(path)
            for handler in root.handlers
        ):
            handler = RotatingFileHandler(
                path, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
            )
            handler.setLevel(logging.INFO)
            handler.setFormatter(logging.Formatter(_FORMAT))
            root.addHandler(handler)
