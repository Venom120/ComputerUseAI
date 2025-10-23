from __future__ import annotations

import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication, QSystemTrayIcon
from PyQt6.QtCore import QTimer

from .utils import configure_logging, load_json, ensure_dirs
from .ui.main_window import MainWindow
from .ui.tray_icon import TrayIcon


def main() -> int:
    ensure_dirs("data", "data/captures", "data/audio", "data/screens", "data/logs")
    configure_logging()

    settings = load_json(Path(__file__).parents[1] / "config" / "settings.json")

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)  # Keep running when window is closed
    
    # Check if system tray is available
    if not QSystemTrayIcon.isSystemTrayAvailable():
        print("System tray is not available on this system")
        return 1
    
    # Create main window
    window = MainWindow(settings)
    
    # Create tray icon
    tray_icon = TrayIcon()
    
    # Connect tray signals
    tray_icon.show_window.connect(window.show)
    tray_icon.show_window.connect(window.raise_)
    tray_icon.show_window.connect(window.activateWindow)
    tray_icon.start_recording.connect(window.start_recording)
    tray_icon.stop_recording.connect(window.stop_recording)
    tray_icon.quit_app.connect(app.quit)
    
    # Connect window signals to tray
    window.start_btn.clicked.connect(lambda: tray_icon.set_recording_state(True))
    window.stop_btn.clicked.connect(lambda: tray_icon.set_recording_state(False))
    
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

