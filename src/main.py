from __future__ import annotations

import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication, QSystemTrayIcon
from PyQt6.QtCore import QTimer

from .utils import configure_logging, load_json, ensure_dirs
from .ui.main_window import MainWindow
from .ui.tray_icon import TrayIcon

PROJECT_ROOT = Path(__file__).resolve().parents[1]

def main() -> int:
    # Use the absolute project root path
    ensure_dirs(
        PROJECT_ROOT / "data", 
        PROJECT_ROOT / "data/captures", 
        PROJECT_ROOT / "data/audio", 
        PROJECT_ROOT / "data/screens", 
        PROJECT_ROOT / "data/logs"
    )
    configure_logging(PROJECT_ROOT / "data/logs")

    settings = load_json(PROJECT_ROOT / "config" / "settings.json")

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # Keep running when window is closed
    
    # Check if system tray is available
    if not QSystemTrayIcon.isSystemTrayAvailable():
        print("System tray is not available on this system")
        return 1
    
    # Create main window
    window = MainWindow(settings, PROJECT_ROOT)
    
    # Create tray icon
    tray_icon = TrayIcon()
    
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
    
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

