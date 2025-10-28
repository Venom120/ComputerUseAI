# src/processing/ocr_engine.py (Updated)

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, List, Union # Added Union

import numpy as np
from PIL import Image, ImageOps, ImageFilter
import pytesseract
import logging
import cv2 # Import OpenCV for color conversion if needed

logger = logging.getLogger(__name__)


@dataclass
class OCRConfig:
    language: str = "eng"


class OCREngine:
    def __init__(self, config: OCRConfig) -> None:
        self.config = config

    def _preprocess(self, img: Image.Image) -> Image.Image:
        """Applies grayscale and sharpening."""
        gray = ImageOps.grayscale(img)
        # Sharpening might enhance text recognition
        sharp = gray.filter(ImageFilter.UnsharpMask(radius=1, percent=150, threshold=3))
        # Optional: Add thresholding if needed
        # thresh = sharp.point(lambda x: 0 if x < 128 else 255, '1')
        return sharp

    def extract(self, image_input: Union[str, Path, np.ndarray, Image.Image]) -> Dict[str, Any]:
        """
        Extracts text data from an image file path, NumPy array, or PIL Image.

        Args:
            image_input: The source image (file path, NumPy array, or PIL Image).

        Returns:
            A dictionary containing extracted text items with confidence and bounding boxes.
        """
        try:
            img: Image.Image
            if isinstance(image_input, (str, Path)):
                img = Image.open(image_input)
            elif isinstance(image_input, np.ndarray):
                # Assume BGR format from OpenCV, convert to RGB for PIL
                if image_input.ndim == 3 and image_input.shape[2] == 3:
                     img = Image.fromarray(cv2.cvtColor(image_input, cv2.COLOR_BGR2RGB))
                elif image_input.ndim == 2: # Grayscale
                     img = Image.fromarray(image_input)
                else:
                     logger.error(f"Unsupported NumPy array shape for OCR: {image_input.shape}")
                     return {"items": []}
            elif isinstance(image_input, Image.Image):
                img = image_input
            else:
                logger.error(f"Unsupported input type for OCR: {type(image_input)}")
                return {"items": []}


            # Preprocess the image (convert to grayscale, maybe threshold/sharpen)
            processed_img = self._preprocess(img.copy()) # Use a copy to avoid modifying original

            # Use pytesseract to get detailed data
            data = pytesseract.image_to_data(
                processed_img,
                lang=self.config.language,
                output_type=pytesseract.Output.DICT
            )

            items: List[Dict[str, Any]] = []
            num_items = len(data["text"])

            for i in range(num_items):
                text = data["text"][i].strip()
                # Tesseract reports confidence as strings, -1 for non-text blocks
                try:
                    conf = float(data["conf"][i])
                except ValueError:
                    conf = 0.0

                # Filter out empty strings and low-confidence results
                if text and conf >= 50: # Using a threshold (e.g., 50)
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
            # Log summary instead of full data if it's large
            logger.debug(f"OCR extracted {len(items)} items with conf >= 50.")
            return {"items": items}
        except pytesseract.TesseractNotFoundError:
             logger.error("Tesseract is not installed or not in your PATH. OCR will not work.")
             return {"items": []}
        except Exception as e:
            # Log the exception with traceback for better debugging
            logger.exception(f"OCR error during extraction: {e}")
            return {"items": []}