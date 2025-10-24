from __future__ import annotations

import logging
from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot

from .speech_to_text import SpeechToText, STTConfig
from .ocr_engine import OCREngine, OCRConfig
from .screen_analyzer import ScreenAnalyzer, ScreenAnalyzerConfig
from ..intelligence.llm_interface import LocalLLM, LLMConfig
from ..storage.database import initialize_database

logger = logging.getLogger(__name__)

class ProcessingPipeline(QObject):
    """
    Orchestrates the processing of captured data.
    Listens for signals from capture threads and processes files.
    """
    
    # Signal to update the UI with a new workflow
    workflow_detected = pyqtSignal(dict)
    
    def __init__(self, settings: dict):
        super().__init__()
        self.settings = settings
        
        # Initialize all processing components
        self.stt = SpeechToText(STTConfig(
            model_path=Path(settings.get("stt", {}).get("model_path", "models/whisper-base.bin"))
        ))
        
        self.ocr = OCREngine(OCRConfig(
            language=settings.get("ocr", {}).get("language", "eng")
        ))
        
        self.screen_analyzer = ScreenAnalyzer(ScreenAnalyzerConfig())
        
        self.llm = LocalLLM(LLMConfig(
            model_path=Path(settings.get("llm", {}).get("model_path", "models/phi-3-mini-4k-instruct-q4.gguf"))
        ))
        
        # TODO: Initialize database connection
        # db_path = settings.get("storage", {}).get("database_path", "data/app.db")
        # self.session_factory = initialize_database(db_path)

        logger.info("ProcessingPipeline initialized")

    @pyqtSlot(str)
    def process_audio(self, file_path_str: str):
        """Slot to process a new audio file."""
        logger.info(f"Pipeline processing audio: {file_path_str}")
        try:
            file_path = Path(file_path_str)
            if file_path.exists():
                # 1. Transcribe
                transcription = self.stt.transcribe_file(file_path)
                logger.info(f"Transcription: {transcription['text']}")
                
                # TODO: 2. Save transcription to database
                # session = self.session_factory()
                # ... save logic ...
                # session.close()

                # 3. Delete file after processing
                file_path.unlink()
            else:
                logger.warning(f"Audio file not found: {file_path_str}")
        except Exception as e:
            logger.exception(f"Failed to process audio file {file_path_str}: {e}")

    @pyqtSlot(str)
    def process_video(self, file_path_str: str):
        """Slot to process a new video segment."""
        logger.info(f"Pipeline processing video: {file_path_str}")
        try:
            file_path = Path(file_path_str)
            if file_path.exists():
                # 1. TODO: Extract frames and run OCR
                # This is complex. For now, we'll just log it.
                # In a real implementation, you'd use OpenCV to read the video,
                # extract keyframes, save them as images, run self.ocr.extract()
                # on them, and then delete the images.
                logger.info("TODO: Implement video frame extraction and OCR")
                
                # TODO: 2. Run analysis (this is a placeholder)
                # self.run_analysis()
                
                # 3. Delete file after processing
                file_path.unlink()
            else:
                logger.warning(f"Video file not found: {file_path_str}")
        except Exception as e:
            logger.exception(f"Failed to process video file {file_path_str}: {e}")
            
    def run_analysis(self):
        """
        Periodically run analysis on recent data.
        This would collect recent screens, audio, and events
        and send them to the LLM.
        """
        logger.info("Running periodic analysis...")
        
        # TODO:
        # 1. Query DB for recent screen_jsons, transcripts, and events
        # 2. Send to LLM
        #    workflow = self.llm.analyze_workflow(screens, audio, events)
        # 3. If repetitive, save workflow to DB and emit signal
        #    if workflow.get("is_repetitive"):
        #        self.workflow_detected.emit(workflow)
        pass