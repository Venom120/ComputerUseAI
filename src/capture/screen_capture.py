from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

import mss
import numpy as np
from PIL import Image
from loguru import logger

from src.utils import ensure_dirs


@dataclass
class ScreenCaptureConfig:
    fps: int = 3
    quality: int = 75
    change_threshold: float = 0.1
    resolution_cap: int = 1080
    format: str = "webp"


class ScreenCapture:
    def __init__(self, output_dir: str | Path, config: ScreenCaptureConfig) -> None:
        self.output_dir = Path(output_dir)
        self.config = config
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._previous_frame: Optional[np.ndarray] = None
        self._mss = mss.mss()
        self._running = False

    def _resize_if_needed(self, frame: np.ndarray) -> np.ndarray:
        h, w = frame.shape[:2]
        cap = self.config.resolution_cap
        if max(h, w) <= cap:
            return frame
        if h >= w:
            new_h = cap
            new_w = int(w * (cap / h))
        else:
            new_w = cap
            new_h = int(h * (cap / w))
        img = Image.fromarray(frame)
        img = img.resize((new_w, new_h), Image.Resampling.BILINEAR)
        return np.asarray(img)

    def _grab(self) -> np.ndarray:
        monitor = self._mss.monitors[0]  # full virtual screen
        sct_img = self._mss.grab(monitor)
        frame = np.array(sct_img)
        frame = frame[:, :, :3]  # drop alpha
        return self._resize_if_needed(frame)

    def _frame_difference_ratio(self, a: np.ndarray, b: np.ndarray) -> float:
        if a.shape != b.shape:
            return 1.0
        diff = np.mean(np.abs(a.astype(np.int16) - b.astype(np.int16))) / 255.0
        return float(diff)

    def _should_save(self, frame: np.ndarray) -> bool:
        if self._previous_frame is None:
            return True
        ratio = self._frame_difference_ratio(frame, self._previous_frame)
        return ratio >= self.config.change_threshold

    def _save_frame(self, frame: np.ndarray, timestamp: float) -> Path:
        ts = time.strftime("%Y%m%d_%H%M%S", time.localtime(timestamp))
        ms = int((timestamp - int(timestamp)) * 1000)
        path = self.output_dir / f"screen_{ts}_{ms:03d}.{self.config.format}"
        img = Image.fromarray(frame)
        img.save(path, format=self.config.format.upper(), quality=self.config.quality)
        return path

    def start(self) -> None:
        self._running = True
        ensure_dirs(self.output_dir)
        interval = 1.0 / max(1, self.config.fps)
        logger.info("Screen capture started at {} FPS", self.config.fps)
        try:
            while self._running:
                t0 = time.time()
                frame = self._grab()
                if self._should_save(frame):
                    path = self._save_frame(frame, t0)
                    logger.debug("Saved frame {}", path.name)
                    self._previous_frame = frame
                elapsed = time.time() - t0
                delay = max(0.0, interval - elapsed)
                if delay:
                    time.sleep(delay)
        except Exception as e:
            logger.exception("Screen capture error: {}", e)
        finally:
            logger.info("Screen capture stopped")
            self._running = False

    def stop(self) -> None:
        self._running = False


