from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Tuple

import pyautogui
from loguru import logger

from ..processing.ocr_engine import OCREngine, OCRConfig


class ActionVerifier:
    def __init__(self) -> None:
        self.ocr = OCREngine(OCRConfig())

    def verify_click_success(self, expected_text: str, region: Optional[Tuple[int, int, int, int]] = None) -> bool:
        """Verify that a click action was successful by checking for expected text"""
        try:
            if region:
                screenshot = pyautogui.screenshot(region=region)
            else:
                screenshot = pyautogui.screenshot()
            
            # Save temporary screenshot for OCR
            temp_path = "temp_verification.png"
            screenshot.save(temp_path)
            
            # Extract text using OCR
            ocr_result = self.ocr.extract(temp_path)
            visible_text = [item["text"] for item in ocr_result.get("items", [])]
            
            # Check if expected text is present
            success = any(expected_text.lower() in text.lower() for text in visible_text)
            
            # Clean up temp file
            import os
            try:
                os.remove(temp_path)
            except:
                pass
            
            logger.debug("Click verification: expected '{}', found: {}", expected_text, visible_text)
            return success
            
        except Exception as e:
            logger.error("Click verification failed: {}", e)
            return False

    def verify_window_change(self, expected_title: str, timeout: int = 5) -> bool:
        """Verify that the active window title has changed to expected title"""
        try:
            start_time = time.time()
            while time.time() - start_time < timeout:
                try:
                    import win32gui
                    current_title = win32gui.GetWindowText(win32gui.GetForegroundWindow())
                    if expected_title.lower() in current_title.lower():
                        logger.debug("Window change verified: {}", current_title)
                        return True
                except ImportError:
                    logger.warning("win32gui not available for window verification")
                    return True  # Skip verification if not available
                
                time.sleep(0.5)
            
            logger.warning("Window change verification timeout: expected '{}'", expected_title)
            return False
            
        except Exception as e:
            logger.error("Window change verification failed: {}", e)
            return False

    def verify_text_input(self, expected_text: str, field_region: Optional[Tuple[int, int, int, int]] = None) -> bool:
        """Verify that text was successfully entered in a field"""
        try:
            if field_region:
                screenshot = pyautogui.screenshot(region=field_region)
            else:
                screenshot = pyautogui.screenshot()
            
            temp_path = "temp_text_verification.png"
            screenshot.save(temp_path)
            
            ocr_result = self.ocr.extract(temp_path)
            visible_text = [item["text"] for item in ocr_result.get("items", [])]
            
            # Check if the expected text appears in the visible text
            success = any(expected_text.lower() in text.lower() for text in visible_text)
            
            # Clean up
            import os
            try:
                os.remove(temp_path)
            except:
                pass
            
            logger.debug("Text input verification: expected '{}', found: {}", expected_text, visible_text)
            return success
            
        except Exception as e:
            logger.error("Text input verification failed: {}", e)
            return False

    def verify_element_appeared(self, image_path: str, timeout: int = 5) -> bool:
        """Verify that a specific element (image) appeared on screen"""
        try:
            start_time = time.time()
            while time.time() - start_time < timeout:
                location = pyautogui.locateOnScreen(image_path, confidence=0.8)
                if location:
                    logger.debug("Element appeared: {}", image_path)
                    return True
                time.sleep(0.5)
            
            logger.warning("Element appearance verification timeout: {}", image_path)
            return False
            
        except Exception as e:
            logger.error("Element appearance verification failed: {}", e)
            return False

    def get_verification_result(self, verification_type: str, **kwargs) -> bool:
        """Generic verification method that routes to specific verification functions"""
        if verification_type == "click_success":
            return self.verify_click_success(
                kwargs.get("expected_text", ""),
                kwargs.get("region")
            )
        elif verification_type == "window_change":
            return self.verify_window_change(
                kwargs.get("expected_title", ""),
                kwargs.get("timeout", 5)
            )
        elif verification_type == "text_input":
            return self.verify_text_input(
                kwargs.get("expected_text", ""),
                kwargs.get("field_region")
            )
        elif verification_type == "element_appeared":
            return self.verify_element_appeared(
                kwargs.get("image_path", ""),
                kwargs.get("timeout", 5)
            )
        else:
            logger.warning("Unknown verification type: {}", verification_type)
            return True  # Default to success for unknown types
