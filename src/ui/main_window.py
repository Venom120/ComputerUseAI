# src/ui/main_window.py (Updated)

import time
import logging
import pytz
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

# --- PyQt Imports ---
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal, QMetaObject, QUrl
from PyQt6.QtGui import QCloseEvent, QDesktopServices
from PyQt6.QtWidgets import (
    QWidget,
    QMainWindow,
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QTabWidget,
    QListWidget,
    QListWidgetItem,
    QTextEdit,
    QSpinBox,
    QCheckBox,
    QGroupBox,
    QFormLayout,
    QProgressBar,
    QTreeWidget,
    QTreeWidgetItem,
    QMessageBox,
    QSlider,
)

from ..utils import human_size, load_json, save_json
from ..storage.database import initialize_database, Workflow, Capture, Event
from ..automation.executor import WorkflowExecutor
from ..capture.screen_capture import ScreenCapture, ScreenCaptureConfig
from ..capture.audio_capture import AudioCapture, AudioCaptureConfig
from ..capture.event_tracker import EventTracker, EventTrackerConfig
from ..processing.pipeline import ProcessingPipeline

logger = logging.getLogger(__name__)


class RecordingTimerThread(QThread):
    """Simple thread to update the recording duration in the UI."""
    status_updated = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._running = False
        self._start_time = 0.0

    def run(self):
        """Periodically emit the elapsed recording time."""
        self._running = True
        self._start_time = time.time()
        while self._running:
            elapsed = time.time() - self._start_time
            # Format as HH:MM:SS
            elapsed_str = time.strftime("%H:%M:%S", time.gmtime(elapsed))
            status_text = f"Recording... ({elapsed_str})"
            self.status_updated.emit(status_text)
            self.msleep(1000) # Sleep for 1 second
        logger.info("RecordingTimerThread run loop finished.")

    def stop(self):
        """Stop the timer thread."""
        logger.debug("RecordingTimerThread stop called.")
        self._running = False
        # Wait for the run loop to exit cleanly
        if not self.wait(1100): # Wait slightly longer than sleep interval
            logger.warning("Recording timer thread did not stop cleanly.")

    def reset_timer(self):
        """Reset the start time without stopping the thread."""
        self._start_time = time.time()


