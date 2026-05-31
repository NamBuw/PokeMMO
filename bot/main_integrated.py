"""
PokeMMO Autonomous Bot - Integrated Main Entry Point
Integrates: LLM + Vision + Knowledge Graph + Navigation + Action
"""
import os
import sys
import json
import time
import signal
import logging
import argparse
from pathlib import Path
from typing import Optional, Dict, Any, List
from enum import Enum
from collections import deque

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from bot.config import Config
from bot.llm.client import LLMClient
from bot.vision.vision_engine import VisionEngine
from bot.vision.ocr_engine import OCREngine
from bot.knowledge.graph.builder import KnowledgeGraphBuilder
from bot.knowledge.graph.queries import GraphQueries
from bot.navigation.navigation_engine import NavigationEngine
from bot.action.input_engine import InputEngine

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('pokemmo_bot.log', encoding='utf-8'),
    ]
)
logger = logging.getLogger('PokeMMO')


class GameState(Enum):
    """Game states"""
    OVERWORLD = "OVERWORLD"
    BATTLE = "BATTLE"
    DIALOG = "DIALOG"
    MENU = "MENU"
    UNKNOWN = "UNKNOWN"


class ScreenCapture:
    """Circular buffer for screen captures"""

    def __init__(self, max_images: int = 20, capture_interval: float = 0.25):
        self.max_images = max_images
        self.capture_interval = capture_interval
        self.images = deque(maxlen=max_images)
        self.last_capture_time = 0
        self.capture_count = 0

    def should_capture(self) -> bool:
        """Check if it's time for a new capture"""
        return time.time() - self.last_capture_time >= self.capture_interval

    def add(self, image):
        """Add image to circular buffer"""
        self.images.append({
            'image': image,
            'timestamp': time.time(),
            'index': self.capture_count
        })
        self.capture_count += 1
        self.last_capture_time = time.time()

        # Reset counter when buffer wraps
        if self.capture_count >= self.max_images:
            self.capture_count = 0

    def get_latest(self):
        """Get the most recent image"""
        if self.images:
            return self.images[-1]['image']
        return None

    def get_all(self) -> List:
        """Get all images in buffer"""
        return list(self.images)


