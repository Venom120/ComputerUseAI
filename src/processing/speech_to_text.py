from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, Optional

import numpy as np
import soundfile as sf

import logging

logger = logging.getLogger(__name__)


@dataclass
class STTConfig:
    engine: str = "faster-whisper"
    model_path: Path = Path("base")  # This is now a model NAME, not a file
    sample_rate: int = 16000


class SpeechToText:
    def __init__(self, config: STTConfig) -> None:
        self.config = config
        self._init_engine()

    def _init_engine(self) -> None:
        self._engine = None

        # It's more reliable and handles its own model downloading/caching.
        if self.config.engine == "faster-whisper":
            try:
                from faster_whisper import WhisperModel  # type: ignore

                # Use config.model_path.as_posix() to pass the model *name* (e.g., "base")
                model_name = self.config.model_path.as_posix()
                self._engine = WhisperModel(model_name, device="cpu")
                logger.info(f"Initialized faster-whisper with model: {model_name}")
            except Exception as e:
                logger.error(f"Failed to init faster-whisper with model {self.config.model_path}: {e}")
        else:
            logger.error(f"Unsupported STT engine: {self.config.engine}. Only 'faster-whisper' is supported in this fix.")

    def transcribe_file(self, audio_path: str | Path) -> Dict[str, Any]:
        audio_path = Path(audio_path)
        if self._engine is None:
            return {"text": "", "confidence": 0.0, "timestamps": []}

        try:
            audio_data, read_sample_rate = sf.read(audio_path.as_posix(), dtype="float32")
            audio_data = np.array(audio_data, dtype=np.float32) # Explicitly ensure float32

            if read_sample_rate != self.config.sample_rate:
                # Resample if necessary (though whisper models usually expect 16kHz)
                # For simplicity, we'll assume the audio is already 16kHz or handle it externally
                logger.warning(
                    "Audio sample rate %d Hz does not match expected %d Hz. "
                    "This might lead to poor transcription quality.",
                    read_sample_rate,
                    self.config.sample_rate,
                )

            segments_generator, info = self._engine.transcribe(audio_data)
            
            segments_data = []
            segment_texts = []
            for s in segments_generator:
                segments_data.append({"start": s.start, "end": s.end, "text": s.text})
                segment_texts.append(s.text)
            
            full_text = " ".join(segment_texts).strip()
            
            return {"text": full_text, "confidence": getattr(info, "language_probability", 0.8), "timestamps": segments_data}
        except Exception as e:
            logger.exception("STT error: %s", e)
            return {"text": "", "confidence": 0.0, "timestamps": []}