"""
PokeMMO Vision-Driven Bot
Bot nhìn màn hình, hiểu tình huống, và hành động
"""
import os
import sys
import time
import logging
from pathlib import Path
from typing import Dict
from enum import Enum

sys.path.insert(0, str(Path(__file__).parent.parent))

from bot.config import Config
from bot.vision.vision_engine import VisionEngine
from bot.vision.ocr_engine import OCREngine
from bot.llm.client import LLMClient
from bot.action.input_engine import InputEngine

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('bot_vision.log', encoding='utf-8'),
    ]
)
logger = logging.getLogger('VisionBot')


class GameState(Enum):
    OVERWORLD = "overworld"
    BATTLE = "battle"
    DIALOG = "dialog"
    MENU = "menu"
    UNKNOWN = "unknown"


class VisionDrivenBot:
    """Bot driven by what it sees on screen"""

    def __init__(self):
        # Components
        self.vision = VisionEngine()
        self.ocr = OCREngine(use_easyocr=True)
        self.input = InputEngine()
        self.llm = None

        # Try to init LLM
        try:
            config = Config()
            self.llm = LLMClient(config.llm)
            logger.info("LLM connected")
        except Exception as e:
            logger.warning(f"LLM not available: {e}")

        # State
        self.state = GameState.UNKNOWN
        self.running = False
        self.paused = False

        # Screen analysis cache
        self.last_screen_text = ""
        self.last_state_change = 0

        # Navigation state
        self.current_direction = "up"
        self.steps_in_direction = 0
        self.max_steps = 8  # Max steps before changing direction

        # Stuck detection
        self.last_positions = []  # Last N screen hashes
        self.stuck_counter = 0
        self.stuck_threshold = 3  # If stuck 3 times, change strategy

        # Direction cycle for exploration
        self.direction_cycle = ["up", "right", "down", "left"]
        self.direction_index = 0

    def start(self):
        """Start the vision-driven bot"""
        self.running = True
        logger.info("=" * 50)
        logger.info("VISION-DRIVEN BOT STARTED")
        logger.info("Bot will LOOK at screen and DECIDE what to do")
        logger.info("=" * 50)

        try:
            self._main_loop()
        except KeyboardInterrupt:
            logger.info("Stopped by user")
        except Exception as e:
            logger.error(f"Error: {e}")
        finally:
            self.running = False

    def _main_loop(self):
        """Main loop: Look -> Understand -> Act"""
        while self.running:
            # Check pause signal
            if self._check_pause_signal():
                time.sleep(0.1)
                continue

            if self.paused:
                time.sleep(0.1)
                continue

            try:
                # 1. LOOK: Capture and analyze screen
                screen_info = self._look_at_screen()

                # 2. UNDERSTAND: What's happening?
                situation = self._understand_situation(screen_info)

                # 3. ACT: Do something based on what we see
                self._take_action(situation)

                # Small delay
                time.sleep(0.05)

            except Exception as e:
                logger.error(f"Loop error: {e}")
                time.sleep(0.5)

    def _look_at_screen(self) -> Dict:
        """Capture and analyze the screen"""
        info = {
            "frame": None,
            "text_regions": {},
            "detected_state": GameState.UNKNOWN,
        }

        try:
            # Capture screen
            frame = self.vision.capture_screen()
            info["frame"] = frame

            # Read different regions safely
            regions = {}
            for roi_name in ["combat_menu", "chat_box", "enemy_name", "player_name"]:
                try:
                    regions[roi_name] = self.vision.get_roi_image(roi_name, frame)
                except Exception as e:
                    logger.debug(f"Failed to get ROI {roi_name}: {e}")

            # OCR each region
            for name, roi in regions.items():
                if roi is not None:
                    try:
                        text = self.ocr.read_text(roi)
                        if text:
                            info["text_regions"][name] = text
                    except Exception as e:
                        logger.debug(f"OCR failed for {name}: {e}")
                        pass

            # Detect game state from text
            info["detected_state"] = self._detect_state_from_text(info["text_regions"])

        except Exception as e:
            logger.debug(f"Look error: {e}")

        return info

    def _detect_state_from_text(self, text_regions: Dict) -> GameState:
        """Detect game state from OCR text"""
        # Check for battle
        combat_text = text_regions.get("combat_menu", "")
        if combat_text:
            if any(word in combat_text for word in ["Fight", "Bag", "Pokemon", "Run"]):
                return GameState.BATTLE

        # Check for dialog
        chat_text = text_regions.get("chat_box", "")
        if chat_text and len(chat_text) > 5:
            return GameState.DIALOG

        # Check for menu
        if any(word in combat_text for word in ["Summary", "Item", "Save"]):
            return GameState.MENU

        # Default: overworld
        return GameState.OVERWORLD

    def _understand_situation(self, screen_info: Dict) -> Dict:
        """Understand what's happening based on screen info"""
        situation = {
            "state": screen_info["detected_state"],
            "texts": screen_info["text_regions"],
            "action_needed": None,
        }

        state = situation["state"]

        if state == GameState.BATTLE:
            # Read enemy info
            enemy_name = screen_info["text_regions"].get("enemy_name", "")
            player_name = screen_info["text_regions"].get("player_name", "")

            situation["enemy"] = enemy_name
            situation["player"] = player_name
            situation["action_needed"] = "battle"

            logger.info(f"BATTLE: {player_name} vs {enemy_name}")

        elif state == GameState.DIALOG:
            situation["action_needed"] = "advance_dialog"
            chat_text = screen_info["text_regions"].get("chat_box", "")
            logger.info(f"DIALOG: {chat_text[:50]}...")

        elif state == GameState.MENU:
            situation["action_needed"] = "close_menu"

        else:
            situation["action_needed"] = "explore"

        return situation

    def _take_action(self, situation: Dict):
        """Take action based on situation"""
        action = situation.get("action_needed")

        if action == "battle":
            self._handle_battle(situation)

        elif action == "advance_dialog":
            self._handle_dialog()

        elif action == "close_menu":
            self._handle_menu()

        elif action == "explore":
            self._handle_explore()

    def _handle_battle(self, situation: Dict):
        """Handle battle situation"""
        enemy = situation.get("enemy", "Unknown")

        # Ask LLM for best action if available
        if self.llm:
            try:
                prompt = f"""You are in a battle against {enemy}.
Choose the best action:
- If enemy is weak, attack
- If your HP is low, use potion or run
- If enemy is rare/on catch list, try to catch

Reply with JSON: {{"action": "attack|catch|run|heal", "reason": "..."}}"""

                response = self.llm.chat_json(
                    system_prompt="You are a Pokemon battle expert.",
                    user_message=prompt,
                    max_tokens=100
                )

                action = response.get("action", "attack")
                logger.info(f"LLM decision: {action} - {response.get('reason', '')}")

                if action == "attack":
                    self._do_attack()
                elif action == "catch":
                    self._do_catch()
                elif action == "run":
                    self._do_run()
                elif action == "heal":
                    self._do_heal()
                return

            except Exception as e:
                logger.debug(f"LLM error: {e}")

        # Default: attack
        self._do_attack()

    def _do_attack(self):
        """Execute attack in battle"""
        logger.info("Attacking!")
        self.input.navigate_to_move(1)  # First move
        time.sleep(0.05)
        self.input.confirm()

    def _do_catch(self):
        """Try to catch Pokemon"""
        logger.info("Throwing Pokeball!")
        self.input.press_button('x')  # Open bag
        time.sleep(0.1)
        self.input.confirm()  # Select ball
        time.sleep(0.05)
        self.input.confirm()  # Throw

    def _do_run(self):
        """Run from battle"""
        logger.info("Running away!")
        self.input.press_button('down')
        time.sleep(0.03)
        self.input.press_button('down')
        time.sleep(0.03)
        self.input.press_button('right')
        time.sleep(0.03)
        self.input.confirm()

    def _do_heal(self):
        """Use potion"""
        logger.info("Using potion!")
        self.input.press_button('x')  # Open bag
        time.sleep(0.1)
        self.input.confirm()  # Select potion
        time.sleep(0.05)
        self.input.confirm()  # Use

    def _handle_dialog(self):
        """Handle dialog - press Z to advance"""
        logger.info("Advancing dialog...")
        self.input.confirm()  # Press Z
        time.sleep(0.1)

    def _handle_menu(self):
        """Handle menu - close it"""
        logger.info("Closing menu...")
        self.input.cancel()  # Press X to close
        time.sleep(0.1)

    def _handle_explore(self):
        """Handle exploration - navigate intelligently with stuck detection"""
        # Capture current screen for stuck detection
        try:
            frame = self.vision.capture_screen()
            # Create a simple hash of the screen center to detect if we're stuck
            center = frame[400:600, 800:1200]  # Center region
            screen_hash = hash(center.tobytes())
        except:
            screen_hash = None

        # Check if stuck (same screen as before)
        if screen_hash and len(self.last_positions) > 0:
            if screen_hash == self.last_positions[-1]:
                self.stuck_counter += 1
                if self.stuck_counter >= self.stuck_threshold:
                    # We're stuck! Change direction
                    self.stuck_counter = 0
                    self.direction_index = (self.direction_index + 1) % len(self.direction_cycle)
                    self.current_direction = self.direction_cycle[self.direction_index]
                    self.steps_in_direction = 0
                    logger.info(f"STUCK! Changing to: {self.current_direction}")
            else:
                self.stuck_counter = 0

        # Store screen hash
        if screen_hash:
            self.last_positions.append(screen_hash)
            if len(self.last_positions) > 5:
                self.last_positions.pop(0)

        # Walk in current direction
        self.steps_in_direction += 1

        # Change direction after max steps
        if self.steps_in_direction >= self.max_steps:
            self.steps_in_direction = 0
            self.direction_index = (self.direction_index + 1) % len(self.direction_cycle)
            self.current_direction = self.direction_cycle[self.direction_index]
            logger.info(f"Exploring: {self.current_direction}")

        # Execute walk
        self.input.walk(self.current_direction, duration=0.02)

    def _check_pause_signal(self) -> bool:
        """Check for pause signal from GUI"""
        try:
            if os.path.exists("bot_signal.txt"):
                with open("bot_signal.txt", "r") as f:
                    signal = f.read().strip()
                if signal == "PAUSE":
                    self.paused = True
                    return True
                elif signal == "RESUME":
                    self.paused = False
                    os.remove("bot_signal.txt")
                    return False
                elif signal == "STOP":
                    self.running = False
                    return True
        except:
            pass
        return False

    def pause(self):
        self.paused = True
        logger.info("PAUSED")

    def resume(self):
        self.paused = False
        logger.info("RESUMED")

    def stop(self):
        self.running = False
        logger.info("STOPPED")


def main():
    """Run the vision-driven bot"""
    print("=" * 50)
    print("VISION-DRIVEN BOT")
    print("=" * 50)
    print()
    print("This bot LOOKS at the screen and DECIDES what to do")
    print()
    print("Features:")
    print("  - Detects battle, dialog, menu, overworld")
    print("  - Uses LLM for battle decisions")
    print("  - Advances dialog with Z button")
    print("  - Explores map intelligently")
    print()
    print("Starting in 3 seconds...")
    print("=" * 50)
    time.sleep(3)

    bot = VisionDrivenBot()
    bot.start()


if __name__ == "__main__":
    main()
