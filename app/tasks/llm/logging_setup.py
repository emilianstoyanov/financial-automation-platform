"""Dedicated file logging for the LLM extraction task."""

import logging
from pathlib import Path
from logging.handlers import RotatingFileHandler
from app.tasks.llm.constants import DEFAULT_LLM_LOG

_CONFIGURED = False


def setup_llm_logging(log_file: str = DEFAULT_LLM_LOG) -> logging.Logger:
    """Configure ``logs/llm.log`` and return the LLM task logger."""
    global _CONFIGURED

    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("app.tasks.llm")
    logger.setLevel(logging.INFO)

    if not _CONFIGURED:
        handler = RotatingFileHandler(
            log_path,
            maxBytes=5 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8",
        )
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        logger.addHandler(handler)
        _CONFIGURED = True

    return logger
