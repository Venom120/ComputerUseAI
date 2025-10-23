from __future__ import annotations

import time
from pathlib import Path
from typing import Iterable

import logging

logger = logging.getLogger(__name__)


def cleanup_old_files(directories: Iterable[str | Path], max_age_days: int) -> int:
    now = time.time()
    cutoff = now - max_age_days * 86400
    removed = 0
    for d in directories:
        for p in Path(d).glob("**/*"):
            if p.is_file() and p.stat().st_mtime < cutoff:
                try:
                    p.unlink()
                    removed += 1
                except Exception as e:
                    logger.debug("Failed to remove %s: %s", p, e)
    return removed


def cleanup_size_limit(directory: str | Path, max_bytes: int) -> int:
    files = sorted(
        [p for p in Path(directory).glob("**/*") if p.is_file()],
        key=lambda p: p.stat().st_mtime,
    )
    total = sum(p.stat().st_size for p in files)
    removed = 0
    while total > max_bytes and files:
        p = files.pop(0)
        sz = p.stat().st_size
        try:
            p.unlink()
            total -= sz
            removed += 1
        except Exception as e:
            logger.debug("Failed to remove %s: %s", p, e)
    return removed


