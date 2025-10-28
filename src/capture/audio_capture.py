# src/capture/audio_capture.py (Updated stop method and start loop)

from __future__ import annotations

import queue
import struct
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional # Import Union

import numpy as np
import sounddevice as sd
import soundfile as sf
from PyQt6.QtCore import QObject, pyqtSignal

import logging

logger = logging.getLogger(__name__)
from src.utils import ensure_dirs


@dataclass
class AudioCaptureConfig:
    sample_rate: int = 16000
    channels: int = 1
    segment_seconds: int = 30
    use_vad: bool = True
    device: Optional[int] = None


class AudioCapture(QObject):

    audio_file_ready = pyqtSignal(str)

    def __init__(self, output_dir: str | Path, config: AudioCaptureConfig) -> None:
        super().__init__()
        self.output_dir = Path(output_dir)
        self.config = config
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._q: queue.Queue[Optional[np.ndarray]] = queue.Queue() # Allow None
        self._stream: Optional[sd.InputStream] = None
        self._running = False
        self._vad = None

    def _callback(self, indata, frames, time_info, status):
        logger.debug(f"Audio callback called. Status: {status}, Frames: {frames}")
        if status:
            logger.warning("Audio status: %s", status)
        self._q.put(indata.copy())

    def start(self) -> None:
        logger.debug("AudioCapture.start() called.")
        ensure_dirs(self.output_dir)
        self._running = True # Set flag before starting stream
        try:
            logger.debug("Initializing sd.InputStream...")
            self._stream = sd.InputStream(
                channels=self.config.channels,
                samplerate=self.config.sample_rate,
                callback=self._callback,
                device=self.config.device
            )
            logger.debug("sd.InputStream initialized.")
            logger.debug("Starting audio stream...") # Add log before stream start
            self._stream.start()
            logger.info("Audio stream started @ %d Hz", self.config.sample_rate)
        except Exception as e:
             logger.exception(f"Failed to initialize or start audio stream: {e}")
             self._running = False
             return

        segment = []
        samples_per_segment = self.config.segment_seconds * self.config.sample_rate

        try:
            while True: # Loop indefinitely until explicitly broken
                try:
                     # Use a shorter timeout to check self._running more often
                     chunk = self._q.get(timeout=0.5)
                except queue.Empty:
                     # If queue times out, check if we should stop, otherwise continue
                     if not self._running:
                          logger.debug("Audio loop: self._running is False after queue timeout. Breaking loop.")
                          break
                     logger.debug("Audio queue timed out (no data received in 0.5s). Continuing loop.")
                     continue # Continue to next iteration

                if chunk is None:
                    logger.debug("Audio loop: Received None sentinel. Breaking loop.")
                    break # Exit loop if None is received

                if not self._running:
                     logger.debug("Audio loop: self._running is False after getting queue item. Breaking loop.")
                     break

                logger.debug(f"Audio loop got chunk of size {chunk.shape}")
                segment.append(chunk)
                buf = np.concatenate(segment, axis=0)

                if self._vad is not None:
                    if not self._contains_voice(chunk):
                        continue

                if len(buf) >= samples_per_segment:
                    ts = time.strftime("%Y%m%d_%H%M%S")
                    path = self.output_dir / f"audio_{ts}.wav"
                    try:
                        sf.write(path, buf, self.config.sample_rate, subtype="PCM_16")
                        logger.info("Saved audio segment %s", path.name)
                        self.audio_file_ready.emit(str(path))
                    except Exception as write_e:
                        logger.exception(f"Failed to write audio segment {path.name}: {write_e}")
                    segment = [] # Reset segment

        except Exception as e:
            logger.exception("Audio capture loop error: %s", e)
        finally:
            # Ensure stream is stopped regardless of how loop exits
            if self._stream is not None and self._stream.active:
                try:
                    logger.debug("Stopping/closing audio stream in finally block...") # Add log
                    self._stream.stop()
                    self._stream.close()
                    logger.info("Audio stream stopped in finally block.")
                except Exception as stop_e:
                    logger.error(f"Error stopping audio stream in finally block: {stop_e}")
            self._stream = None # Reset stream reference

            logger.info("Audio capture loop finished.")

    def _contains_voice(self, chunk: np.ndarray) -> bool:
        if self._vad is None:
            return True
        # VAD expects 16-bit mono PCM, 10/20/30ms frames
        frame_ms = 30
        samples_per_frame = int(self.config.sample_rate * frame_ms / 1000)
        mono = chunk[:, 0] if chunk.ndim > 1 else chunk
        mono = (mono * 32767).astype(np.int16)
        for i in range(0, len(mono) - samples_per_frame, samples_per_frame):
            frame = mono[i : i + samples_per_frame]
            if self._vad.is_speech(frame.tobytes(), self.config.sample_rate):
                return True
        return False

    def stop(self) -> None:
        logger.debug("AudioCapture.stop() called.")
        self._running = False
        try:
             # Put None sentinel to wake up the thread if blocked on _q.get()
             self._q.put(None, timeout=0.1) # Use small timeout
             logger.debug("Put None sentinel into audio queue.")
        except queue.Full:
             logger.warning("Audio queue was full when trying to add None sentinel.")
