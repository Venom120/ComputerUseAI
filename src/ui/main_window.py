from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Dict, Any, List

from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
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
    QLineEdit,
    QGroupBox,
    QFormLayout,
    QProgressBar,
    QSplitter,
    QTreeWidget,
    QTreeWidgetItem,
    QMessageBox,
    QFileDialog,
    QSlider,
)

from ..utils import human_size, load_json, save_json
from ..storage.database import initialize_database
from ..automation.executor import WorkflowExecutor


class CaptureThread(QThread):
    status_updated = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.running = False
    
    def run(self):
        self.running = True
        while self.running:
            self.status_updated.emit("Recording...")
            time.sleep(1)
    
    def stop(self):
        self.running = False


class MainWindow(QMainWindow):
    def __init__(self, settings: Dict[str, Any]):
        super().__init__()
        self.settings = settings
        self.workflow_executor = WorkflowExecutor()
        self.capture_thread = CaptureThread()
        self.capture_thread.status_updated.connect(self.update_status)
        
        self.setWindowTitle("ComputerUseAI")
        self.setMinimumSize(1000, 700)
        
        # Initialize database
        db_path = Path("data/app.db")
        self.session_factory = initialize_database(db_path)
        
        self._init_ui()
        self._load_workflows()

    def _init_ui(self) -> None:
        tabs = QTabWidget()
        tabs.addTab(self._dashboard_tab(), "Dashboard")
        tabs.addTab(self._workflows_tab(), "Workflows")
        tabs.addTab(self._timeline_tab(), "Timeline")
        tabs.addTab(self._automation_tab(), "Automation")
        tabs.addTab(self._settings_tab(), "Settings")

        self.setCentralWidget(tabs)

    def _dashboard_tab(self) -> QWidget:
        root = QWidget()
        layout = QVBoxLayout(root)

        # Status section
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
        
        # Stats section
        stats_group = QGroupBox("Statistics")
        stats_layout = QVBoxLayout(stats_group)
        
        self.storage_label = QLabel("Storage usage: Calculating...")
        self.workflows_label = QLabel("Learned workflows: 0")
        self.captures_label = QLabel("Total captures: 0")
        
        stats_layout.addWidget(self.storage_label)
        stats_layout.addWidget(self.workflows_label)
        stats_layout.addWidget(self.captures_label)
        
        # Progress section
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
        root = QWidget()
        layout = QHBoxLayout(root)
        
        # Left panel - workflow list
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        left_layout.addWidget(QLabel("Detected Workflows:"))
        self.workflow_list = QListWidget()
        left_layout.addWidget(self.workflow_list)
        
        # Workflow buttons
        workflow_buttons = QHBoxLayout()
        self.create_workflow_btn = QPushButton("Create New")
        self.edit_workflow_btn = QPushButton("Edit")
        self.delete_workflow_btn = QPushButton("Delete")
        self.run_workflow_btn = QPushButton("Run")
        
        self.create_workflow_btn.clicked.connect(self.create_workflow)
        self.edit_workflow_btn.clicked.connect(self.edit_workflow)
        self.delete_workflow_btn.clicked.connect(self.delete_workflow)
        self.run_workflow_btn.clicked.connect(self.run_workflow)
        
        workflow_buttons.addWidget(self.create_workflow_btn)
        workflow_buttons.addWidget(self.edit_workflow_btn)
        workflow_buttons.addWidget(self.delete_workflow_btn)
        workflow_buttons.addWidget(self.run_workflow_btn)
        
        left_layout.addLayout(workflow_buttons)
        
        # Right panel - workflow details
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        right_layout.addWidget(QLabel("Workflow Details:"))
        self.workflow_details = QTextEdit()
        self.workflow_details.setReadOnly(True)
        right_layout.addWidget(self.workflow_details)
        
        layout.addWidget(left_panel, 1)
        layout.addWidget(right_panel, 1)
        
        return root

    def _timeline_tab(self) -> QWidget:
        root = QWidget()
        layout = QVBoxLayout(root)
        
        # Timeline tree
        self.timeline_tree = QTreeWidget()
        self.timeline_tree.setHeaderLabels(["Time", "Type", "Description", "Duration"])
        layout.addWidget(self.timeline_tree)
        
        # Timeline controls
        controls_layout = QHBoxLayout()
        self.refresh_timeline_btn = QPushButton("Refresh")
        self.export_timeline_btn = QPushButton("Export")
        self.clear_timeline_btn = QPushButton("Clear")
        
        self.refresh_timeline_btn.clicked.connect(self.refresh_timeline)
        self.export_timeline_btn.clicked.connect(self.export_timeline)
        self.clear_timeline_btn.clicked.connect(self.clear_timeline)
        
        controls_layout.addWidget(self.refresh_timeline_btn)
        controls_layout.addWidget(self.export_timeline_btn)
        controls_layout.addWidget(self.clear_timeline_btn)
        controls_layout.addStretch(1)
        
        layout.addLayout(controls_layout)
        
        return root

    def _automation_tab(self) -> QWidget:
        root = QWidget()
        layout = QVBoxLayout(root)
        
        # Automation controls
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
        
        # Automation log
        log_group = QGroupBox("Automation Log")
        log_layout = QVBoxLayout(log_group)
        
        self.automation_log = QTextEdit()
        self.automation_log.setReadOnly(True)
        log_layout.addWidget(self.automation_log)
        
        layout.addWidget(controls_group)
        layout.addWidget(log_group)
        
        return root

    def _settings_tab(self) -> QWidget:
        root = QWidget()
        layout = QVBoxLayout(root)
        
        # Capture settings
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
        
        capture_layout.addRow("FPS:", self.fps_spinbox)
        capture_layout.addRow("Quality:", self.quality_spinbox)
        capture_layout.addRow("Storage Limit (MB):", self.storage_limit_spinbox)
        
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

    def start_recording(self):
        self.capture_thread.start()
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.update_status("Starting recording...")

    def stop_recording(self):
        self.capture_thread.stop()
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.update_status("Stopped recording")

    def update_status(self, status: str):
        self.status_label.setText(f"Status: {status}")

    def update_stats(self):
        # Calculate storage usage
        try:
            total_size = 0
            for path in Path("data").rglob("*"):
                if path.is_file():
                    total_size += path.stat().st_size
            self.storage_label.setText(f"Storage usage: {human_size(total_size)}")
        except:
            self.storage_label.setText("Storage usage: Unknown")
        
        # Update workflow count
        workflow_count = self.workflow_list.count()
        self.workflows_label.setText(f"Learned workflows: {workflow_count}")

    def _load_workflows(self):
        # Load workflows from database or files
        # This is a placeholder implementation
        pass

    def create_workflow(self):
        QMessageBox.information(self, "Create Workflow", "Workflow creation dialog would open here")

    def edit_workflow(self):
        current_item = self.workflow_list.currentItem()
        if current_item:
            QMessageBox.information(self, "Edit Workflow", f"Editing workflow: {current_item.text()}")

    def delete_workflow(self):
        current_item = self.workflow_list.currentItem()
        if current_item:
            reply = QMessageBox.question(self, "Delete Workflow", 
                                      f"Delete workflow: {current_item.text()}?",
                                      QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                self.workflow_list.takeItem(self.workflow_list.row(current_item))

    def run_workflow(self):
        current_item = self.workflow_list.currentItem()
        if current_item:
            QMessageBox.information(self, "Run Workflow", f"Running workflow: {current_item.text()}")

    def refresh_timeline(self):
        self.timeline_tree.clear()
        # Add sample timeline items
        item = QTreeWidgetItem(["2025-01-23 14:30:00", "Workflow", "Excel data entry", "2m 15s"])
        self.timeline_tree.addTopLevelItem(item)

    def export_timeline(self):
        QMessageBox.information(self, "Export Timeline", "Timeline export functionality")

    def clear_timeline(self):
        reply = QMessageBox.question(self, "Clear Timeline", "Clear all timeline data?",
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.timeline_tree.clear()

    def save_settings(self):
        # Update settings with current values
        self.settings["capture"]["fps"] = self.fps_spinbox.value()
        self.settings["capture"]["quality"] = self.quality_spinbox.value()
        self.settings["capture"]["max_storage_mb"] = self.storage_limit_spinbox.value()
        
        excluded_text = self.exclude_apps_text.toPlainText()
        self.settings["privacy"]["exclude_apps"] = [app.strip() for app in excluded_text.split("\n") if app.strip()]
        
        # Save to file
        save_json(Path("config/settings.json"), self.settings)
        QMessageBox.information(self, "Settings", "Settings saved successfully")

