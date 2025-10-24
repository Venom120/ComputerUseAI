from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

import mss
import numpy as np
from PIL import Image
import logging
import cv2  # Import OpenCV
from PyQt6.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)

from src.utils import ensure_dirs


@dataclass
class ScreenCaptureConfig:
    fps: int = 3
    quality: int = 70
    change_threshold: float = 0.1
    resolution_cap: int = 1080
    format: str = "webp"
    monitor: int = 0
    capture_mode: str = "images"  # "images" or "video"
    video_segment_sec: int = 60
    video_codec: str = "mp4v"


class ScreenCapture(QObject):

    video_file_ready = pyqtSignal(str)

    def __init__(self, output_dir: str | Path, config: ScreenCaptureConfig) -> None:
        super().__init__()
        self.output_dir = Path(output_dir)
        self.config = config
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._previous_frame: Optional[np.ndarray] = None
        self._mss = mss.mss()
        self._running = False
        self._video_writer: Optional[cv2.VideoWriter] = None
        self._segment_start_time: float = 0.0
        self._current_video_path: Optional[Path] = None

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
        
        # Use cv2.resize for numpy arrays
        return cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

    def _grab(self) -> np.ndarray:
        monitor_index = self.config.monitor
        if monitor_index < 0 or monitor_index >= len(self._mss.monitors):
            logger.warning("Invalid monitor index %d, falling back to all screens (0)", monitor_index)
            monitor_index = 0
            
        monitor = self._mss.monitors[monitor_index]
        sct_img = self._mss.grab(monitor)
        frame = np.array(sct_img)
        frame = frame[:, :, :3]  # drop alpha
        frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR) # Convert to BGR for OpenCV
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
        
        # Save with cv2
        img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        img.save(path, format=self.config.format.upper(), quality=self.config.quality)
        return path

    def _start_video_segment(self, frame: np.ndarray) -> None:
        ts = time.strftime("%Y%m%d_%H%M%S", time.localtime())
        self._current_video_path = self.output_dir / f"video_{ts}.mp4"
        fourcc = cv2.VideoWriter.fourcc(*self.config.video_codec)
        h, w = frame.shape[:2]
        self._video_writer = cv2.VideoWriter(
            str(self._current_video_path), fourcc, self.config.fps, (w, h)
        )
        self._segment_start_time = time.time()
        logger.info("Starting new video segment: %s", self._current_video_path.name)

    def _stop_video_segment(self) -> None:
        if self._video_writer:
            self._video_writer.release()
            self._video_writer = None
            logger.info("Completed video segment: %s", self._current_video_path)
            
            # --- PROCESSING HOOK ---
            # This is where you would trigger processing and deletion
            if self._current_video_path:
                logger.debug("Calling process_and_delete_video for %s", self._current_video_path)
                self.process_and_delete_video(self._current_video_path)
            else:
                logger.warning("Attempted to stop video segment but _current_video_path was None.")
            
            self._current_video_path = None

    def process_and_delete_video(self, video_path: Path):
        """
        This hook is called when a video segment is finished.
        Instead of processing, it emits a signal for the pipeline.
        The pipeline will be responsible for deletion.
        """
        logger.info(f"Screen capture finished segment: {video_path}")
        self.video_file_ready.emit(str(video_path))
        
        # NOTE: We REMOVE the deletion logic from here.
        # The processing pipeline will delete the file.


    def start(self) -> None:
        self._running = True
        ensure_dirs(self.output_dir)
        interval = 1.0 / max(1, self.config.fps)
        logger.info("Screen capture started at %d FPS", self.config.fps)
        
        try:
            while self._running:
                t0 = time.time()
                frame = self._grab()

                if self.config.capture_mode == "video":
                    if self._video_writer is None:
                        self._start_video_segment(frame)
                    
                    if self._video_writer:
                        self._video_writer.write(frame)
                    else:
                        logger.warning("Attempted to write frame but video writer was not initialized.")
                    
                    if time.time() - self._segment_start_time >= self.config.video_segment_sec:
                        self._stop_video_segment()

                else: # "images" mode (original logic)
                    if self._should_save(frame):
                        path = self._save_frame(frame, t0)
                        logger.debug("Saved frame %s", path.name)
                        self._previous_frame = frame
                
                elapsed = time.time() - t0
                delay = max(0.0, interval - elapsed)
                if delay:
                    time.sleep(delay)
                    
        except Exception as e:
            logger.exception("Screen capture error: %s", e)
        finally:
            if self._video_writer:
                self._stop_video_segment() # Save final segment
            logger.info("Screen capture stopped")
            self._running = False

    def stop(self) -> None:
        self._running = False