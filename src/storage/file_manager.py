from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Optional

from loguru import logger


class FileManager:
    def __init__(self, encrypt: bool = False, key: Optional[bytes] = None) -> None:
        self.encrypt = encrypt
        self.key = key

    def store(self, src_path: str | Path, dest_dir: str | Path) -> Path:
        dest_dir = Path(dest_dir)
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = dest_dir / Path(src_path).name
        if self.encrypt:
            # Placeholder: copy as-is; replace with AES-256 if enabled
            shutil.copy2(src_path, dest_path)
        else:
            shutil.copy2(src_path, dest_path)
        logger.debug("Stored file {} -> {}", src_path, dest_path)
        return dest_path

    def delete(self, path: str | Path) -> None:
        try:
            Path(path).unlink(missing_ok=True)
        except Exception as e:
            logger.warning("Failed to delete {}: {}", path, e)

    def total_size(self, directory: str | Path) -> int:
        total = 0
        for root, _, files in os.walk(directory):
            for f in files:
                total += Path(root, f).stat().st_size
        return total


