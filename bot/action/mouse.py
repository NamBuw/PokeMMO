"""
Mouse & Screen Interaction Module
Hỗ trợ click, drag, tìm vị trí trên màn hình
Tương thích với headless (Xvfb) và real display
"""
import time
import random
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# Try importing display libraries
import os
if 'DISPLAY' not in os.environ:
    os.environ['DISPLAY'] = ':0'  # Default display for headless

try:
    import pyautogui
    pyautogui.FAILSAFE = True  # Move mouse to corner to abort
    pyautogui.PAUSE = 0.05
    HAS_PYAUTOGUI = True
except (ImportError, Exception) as e:
    HAS_PYAUTOGUI = False
    logger.warning(f"pyautogui not available: {e}")

try:
    from pynput.mouse import Controller as MouseController, Button
    HAS_PYNPUT_MOUSE = True
except ImportError:
    HAS_PYNPUT_MOUSE = False

try:
    import cv2
    import numpy as np
    HAS_OPENCV = True
except ImportError:
    HAS_OPENCV = False


class MouseEngine:
    """Điều khiển chuột và click trên màn hình"""

    def __init__(self, game_bbox: Optional[dict] = None):
        """
        Args:
            game_bbox: Game window bounding box {'top':0, 'left':0, 'width':1920, 'height':1080}
        """
        self.game_bbox = game_bbox or {'top': 0, 'left': 0, 'width': 1920, 'height': 1080}

        if HAS_PYAUTOGUI:
            self.mouse = None  # pyautogui uses module-level functions
            self.backend = "pyautogui"
        elif HAS_PYNPUT_MOUSE:
            self.mouse = MouseController()
            self.backend = "pynput"
        else:
            self.mouse = None
            self.backend = "mock"
            logger.warning("No mouse backend available. Running in mock mode.")

    def get_position(self) -> Tuple[int, int]:
        """Lấy vị trí chuột hiện tại"""
        if self.backend == "pyautogui":
            pos = pyautogui.position()
            return (pos.x, pos.y)
        elif self.backend == "pynput":
            pos = self.mouse.position
            return (int(pos[0]), int(pos[1]))
        return (0, 0)

    def move_to(self, x: int, y: int, duration: float = 0.3):
        """
        Di chuyển chuột đến vị trí (x, y) với human-like movement

        Args:
            x, y: Tọa độ tuyệt đối trên màn hình
            duration: Thời gian di chuyển (giây)
        """
        # Add slight randomization to target
        x += random.randint(-2, 2)
        y += random.randint(-2, 2)

        if self.backend == "pyautogui":
            # pyautogui has built-in tween for human-like movement
            pyautogui.moveTo(x, y, duration=duration,
                             tween=pyautogui.easeOutQuad)
        elif self.backend == "pynput":
            # pynput doesn't have smooth movement, simulate it
            steps = max(5, int(duration / 0.02))
            cur_x, cur_y = self.get_position()
            for i in range(steps):
                t = (i + 1) / steps
                # Ease out quad
                t_ease = 1 - (1 - t) ** 2
                new_x = int(cur_x + (x - cur_x) * t_ease)
                new_y = int(cur_y + (y - cur_y) * t_ease)
                self.mouse.position = (new_x, new_y)
                time.sleep(duration / steps)

    def click(self, x: int, y: int, button: str = "left",
              clicks: int = 1, interval: float = 0.1):
        """
        Click tại vị trí (x, y)

        Args:
            x, y: Tọa độ click
            button: "left" | "right" | "middle"
            clicks: Số lần click (1 = single, 2 = double)
            interval: Thời gian giữa các click
        """
        # Move to position first with human-like delay
        self.move_to(x, y, duration=random.uniform(0.15, 0.4))
        time.sleep(random.uniform(0.05, 0.15))  # Pause before click

        if self.backend == "pyautogui":
            pyautogui.click(x, y, clicks=clicks, interval=interval,
                            button=button)
        elif self.backend == "pynput":
            btn = Button.left if button == "left" else (
                Button.right if button == "right" else Button.middle)
            for i in range(clicks):
                self.mouse.position = (x, y)
                self.mouse.press(btn)
                time.sleep(random.uniform(0.05, 0.12))  # Hold time
                self.mouse.release(btn)
                if i < clicks - 1:
                    time.sleep(interval)

        logger.debug(f"Clicked ({x}, {y}) button={button} clicks={clicks}")

    def click_game_offset(self, x_pct: float, y_pct: float, button: str = "left"):
        """
        Click tại vị trí tương đối trong game window (0.0 - 1.0)

        Args:
            x_pct: Phần trăm theo chiều ngang (0.0 = trái, 1.0 = phải)
            y_pct: Phần trăm theo chiều dọc (0.0 = trên, 1.0 = dưới)
            button: "left" | "right"
        """
        abs_x = self.game_bbox['left'] + int(self.game_bbox['width'] * x_pct)
        abs_y = self.game_bbox['top'] + int(self.game_bbox['height'] * y_pct)
        self.click(abs_x, abs_y, button=button)

    def drag(self, start_x: int, start_y: int,
             end_x: int, end_y: int, duration: float = 0.5):
        """
        Kéo chuột từ start đến end

        Args:
            start_x, start_y: Vị trí bắt đầu
            end_x, end_y: Vị trí kết thúc
            duration: Thời gian kéo
        """
        if self.backend == "pyautogui":
            pyautogui.moveTo(start_x, start_y, duration=0.1)
            time.sleep(0.1)
            pyautogui.drag(end_x - start_x, end_y - start_y,
                           duration=duration)
        elif self.backend == "pynput":
            self.mouse.position = (start_x, start_y)
            time.sleep(0.1)
            self.mouse.press(Button.left)
            # Smooth drag
            steps = max(10, int(duration / 0.02))
            for i in range(steps):
                t = (i + 1) / steps
                new_x = int(start_x + (end_x - start_x) * t)
                new_y = int(start_y + (end_y - start_y) * t)
                self.mouse.position = (new_x, new_y)
                time.sleep(duration / steps)
            self.mouse.release(Button.left)

        logger.debug(f"Dragged ({start_x},{start_y}) -> ({end_x},{end_y})")

    def scroll(self, x: int, y: int, clicks: int = 3, direction: str = "down"):
        """
        Cuộn tại vị trí

        Args:
            x, y: Vị trí cuộn
            clicks: Số "notch" cuộn
            direction: "up" | "down"
        """
        amount = -clicks if direction == "up" else clicks

        if self.backend == "pyautogui":
            pyautogui.moveTo(x, y, duration=0.1)
            pyautogui.scroll(amount, x, y)
        elif self.backend == "pynput":
            self.mouse.position = (x, y)
            self.mouse.scroll(0, amount)

        logger.debug(f"Scrolled {direction} {clicks} at ({x}, {y})")

    def find_and_click_image(self, template_path: str,
                              confidence: float = 0.8) -> bool:
        """
        Tìm ảnh template trên màn hình và click vào nó

        Args:
            template_path: Đường dẫn đến ảnh template
            confidence: Độ tin cậy (0.0 - 1.0)

        Returns:
            True nếu tìm thấy và click, False nếu không
        """
        if not HAS_PYAUTOGUI:
            logger.warning("pyautogui required for image search")
            return False

        try:
            location = pyautogui.locateOnScreen(template_path,
                                                 confidence=confidence)
            if location:
                center = pyautogui.center(location)
                self.click(center.x, center.y)
                logger.info(f"Found and clicked {template_path} at ({center.x}, {center.y})")
                return True
        except Exception as e:
            logger.debug(f"Image search failed: {e}")

        return False

    def wait_and_click_image(self, template_path: str,
                              timeout: float = 10.0,
                              confidence: float = 0.8) -> bool:
        """
        Đợi cho đến khi ảnh xuất hiện trên màn hình rồi click

        Args:
            template_path: Đường dẫn đến ảnh template
            timeout: Thời gian tối đa đợi (giây)
            confidence: Độ tin cậy

        Returns:
            True nếu tìm thấy trong timeout
        """
        start = time.time()
        while time.time() - start < timeout:
            if self.find_and_click_image(template_path, confidence):
                return True
            time.sleep(0.5)
        logger.warning(f"Timeout waiting for {template_path}")
        return False


# === CONVENIENCE FUNCTIONS ===

def click_at(x: int, y: int, human_like: bool = True):
    """Click nhanh tại tọa độ"""
    engine = MouseEngine()
    if human_like:
        engine.click(x, y)
    else:
        if engine.backend == "pyautogui":
            pyautogui.click(x, y)
        elif engine.backend == "pynput":
            engine.mouse.position = (x, y)
            engine.mouse.press(Button.left)
            time.sleep(0.05)
            engine.mouse.release(Button.left)


def click_game_position(x_pct: float, y_pct: float,
                         game_bbox: Optional[dict] = None):
    """Click tại vị trí tương đối trong game window"""
    engine = MouseEngine(game_bbox)
    engine.click_game_offset(x_pct, y_pct)


if __name__ == "__main__":
    print(f"Mouse backend: pyautogui={HAS_PYAUTOGUI}, pynput={HAS_PYNPUT_MOUSE}")
    engine = MouseEngine()
    print(f"Using: {engine.backend}")
    print(f"Current position: {engine.get_position()}")
