from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, Optional

import logging

logger = logging.getLogger(__name__)


@dataclass
class STTConfig:
    engine: str = "whispercpp"
    model_path: Path = Path("models/whisper-base.bin")
    sample_rate: int = 16000


class SpeechToText:
    def __init__(self, config: STTConfig) -> None:
        self.config = config
        self._init_engine()

    def _init_engine(self) -> None:
        self._engine = None
        if self.config.engine == "whispercpp":
            try:
                from whispercpp import Whisper  # type: ignore

                self._engine = Whisper(self.config.model_path.as_posix())
                logger.info("Initialized Whisper.cpp with %s", self.config.model_path)
            except Exception as e:
                logger.warning("Failed to init whispercpp: %s", e)
        if self._engine is None:
            try:
                from faster_whisper import WhisperModel  # type: ignore

                self._engine = WhisperModel(self.config.model_path.as_posix(), device="cpu")
                logger.info("Initialized faster-whisper with %s", self.config.model_path)
                self.config.engine = "faster-whisper"
            except Exception as e:
                logger.error("No STT engine available: %s", e)

    def transcribe_file(self, audio_path: str | Path) -> Dict[str, Any]:
        audio_path = Path(audio_path)
        if self._engine is None:
            return {"text": "", "confidence": 0.0, "timestamps": []}

        try:
            if self.config.engine == "whispercpp":
                segments = []
                for (start, end, text) in self._engine.transcribe(audio_path.as_posix()):
                    segments.append({"start": start, "end": end, "text": text})
                full_text = " ".join(s["text"] for s in segments).strip()
                return {"text": full_text, "confidence": 0.8, "timestamps": segments}
            else:
                # faster-whisper
                segments_out, info = self._engine.transcribe(audio_path.as_posix())
                segments = [
                    {"start": s.start, "end": s.end, "text": s.text}
                    for s in segments_out
                ]
                full_text = " ".join(s["text"] for s in segments).strip()
                return {"text": full_text, "confidence": getattr(info, "language_probability", 0.8), "timestamps": segments}
        except Exception as e:
            logger.exception("STT error: %s", e)
            return {"text": "", "confidence": 0.0, "timestamps": []}


