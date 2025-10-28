# src/processing/pipeline.py (Updated)

from __future__ import annotations

import logging
from pathlib import Path
import cv2, pytz
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

    # --- NEW ---
    @pyqtSlot()
    # --- END NEW ---
    def start(self):
        """Starts the periodic analysis timer."""
        # Check if timer is already active to prevent multiple starts
        if self.analysis_timer.isActive():
            logger.warning("Analysis timer is already active. Ignoring start request.")
            return
            
        analysis_interval_ms = self.settings.get("processing", {}).get("analysis_interval_sec", 60) * 1000
        self.analysis_timer.start(analysis_interval_ms)
        logger.info(f"ProcessingPipeline started analysis timer with interval: {analysis_interval_ms / 1000} seconds")

    # --- NEW ---
    @pyqtSlot()
    # --- END NEW ---
    def stop(self):
        """Stops the periodic analysis timer."""
        if not self.analysis_timer.isActive():
            logger.warning("Analysis timer is not active. Ignoring stop request.")
            return
            
        self.analysis_timer.stop()
        logger.info("ProcessingPipeline stopped analysis timer.")

    @pyqtSlot(str)
    def process_audio(self, file_path_str: str):
        """Slot to process a new audio file."""
        logger.debug(f"Pipeline received audio file signal: {file_path_str}")
        try:
            file_path = Path(file_path_str)
            if file_path.exists():
                logger.info(f"Processing audio: {file_path.name}")
                # 1. Transcribe
                transcription = self.stt.transcribe_file(file_path)
                logger.info(f"Transcription result (first 50 chars): {transcription.get('text', '')[:50]}...")

                # 2. Save transcription to database
                session = self.session_factory()
                try:
                    new_capture = Capture(
                        type="audio",
                        file_path=file_path_str,
                        size_bytes=file_path.stat().st_size,
                        metadata_json={"transcription": transcription.get('text', '')} # Store only text
                    )
                    session.add(new_capture)
                    session.commit()
                    logger.debug(f"Saved transcription for {file_path.name} to DB.")
                except Exception as db_e:
                    session.rollback()
                    logger.error(f"Failed to save transcription to DB for {file_path.name}: {db_e}")
                finally:
                    session.close()

                # 3. Delete file after processing
                try:
                    file_path.unlink()
                    logger.debug(f"Deleted audio file: {file_path.name}")
                except Exception as del_e:
                    logger.warning(f"Failed to delete audio file {file_path.name}: {del_e}")
            else:
                logger.warning(f"Audio file not found when trying to process: {file_path_str}")
        except Exception as e:
            logger.exception(f"Failed to process audio file {file_path_str}: {e}")

    @pyqtSlot(str)
    def process_video(self, file_path_str: str):
        """Slot to process a new video segment."""
        logger.debug(f"Pipeline received video file signal: {file_path_str}")
        try:
            file_path = Path(file_path_str)
            if file_path.exists():
                logger.info(f"Processing video: {file_path.name}")
                # 1. Extract frames and run OCR (Simplified: First frame only)
                try:
                    video_capture = cv2.VideoCapture(file_path_str)
                    if not video_capture.isOpened():
                         logger.error(f"Could not open video file: {file_path_str}")
                         return # Exit early if video can't be opened

                    success, frame = video_capture.read()
                    video_capture.release() # Release immediately after getting the frame

                    if success and frame is not None:
                        # Convert to RGB for Pillow/Tesseract if needed by OCR engine
                        # Assuming self.ocr.extract can handle numpy array directly
                        ocr_result = self.ocr.extract(frame) # Pass the NumPy array directly
                        logger.info(f"OCR result from video frame (items count): {len(ocr_result.get('items', []))}")

                        # Save OCR result to database
                        session = self.session_factory()
                        try:
                            # Store only the extracted text items for brevity
                            ocr_items_metadata = {"items": ocr_result.get("items", [])}
                            new_capture = Capture(
                                type="screen", # Treat video frame analysis as screen capture
                                file_path=file_path_str, # Link DB record to original video file name
                                size_bytes=file_path.stat().st_size,
                                metadata_json={"ocr_data": ocr_items_metadata} # Store OCR items
                            )
                            session.add(new_capture)
                            session.commit()
                            logger.debug(f"Saved OCR result for {file_path.name} to DB.")
                        except Exception as db_e:
                            session.rollback()
                            logger.error(f"Failed to save OCR result to DB for {file_path.name}: {db_e}")
                        finally:
                            session.close()
                    else:
                        logger.warning(f"Failed to extract first frame from video: {file_path.name}")
                        
                except Exception as cv_e:
                     logger.exception(f"Error during video frame extraction/OCR for {file_path.name}: {cv_e}")

                # 2. Delete file after processing attempts
                try:
                    file_path.unlink()
                    logger.debug(f"Deleted video file: {file_path.name}")
                except Exception as del_e:
                    logger.warning(f"Failed to delete video file {file_path.name}: {del_e}")
            else:
                logger.warning(f"Video file not found when trying to process: {file_path_str}")
        except Exception as e:
            logger.exception(f"Failed to process video file {file_path_str}: {e}")

    # Note: run_analysis is called by the QTimer, not directly invoked,
    # so it doesn't strictly need @pyqtSlot, but adding it doesn't hurt.
    @pyqtSlot()
    def run_analysis(self):
        """
        Periodically run analysis on recent data.
        Collects recent screens, audio transcripts, and events, then sends to LLM.
        """
        logger.info("Running periodic analysis...")

        session = self.session_factory()
        try:
            # --- Simplified Query Example ---
            # Query the last 10 capture records regardless of type for analysis context
            # A more robust implementation would filter by timestamp (e.g., last 60 seconds)
            # and potentially fetch related events based on timestamps.
            recent_captures = session.query(Capture)\
                                     .filter(Capture.deleted == False)\
                                     .order_by(Capture.timestamp.desc())\
                                     .limit(10)\
                                     .all()

            screens = [c.metadata_json.get("ocr_data", {}) for c in recent_captures if c.type == "screen" and c.metadata_json]
            audio_transcripts = [c.metadata_json.get("transcription", "") for c in recent_captures if c.type == "audio" and c.metadata_json]
            # Fetch events separately if needed, or assume they are logged elsewhere for now
            events = [] # Placeholder - event data isn't currently stored via this pipeline

            # Basic logging of collected data for debugging
            logger.debug(f"Analysis using {len(screens)} recent screens and {len(audio_transcripts)} audio transcripts.")
            # logger.debug(f"Screens sample: {screens[:1]}") # Log first screen's data
            # logger.debug(f"Transcripts sample: {audio_transcripts[:2]}") # Log first few transcripts

            # 2. Send to LLM if data is available
            if screens or audio_transcripts:
                workflow = self.llm.analyze_workflow(screens, audio_transcripts, events)
                logger.info(f"LLM workflow analysis result: Summary='{workflow.get('workflow_summary')}', Repetitive={workflow.get('is_repetitive')}")

                # 3. If repetitive, save workflow to DB and emit signal
                # Check for a meaningful summary and repetitive flag
                if workflow and workflow.get("is_repetitive") and workflow.get("workflow_summary") not in ["", "LLM response was not valid JSON."]:
                    # Ensure session is still active
                    if not session.is_active:
                         session = self.session_factory() # Get a new session if needed

                    try:
                        workflow_name = workflow.get("workflow_summary", "Unnamed Workflow")
                        new_workflow = Workflow(
                            name=workflow_name,
                            description=workflow.get("workflow_summary", ""),
                            pattern_json=workflow, # Store the entire LLM response dict
                            last_used=datetime.now(pytz.UTC)
                        )
                        session.add(new_workflow)
                        session.commit()
                        logger.info(f"Repetitive workflow detected and saved to DB: '{new_workflow.name}'. Emitting signal.")
                        # Emit the *original* workflow dictionary received from LLM
                        self.workflow_detected.emit(workflow)
                    except Exception as db_e:
                        session.rollback()
                        logger.error(f"Failed to save workflow to DB: {db_e}")
            else:
                logger.info("No recent screen or audio data found for analysis.")

        except Exception as e:
            logger.exception(f"Error during periodic analysis: {e}")
            if session.is_active:
                session.rollback() # Rollback on general errors too
        finally:
            if session.is_active:
                session.close()