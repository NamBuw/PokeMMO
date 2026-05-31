"""
PokeMMO Autonomous Bot - Main Entry Point
Usage: python -m bot.main [--config config_file] [--dry-run]
"""
import sys
import json
import time
import signal
import logging
import argparse
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from bot.config import Config
from bot.llm.client import LLMClient
from bot.knowledge.damage_calc import DamageCalculator
from bot.knowledge.graph.builder import KnowledgeGraphBuilder
from bot.knowledge.graph.queries import GraphQueries


# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('pokemmo_bot.log'),
    ]
)
logger = logging.getLogger('PokeMMO')


class PokeMMOBot:
    """Main bot class - orchestrates all modules"""

    def __init__(self, config: Config):
        self.config = config
        self.running = False

        # Initialize LLM
        logger.info(f"Initializing LLM: {config.llm.provider}")
        self.llm = LLMClient(config.llm)

        # Initialize damage calculator
        logger.info("Loading game data...")
        self.damage_calc = DamageCalculator(config.data_dir)

        # Initialize knowledge graph
        logger.info("Building knowledge graph...")
        try:
            self.graph = KnowledgeGraphBuilder(config.data_dir).build()
            self.queries = GraphQueries(self.graph)
            logger.info("Knowledge graph built successfully!")
        except Exception as e:
            logger.error(f"Failed to build knowledge graph: {e}", exc_info=True)
            self.graph = None
            self.queries = None

        # Game state
        self.game_state = {
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
        }

        logger.info("PokeMMO Bot initialized!")

    def start(self):
        """Start the bot main loop"""
        self.running = True
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)

        logger.info("=" * 50)
        logger.info("PokeMMO Autonomous Bot STARTED")
        logger.info(f"Provider: {self.config.llm.provider}")
        logger.info(f"Region: {self.config.game.current_region}")
        logger.info(f"Goal: {self.config.game.goal}")
        logger.info("=" * 50)

        try:
            self._main_loop()
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        finally:
            self.stop()

    def stop(self):
        """Stop the bot gracefully"""
        self.running = False
        self._save_session_stats()
        logger.info("Bot stopped.")

    def _main_loop(self):
        """Main game loop"""
        while self.running:
            try:
                # 1. Capture screen & update game state
                self._update_game_state()

                # 2. Make decision via LLM
                action = self._make_decision()

                # 3. Execute action
                self._execute_action(action)

                # 4. Anti-detection delay
                self._human_delay()

                # 5. Check session limits
                if self._should_take_break():
                    self._take_break()

            except Exception as e:
                logger.error(f"Error in main loop: {e}", exc_info=True)
                time.sleep(2)

    def _update_game_state(self):
        """Update game state from vision (placeholder)"""
        # TODO: Connect to vision engine
        pass

    def _make_decision(self) -> dict:
        """Make a decision using LLM"""
        from bot.llm.prompts import SYSTEM_PROMPT

        # Augment with Knowledge Graph data if in BATTLE state
        state_to_send = dict(self.game_state)
        
        if self.game_state.get("game_state") == "BATTLE" and self.game_state.get("enemy"):
            enemy_name = self.game_state["enemy"].get("name")
            if enemy_name and self.queries:
                try:
                    pokemon_info = self.queries.get_pokemon_info(enemy_name)
                    if pokemon_info:
                        knowledge_base = {}
                        enemy_types = pokemon_info.get("types", [])
                        knowledge_base["enemy_types"] = enemy_types
                        
                        # Combined defensive type matchups
                        multipliers = {}
                        all_types = ["Normal", "Fire", "Water", "Electric", "Grass", "Ice", "Fighting", "Poison", 
                                     "Ground", "Flying", "Psychic", "Bug", "Rock", "Ghost", "Dragon", "Dark", "Steel", "Fairy"]
                        for t in all_types:
                            multipliers[t] = 1.0
                            
                        for et in enemy_types:
                            matchups = self.queries.get_type_matchups(et)
                            if matchups:
                                for weak in matchups.get("defensive", {}).get("weak_to", []):
                                    multipliers[weak] *= 2.0
                                for resist in matchups.get("defensive", {}).get("resists", []):
                                    multipliers[resist] *= 0.5
                                    
                            type_node = f"type_{et.lower()}"
                            if type_node in self.queries.graph:
                                for source, _, data in self.queries.graph.in_edges(type_node, data=True):
                                    if data.get("relation") == "immune":
                                        attacker_name = self.queries.graph.nodes[source].get("name", "")
                                        if attacker_name:
                                            multipliers[attacker_name] = 0.0

                        double_weak = [t for t, m in multipliers.items() if m == 4.0]
                        weak = [t for t, m in multipliers.items() if m == 2.0]
                        resist = [t for t, m in multipliers.items() if m == 0.5]
                        double_resist = [t for t, m in multipliers.items() if m == 0.25]
                        immune = [t for t, m in multipliers.items() if m == 0.0]
                        
                        knowledge_base["double_weaknesses"] = double_weak
                        knowledge_base["weaknesses"] = weak
                        knowledge_base["resistances"] = resist
                        knowledge_base["double_resistances"] = double_resist
                        knowledge_base["immunities"] = immune
                        
                        counters = self.queries.get_pokemon_counters(enemy_name)
                        if counters:
                            knowledge_base["recommended_counters"] = [c.get("name") for c in counters[:3]]
                            
                        state_to_send["knowledge_base"] = knowledge_base
                except Exception as ex:
                    logger.warning(f"Error querying knowledge graph: {ex}")

        context = json.dumps(state_to_send, indent=2)

        try:
            action = self.llm.chat_json(SYSTEM_PROMPT, context)
            logger.info(f"LLM decision: {action.get('action', 'unknown')}")
            return action
        except Exception as e:
            logger.error(f"LLM decision failed: {e}")
            return {"action": "wait", "parameters": {"duration_ms": 2000}}

    def _execute_action(self, action: dict):
        """Execute an action (placeholder)"""
        action_type = action.get("action", "wait")
        logger.debug(f"Executing: {action_type}")
        # TODO: Connect to action executor
        pass

    def _human_delay(self):
        """Add human-like delay between actions"""
        import random
        profiles = self.config.anti_detection.timing_profiles
        base, std, min_d, max_d = profiles.get("battle_action", (500, 200, 200, 1200))
        delay = random.gauss(base, std) / 1000
        delay = max(min_d / 1000, min(max_d / 1000, delay))
        time.sleep(delay)

    def _should_take_break(self) -> bool:
        """Check if it's time for a break"""
        elapsed_min = (time.time() - self.session_stats["start_time"]) / 60
        return elapsed_min >= self.config.anti_detection.session_max_minutes

    def _take_break(self):
        """Take a break"""
        import random
        break_min = random.randint(
            self.config.anti_detection.break_min_minutes,
            self.config.anti_detection.break_max_minutes
        )
        logger.info(f"Taking a break for {break_min} minutes...")
        time.sleep(break_min * 60)
        self.session_stats["start_time"] = time.time()

    def _save_session_stats(self):
        """Save session statistics"""
        elapsed = time.time() - self.session_stats["start_time"]
        stats = {
            **self.session_stats,
            "duration_minutes": elapsed / 60,
            "end_time": time.time(),
        }
        logger.info(f"Session stats: {json.dumps(stats, indent=2)}")

    def _handle_shutdown(self, signum, frame):
        """Handle shutdown signal"""
        logger.info("Shutdown signal received...")
        self.running = False


def main():
    parser = argparse.ArgumentParser(description="PokeMMO Autonomous Bot")
    parser.add_argument("--provider", default="local_vllm",
                        choices=["local_vllm", "gemma", "mimo", "openai", "custom"],
                        help="LLM provider")
    parser.add_argument("--api-key", default=None, help="API key for LLM")
    parser.add_argument("--region", default="Kanto", help="Starting region")
    parser.add_argument("--goal", default="farm", help="Bot goal")
    parser.add_argument("--dry-run", action="store_true", help="Dry run mode")
    args = parser.parse_args()

    config = Config()
    config.llm.provider = args.provider
    if args.api_key:
        config.llm.vllm_api_key = args.api_key
    config.game.current_region = args.region
    config.game.goal = args.goal

    bot = PokeMMOBot(config)

    if args.dry_run:
        logger.info("DRY RUN - Testing LLM connection...")
        response = bot.llm.chat(
            system_prompt="You are a PokeMMO bot. Reply with JSON.",
            user_message='{"test": true}',
            max_tokens=50
        )
        logger.info(f"LLM response: {response}")
    else:
        bot.start()


if __name__ == "__main__":
    main()
