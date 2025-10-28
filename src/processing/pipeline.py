# src/processing/pipeline.py (Updated)

from __future__ import annotations

import logging
from pathlib import Path
import cv2, pytz
import numpy as np
from datetime import datetime, timedelta # Added timedelta

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot, QTimer

from .speech_to_text import SpeechToText, STTConfig
from .ocr_engine import OCREngine, OCRConfig
from .screen_analyzer import ScreenAnalyzer, ScreenAnalyzerConfig


from ..intelligence.llm_interface import LocalLLM, LLMConfig
from ..storage.database import initialize_database, Capture, Workflow, Event # Added Event

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
            model_path=Path(stt_model_name) # Pass the name directly
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

        db_path_str = settings.get("storage", {}).get("database_path", "data/app.db")
        db_path = self.project_root / db_path_str
        self.session_factory = initialize_database(db_path)

        # Initialize a timer for periodic analysis
        self.analysis_timer = QTimer(self)
        self.analysis_timer.timeout.connect(self.run_analysis)
        self.analysis_interval_sec = settings.get("processing", {}).get("analysis_interval_sec", 60) # Store interval

        logger.info("ProcessingPipeline initialized")

    @pyqtSlot()
    def start(self):
        """Starts the periodic analysis timer."""
        # Check if timer is already active to prevent multiple starts
        if self.analysis_timer.isActive():
            logger.warning("Analysis timer is already active. Ignoring start request.")
            return

        analysis_interval_ms = self.analysis_interval_sec * 1000
        self.analysis_timer.start(analysis_interval_ms)
        logger.info(f"ProcessingPipeline started analysis timer with interval: {analysis_interval_ms / 1000} seconds")
        # Run analysis immediately on start as well
        self.run_analysis()


    @pyqtSlot()
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
                    # --- ADDED: Extract timestamp from filename ---
                    timestamp_from_name = self._extract_timestamp_from_filename(file_path.name)

                    new_capture = Capture(
                        timestamp=timestamp_from_name, # Use extracted timestamp
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
                # 1. Extract frames and run OCR (Simplified: First frame only for now)
                # TODO: Enhance this to extract multiple keyframes and process them.
                try:
                    video_capture = cv2.VideoCapture(file_path_str)
                    if not video_capture.isOpened():
                         logger.error(f"Could not open video file: {file_path_str}")
                         # --- ADDED: Attempt to delete corrupt file ---
                         try:
                             file_path.unlink()
                             logger.warning(f"Deleted potentially corrupt video file: {file_path.name}")
                         except Exception as del_e:
                             logger.warning(f"Failed to delete video file {file_path.name} after open error: {del_e}")
                         return # Exit early

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
                            # --- ADDED: Extract timestamp from filename ---
                            timestamp_from_name = self._extract_timestamp_from_filename(file_path.name)

                            # Store only the extracted text items for brevity
                            ocr_items_metadata = {"items": ocr_result.get("items", [])}
                            new_capture = Capture(
                                timestamp=timestamp_from_name, # Use extracted timestamp
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

    def _extract_timestamp_from_filename(self, filename: str) -> datetime:
        """Helper to extract timestamp from 'prefix_YYYYMMDD_HHMMSS...' format."""
        # Expecting format like audio_YYYYMMDD_HHMMSS.wav or video_YYYYMMDD_HHMMSS.mp4
        parts = filename.split('_')
        if len(parts) >= 3:
            try:
                # Combine date and time parts
                timestamp_str = f"{parts[1]}{parts[2].split('.')[0]}" # Remove extension if present
                dt_obj = datetime.strptime(timestamp_str, "%Y%m%d%H%M%S")
                # Assume local timezone initially and convert to UTC
                local_tz = datetime.now(pytz.UTC).astimezone().tzinfo
                dt_local = dt_obj.replace(tzinfo=local_tz)
                dt_utc = dt_local.astimezone(pytz.utc)
                logger.debug(f"Extracted timestamp {dt_utc} from filename {filename}")
                return dt_utc
            except (ValueError, IndexError) as e:
                logger.warning(f"Could not parse timestamp from filename '{filename}': {e}. Using current UTC time.")
        else:
            logger.warning(f"Filename '{filename}' doesn't match expected format for timestamp extraction. Using current UTC time.")
        return datetime.now(pytz.UTC)


    @pyqtSlot()
    def run_analysis(self):
        """
        Periodically run analysis on recent data.
        Collects recent screens, audio transcripts, and events, then sends to LLM.
        """
        logger.info("Running periodic analysis...")

        session = self.session_factory()
        try:
            # --- MODIFIED Query: Fetch data within the analysis interval ---
            now_utc = datetime.now(pytz.UTC)
            start_time_utc = now_utc - timedelta(seconds=self.analysis_interval_sec * 1.1) # Add a small buffer

            logger.debug(f"Analysis query time range: {start_time_utc} to {now_utc}")

            recent_captures = session.query(Capture)\
                                     .filter(Capture.timestamp >= start_time_utc,
                                             Capture.deleted == False)\
                                     .order_by(Capture.timestamp.asc())\
                                     .all()

            # --- ADDED: Query recent events ---
            recent_events = session.query(Event)\
                                   .filter(Event.timestamp >= start_time_utc,
                                           Event.deleted == False)\
                                   .order_by(Event.timestamp.asc())\
                                   .all()

            screens = [c.metadata_json.get("ocr_data", {}) for c in recent_captures if c.type == "screen" and c.metadata_json]
            audio_transcripts = [c.metadata_json.get("transcription", "") for c in recent_captures if c.type == "audio" and c.metadata_json]

            # --- ADDED: Format events for LLM ---
            # Extract key info from events to keep the prompt concise
            events_for_llm = [
                {
                    "ts": event.timestamp.isoformat(),
                    "type": event.event_type,
                    "app": event.application,
                    "details": event.details_json
                }
                for event in recent_events
            ]


            # Basic logging of collected data for debugging
            logger.debug(f"Analysis using {len(screens)} recent screens, {len(audio_transcripts)} audio transcripts, and {len(events_for_llm)} events.")
            # logger.debug(f"Screens sample: {screens[:1]}") # Log first screen's data
            # logger.debug(f"Transcripts sample: {audio_transcripts[:2]}") # Log first few transcripts
            # logger.debug(f"Events sample: {events_for_llm[:5]}") # Log first few events

            # 2. Send to LLM if data is available
            if screens or audio_transcripts or events_for_llm:
                # --- MODIFIED: Pass events_for_llm ---
                workflow = self.llm.analyze_workflow(screens, audio_transcripts, events_for_llm)
                logger.info(f"LLM workflow analysis result: Summary='{workflow.get('workflow_summary')}', Repetitive={workflow.get('is_repetitive')}")

                # 3. If repetitive, save workflow to DB and emit signal
                # Check for a meaningful summary and repetitive flag
                if workflow and workflow.get("is_repetitive") and workflow.get("workflow_summary") not in ["", "LLM response was not valid JSON.", "LLM returned no content."]:
                    # Ensure session is still active
                    if not session.is_active:
                         session = self.session_factory() # Get a new session if needed

                    try:
                        workflow_name = workflow.get("workflow_summary", "Unnamed Workflow")
                        # --- Check if workflow with the same name exists ---
                        existing_workflow = session.query(Workflow).filter_by(name=workflow_name).first()
                        if existing_workflow:
                             logger.info(f"Workflow '{workflow_name}' already exists. Updating last_used timestamp.")
                             existing_workflow.last_used = datetime.now(pytz.UTC)
                             existing_workflow.pattern_json = workflow # Update with latest pattern
                             # Potentially update success rate or other metrics here later
                        else:
                             logger.info(f"Saving new repetitive workflow to DB: '{workflow_name}'.")
                             new_workflow = Workflow(
                                 name=workflow_name,
                                 description=workflow.get("workflow_summary", ""),
                                 pattern_json=workflow, # Store the entire LLM response dict
                                 last_used=datetime.now(pytz.UTC)
                             )
                             session.add(new_workflow)

                        session.commit()
                        logger.info(f"Workflow '{workflow_name}' processed. Emitting signal.")
                        # Emit the *original* workflow dictionary received from LLM
                        self.workflow_detected.emit(workflow)
                    except Exception as db_e:
                        session.rollback()
                        logger.error(f"Failed to save or update workflow in DB: {db_e}")
            else:
                logger.info("No recent screen, audio, or event data found for analysis.")

        except Exception as e:
            logger.exception(f"Error during periodic analysis: {e}")
            if session.is_active:
                session.rollback() # Rollback on general errors too
        finally:
            if session.is_active:
                session.close()
