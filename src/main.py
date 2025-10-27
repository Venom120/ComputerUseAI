from __future__ import annotations

import sys
import traceback
import logging
from pathlib import Path

from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMessageBox
from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QIcon

from .utils import configure_logging, load_json, ensure_dirs
from .ui.main_window import MainWindow
from .ui.tray_icon import TrayIcon
from .storage.cleanup import cleanup_old_files, cleanup_size_limit, physical_cleanup_deleted_records
from .storage.database import initialize_database
from .automation.executor import WorkflowExecutor

PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_NAME = "ComputerUseAI"
logger = logging.getLogger(__name__)

def custom_exception_hook(exc_type, exc_value, exc_traceback):
    """Global exception hook to log unhandled exceptions."""
    if issubclass(exc_type, KeyboardInterrupt):
        # Don't interfere with Ctrl+C
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    logger.critical("Unhandled exception caught by custom hook:", exc_info=(exc_type, exc_value, exc_traceback))
    
    # Optionally, display a message box to the user
    error_message = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    QMessageBox.critical(
        None,
        "Application Error",
        "An unexpected error occurred. The application might become unstable.\n\n"
        f"Error: {exc_value}\n\n"
        "Please check the logs for more details."
    )

def main() -> int:
    # Set the custom exception hook
    sys.excepthook = custom_exception_hook

    # Use the absolute project root path
    settings = load_json(PROJECT_ROOT / "config" / "settings.json")

    ensure_dirs(
        PROJECT_ROOT / "data",
        PROJECT_ROOT / "data/captures",
        PROJECT_ROOT / "data/audio",
        PROJECT_ROOT / "data/screens",
        PROJECT_ROOT / "data/logs"
    )
    configure_logging(PROJECT_ROOT / "data/logs", settings.get("logging", {}).get("level"))
    logger.info(f"{APP_NAME} application starting...")

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setWindowIcon(QIcon(str(PROJECT_ROOT / "assets/icon.png")))
    app.setQuitOnLastWindowClosed(False)  # Keep running when window is closed
    
    # Check if system tray is available
    if not QSystemTrayIcon.isSystemTrayAvailable():
        print("System tray is not available on this system")
        return 1
    
    # Create main window
    window = MainWindow(settings, PROJECT_ROOT)
    
    # Create tray icon
    tray_icon = TrayIcon()

    # Initialize WorkflowExecutor
    workflow_executor = WorkflowExecutor()
    
    # Connect workflow_detected signal from pipeline to executor
    if window.processing_pipeline:
        window.processing_pipeline.workflow_detected.connect(workflow_executor.execute_workflow_from_llm)
    
    # Connect tray signals
    tray_icon.show_window.connect(window.show)
    tray_icon.show_window.connect(window.raise_)
    tray_icon.show_window.connect(window.activateWindow)
    tray_icon.show_settings.connect(window.show_settings_tab)
    tray_icon.start_recording.connect(window.start_recording)
    tray_icon.stop_recording.connect(window.stop_recording)
    tray_icon.quit_app.connect(app.quit)
    
    # Connect window signals to tray
    window.start_btn.clicked.connect(lambda: tray_icon.set_recording_state(True))
    window.stop_btn.clicked.connect(lambda: tray_icon.set_recording_state(False))

    # Connect main window events back to the tray to sync state
    window.recording_started.connect(lambda: tray_icon.set_recording_state(True))
    window.recording_stopped.connect(lambda: tray_icon.set_recording_state(False))
    
    # Show tray icon
    tray_icon.show()
    
    # Show window if not set to start minimized
    if not settings.get("ui", {}).get("start_minimized", True):
        window.show()
    else:
        tray_icon.show_notification("ComputerUseAI", "Application started. Click tray icon to open.")
    
    # Initialize database and session factory
    db_path = PROJECT_ROOT / settings.get("storage", {}).get("database_path", "data/app.db")
    session_factory = initialize_database(db_path)

    # Run cleanup on startup
    capture_dirs = [
        PROJECT_ROOT / settings.get("storage", {}).get("captures_dir", "data/captures"),
        PROJECT_ROOT / settings.get("storage", {}).get("audio_dir", "data/audio"),
        PROJECT_ROOT / settings.get("storage", {}).get("screens_dir", "data/screens")
    ]
    max_keep_days = settings.get("capture", {}).get("max_keep_days", 7)
    max_storage_mb = settings.get("capture", {}).get("max_storage_mb", 10000)
    
    removed_age = cleanup_old_files(session_factory, capture_dirs, max_keep_days)
    logger.info(f"Cleaned up {removed_age} old files/records.")
    
    # For simplicity, apply size limit to the main captures directory
    main_capture_dir = PROJECT_ROOT / settings.get("storage", {}).get("captures_dir", "data/captures")
    removed_size = cleanup_size_limit(session_factory, main_capture_dir, max_storage_mb * 1024 * 1024)
    logger.info(f"Cleaned up {removed_size} files/records due to size limit.")

    # Perform hard deletion of records marked as deleted and past retention period
    retention_days = settings.get("storage", {}).get("deleted_retention_days", 30)
    hard_deleted_count = physical_cleanup_deleted_records(session_factory, retention_days)
    logger.info(f"Hard deleted {hard_deleted_count} records and files past retention period.")

    exit_code = app.exec()
    logger.info(f"{APP_NAME} application exiting with code {exit_code}.")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())

