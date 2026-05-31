import time
from vision_engine import VisionEngine
from input_engine import InputEngine

class PokeMMOAgent:
    """
    The Master LLM API Controller for PokeMMO.
    Bridges the CV sensory engine and PyAutoGUI actuator engine.
    """
    def __init__(self):
        self.vision = VisionEngine()
        self.actuator = InputEngine()
        print("PokeMMO API Initialized. Ready for LLM commands.")

    def calibrate_screen(self, bbox: dict = None):
        """
        Calibrate the game screen. If bbox is None, it defaults to the full monitor.
        bbox format: {'top': 0, 'left': 0, 'width': 1920, 'height': 1080}
        """
        self.vision.set_game_bbox(bbox)

    def get_game_state(self) -> str:
        """
        Uses OCR and heuristics to determine the current state of the game.
        Returns: "OVERWORLD", "BATTLE", "DIALOG", "MENU", or "UNKNOWN"
        """
        # Capture screen once for all heuristics
        frame = self.vision.capture_screen()
        
        # Heuristic 1: Check if enemy HP bar exists
        hp_percent = self.vision.estimate_hp_percentage('enemy_hp_bar', frame)
        if hp_percent > 0:
            return "BATTLE"
            
        # Heuristic 2: Check for dialog text
        dialog_text = self.vision.read_text('chat_box')
        if len(dialog_text) > 5:
            return "DIALOG"
            
        return "OVERWORLD"

    def read_dialog_text(self) -> str:
        """Reads text from the dialog/chat box."""
        return self.vision.read_text('chat_box')

    def get_battle_context(self) -> dict:
        """
        Retrieves full context of the current battle screen.
        """
        frame = self.vision.capture_screen()
        
        # Check if we are actually in battle
        hp_percent = self.vision.estimate_hp_percentage('enemy_hp_bar', frame)
        if hp_percent == 0:
            return {"error": "Not currently in battle or HP bar not visible."}
            
        enemy_name = self.vision.read_text('enemy_name')
        is_shiny = self.vision.detect_shiny_star(frame)
        
        return {
            "enemy_name": enemy_name,
            "enemy_hp_percent": hp_percent,
            "is_shiny": is_shiny,
            # Note: My HP and active pokemon require additional ROIs in production
        }

    def walk(self, direction: str, duration: float = 0.5) -> None:
        """
        Walks in the specified direction ('up', 'down', 'left', 'right') for 'duration' seconds.
        """
        print(f"Agent walking {direction} for {duration}s")
        self.actuator.walk(direction, duration)

    def execute_move(self, move_slot: int) -> bool:
        """
        Executes a move in battle given its slot (1, 2, 3, or 4).
        """
        print(f"Agent selecting move slot {move_slot}...")
        
        # 1. Ensure we are in the fight menu by pressing 'z' (A button equivalent)
        self.actuator.press_button('a')
        time.sleep(0.5)
        
        # 2. Navigate to the correct slot
        # Assuming grid layout:
        # 1 2
        # 3 4
        # Default cursor is usually on 1.
        if move_slot == 2:
            self.actuator.press_button('right')
        elif move_slot == 3:
            self.actuator.press_button('down')
        elif move_slot == 4:
            self.actuator.press_button('down')
            time.sleep(0.1)
            self.actuator.press_button('right')
            
        time.sleep(0.2)
        # 3. Confirm move
        self.actuator.press_button('a')
        return True
        
    def interact(self) -> None:
        """
        Presses the action button ('A' / 'z') to interact with NPCs or objects.
        """
        print("Agent interacting...")
        self.actuator.press_button('a')
        
    def close_dialog(self) -> None:
        """
        Mashes 'B' ('x') to close open dialogs or back out of menus.
        """
        print("Agent backing out...")
        self.actuator.press_button('b')
        time.sleep(0.1)
        self.actuator.press_button('b')

if __name__ == "__main__":
    agent = PokeMMOAgent()
    print("API is ready to be imported by the LLM Brain.")
