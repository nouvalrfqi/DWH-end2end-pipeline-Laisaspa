"""Logging helpers: console output + per-batch JSON metadata file."""

import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import List

LOGS_DIR = Path("logs")


def setup_logger(name: str = "extract") -> logging.Logger:
    """Return a console logger (single handler, no duplicates)."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s | %(levelname)-5s | %(message)s",
                "%Y-%m-%d %H:%M:%S",
            )
        )
        logger.addHandler(handler)
    return logger


def write_batch_metadata(batch_id: str, records: List[dict]) -> Path:
    """Write per-batch metadata JSON to logs/extract_log_<batch>.json."""
    LOGS_DIR.mkdir(exist_ok=True)
    path = LOGS_DIR / f"extract_log_{batch_id}.json"
    payload = {
        "batch_id": batch_id,
        "generated_at": datetime.now().isoformat(),
        "tables": records,
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    return path

