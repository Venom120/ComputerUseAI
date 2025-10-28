from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

import logging
from PyQt6.QtCore import QObject

logger = logging.getLogger(__name__)
from pynput import keyboard, mouse

try:
    import win32gui  # type: ignore
    import win32process  # type: ignore
    import psutil  # type: ignore
except Exception:  # pragma: no cover
    win32gui = None
    win32process = None
    psutil = None


@dataclass
class EventTrackerConfig:
    log_path: Path


class EventTracker(QObject):
    def __init__(self, config: EventTrackerConfig) -> None:
        super().__init__()
        self.config = config
        self.config.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._mouse_listener = None
        self._keyboard_listener = None
        self._running = False

    def _log(self, event_type: str, details: Dict[str, Any]) -> None:
        # Check if running before logging to prevent logs after stop request
        if not self._running:
            logger.debug(f"Event logging skipped as tracker is stopped (Event: {event_type})")
            return
        entry = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "event_type": event_type,
            "window": self._active_window_title(),
            "app": self._active_process_name(),
            "details": details,
        }
        try:
            with self.config.log_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            logger.error(f"Failed to write event log entry: {e}")


    def _active_window_title(self) -> str:
        if not win32gui:
            return ""
        try:
            hwnd = win32gui.GetForegroundWindow()
            return win32gui.GetWindowText(hwnd)
        except Exception:
            return ""

    def _active_process_name(self) -> str:
        if not (win32gui and win32process and psutil):
            return ""
        try:
            hwnd = win32gui.GetForegroundWindow()
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            return psutil.Process(pid).name()
        except Exception:
            return ""

    def start(self) -> None:
        logger.debug("EventTracker.start() called.")
        if self._running:
            logger.warning("Event tracker is already running.")
            return
        self._running = True

        def on_click(x, y, button, pressed):
            # Only log if tracker is still running
            if self._running and pressed:
                self._log("mouse_click", {"x": x, "y": y, "button": str(button)})

        def on_press(key):
            # Only log if tracker is still running
            if self._running:
                try:
                    name = key.char if hasattr(key, "char") and key.char else str(key)
                except Exception:
                    name = str(key)
                self._log("key_press", {"key": name})

        try:
            logger.debug("Initializing pynput listeners...")
            # Ensure listeners are None before creating new ones
            if self._mouse_listener or self._keyboard_listener:
                 logger.warning("Listeners already exist before start. Attempting to clean up.")
                 self.stop() # Try to stop existing ones first

            self._mouse_listener = mouse.Listener(on_click=on_click)
            self._keyboard_listener = keyboard.Listener(on_press=on_press)
            logger.debug("pynput listeners initialized.")

            logger.debug("Starting mouse listener...")
            self._mouse_listener.start()
            logger.debug("Mouse listener started.")

            logger.debug("Starting keyboard listener...")
            self._keyboard_listener.start()
            logger.debug("Keyboard listener started.")

            logger.info("Event tracker started successfully") # Changed log message
        except Exception as e:
             logger.exception(f"Failed to start pynput listeners: {e}")
             self._running = False # Ensure running state is correct
             # Attempt to stop any partially started listeners
             self.stop()

    def stop(self) -> None:
        logger.debug("EventTracker.stop() called.")
        # Set running flag to False FIRST to prevent further logging from callbacks
        self._running = False

        listeners_to_stop = []
        if hasattr(self, '_mouse_listener') and self._mouse_listener:
             listeners_to_stop.append(self._mouse_listener)
        if hasattr(self, '_keyboard_listener') and self._keyboard_listener:
             listeners_to_stop.append(self._keyboard_listener)

        for l in listeners_to_stop:
            try:
                # Check listener existence and that it has a callable stop method
                if l and hasattr(l, 'stop') and callable(l.stop):
                    logger.debug(f"Attempting to stop listener: {type(l)}")
                    l.stop()
                    # Optionally wait for listener thread join if pynput supports it reliably
                    # if hasattr(l, 'join') and callable(l.join):
                    #     l.join(timeout=0.5) # Add a small timeout
                    logger.debug(f"Listener {type(l)} stop method called.")
            except Exception as e:
                 logger.exception(f"Error calling stop on listener {type(l)}: {e}")

        # Reset listener attributes after attempting to stop
        self._mouse_listener = None
        self._keyboard_listener = None
        logger.info("Event tracker stop sequence completed.") # Changed log message
