from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

import logging

logger = logging.getLogger(__name__)


@dataclass
class ScreenAnalyzerConfig:
    pass


class ScreenAnalyzer:
    def __init__(self, config: ScreenAnalyzerConfig) -> None:
        self.config = config

    def generate_screen_json(
        self,
        screenshot_path: str | Path,
        ocr_data: Dict[str, Any],
        app_name: str = "",
        window_title: str = "",
    ) -> Dict[str, Any]:
        visible_text = [item["text"] for item in ocr_data.get("items", [])]
        ui_elements: List[Dict[str, Any]] = []

        data = {
            "timestamp": None,
            "application": app_name,
            "window_title": window_title,
            "screenshot": str(screenshot_path),
            "visible_text": visible_text,
            "ui_elements": ui_elements,
            "context": "",
        }
        logger.debug("Screen JSON generated for %s", screenshot_path)
        return data


