from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, List

import numpy as np
from PIL import Image, ImageOps, ImageFilter
import pytesseract
import logging

logger = logging.getLogger(__name__)


@dataclass
class OCRConfig:
    language: str = "eng"


class OCREngine:
    def __init__(self, config: OCRConfig) -> None:
        self.config = config

    def _preprocess(self, img: Image.Image) -> Image.Image:
        gray = ImageOps.grayscale(img)
        sharp = gray.filter(ImageFilter.UnsharpMask(radius=1, percent=150, threshold=3))
        return sharp

    def extract(self, image_path: str | Path) -> Dict[str, Any]:
        try:
            img = Image.open(image_path)
            proc = self._preprocess(img)
            data = pytesseract.image_to_data(proc, lang=self.config.language, output_type=pytesseract.Output.DICT)
            items: List[Dict[str, Any]] = []
            for i in range(len(data["text"])):
                text = data["text"][i].strip()
                conf = float(data["conf"][i]) if data["conf"][i] != "-1" else 0.0
                if text and conf >= 60:
                    items.append(
                        {
                            "text": text,
                            "conf": conf,
                            "bbox": [
                                int(data["left"][i]),
                                int(data["top"][i]),
                                int(data["width"][i]),
                                int(data["height"][i]),
                            ],
                        }
                    )
            return {"items": items}
        except Exception as e:
            logger.exception("OCR error: %s", e)
            return {"items": []}


