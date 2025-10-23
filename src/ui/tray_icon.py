from __future__ import annotations

import logging
from typing import Callable, Optional

# Import pyqtSignal as Signal for explicit typing
from PyQt6.QtCore import QObject, pyqtSignal, pyqtSignal as Signal
from PyQt6.QtGui import QIcon, QAction, QPixmap, QPainter, QBrush, QColor, QCursor
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QApplication

logger = logging.getLogger(__name__)


class TrayIcon(QObject):
    # Explicitly type-hint signals for linters like mypy
    show_window: Signal = pyqtSignal()
    show_settings: Signal = pyqtSignal()
    start_recording: Signal = pyqtSignal()
    stop_recording: Signal = pyqtSignal()
    quit_app: Signal = pyqtSignal()
    
    def __init__(self, app_icon: Optional[QIcon] = None):
        super().__init__()
        logger.debug("Initializing TrayIcon...")
        if app_icon is None:
            app_icon = self._create_default_icon()
        self.tray = QSystemTrayIcon(app_icon)
        self.tray.setToolTip("ComputerUseAI - Desktop AI Assistant")
        
        self.tray.activated.connect(self._on_tray_activated)
        
        # Add a local state to track recording, as the menu will be built on the fly
        self._is_recording = False
        
        logger.debug("TrayIcon initialized successfully.")
    
    def _create_default_icon(self) -> QIcon:
        """Create a simple default icon for the tray"""
        pixmap = QPixmap(32, 32)
        pixmap.fill(QColor(0, 0, 0, 0))  # Transparent background
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw a simple circle with "AI" text
        painter.setBrush(QBrush(QColor(70, 130, 180)))  # Steel blue
        painter.setPen(QColor(255, 255, 255))  # White border
        painter.drawEllipse(2, 2, 28, 28)
        
        # Draw "AI" text
        painter.setPen(QColor(255, 255, 255))  # White text
        painter.drawText(8, 8, 16, 16, 0, "AI")
        
        painter.end()
        return QIcon(pixmap)
    
    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            logger.debug("Tray icon double-clicked.")
            self.show_window.emit()
            
        elif reason == QSystemTrayIcon.ActivationReason.Context: # This is a right-click
            logger.debug("Tray icon right-clicked, dynamically building menu.")
            
            # --- Dynamically create the menu every time ---
            menu = QMenu()
            
            # Main actions
            show_action = QAction("Show Window")
            show_action.triggered.connect(self.show_window.emit)
            menu.addAction(show_action)
            
            menu.addSeparator()
            
            # Recording actions
            start_action = QAction("Start Recording")
            start_action.triggered.connect(self.start_recording.emit)
            menu.addAction(start_action)
            
            stop_action = QAction("Stop Recording")
            stop_action.triggered.connect(self.stop_recording.emit)
            menu.addAction(stop_action)
            
            # Set enabled/disabled based on our local state
            start_action.setEnabled(not self._is_recording)
            stop_action.setEnabled(self._is_recording)
            
            menu.addSeparator()
            
            # Workflow actions
            run_workflow_action = QAction("Run Last Workflow")
            run_workflow_action.triggered.connect(self._run_last_workflow)
            menu.addAction(run_workflow_action)
            
            menu.addSeparator()
            
            # System actions
            settings_action = QAction("Settings")
            settings_action.triggered.connect(self.show_settings.emit) 
            menu.addAction(settings_action)
            
            about_action = QAction("About")
            about_action.triggered.connect(self._show_about)
            menu.addAction(about_action)
            
            menu.addSeparator()
            
            quit_action = QAction("Quit")
            quit_action.triggered.connect(self.quit_app.emit)
            menu.addAction(quit_action)
            
            # Show the menu at the cursor's current position
            menu.exec(QCursor.pos())
    
    def _run_last_workflow(self):
        # Placeholder for running last workflow
        self.tray.showMessage("ComputerUseAI", "Running last workflow...", 
                            QSystemTrayIcon.MessageIcon.Information, 2000)
    
    def _show_about(self):
        self.tray.showMessage("ComputerUseAI", 
                            "Desktop AI Assistant\nVersion 1.0\nPrivacy-First Design", 
                            QSystemTrayIcon.MessageIcon.Information, 3000)
    
    def set_recording_state(self, is_recording: bool):
        """Update menu based on recording state"""
        # Store the state locally
        self._is_recording = is_recording
        logger.debug(f"Set recording state: {is_recording}")
        
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
        logger.info("Showing system tray icon.")
        self.tray.show()
    
    def hide(self):
        """Hide the tray icon"""
        self.tray.hide()