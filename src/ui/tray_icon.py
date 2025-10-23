from __future__ import annotations

from typing import Callable, Optional

from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QApplication


class TrayIcon(QObject):
    show_window = pyqtSignal()
    start_recording = pyqtSignal()
    stop_recording = pyqtSignal()
    quit_app = pyqtSignal()
    
    def __init__(self, app_icon: Optional[QIcon] = None):
        super().__init__()
        self.tray = QSystemTrayIcon(app_icon)
        self.tray.setToolTip("ComputerUseAI - Desktop AI Assistant")
        self._create_menu()
        self.tray.activated.connect(self._on_tray_activated)
    
    def _create_menu(self):
        menu = QMenu()
        
        # Main actions
        show_action = QAction("Show Window")
        show_action.triggered.connect(self.show_window.emit)
        menu.addAction(show_action)
        
        menu.addSeparator()
        
        # Recording actions
        self.start_action = QAction("Start Recording")
        self.start_action.triggered.connect(self.start_recording.emit)
        menu.addAction(self.start_action)
        
        self.stop_action = QAction("Stop Recording")
        self.stop_action.triggered.connect(self.stop_recording.emit)
        self.stop_action.setEnabled(False)
        menu.addAction(self.stop_action)
        
        menu.addSeparator()
        
        # Workflow actions
        run_workflow_action = QAction("Run Last Workflow")
        run_workflow_action.triggered.connect(self._run_last_workflow)
        menu.addAction(run_workflow_action)
        
        menu.addSeparator()
        
        # System actions
        settings_action = QAction("Settings")
        settings_action.triggered.connect(self._show_settings)
        menu.addAction(settings_action)
        
        about_action = QAction("About")
        about_action.triggered.connect(self._show_about)
        menu.addAction(about_action)
        
        menu.addSeparator()
        
        quit_action = QAction("Quit")
        quit_action.triggered.connect(self.quit_app.emit)
        menu.addAction(quit_action)
        
        self.tray.setContextMenu(menu)
    
    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show_window.emit()
    
    def _run_last_workflow(self):
        # Placeholder for running last workflow
        self.tray.showMessage("ComputerUseAI", "Running last workflow...", 
                            QSystemTrayIcon.MessageIcon.Information, 2000)
    
    def _show_settings(self):
        self.show_window.emit()
        # Could emit a specific signal to show settings tab
    
    def _show_about(self):
        self.tray.showMessage("ComputerUseAI", 
                            "Desktop AI Assistant\nVersion 1.0\nPrivacy-First Design", 
                            QSystemTrayIcon.MessageIcon.Information, 3000)
    
    def set_recording_state(self, is_recording: bool):
        """Update menu based on recording state"""
        self.start_action.setEnabled(not is_recording)
        self.stop_action.setEnabled(is_recording)
        
        if is_recording:
            self.tray.setToolTip("ComputerUseAI - Recording...")
        else:
            self.tray.setToolTip("ComputerUseAI - Desktop AI Assistant")
    
    def show_notification(self, title: str, message: str, duration: int = 3000):
        """Show a system notification"""
        self.tray.showMessage(title, message, 
                            QSystemTrayIcon.MessageIcon.Information, duration)
    
    def show(self):
        """Show the tray icon"""
        self.tray.show()
    
    def hide(self):
        """Hide the tray icon"""
        self.tray.hide()

