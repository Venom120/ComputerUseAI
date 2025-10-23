from __future__ import annotations

import queue
import struct
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np
import sounddevice as sd
import soundfile as sf

# webrtcvad = None  # Disabled due to build requirements

from loguru import logger
from src.utils import ensure_dirs


@dataclass
class AudioCaptureConfig:
    sample_rate: int = 16000
    channels: int = 1
    segment_seconds: int = 30
    use_vad: bool = True


class AudioCapture:
    def __init__(self, output_dir: str | Path, config: AudioCaptureConfig) -> None:
        self.output_dir = Path(output_dir)
        self.config = config
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._q: "queue.Queue[np.ndarray]" = queue.Queue()
        self._stream: Optional[sd.InputStream] = None
        self._running = False
        self._vad = None  # VAD disabled due to build requirements

    def _callback(self, indata, frames, time_info, status):  # sd callback signature
        if status:
            logger.debug("Audio status: {}", status)
        self._q.put(indata.copy())

    def start(self) -> None:
        ensure_dirs(self.output_dir)
        self._running = True
        self._stream = sd.InputStream(
            channels=self.config.channels,
            samplerate=self.config.sample_rate,
            callback=self._callback,
        )
        self._stream.start()
        logger.info("Audio capture started @ {} Hz", self.config.sample_rate)

        segment = []
        samples_per_segment = self.config.segment_seconds * self.config.sample_rate

        try:
            while self._running:
                chunk = self._q.get(timeout=1.0)
                segment.append(chunk)
                buf = np.concatenate(segment, axis=0)

                if self._vad is not None:
                    if not self._contains_voice(chunk):
                        continue

                if len(buf) >= samples_per_segment:
                    ts = time.strftime("%Y%m%d_%H%M%S")
                    path = self.output_dir / f"audio_{ts}.wav"
                    sf.write(path, buf, self.config.sample_rate, subtype="PCM_16")
                    logger.debug("Saved audio segment {}", path.name)
                    segment = []
        except queue.Empty:
            pass
        except Exception as e:
            logger.exception("Audio capture error: {}", e)
        finally:
            self.stop()
            logger.info("Audio capture stopped")

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
        self._running = False
        try:
            if self._stream is not None:
                self._stream.stop()
                self._stream.close()
        finally:
            self._stream = None