class PokeMMOBot:
    """Integrated PokeMMO Autonomous Bot"""

    def __init__(self, config: Config):
        self.config = config
        self.running = False
        self.paused = False
        self.game_state = GameState.UNKNOWN

        # Game state data
        self.state_data = {
            "game_state": "OVERWORLD",
            "current_region": config.game.current_region,
            "badges": 0,
            "level_cap": 20,
            "money": 0,
            "party": [],
            "enemy": None,
            "inventory": {},
            "catch_list": config.game.catch_list,
            "weather": "Normal",
            "turn_count": 0,
        }

        # Session stats
        self.session_stats = {
            "start_time": time.time(),
            "battles": 0,
            "catches": 0,
            "faints": 0,
            "steps": 0,
            "llm_calls": 0,
        }

        # Screen capture buffer (max 20 images, capture every 0.25s)
        self.screen_capture = ScreenCapture(max_images=20, capture_interval=0.25)

        # Navigation state - walk in patterns, not random
        # Zigzag pattern to cover grass area: up, right, down, right, up, right, down, ...
        self.walk_pattern = ["up", "right", "down", "right"]
        self.walk_index = 0
        self.steps_in_direction = 0
        self.max_steps_per_direction = 5  # Walk 5 steps before turning

        # Dynamic player coordinates for regional mapping
        self.player_x = 50
        self.player_y = 50
        self.map_id = None

        # Initialize components
        self._init_components()

    def _init_components(self):
        """Initialize all bot components"""
        logger.info("=" * 50)
        logger.info("Initializing PokeMMO Bot...")
        logger.info("=" * 50)

        # 1. LLM Client
        logger.info("[1/5] LLM Client...")
        try:
            self.llm = LLMClient(self.config.llm)
            logger.info(f"  OK: {self.config.llm.provider}")
        except Exception as e:
            logger.error(f"  FAIL: {e}")
            self.llm = None

        # 2. Vision Engine + OCR
        logger.info("[2/5] Vision + OCR...")
        try:
            self.vision = VisionEngine()
            self.ocr = OCREngine(use_easyocr=True)
            logger.info("  OK: Vision + OCR ready")
        except Exception as e:
            logger.error(f"  FAIL: {e}")
            self.vision = None
            self.ocr = None

        # 3. Knowledge Graph
        logger.info("[3/5] Knowledge Graph...")
        try:
            data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
            builder = KnowledgeGraphBuilder(data_dir)
            self.graph = builder.build()
            self.graph_queries = GraphQueries(self.graph)
            logger.info(f"  OK: {self.graph.number_of_nodes()} nodes")
        except Exception as e:
            logger.error(f"  FAIL: {e}")
            self.graph = None
            self.graph_queries = None

        # 4. Input Engine + Navigation
        logger.info("[4/5] Input + Navigation...")
        try:
            self.input_engine = InputEngine()
            logger.info("  OK: Input engine ready")

            maps_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'maps')
            self.navigation = NavigationEngine(maps_dir, input_engine=self.input_engine)
            self.navigation.set_state_check_fn(lambda: self.state_data["game_state"])
            
            if self.navigation:
                # Load or create dynamic regional farm map
                self.map_id = f"{self.config.game.current_region.lower()}_farm_map"
                self.navigation.load_map(self.map_id)
                if not self.navigation.get_current_map():
                    from bot.navigation.map_data import MapData
                    from bot.navigation.pathfinder import AStarPathfinder
                    blank_map = MapData(
                        map_id=self.map_id,
                        name=f"{self.config.game.current_region} Dynamic Farm Map",
                        region=self.config.game.current_region,
                        width=100,
                        height=100,
                    )
                    self.navigation.map_loader.maps[self.map_id] = blank_map
                    self.navigation.map_loader.current_map = blank_map
                    self.navigation.pathfinder = AStarPathfinder(blank_map)
                
                # Align player position and mark current spot as walkable
                self.navigation.set_position(self.player_x, self.player_y)
                cur_map = self.navigation.get_current_map()
                if cur_map:
                    cur_map.walkable_coords.add((self.player_x, self.player_y))
                    self.navigation.map_loader.save_map(cur_map)
                    
            logger.info("  OK: Navigation and Dynamic Mapping ready")
        except Exception as e:
            logger.error(f"  FAIL: {e}")
            self.input_engine = None
            self.navigation = None

        # 5. Decision Engine
        logger.info("[5/5] Decision Engine...")
        self.decision_cache = {}
        logger.info("  OK: Ready")

        logger.info("=" * 50)
        logger.info("All components initialized!")
        logger.info("=" * 50)

    def start(self):
        """Start the bot"""
        self.running = True
        self.paused = False
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)

        logger.info("\n" + "=" * 50)
        logger.info("BOT STARTED")
        logger.info(f"Region: {self.config.game.current_region}")
        logger.info(f"Goal: {self.config.game.goal}")
        logger.info("=" * 50 + "\n")

        try:
            self._main_loop()
        except KeyboardInterrupt:
            logger.info("Interrupted")
        except Exception as e:
            logger.error(f"Error: {e}")
        finally:
            self.stop()

    def stop(self):
        """Stop the bot"""
        self.running = False
        self.paused = False
        self._save_session_stats()
        logger.info("\nBOT STOPPED")

    def pause(self):
        """Pause the bot"""
        self.paused = True
        logger.info("BOT PAUSED")

    def resume(self):
        """Resume the bot"""
        self.paused = False
        logger.info("BOT RESUMED")

    def _main_loop(self):
        """Main game loop - Sense -> Think -> Act"""
        while self.running:
            # Check for pause signal from GUI
            try:
                if os.path.exists("bot_signal.txt"):
                    with open("bot_signal.txt", "r") as f:
                        signal = f.read().strip()
                    if signal == "PAUSE":
                        self.paused = True
                    elif signal == "RESUME":
                        self.paused = False
                        os.remove("bot_signal.txt")
            except:
                pass

            # Check if paused
            if self.paused:
                time.sleep(0.1)
                continue

            try:
                # 1. SENSE: Capture screen and detect state
                self._sense()

                # 2. THINK: Make decision
                action = self._think()

                # 3. ACT: Execute action
                self._act(action)

                # 4. Small delay between cycles
                time.sleep(0.05)

            except Exception as e:
                logger.error(f"Loop error: {e}")
                time.sleep(1)

    def _sense(self):
        """Sense: Capture screen and detect game state"""
        if not self.vision:
            return

        try:
            # Check if it's time to capture (every 0.25s)
            if self.screen_capture.should_capture():
                # Capture screen
                frame = self.vision.capture_screen()

                # Add to circular buffer (max 20 images)
                self.screen_capture.add(frame)

                # Detect game state
                old_state = self.game_state
                self._detect_game_state(frame)

                # Log state change
                if old_state != self.game_state:
                    logger.info(f"State: {old_state.value} -> {self.game_state.value}")

                # Update state based on detection
                if self.game_state == GameState.BATTLE:
                    self._update_battle_state(frame)
                elif self.game_state == GameState.OVERWORLD:
                    self._update_overworld_state(frame)

        except Exception as e:
            logger.debug(f"Sense error: {e}")

    def _think(self) -> Dict[str, Any]:
        """Think: Make decision based on current state"""
        # Rule-based decisions first (fast)
        rule_action = self._rule_based_decision()
        if rule_action:
            return rule_action

        # LLM decisions for complex cases
        if self.llm:
            return self._llm_decision()

        # Default action
        return {"action": "wait", "duration": 0.5}

    def _act(self, action: Dict[str, Any]):
        """Act: Execute the decided action"""
        if not self.input_engine:
            return

        action_type = action.get("action", "wait")

        # Log action
        if action_type != "wait":
            direction = action.get("direction", "")
            slot = action.get("slot", "")
            logger.info(f"Action: {action_type} {direction} {slot}")

        if action_type == "walk":
            self._do_walk(action)
        elif action_type == "move":
            self._do_walk(action)
        elif action_type == "attack":
            self._do_attack(action)
        elif action_type == "catch":
            self._do_catch(action)
        elif action_type == "run":
            self._do_run()
        elif action_type == "heal":
            self._do_heal()
        elif action_type == "wait":
            time.sleep(action.get("duration", 0.5))
        else:
            # Default: walk in pattern
            self._do_walk_random()

    def _detect_game_state(self, frame):
        """Detect current game state from frame"""
        if not self.ocr:
            return

        try:
            # Check for battle menu
            battle_roi = self.vision.get_roi_image('combat_menu', frame)
            if battle_roi is not None:
                text = self.ocr.read_text(battle_roi)
                if text:
                    logger.debug(f"Combat menu text: {text[:50]}")
                    if "Fight" in text or "Bag" in text or "Pokemon" in text:
                        self.game_state = GameState.BATTLE
                        self.state_data["game_state"] = "BATTLE"
                        return

            # Check for dialog
            chat_roi = self.vision.get_roi_image('chat_box', frame)
            if chat_roi is not None:
                text = self.ocr.read_text(chat_roi)
                if text:
                    logger.debug(f"Chat box text: {text[:50]}")
                    if len(text) > 10:
                        self.game_state = GameState.DIALOG
                        self.state_data["game_state"] = "DIALOG"
                        return

            # Default: overworld
            self.game_state = GameState.OVERWORLD
            self.state_data["game_state"] = "OVERWORLD"

        except Exception as e:
            logger.debug(f"State detection error: {e}")

    def _update_battle_state(self, frame):
        """Update battle state from frame"""
        try:
            # Read enemy name
            enemy_roi = self.vision.get_roi_image('enemy_name', frame)
            if enemy_roi is not None and self.ocr:
                enemy_name = self.ocr.read_pokemon_name(enemy_roi)
                if enemy_name:
                    # Get enemy info from knowledge graph
                    enemy_info = None
                    if self.graph_queries:
                        enemy_info = self.graph_queries.get_pokemon_info(enemy_name)

                    self.state_data["enemy"] = {
                        "name": enemy_name,
                        "hp_percent": self._read_hp('enemy_hp_bar', frame),
                        "types": enemy_info.get('types', []) if enemy_info else [],
                    }

            # Read player Pokemon
            player_roi = self.vision.get_roi_image('player_name', frame)
            if player_roi is not None and self.ocr:
                player_name = self.ocr.read_pokemon_name(player_roi)
                if player_name:
                    self.state_data["party"] = [{
                        "name": player_name,
                        "hp_percent": self._read_hp('player_hp_bar', frame),
                    }]

        except Exception as e:
            logger.debug(f"Battle state error: {e}")

    def _update_overworld_state(self, frame):
        """Update overworld state and dynamically detect tall grass via CV (Method B)"""
        self.session_stats["steps"] += 1

        if frame is None:
            return

        try:
            import cv2
            import numpy as np

            # Tall Grass Visual Detection (Method B)
            # Take a small ROI at the player's feet (always centered on the screen)
            h, w, _ = frame.shape
            y_start = int(h * 0.52)
            y_end = int(h * 0.56)
            x_start = int(w * 0.48)
            x_end = int(w * 0.52)
            player_tile = frame[y_start:y_end, x_start:x_end]

            # Convert to HSV color space
            hsv = cv2.cvtColor(player_tile, cv2.COLOR_BGR2HSV)

            # Standard dark/saturated green threshold for GBA/NDS tall grass clumps
            lower_green = np.array([35, 40, 30])
            upper_green = np.array([85, 255, 200])

            # Apply mask and count the ratio of green pixels
            mask = cv2.inRange(hsv, lower_green, upper_green)
            green_ratio = np.sum(mask == 255) / mask.size

            # If green ratio exceeds 15%, register it as tall grass in dynamic map
            if green_ratio > 0.15:
                if self.navigation:
                    cur_map = self.navigation.get_current_map()
                    if cur_map:
                        coord = (self.player_x, self.player_y)
                        if coord not in cur_map.grass_coords:
                            cur_map.grass_coords.add(coord)
                            logger.info(f"🌾 Visual Grass detected at grid ({self.player_x}, {self.player_y}) [Green ratio: {green_ratio:.2f}]")
                            self.navigation.map_loader.save_map(cur_map)
        except Exception as e:
            logger.debug(f"Visual grass detection failed: {e}")

    def _read_hp(self, roi_name: str, frame) -> float:
        """Read HP percentage"""
        try:
            roi = self.vision.get_roi_image(roi_name, frame)
            if roi is not None:
                return self.vision.estimate_hp_percentage(roi_name, frame)
        except:
            pass
        return 100.0

    def _rule_based_decision(self) -> Optional[Dict]:
        """Rule-based decisions for common cases"""
        state = self.state_data["game_state"]

        # BATTLE STATE
        if state == "BATTLE":
            party = self.state_data.get("party", [])

            if party:
                player_hp = party[0].get("hp_percent", 100)

                # Low HP - try to run or use potion
                if player_hp < 30:
                    return {"action": "run"}

            # Default battle action - attack
            return {"action": "attack", "slot": 1}

        # DIALOG STATE
        if state == "DIALOG":
            return {"action": "walk", "direction": "confirm"}

        # OVERWORLD STATE
        if state == "OVERWORLD":
            # Check if need healing
            party_pokemon = self.state_data.get("party", [])
            if party_pokemon:
                avg_hp = sum(pk.get("hp_percent", 100) for pk in party_pokemon) / len(party_pokemon)
                if avg_hp < 40:
                    return {"action": "heal"}

            # Farm mode: walk around
            if self.config.game.goal == "farm":
                return {"action": "walk", "direction": self._random_direction()}

            # Catch mode: walk in grass
            if self.config.game.goal == "catch":
                return {"action": "walk", "direction": self._random_direction()}

            # Battle mode: look for trainers
            if self.config.game.goal == "battle":
                return {"action": "walk", "direction": self._random_direction()}

        return None

    def _llm_decision(self) -> Dict[str, Any]:
        """LLM-based decision"""
        try:
            context = json.dumps(self.state_data, indent=2)
            response = self.llm.chat_json(
                system_prompt=self._get_system_prompt(),
                user_message=context,
                max_tokens=200
            )
            self.session_stats["llm_calls"] += 1
            return response
        except Exception as e:
            logger.debug(f"LLM error: {e}")
            return {"action": "walk", "direction": self._random_direction()}

    def _get_system_prompt(self) -> str:
        """Get system prompt for LLM"""
        return """You are a PokeMMO bot. Reply with a single JSON action.

Actions:
{"action": "walk", "direction": "up|down|left|right"}
{"action": "attack", "slot": 1-4}
{"action": "catch", "ball": "Quick Ball|Ultra Ball|Timer Ball"}
{"action": "run"}
{"action": "heal"}

Priorities:
1. If HP < 30% in battle: run or heal
2. If enemy is in catch_list: catch
3. Otherwise: attack with best move
4. In overworld: walk to find Pokemon"""

    def _do_walk(self, action: Dict):
        """Execute walk action"""
        direction = action.get("direction", "up")

        if direction == "confirm":
            self.input_engine.confirm()
            time.sleep(0.1)
            return

        self.input_engine.walk(direction, duration=0.02)  # 20ms hold time
        self.session_stats["steps"] += 1

        # Track relative movement to dynamically map the region
        if direction == "up":
            self.player_y -= 1
        elif direction == "down":
            self.player_y += 1
        elif direction == "left":
            self.player_x -= 1
        elif direction == "right":
            self.player_x += 1

        # Register position and walkable tile in dynamic regional map
        if self.navigation:
            self.navigation.set_position(self.player_x, self.player_y)
            cur_map = self.navigation.get_current_map()
            if cur_map:
                coord = (self.player_x, self.player_y)
                if coord not in cur_map.walkable_coords:
                    cur_map.walkable_coords.add(coord)
                    # Discard from obstacles in case it was incorrectly marked
                    cur_map.obstacle_coords.discard(coord)
                    self.navigation.map_loader.save_map(cur_map)

    def _do_walk_random(self):
        """Walk in pattern (not random)"""
        direction = self._random_direction()
        self.input_engine.walk(direction, duration=0.02)

    def _do_attack(self, action: Dict):
        """Execute attack"""
        slot = action.get("slot", 1)
        self.input_engine.navigate_to_move(slot)
        time.sleep(0.05)
        self.input_engine.confirm()

    def _do_catch(self, action: Dict):
        """Execute catch"""
        self.input_engine.press_button('x')  # Open bag
        time.sleep(0.1)
        self.input_engine.confirm()
        time.sleep(0.05)
        self.input_engine.confirm()

    def _do_run(self):
        """Run from battle"""
        self.input_engine.press_button('down')
        time.sleep(0.05)
        self.input_engine.press_button('down')
        time.sleep(0.05)
        self.input_engine.press_button('right')
        time.sleep(0.05)
        self.input_engine.confirm()

    def _do_heal(self):
        """Heal at Pokemon Center"""
        self.input_engine.confirm()
        time.sleep(0.1)
        self.input_engine.confirm()
        time.sleep(1.5)
        self.input_engine.confirm()
        time.sleep(0.1)
        self.input_engine.confirm()

    def _random_direction(self) -> str:
        """Get next direction in walking pattern"""
        # Walk in pattern: up x10, down x10, up x10, down x10, ...
        # This covers grass area without spinning in circles

        self.steps_in_direction += 1

        # Change direction after max steps
        if self.steps_in_direction >= self.max_steps_per_direction:
            self.steps_in_direction = 0
            self.walk_index = (self.walk_index + 1) % len(self.walk_pattern)

        return self.walk_pattern[self.walk_index]

    def _save_session_stats(self):
        """Save session stats"""
        elapsed = time.time() - self.session_stats["start_time"]
        stats = {
            **self.session_stats,
            "duration_minutes": elapsed / 60,
        }
        logger.info(f"Session: {json.dumps(stats, indent=2)}")

    def _handle_shutdown(self, signum, frame):
        """Handle shutdown signal"""
        self.running = False


def main():
    parser = argparse.ArgumentParser(description="PokeMMO Bot")
    parser.add_argument("--provider", default="local_vllm", help="LLM provider")
    parser.add_argument("--region", default="Unova", help="Region")
    parser.add_argument("--goal", default="farm", help="Goal: farm/battle/catch/ev_train")
    parser.add_argument("--api-key", default=None, help="API key")
    args = parser.parse_args()

    config = Config()
    config.llm.provider = args.provider
    if args.api_key:
        config.llm.vllm_api_key = args.api_key
    config.game.current_region = args.region
    config.game.goal = args.goal

    bot = PokeMMOBot(config)
    bot.start()


if __name__ == "__main__":
    main()
