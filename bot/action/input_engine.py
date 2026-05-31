"""
Input Engine - Keyboard + Mouse cho PokeMMO
Tổ hợp từ input_engine.py gốc + mouse support
"""
import time
import random
import logging
from typing import Optional

logger = logging.getLogger(__name__)

try:
    from pynput.keyboard import Controller as KeyController, Key, KeyCode
    HAS_KEYBOARD = True
except ImportError:
    HAS_KEYBOARD = False
    logger.warning("pynput keyboard not available")

from .mouse import MouseEngine


class InputEngine:
    """Điều khiển keyboard + mouse cho PokeMMO"""

    def __init__(self, game_bbox: Optional[dict] = None):
        # Keyboard
        if HAS_KEYBOARD:
            self.keyboard = KeyController()
            self.Key = Key
            self.KeyCode = KeyCode
        else:
            self.keyboard = None
            self.Key = type('MockKey', (), {
                'enter': 'enter', 'shift': 'shift', 'esc': 'esc',
                'tab': 'tab', 'space': 'space',
            })
            self.KeyCode = type('MockKeyCode', (), {
                'from_char': lambda c: c
            })

        # Mouse
        self.mouse = MouseEngine(game_bbox)

        # PokeMMO key mapping
        self.keymap = {
            'up': 'w',
            'down': 's',
            'left': 'a',
            'right': 'd',
            'a': 'z',       # Confirm / A button
            'b': 'x',       # Cancel / B button
            'x': 'c',       # X button
            'y': 'v',       # Y button
            'start': self.Key.enter,
            'select': self.Key.shift,
            'menu': self.Key.esc,
            'tab': self.Key.tab,
            'space': self.Key.space,
        }

    def _get_key(self, button: str):
        """Map button name to actual key"""
        button = button.lower()
        if button not in self.keymap:
            raise ValueError(f"Unknown button: {button}. Valid: {list(self.keymap.keys())}")
        mapped = self.keymap[button]
        if isinstance(mapped, str):
            return self.KeyCode.from_char(mapped)
        return mapped

    # === KEYBOARD METHODS ===

    def press_button(self, button: str, hold_time: float = 0.1):
        """
        Nhấn một nút với human-like timing

        Args:
            button: Tên nút (up/down/left/right/a/b/x/y/start/select/menu)
            hold_time: Thời gian giữ nút (giây)
        """
        key = self._get_key(button)

        # Add slight randomization to hold time
        hold_time += random.uniform(-0.02, 0.02)
        hold_time = max(0.03, hold_time)

        if self.keyboard:
            self.keyboard.press(key)
        time.sleep(hold_time)
        if self.keyboard:
            self.keyboard.release(key)

        # Human-like delay after release
        time.sleep(random.uniform(0.02, 0.08))

    def walk(self, direction: str, duration: float = 0.5):
        """
        Giữ phím di chuyển để đi bộ

        Args:
            direction: Hướng (up/down/left/right)
            duration: Thời gian đi (giây)
        """
        key = self._get_key(direction)
        if self.keyboard:
            self.keyboard.press(key)
        time.sleep(duration)
        if self.keyboard:
            self.keyboard.release(key)
        time.sleep(random.uniform(0.02, 0.05))

    def sequence(self, buttons: list, delay_between: float = 0.2):
        """
        Nhấn chuỗi nút tuần tự

        Args:
            buttons: Danh sách tên nút
            delay_between: Thời gian giữa các nút
        """
        for btn in buttons:
            self.press_button(btn)
            time.sleep(delay_between + random.uniform(-0.05, 0.05))

    def mash_button(self, button: str, times: int = 5, delay: float = 0.3):
        """
        Nhấn lặp lại một nút nhiều lần (ví dụ: mash A để qua dialog)

        Args:
            button: Tên nút
            times: Số lần nhấn
            delay: Thời gian giữa các lần
        """
        for _ in range(times):
            self.press_button(button)
            time.sleep(delay + random.uniform(-0.1, 0.1))

    # === MOUSE METHODS ===

    def click(self, x: int, y: int, button: str = "left"):
        """Click chuột tại tọa độ tuyệt đối"""
        self.mouse.click(x, y, button=button)

    def click_game(self, x_pct: float, y_pct: float, button: str = "left"):
        """Click tại vị trí tương đối trong game window (0.0 - 1.0)"""
        self.mouse.click_game_offset(x_pct, y_pct, button=button)

    def right_click(self, x: int, y: int):
        """Right click"""
        self.mouse.click(x, y, button="right")

    def drag(self, start_x: int, start_y: int, end_x: int, end_y: int):
        """Kéo chuột"""
        self.mouse.drag(start_x, start_y, end_x, end_y)

    def scroll(self, x: int, y: int, clicks: int = 3, direction: str = "down"):
        """Cuộn tại vị trí"""
        self.mouse.scroll(x, y, clicks, direction)

    # === HIGH-LEVEL GAME ACTIONS ===

    def confirm(self):
        """Nhấn nút A (confirm)"""
        self.press_button('a')

    def cancel(self):
        """Nhấn nút B (cancel/back)"""
        self.press_button('b')

    def open_menu(self):
        """Mở menu"""
        self.press_button('menu')

    def navigate_to_move(self, slot: int):
        """
        Di chuyển con trỏ đến move slot trong battle

        Args:
            slot: 1-4 (1=top-left, 2=top-right, 3=bottom-left, 4=bottom-right)
        """
        if slot == 2:
            self.press_button('right')
        elif slot == 3:
            self.press_button('down')
        elif slot == 4:
            self.press_button('down')
            time.sleep(0.1)
            self.press_button('right')

    def navigate_menu_grid(self, target_row: int, target_col: int,
                            current_row: int = 0, current_col: int = 0):
        """
        Di chuyển trong menu grid

        Args:
            target_row, target_col: Vị trí muốn đến
            current_row, current_col: Vị trí hiện tại
        """
        row_diff = target_row - current_row
        col_diff = target_col - current_col

        for _ in range(abs(row_diff)):
            self.press_button('down' if row_diff > 0 else 'up')
            time.sleep(0.1)

        for _ in range(abs(col_diff)):
            self.press_button('right' if col_diff > 0 else 'left')
            time.sleep(0.1)


if __name__ == "__main__":
    engine = InputEngine()
    print(f"Keyboard: {'OK' if HAS_KEYBOARD else 'Mock'}")
    print(f"Mouse: {engine.mouse.backend}")
    print("Input Engine ready!")
