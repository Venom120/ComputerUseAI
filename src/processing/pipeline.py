from __future__ import annotations

import logging
from pathlib import Path
import cv2
import numpy as np

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot, QTimer

from .speech_to_text import SpeechToText, STTConfig
from .ocr_engine import OCREngine, OCRConfig
from .screen_analyzer import ScreenAnalyzer, ScreenAnalyzerConfig
from datetime import datetime

from ..intelligence.llm_interface import LocalLLM, LLMConfig
from ..storage.database import initialize_database, Capture, Workflow

logger = logging.getLogger(__name__)

class ProcessingPipeline(QObject):
    """
    Orchestrates the processing of captured data.
    Listens for signals from capture threads and processes files.
    """
    
    # Signal to update the UI with a new workflow
    workflow_detected = pyqtSignal(dict)
    
    # Accept project_root in the constructor
    def __init__(self, settings: dict, project_root: Path):
        super().__init__()
        self.settings = settings
        self.project_root = project_root  # Store the root path
        
        # Initialize all processing components
        
        # Correctly read the STT model *name* (e.g., "base") from settings.
        stt_model_name = settings.get("stt", {}).get("model", "base")
        self.stt = SpeechToText(STTConfig(
            model_path=Path(stt_model_name)
        ))
        
        self.ocr = OCREngine(OCRConfig(
            language=settings.get("ocr", {}).get("language", "eng")
        ))
        
        self.screen_analyzer = ScreenAnalyzer(ScreenAnalyzerConfig())
        
        # Get the LLM model *name* from settings
        llm_model_name = settings.get("llm", {}).get("model", "phi-3-mini-4k-instruct-q4.gguf")
        # Always look for the LLM model inside the 'models' directory
        # using the absolute project_root path
        llm_model_path = self.project_root / "models" / llm_model_name 
        self.llm = LocalLLM(LLMConfig(
            model_path=llm_model_path
        ))
        
        db_path = self.project_root / settings.get("storage", {}).get("database_path", "data/app.db")
        self.session_factory = initialize_database(db_path)

        # Initialize a timer for periodic analysis
        self.analysis_timer = QTimer(self)
        self.analysis_timer.timeout.connect(self.run_analysis)
        
        logger.info("ProcessingPipeline initialized")

    def start(self):
        """Starts the periodic analysis timer."""
        analysis_interval_ms = self.settings.get("processing", {}).get("analysis_interval_sec", 60) * 1000
        self.analysis_timer.start(analysis_interval_ms)
        logger.info(f"ProcessingPipeline started with analysis interval: {analysis_interval_ms / 1000} seconds")

    def stop(self):
        """Stops the periodic analysis timer."""
        self.analysis_timer.stop()
        logger.info("ProcessingPipeline stopped")

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
                
                # 2. Save transcription to database
                session = self.session_factory()
                try:
                    new_capture = Capture(
                        type="audio",
                        file_path=file_path_str,
                        size_bytes=file_path.stat().st_size,
                        metadata_json={"transcription": transcription['text']}
                    )
                    session.add(new_capture)
                    session.commit()
                    logger.debug(f"Saved transcription for {file_path_str} to DB.")
                except Exception as e:
                    session.rollback()
                    logger.error(f"Failed to save transcription to DB: {e}")
                finally:
                    session.close()

                # 3. Delete file after processing
                try:
                    file_path.unlink()
                    logger.debug(f"Deleted audio file: {file_path_str}")
                except Exception as e:
                    logger.warning(f"Failed to delete audio file {file_path_str}: {e}")
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
                # 1. Extract frames and run OCR
                video_capture = cv2.VideoCapture(file_path_str)
                frames = []
                while True:
                    success, frame = video_capture.read()
                    if not success:
                        break
                    frames.append(frame)
                video_capture.release()

                if frames:
                    # For simplicity, process only the first frame for OCR
                    # In a real scenario, you'd extract keyframes or sample frames
                    first_frame_rgb = cv2.cvtColor(frames[0], cv2.COLOR_BGR2RGB)
                    ocr_result = self.ocr.extract(first_frame_rgb)
                    logger.info(f"OCR result from video frame: {ocr_result}")
                    
                    session = self.session_factory()
                    try:
                        new_capture = Capture(
                            type="screen", # Assuming video frames are treated as screens
                            file_path=file_path_str,
                            size_bytes=file_path.stat().st_size,
                            metadata_json={"ocr_text": ocr_result}
                        )
                        session.add(new_capture)
                        session.commit()
                        logger.debug(f"Saved OCR result for {file_path_str} to DB.")
                    except Exception as e:
                        session.rollback()
                        logger.error(f"Failed to save OCR result to DB: {e}")
                    finally:
                        session.close()
                else:
                    logger.warning(f"No frames extracted from video: {file_path_str}")
                
                # 2. Run analysis
                self.run_analysis()
                
                # 3. Delete file after processing
                try:
                    file_path.unlink()
                    logger.debug(f"Deleted video file: {file_path_str}")
                except Exception as e:
                    logger.warning(f"Failed to delete video file {file_path_str}: {e}")
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
        
        # 1. Query DB for recent screen_jsons, transcripts, and events
        # This is a simplified query for demonstration. In a real app, you'd filter by time.
        session = self.session_factory()
        try:
            recent_captures = session.query(Capture).order_by(Capture.timestamp.desc()).limit(10).all()
            # For now, we'll just log them. In a real scenario, you'd process them.
            screens = [c.metadata_json for c in recent_captures if c.type == "screen" and c.metadata_json]
            audio_transcripts = [c.metadata_json["transcription"] for c in recent_captures if c.type == "audio" and c.metadata_json and "transcription" in c.metadata_json]
            events = [c.metadata_json for c in recent_captures if c.type == "event" and c.metadata_json]

            logger.info(f"Recent screens (OCR): {screens}")
            logger.info(f"Recent audio transcripts: {audio_transcripts}")
            logger.info(f"Recent events: {events}")

            # 2. Send to LLM
            workflow = self.llm.analyze_workflow(screens, audio_transcripts, events)
            logger.info(f"LLM workflow analysis: {workflow}")

            # 3. If repetitive, save workflow to DB and emit signal
            if workflow and workflow.get("is_repetitive"):
                session = self.session_factory()
                try:
                    # Assuming 'workflow' dict can be directly stored or has a suitable structure
                    # You might want to create a more specific Workflow object here
                    new_workflow = Workflow(
                        name=workflow.get("workflow_summary", "Unnamed Workflow"),
                        description=workflow.get("workflow_summary", ""),
                        pattern_json=workflow, # Store the entire workflow dict
                        last_used=datetime.utcnow()
                    )
                    session.add(new_workflow)
                    session.commit()
                    logger.info(f"Repetitive workflow detected and saved to DB: {new_workflow.name}. Emitting signal.")
                    self.workflow_detected.emit(workflow)
                except Exception as e:
                    session.rollback()
                    logger.error(f"Failed to save workflow to DB: {e}")
                finally:
                    session.close()
        except Exception as e:
            logger.error(f"Error during periodic analysis: {e}")
        finally:
            session.close()