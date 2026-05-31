import time
import os
try:
    from pynput.keyboard import Controller, Key, KeyCode
    HAS_DISPLAY = True
except ImportError:
    HAS_DISPLAY = False

class InputEngine:
    def __init__(self):
        if HAS_DISPLAY:
            self.keyboard = Controller()
            self.Key = Key
            self.KeyCode = KeyCode
        else:
            print("WARNING: Running in headless environment. Hardware inputs disabled.")
            self.keyboard = None
            self.Key = type('MockKey', (), {'enter': 'enter', 'shift': 'shift', 'esc': 'esc'})
            self.KeyCode = type('MockKeyCode', (), {'from_char': lambda c: c})
            
        # Default mapping for PokeMMO
        self.keymap = {
            'up': 'w',
            'down': 's',
            'left': 'a',
            'right': 'd',
            'a': 'z',
            'b': 'x',
            'x': 'c',
            'y': 'v',
            'start': self.Key.enter,
            'select': self.Key.shift,
            'menu': self.Key.esc
        }

    def _get_key(self, button: str):
        button = button.lower()
        if button not in self.keymap:
            raise ValueError(f"Unknown button: {button}. Valid options: {list(self.keymap.keys())}")
        
        mapped = self.keymap[button]
        if isinstance(mapped, str):
            return self.KeyCode.from_char(mapped)
        return mapped

    def press_button(self, button: str, hold_time: float = 0.1):
        """
        Simulate a human-like button press with a slight hold delay.
        """
        key = self._get_key(button)
        if self.keyboard:
            self.keyboard.press(key)
        time.sleep(hold_time)
        if self.keyboard:
            self.keyboard.release(key)
        # Small delay after releasing to mimic human reset time
        time.sleep(0.05)

    def walk(self, direction: str, duration: float):
        """
        Hold a directional key to walk or run.
        """
        key = self._get_key(direction)
        if self.keyboard:
            self.keyboard.press(key)
        time.sleep(duration)
        if self.keyboard:
            self.keyboard.release(key)
        time.sleep(0.05)

    def sequence(self, buttons: list, delay_between: float = 0.2):
        """
        Press a sequence of buttons sequentially.
        """
        for btn in buttons:
            self.press_button(btn)
            time.sleep(delay_between)

if __name__ == "__main__":
    # Test script (do not run while typing)
    print("Initializing Input Engine...")
    engine = InputEngine()
    print("Ready to send virtual inputs.")
