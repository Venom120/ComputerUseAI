from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

import pyautogui
import logging

logger = logging.getLogger(__name__)


@dataclass
class ComputerUseConfig:
    click_delay: float = 0.1
    type_delay: float = 0.05
    scroll_delay: float = 0.1


class ComputerUse:
    def __init__(self, config: ComputerUseConfig) -> None:
        self.config = config
        pyautogui.FAILSAFE = True
        pyautogui.PAUSE = 0.1

    def click_at_position(self, x: int, y: int, button: str = "left") -> bool:
        try:
            pyautogui.click(x, y, button=button)
            time.sleep(self.config.click_delay)
            logger.debug("Clicked at (%d, %d) with %s button", x, y, button)
            return True
        except Exception as e:
            logger.error("Click failed at (%d, %d): %s", x, y, e)
            return False

    def type_text(self, text: str, interval: float | None = None) -> bool:
        try:
            interval = interval or self.config.type_delay
            pyautogui.typewrite(text, interval=interval)
            logger.debug("Typed text: %s", text[:50] + "..." if len(text) > 50 else text)
            return True
        except Exception as e:
            logger.error("Type text failed: %s", e)
            return False

    def press_key(self, key: str) -> bool:
        try:
            pyautogui.press(key)
            time.sleep(self.config.click_delay)
            logger.debug("Pressed key: %s", key)
            return True
        except Exception as e:
            logger.error("Press key failed: %s", e)
            return False

    def press_key_combination(self, keys: list[str]) -> bool:
        try:
            pyautogui.hotkey(*keys)
            time.sleep(self.config.click_delay)
            logger.debug("Pressed key combination: %s", keys)
            return True
        except Exception as e:
            logger.error("Key combination failed: %s", e)
            return False

    def scroll(self, clicks: int, x: Optional[int] = None, y: Optional[int] = None) -> bool:
        try:
            if x is not None and y is not None:
                pyautogui.scroll(clicks, x=x, y=y)
            else:
                pyautogui.scroll(clicks)
            time.sleep(self.config.scroll_delay)
            logger.debug("Scrolled %d clicks", clicks)
            return True
        except Exception as e:
            logger.error("Scroll failed: %s", e)
            return False

    def get_screen_region(self, x: int, y: int, width: int, height: int) -> Optional[Any]:
        try:
            screenshot = pyautogui.screenshot(region=(x, y, width, height))
            logger.debug("Captured region: %dx%d at (%d, %d)", width, height, x, y)
            return screenshot
        except Exception as e:
            logger.error("Screen region capture failed: %s", e)
            return None

    def find_image_on_screen(self, image_path: str, confidence: float = 0.8) -> Optional[Tuple[int, int]]:
        try:
            location = pyautogui.locateOnScreen(image_path, confidence=confidence)
            if location:
                center = pyautogui.center(location)
                logger.debug("Found image at (%d, %d)", center.x, center.y)
                return (center.x, center.y)
            return None
        except Exception as e:
            logger.error("Image search failed: %s", e)
            return None

    def wait_for_element(self, image_path: str, timeout: int = 10, confidence: float = 0.8) -> Optional[Tuple[int, int]]:
        start_time = time.time()
        while time.time() - start_time < timeout:
            location = self.find_image_on_screen(image_path, confidence)
            if location:
                return location
            time.sleep(0.5)
        logger.warning("Element not found within %d seconds", timeout)
        return None

    def verify_action_success(self, expected_state: str) -> bool:
        # Placeholder for verification logic
        # In a real implementation, this would check screen state, window titles, etc.
        logger.debug("Verifying action success: %s", expected_state)
        return True