class MainWindow(QMainWindow):
    """Main application window."""
    recording_started = pyqtSignal()
    recording_stopped = pyqtSignal()

    def __init__(self, settings: Dict[str, Any], project_root: Path):
        super().__init__()
        self.settings = settings
        self.project_root = project_root
        self.workflow_executor = WorkflowExecutor()

        self.timer_thread = RecordingTimerThread()
        self.timer_thread.status_updated.connect(self.update_status)

        # Initialize background processing pipeline
        self.processing_pipeline: Optional[ProcessingPipeline] = None
        self.processing_thread: Optional[QThread] = None
        self._initialize_processing_pipeline()

        # Placeholders for capture components and their threads
        self.screen_capture: Optional[ScreenCapture] = None
        self.audio_capture: Optional[AudioCapture] = None
        self.event_tracker: Optional[EventTracker] = None

        self.screen_thread: Optional[QThread] = None
        self.audio_thread: Optional[QThread] = None
        self.event_thread: Optional[QThread] = None

        self.setWindowTitle("ComputerUseAI")
        self.setMinimumSize(1000, 700)

        # Initialize database connection factory
        db_path_str = settings.get("storage", {}).get("database_path", "data/app.db")
        self.db_path = project_root / db_path_str
        self.session_factory = initialize_database(self.db_path)

        self._init_ui()
        self._load_workflows() # Load initial workflows into the UI

    def _initialize_processing_pipeline(self):
        """Initialize the processing pipeline and its thread."""
        try:
            self.processing_pipeline = ProcessingPipeline(self.settings, self.project_root)
            self.processing_thread = QThread()
            self.processing_pipeline.moveToThread(self.processing_thread)
            # Connect signal for newly detected workflows from pipeline to UI handler
            self.processing_pipeline.workflow_detected.connect(self.handle_workflow_detected)
            # Start the thread. The pipeline itself waits for a start signal.
            self.processing_thread.start()
            logger.info("Processing pipeline thread started at launch. Models are loading.")
        except Exception as e:
            logger.exception(f"Failed to initialize ProcessingPipeline at startup: {e}")
            QMessageBox.critical(self, "Fatal Error", f"Failed to load AI models: {e}\nApplication may not function correctly.")
            self.processing_pipeline = None
            self.processing_thread = None

    def _init_ui(self) -> None:
        """Initialize the main user interface components and tabs."""
        self.tabs = QTabWidget()
        self.tabs.addTab(self._dashboard_tab(), "Dashboard")
        self.tabs.addTab(self._workflows_tab(), "Workflows")
        self.tabs.addTab(self._timeline_tab(), "Timeline")
        self.tabs.addTab(self._automation_tab(), "Automation")
        self.tabs.addTab(self._settings_tab(), "Settings")
        self.setCentralWidget(self.tabs)

        # Connect signals for UI interactions
        self.workflow_list.currentItemChanged.connect(self.display_workflow_details)
        self.tabs.currentChanged.connect(self._handle_tab_change)

    def show_settings_tab(self):
        """Switch to the Settings tab and ensure the window is visible."""
        settings_index = -1
        for i in range(self.tabs.count()):
            if self.tabs.tabText(i).lower() == "settings":
                settings_index = i
                break
        
        if settings_index != -1:
            self.tabs.setCurrentIndex(settings_index)

        # Ensure window is visible, raised, and active
        self.show()
        self.raise_()
        self.activateWindow()

    # --- UI Tab Creation Methods ---

    def _dashboard_tab(self) -> QWidget:
        """Create the Dashboard tab UI."""
        root = QWidget()
        layout = QVBoxLayout(root)

        # Status Group
        status_group = QGroupBox("System Status")
        status_layout = QVBoxLayout(status_group)
        
        self.status_label = QLabel("Status: Idle")
        self.status_label.setStyleSheet("font-weight: bold; color: green;")
        
        button_layout = QHBoxLayout()
        self.start_btn = QPushButton("Start Recording")
        self.stop_btn = QPushButton("Stop Recording")
        self.stop_btn.setEnabled(False)
        
        self.start_btn.clicked.connect(self.start_recording)
        self.stop_btn.clicked.connect(self.stop_recording)
        
        button_layout.addWidget(self.start_btn)
        button_layout.addWidget(self.stop_btn)
        
        status_layout.addWidget(self.status_label)
        status_layout.addLayout(button_layout)
        
        # Stats Group
        stats_group = QGroupBox("Statistics")
        stats_layout = QVBoxLayout(stats_group)
        self.storage_label = QLabel("Storage usage: Calculating...")
        self.workflows_label = QLabel("Learned workflows: 0")
        self.captures_label = QLabel("Total captures: 0") # TODO: Implement capture count query
        open_data_dir_btn = QPushButton("Open Data Directory")
        open_data_dir_btn.clicked.connect(self.open_data_directory)
        stats_layout.addWidget(self.storage_label)
        stats_layout.addWidget(self.workflows_label)
        stats_layout.addWidget(self.captures_label)
        stats_layout.addWidget(open_data_dir_btn)

        # Processing Group
        progress_group = QGroupBox("Processing")
        progress_layout = QVBoxLayout(progress_group)
        
        self.progress_bar = QProgressBar()
        self.progress_label = QLabel("Ready")
        
        progress_layout.addWidget(self.progress_label)
        progress_layout.addWidget(self.progress_bar)
        
        layout.addWidget(status_group)
        layout.addWidget(stats_group)
        layout.addWidget(progress_group)
        layout.addStretch(1)
        
        # Update stats periodically
        self.stats_timer = QTimer()
        self.stats_timer.timeout.connect(self.update_stats)
        self.stats_timer.start(5000)  # Update every 5 seconds
        
        return root

    def _workflows_tab(self) -> QWidget:
        """Create the Workflows tab UI."""
        root = QWidget()
        layout = QHBoxLayout(root)

        # Left Panel (Workflow List)
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        left_layout.addWidget(QLabel("Detected Workflows:"))
        self.workflow_list = QListWidget()
        left_layout.addWidget(self.workflow_list)
        workflow_buttons = QHBoxLayout()
        self.edit_workflow_btn = QPushButton("Edit (Not Implemented)")
        self.delete_workflow_btn = QPushButton("Delete")
        self.run_workflow_btn = QPushButton("Run Manually")
        self.delete_workflow_btn.clicked.connect(self.delete_workflow)
        self.run_workflow_btn.clicked.connect(self.run_workflow)
        workflow_buttons.addWidget(self.edit_workflow_btn)
        workflow_buttons.addWidget(self.delete_workflow_btn)
        workflow_buttons.addWidget(self.run_workflow_btn)
        left_layout.addLayout(workflow_buttons)

        # Right Panel (Workflow Details)
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        right_layout.addWidget(QLabel("Workflow Details:"))
        self.workflow_details = QTextEdit()
        self.workflow_details.setReadOnly(True)
        right_layout.addWidget(self.workflow_details)

        layout.addWidget(left_panel, 1) # Equal initial width
        layout.addWidget(right_panel, 1)

        return root

    def _timeline_tab(self) -> QWidget:
        """Create the Timeline tab UI."""
        root = QWidget()
        layout = QVBoxLayout(root)

        self.timeline_tree = QTreeWidget()
        self.timeline_tree.setHeaderLabels(["Time (UTC)", "Type", "Details", "App"])
        self.timeline_tree.setColumnWidth(0, 180)
        self.timeline_tree.setColumnWidth(1, 100) # Wider type column
        self.timeline_tree.setColumnWidth(2, 400)
        self.timeline_tree.setColumnWidth(3, 150)
        layout.addWidget(self.timeline_tree)

        controls_layout = QHBoxLayout()
        self.refresh_timeline_btn = QPushButton("Refresh")
        self.export_timeline_btn = QPushButton("Export")
        self.clear_timeline_btn = QPushButton("Clear")
        
        self.refresh_timeline_btn.clicked.connect(self.refresh_timeline)
        self.export_timeline_btn.clicked.connect(self.export_timeline)
        self.clear_timeline_btn.clicked.connect(self.clear_timeline)
        
        controls_layout.addWidget(self.refresh_timeline_btn)
        controls_layout.addStretch(1)
        layout.addLayout(controls_layout)

        return root

    def _automation_tab(self) -> QWidget:
        """Create the Automation tab UI."""
        root = QWidget()
        layout = QVBoxLayout(root)

        # Controls Group
        controls_group = QGroupBox("Automation Controls")
        controls_layout = QVBoxLayout(controls_group)
        
        self.auto_enabled_checkbox = QCheckBox("Enable Automation")
        self.auto_enabled_checkbox.setChecked(False)
        
        self.auto_confidence_slider = QSlider(Qt.Orientation.Horizontal)
        self.auto_confidence_slider.setMinimum(50)
        self.auto_confidence_slider.setMaximum(100)
        self.auto_confidence_slider.setValue(80)
        
        confidence_layout = QHBoxLayout()
        confidence_layout.addWidget(QLabel("Confidence Threshold:"))
        confidence_layout.addWidget(self.auto_confidence_slider)
        self.confidence_label = QLabel("80%")
        self.auto_confidence_slider.valueChanged.connect(
            lambda v: self.confidence_label.setText(f"{v}%")
        )
        confidence_layout.addWidget(self.confidence_label)
        controls_layout.addWidget(self.auto_enabled_checkbox)
        controls_layout.addLayout(confidence_layout)

        # Log Group
        log_group = QGroupBox("Automation Log")
        log_layout = QVBoxLayout(log_group)
        
        self.automation_log = QTextEdit()
        self.automation_log.setReadOnly(True)
        log_layout.addWidget(self.automation_log)

        layout.addWidget(controls_group)
        layout.addWidget(log_group)
        layout.addStretch(1) # Push to top

        return root

    def _settings_tab(self) -> QWidget:
        """Create the Settings tab UI."""
        root = QWidget()
        layout = QVBoxLayout(root)

        # Capture Settings Group
        capture_group = QGroupBox("Capture Settings")
        capture_layout = QFormLayout(capture_group)
        
        self.fps_spinbox = QSpinBox()
        self.fps_spinbox.setRange(1, 10)
        self.fps_spinbox.setValue(self.settings.get("capture", {}).get("fps", 3))
        
        self.quality_spinbox = QSpinBox()
        self.quality_spinbox.setRange(10, 100)
        self.quality_spinbox.setValue(self.settings.get("capture", {}).get("quality", 75))
        
        self.storage_limit_spinbox = QSpinBox()
        self.storage_limit_spinbox.setRange(100, 10000)
        self.storage_limit_spinbox.setValue(self.settings.get("capture", {}).get("max_storage_mb", 1000))
        
        self.monitor_spinbox = QSpinBox()
        self.monitor_spinbox.setRange(0, 10) # 0 for all, 1-10 for individual
        self.monitor_spinbox.setValue(self.settings.get("capture", {}).get("monitor", 0))
        self.monitor_spinbox.setToolTip("0 = All Monitors, 1 = Monitor 1, 2 = Monitor 2, etc.")
        
        capture_layout.addRow("FPS:", self.fps_spinbox)
        capture_layout.addRow("Quality:", self.quality_spinbox)
        capture_layout.addRow("Storage Limit (MB):", self.storage_limit_spinbox)
        capture_layout.addRow("Monitor:", self.monitor_spinbox)
        
        # Privacy settings
        privacy_group = QGroupBox("Privacy Settings")
        privacy_layout = QVBoxLayout(privacy_group)
        
        self.exclude_apps_text = QTextEdit()
        self.exclude_apps_text.setMaximumHeight(100)
        excluded = self.settings.get("privacy", {}).get("exclude_apps", [])
        self.exclude_apps_text.setPlainText("\n".join(excluded))
        
        privacy_layout.addWidget(QLabel("Excluded Applications (one per line):"))
        privacy_layout.addWidget(self.exclude_apps_text)
        
        # Save button
        save_btn = QPushButton("Save Settings")
        save_btn.clicked.connect(self.save_settings)
        
        layout.addWidget(capture_group)
        layout.addWidget(privacy_group)
        layout.addWidget(save_btn)
        layout.addStretch(1)
        
        return root

    # --- Utility Methods ---

    def open_data_directory(self):
        """Opens the main data directory in the file explorer."""
        data_dir = self.project_root / "data"
        # Fallback if 'data' doesn't exist yet but DB path does
        if not data_dir.exists() and self.db_path.exists():
            data_dir = self.db_path.parent

        url = QUrl.fromLocalFile(str(data_dir.resolve()))
        logger.info(f"Attempting to open data directory: {url.toString()}")
        if not QDesktopServices.openUrl(url):
            logger.error(f"Failed to open directory: {data_dir}")
            QMessageBox.warning(self, "Open Directory", f"Could not automatically open the data directory:\n{data_dir}\nPlease navigate there manually.")

    def _handle_tab_change(self, index):
        """Refreshes data when specific tabs are selected."""
        tab_text = self.tabs.tabText(index)
        if tab_text == "Timeline":
            logger.debug("Timeline tab selected, refreshing data.")
            self.refresh_timeline()
        elif tab_text == "Workflows":
            logger.debug("Workflows tab selected, refreshing data.")
            self._load_workflows()

    # --- Recording Control ---

    def start_recording(self):
        """Starts screen, audio, and event capture threads."""
        logger.info("Start recording requested.")
        if self.stop_btn.isEnabled(): # Prevent double start
             logger.warning("Recording is already active.")
             return
        try:
            # Load current settings
            cap_settings = self.settings.get("capture", {})
            aud_settings = self.settings.get("audio", {})
            stor_settings = self.settings.get("storage", {})

            # Create Config objects
            screen_config = ScreenCaptureConfig(
                fps=cap_settings.get("fps", 3),
                quality=cap_settings.get("quality", 80),
                change_threshold=cap_settings.get("change_threshold", 0.1),
                resolution_cap=cap_settings.get("resolution_cap", 1080),
                format=cap_settings.get("screenshot_format", "webp"),
                monitor=cap_settings.get("monitor", 0),
                capture_mode="video", # Currently hardcoded to video
                video_segment_sec=cap_settings.get("video_segment_sec", 60),
                video_codec=cap_settings.get("video_codec", "mp4v"),
            )
            audio_config = AudioCaptureConfig(
                sample_rate=aud_settings.get("sample_rate", 16000),
                channels=aud_settings.get("channels", 1),
                segment_seconds=aud_settings.get("segment_seconds", 30),
                use_vad=aud_settings.get("use_vad", True),
                device=aud_settings.get("device", None),
            )
            event_config = EventTrackerConfig(
                log_path=self.project_root / "data/logs/events.jsonl"
            )

            # Define and ensure output directories exist
            screens_dir = self.project_root / stor_settings.get("screens_dir", "data/screens")
            audio_dir = self.project_root / stor_settings.get("audio_dir", "data/audio")
            log_dir = self.project_root / "data/logs"
            screens_dir.mkdir(parents=True, exist_ok=True)
            audio_dir.mkdir(parents=True, exist_ok=True)
            log_dir.mkdir(parents=True, exist_ok=True)

            # Create Capture Objects
            self.screen_capture = ScreenCapture(screens_dir, screen_config)
            self.audio_capture = AudioCapture(audio_dir, audio_config)
            self.event_tracker = EventTracker(event_config)

            # Create and Start Threads
            self.screen_thread = QThread()
            self.screen_capture.moveToThread(self.screen_thread)
            self.screen_thread.started.connect(self.screen_capture.start)
            logger.info("Starting screen capture thread...")
            self.screen_thread.start()

            self.audio_thread = QThread()
            self.audio_capture.moveToThread(self.audio_thread)
            self.audio_thread.started.connect(self.audio_capture.start)
            logger.info("Starting audio capture thread...")
            self.audio_thread.start()

            self.event_thread = QThread()
            self.event_tracker.moveToThread(self.event_thread)
            self.event_thread.started.connect(self.event_tracker.start)
            logger.info("Starting event tracker thread...")
            self.event_thread.start()

            # Connect Signals to Processing Pipeline
            if not self.processing_pipeline:
                logger.error("Processing pipeline is not initialized. Cannot connect signals.")
                self._initialize_processing_pipeline() # Attempt re-initialization
                if not self.processing_pipeline:
                    raise Exception("Processing pipeline failed to initialize.")

            # Ensure signals are connected (re-connect just in case)
            try: self.audio_capture.audio_file_ready.disconnect()
            except TypeError: pass
            try: self.screen_capture.video_file_ready.disconnect()
            except TypeError: pass
            self.audio_capture.audio_file_ready.connect(self.processing_pipeline.process_audio)
            self.screen_capture.video_file_ready.connect(self.processing_pipeline.process_video)
            logger.info("Connected capture signals to processing pipeline.")

            # Start Processing Pipeline Analysis Timer
            QMetaObject.invokeMethod(self.processing_pipeline, "start", Qt.ConnectionType.QueuedConnection)
            logger.info("Signaled processing pipeline to start its analysis timer.")

            # Update UI State and Start UI Timer
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            self.recording_started.emit() # For tray icon state

            if not self.timer_thread.isRunning():
                logger.info("Starting UI timer thread...")
                self.timer_thread.start()
            else:
                self.timer_thread.reset_timer()

            self.update_status("Starting...")

        except Exception as e:
            logger.exception("Failed to start recording: %s", e)
            QMessageBox.critical(self, "Error", f"Failed to start recording: {e}")
            self.stop_recording() # Attempt cleanup

    def stop_recording(self):
        """Stops all capture threads and the processing timer."""
        logger.info("Stop recording requested.")
        if not self.stop_btn.isEnabled(): # Prevent double stop
             logger.warning("Recording is not currently active.")
             return

        self.update_status("Stopping...") # Update UI immediately

        # Stop UI Timer First
        if self.timer_thread.isRunning():
            logger.debug("Stopping RecordingTimerThread...")
            self.timer_thread.stop()
            logger.debug("RecordingTimerThread finished.")

        # Flag to track shutdown status
        capture_stopped_cleanly = True

        # Stop Backend Capture Threads Safely
        threads_to_wait = []

        # Screen Capture
        if self.screen_capture:
            logger.debug("Signaling ScreenCapture to stop...")
            # Assuming stop() signals the loop to exit, doesn't block long
            self.screen_capture.stop()
        if self.screen_thread and self.screen_thread.isRunning():
            logger.debug("Quitting screen_thread...")
            self.screen_thread.quit()
            threads_to_wait.append(("Screen", self.screen_thread))
        self.screen_capture = None # Clear reference early

        # Audio Capture
        if self.audio_capture:
            logger.debug("Signaling AudioCapture to stop...")
            self.audio_capture.stop()
        if self.audio_thread and self.audio_thread.isRunning():
            logger.debug("Quitting audio_thread...")
            self.audio_thread.quit()
            threads_to_wait.append(("Audio", self.audio_thread))
        self.audio_capture = None

        # Event Tracker
        if self.event_tracker:
            logger.debug("Signaling EventTracker to stop...")
            self.event_tracker.stop() # Stops pynput listeners
        if self.event_thread and self.event_thread.isRunning():
            logger.debug("Quitting event_thread...")
            self.event_thread.quit()
            threads_to_wait.append(("Event", self.event_thread))
        self.event_tracker = None

        # Wait for threads to finish
        wait_timeout_ms = 3000 # 3 seconds per thread type
        for name, thread in threads_to_wait:
            if not thread.wait(wait_timeout_ms):
                logger.warning(f"{name} capture thread did not finish cleanly.")
                capture_stopped_cleanly = False
            else:
                logger.info(f"{name} capture thread stopped.")
        # Clear thread references after waiting
        self.screen_thread = None
        self.audio_thread = None
        self.event_thread = None


        # Stop Processing Pipeline Timer
        if self.processing_pipeline:
            logger.debug("Signaling processing pipeline timer to stop...")
            QMetaObject.invokeMethod(self.processing_pipeline, "stop", Qt.ConnectionType.QueuedConnection)
            logger.info("Signaled processing pipeline to stop its analysis timer.")
        else:
            logger.warning("Processing pipeline not found during stop.")

        # Final UI Update
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        final_status = "Stopped recording" if capture_stopped_cleanly else "Stopped recording (Warning: Some threads timed out)"
        self.update_status(final_status)
        self.recording_stopped.emit() # For tray icon state
        logger.info(f"Stop recording sequence finished. Final status: {final_status}")


    # --- UI Updates ---

    def update_status(self, status: str):
        """Update status labels and progress bar based on recording state."""
        self.status_label.setText(f"Status: {status}")
        self.progress_label.setText(f"Status: {status}")
        is_recording = "Recording" in status
        is_processing = "Stopping" in status or "Starting" in status # Could refine this

        if is_recording:
            self.status_label.setStyleSheet("font-weight: bold; color: red;")
            self.progress_bar.setVisible(True)
        elif is_processing:
            self.status_label.setStyleSheet("font-weight: bold; color: orange;")
            self.progress_bar.setVisible(True)
        else: # Idle or Stopped
            self.status_label.setStyleSheet("font-weight: bold; color: green;")
            self.progress_bar.setVisible(False)

    def update_stats(self):
        """Update dashboard statistics like storage usage and workflow count."""
        # Calculate storage size
        try:
            total_size = 0
            data_dirs = [
                self.project_root / self.settings.get("storage", {}).get("screens_dir", "data/screens"),
                self.project_root / self.settings.get("storage", {}).get("audio_dir", "data/audio"),
                self.db_path.parent # Include DB directory
            ]
            checked_paths = set()
            for data_dir in data_dirs:
                resolved_dir = data_dir.resolve()
                if resolved_dir not in checked_paths and resolved_dir.exists():
                    logger.debug(f"Calculating size for: {resolved_dir}")
                    for path in resolved_dir.rglob("*"):
                        if path.is_file():
                            try: total_size += path.stat().st_size
                            except FileNotFoundError: continue
                    checked_paths.add(resolved_dir)
            self.storage_label.setText(f"Storage usage: {human_size(total_size)}")
        except Exception as e:
            logger.warning("Could not calculate storage size: %s", e)
            self.storage_label.setText("Storage usage: Error")

        # Update workflow count (query DB for accuracy)
        session = self.session_factory()
        try:
            workflow_count = session.query(Workflow).count()
            self.workflows_label.setText(f"Learned workflows: {workflow_count}")
        except Exception as e:
             logger.warning(f"Could not query workflow count: {e}")
             self.workflows_label.setText("Learned workflows: Error")
        finally:
             session.close()

        # TODO: Implement capture count update (requires querying DB Capture table)

    def handle_workflow_detected(self, workflow_data: dict):
        """Handles the signal emitted when the processing pipeline detects a new workflow."""
        summary = workflow_data.get('workflow_summary', 'Unnamed Workflow')
        logger.info(f"UI Received workflow detected signal: {summary}")
        self._load_workflows() # Reload list to show the new/updated workflow

        # Handle automatic execution if enabled
        if self.auto_enabled_checkbox.isChecked():
            # Basic check - could add confidence slider check here
            logger.info(f"Automation enabled, queueing execution for: {summary}")
            self.automation_log.append(f"[{time.strftime('%H:%M:%S')}] Detected: {summary}. Attempting auto-execution...")
            # Execute after a short delay to allow UI to update
            QTimer.singleShot(200, lambda wd=workflow_data: self.workflow_executor.execute_workflow_from_llm(wd))


    # --- Workflow Management ---

    def _load_workflows(self):
        """Loads workflows from the database and populates the UI list."""
        logger.debug("Loading workflows from database...")
        session = self.session_factory()
        try:
            workflows = session.query(Workflow).order_by(Workflow.last_used.desc()).all()
            current_selection_id = self.workflow_list.currentItem()
            if current_selection_id:
                current_selection_id = current_selection_id.data(Qt.ItemDataRole.UserRole)

            self.workflow_list.clear()
            if not workflows:
                logger.info("No saved workflows found.")
                placeholder = QListWidgetItem("No workflows detected yet.")
                placeholder.setData(Qt.ItemDataRole.UserRole, None)
                self.workflow_list.addItem(placeholder)
            else:
                for wf in workflows:
                    last_used_str = wf.last_used.strftime('%Y-%m-%d %H:%M') if wf.last_used else 'Never'
                    item = QListWidgetItem(f"{wf.name} (Last used: {last_used_str})")
                    item.setData(Qt.ItemDataRole.UserRole, wf.id) # Store workflow ID
                    self.workflow_list.addItem(item)
                    # Re-select previously selected item
                    if wf.id == current_selection_id:
                         self.workflow_list.setCurrentItem(item)

            logger.info(f"Loaded {len(workflows)} workflows into UI list.")
            # Update dashboard count (handled by update_stats now)
        except Exception as e:
            logger.exception(f"Failed to load workflows: {e}")
            QMessageBox.warning(self, "Load Error", f"Failed to load workflows: {e}")
        finally:
            session.close()

    def display_workflow_details(self, current: Optional[QListWidgetItem], previous: Optional[QListWidgetItem]):
        """Shows the raw JSON pattern for the selected workflow."""
        self.workflow_details.clear()
        is_valid_item = current is not None and current.data(Qt.ItemDataRole.UserRole) is not None

        # Enable/disable buttons based on selection
        self.edit_workflow_btn.setEnabled(False) # Edit not implemented
        self.delete_workflow_btn.setEnabled(is_valid_item)
        self.run_workflow_btn.setEnabled(is_valid_item)

        if not is_valid_item:
            return

        if current is None:
            return
        workflow_id = current.data(Qt.ItemDataRole.UserRole)
        session = self.session_factory()
        try:
            workflow = session.get(Workflow, workflow_id)
            if workflow and workflow.pattern_json:
                import json
                details_text = json.dumps(workflow.pattern_json, indent=2)
                self.workflow_details.setText(details_text)
            else:
                logger.warning(f"Workflow ID {workflow_id} not found or has no pattern data.")
                self.workflow_details.setText(f"Error: Workflow data for ID {workflow_id} not found.")
        except Exception as e:
            logger.exception(f"Failed to fetch workflow details for ID {workflow_id}: {e}")
            self.workflow_details.setText(f"Error loading details: {e}")
        finally:
            session.close()

    def create_workflow(self):
        QMessageBox.information(self, "Create Workflow", "Manual workflow creation is not implemented.")

    def edit_workflow(self):
         QMessageBox.information(self, "Edit Workflow", "Workflow editing is not implemented.")

    def delete_workflow(self):
        """Deletes the currently selected workflow from the database."""
        current_item = self.workflow_list.currentItem()
        if not current_item or current_item.data(Qt.ItemDataRole.UserRole) is None:
            QMessageBox.warning(self, "Delete Workflow", "Please select a valid workflow to delete.")
            return

        workflow_id = current_item.data(Qt.ItemDataRole.UserRole)
        workflow_name = current_item.text().split(" (Last used:")[0]

        reply = QMessageBox.question(self, "Delete Workflow",
                                      f"Are you sure you want to permanently delete workflow:\n'{workflow_name}'?",
                                      QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                      QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            session = self.session_factory()
            try:
                workflow = session.get(Workflow, workflow_id)
                if workflow:
                    session.delete(workflow)
                    session.commit()
                    logger.info(f"Deleted workflow ID {workflow_id} ('{workflow_name}')")
                    self._load_workflows() # Refresh the list
                    self.workflow_details.clear() # Clear details pane
                else:
                    QMessageBox.warning(self, "Delete Error", "Workflow not found in database (perhaps already deleted?).")
                    self._load_workflows() # Refresh list anyway
            except Exception as e:
                session.rollback()
                logger.exception(f"Failed to delete workflow ID {workflow_id}: {e}")
                QMessageBox.critical(self, "Delete Error", f"Failed to delete workflow: {e}")
            finally:
                session.close()

    def run_workflow(self):
        """Manually triggers the execution of the selected workflow."""
        current_item = self.workflow_list.currentItem()
        if not current_item or current_item.data(Qt.ItemDataRole.UserRole) is None:
            QMessageBox.warning(self, "Run Workflow", "Please select a valid workflow to run.")
            return

        workflow_id = current_item.data(Qt.ItemDataRole.UserRole)
        session = self.session_factory()
        try:
            workflow = session.get(Workflow, workflow_id)
            if workflow and workflow.pattern_json:
                workflow_name = workflow.name
                # Ensure pattern_json is treated as the source workflow_data dict
                workflow_data_to_run = workflow.pattern_json

                logger.info(f"Manually running workflow: {workflow_name} (ID: {workflow_id})")
                self.automation_log.append(f"[{time.strftime('%H:%M:%S')}] Manually running: {workflow_name}...")

                # Execute using the executor via a short delay
                QTimer.singleShot(100, lambda wd=workflow_data_to_run: self.workflow_executor.execute_workflow_from_llm(wd))

                # Update last used time in DB
                workflow.last_used = datetime.now(pytz.UTC) # Store as Unix timestamp float or convert to datetime
                session.commit()
                self._load_workflows() # Refresh list to show updated time
            else:
                QMessageBox.warning(self, "Run Error", "Selected workflow data not found or is invalid.")
        except Exception as e:
            session.rollback() # Rollback DB changes on error
            logger.exception(f"Failed to run workflow ID {workflow_id}: {e}")
            QMessageBox.critical(self, "Run Error", f"Failed to run workflow: {e}")
        finally:
            session.close()


    # --- Timeline Management ---

    def refresh_timeline(self):
        """Loads recent captures and events into the timeline view."""
        logger.debug("Refreshing timeline...")
        self.timeline_tree.clear()
        session = self.session_factory()
        try:
            limit = 200 # Increased limit
            # Query captures and events, filtering out deleted items
            captures = session.query(Capture)\
                              .filter(Capture.deleted == False)\
                              .order_by(Capture.timestamp.desc())\
                              .limit(limit)\
                              .all()
            events = session.query(Event)\
                            .filter(Event.deleted == False)\
                            .order_by(Event.timestamp.desc())\
                            .limit(limit)\
                            .all()

            timeline_items_map = {} # Use dict to combine items by timestamp

            for cap in captures:
                ts = cap.timestamp
                details = f"File: {Path(cap.file_path).name}"
                if cap.type == 'audio' and cap.metadata_json and 'transcription' in cap.metadata_json:
                    details += f" | Tx: '{cap.metadata_json['transcription'][:50]}...'"
                elif cap.type == 'screen' and cap.metadata_json and 'ocr_data' in cap.metadata_json:
                     item_count = len(cap.metadata_json['ocr_data'].get('items', []))
                     details += f" | OCR: {item_count} items"

                if ts not in timeline_items_map: timeline_items_map[ts] = []
                timeline_items_map[ts].append({ "type": f"Capture ({cap.type})", "details": details, "app": "N/A"})

            for ev in events:
                ts = ev.timestamp
                if ts not in timeline_items_map: timeline_items_map[ts] = []
                timeline_items_map[ts].append({ "type": f"Event ({ev.event_type})", "details": str(ev.details_json), "app": ev.application})

            # Sort timestamps descending
            sorted_timestamps = sorted(timeline_items_map.keys(), reverse=True)

            # Add to tree widget
            added_count = 0
            for ts in sorted_timestamps:
                 ts_str = ts.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3] # Include milliseconds
                 for item_data in timeline_items_map[ts]:
                      tree_item = QTreeWidgetItem([
                          ts_str,
                          item_data["type"],
                          item_data["details"],
                          item_data["app"]
                      ])
                      self.timeline_tree.addTopLevelItem(tree_item)
                      added_count += 1

            logger.info(f"Timeline refreshed with {added_count} items.")

        except Exception as e:
            logger.exception(f"Failed to refresh timeline: {e}")
            QMessageBox.warning(self, "Timeline Error", f"Failed to load timeline data: {e}")
        finally:
            session.close()

    def export_timeline(self):
        QMessageBox.information(self, "Export Timeline", "Timeline export is not yet implemented.")

    def clear_timeline(self):
        QMessageBox.information(self, "Clear Timeline", "Clearing timeline data is not yet implemented.")

    # --- Settings Management ---

    def save_settings(self):
        """Saves the current UI settings values back to the config file."""
        logger.info("Saving settings...")
        try:
            # Capture Settings
            self.settings["capture"]["fps"] = self.fps_spinbox.value()
            self.settings["capture"]["quality"] = self.quality_spinbox.value()
            self.settings["capture"]["max_storage_mb"] = self.storage_limit_spinbox.value()
            self.settings["capture"]["monitor"] = self.monitor_spinbox.value()

            # Privacy Settings
            excluded_text = self.exclude_apps_text.toPlainText()
            self.settings["privacy"]["exclude_apps"] = [app.strip() for app in excluded_text.split("\n") if app.strip()]

            # Save to JSON file
            config_path = self.project_root / "config/settings.json"
            save_json(config_path, self.settings) # Uses safe save (write tmp then replace)
            logger.info(f"Settings saved to {config_path.resolve()}")
            QMessageBox.information(self, "Settings Saved", f"Settings saved successfully.\nSome changes require restarting recording.")

        except Exception as e:
            logger.exception(f"Failed to save settings: {e}")
            QMessageBox.critical(self, "Error Saving Settings", f"Failed to save settings: {e}")

    # --- Application Lifecycle ---

    def closeEvent(self, a0: Optional[QCloseEvent]):
        """Overrides the window close event to hide instead of quit."""
        # This is triggered by clicking the 'X' button.
        if a0:
            logger.info("Main window close event triggered by user (X button). Hiding window.")
            a0.ignore() # Prevent the window from actually closing
            self.hide()      # Hide it
            # Potential place for a tray notification if tray icon exists
            # Example: self.tray_icon.show_notification("Still Running", "Minimized to tray.")
        else:
            # This 'else' block might be reached if .close() is called programmatically
            # without an event object, or potentially during shutdown.
            logger.info("Internal close() called without event. Proceeding with cleanup.")
            self.cleanup_and_exit()

    def cleanup_and_exit(self):
        """Performs necessary cleanup before the application fully exits."""
        # This should be called by the application's aboutToQuit signal or similar mechanism.
        logger.info("Performing cleanup before application exit...")

        # 1. Stop Recording if Active
        if self.stop_btn.isEnabled():
            logger.info("Recording active during exit, attempting to stop gracefully...")
            # Use BlockingQueuedConnection to ensure stop_recording finishes before continuing exit
            QMetaObject.invokeMethod(self, "stop_recording", Qt.ConnectionType.BlockingQueuedConnection)
            # Short sleep to allow signals/events to process after blocking call returns
            QThread.msleep(500)
            logger.info("stop_recording call completed.")


        # 2. Stop Processing Pipeline Thread
        if self.processing_pipeline:
             # Stop the pipeline's internal timer first
             logger.debug("Signaling processing pipeline timer to stop...")
             QMetaObject.invokeMethod(self.processing_pipeline, "stop", Qt.ConnectionType.BlockingQueuedConnection) # Block here too
        if self.processing_thread and self.processing_thread.isRunning():
            logger.info("Quitting processing thread...")
            self.processing_thread.quit()
            if not self.processing_thread.wait(3000): # Wait up to 3 seconds
                 logger.warning("Processing thread did not shut down gracefully.")
            else:
                logger.info("Processing pipeline thread shut down.")
        self.processing_thread = None
        self.processing_pipeline = None # Clear reference


        # 3. Stop UI Timer Thread (should already be stopped if recording was active)
        if self.timer_thread.isRunning():
            logger.info("Stopping UI timer thread during exit...")
            self.timer_thread.stop() # stop() includes wait()
            logger.info("UI timer thread shut down.")

        logger.info("Cleanup complete. Application will now exit.")
        # The application should exit naturally after this returns (e.g., from app.exec())

