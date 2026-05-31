import os
import json
import math
import logging

logger = logging.getLogger(__name__)

class CatchCalculator:
    def __init__(self, data_dir='d:/PokeMMO/pokemmo_crawler/data'):
        self.data_dir = data_dir
        self.species = {}
        self.load_species_database()

    def load_species_database(self):
        try:
            filepath = os.path.join(self.data_dir, 'species.json')
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    for s in json.load(f):
                        self.species[s['id']] = s
                logger.info(f"CatchCalculator loaded {len(self.species)} species catch rates.")
        except Exception as e:
            logger.error(f"Error loading species catch rates: {e}")

    def to_id(self, name):
        import re
        return re.sub(r'[^a-z0-9]', '', name.lower())

    def get_base_catch_rate(self, species_name: str) -> int:
        sid = self.to_id(species_name)
        if sid in self.species:
            return self.species[sid].get("catchRate", 255)
        return 255

    def calculate_catch_probability(self, species_name: str, hp_percent: float, status: str, 
                                    ball_name: str, turn_count: int = 1, 
                                    is_cave: bool = False, is_night: bool = False,
                                    attacker_level: int = 50, defender_level: int = 50) -> float:
        """
        Calculates catch probability based on Gen 8 PokeMMO mechanics.
        Returns percentage (0.0 to 100.0).
        """
        catch_rate = self.get_base_catch_rate(species_name)

        # 1. Status Modifier
        status = (status or "").lower()
        if status in ["sleep", "slp", "freeze", "frz"]:
            mod_status = 2.5
        elif status in ["paralysis", "par", "poison", "psn", "burn", "brn", "tê liệt", "ngủ"]:
            mod_status = 1.5
        else:
            mod_status = 1.0

        # 2. Ball Modifier
        ball_name_clean = ball_name.lower().replace(" ", "")
        mod_ball = 1.0
        
        if ball_name_clean == "quickball":
            mod_ball = 5.0 if turn_count == 1 else 1.0
        elif ball_name_clean == "duskball":
            mod_ball = 2.5 if (is_cave or is_night) else 1.0
        elif ball_name_clean == "netball":
            sid = self.to_id(species_name)
            types = []
            if sid in self.species:
                types = [t.lower() for t in self.species[sid].get("types", [])]
            if "water" in types or "bug" in types:
                mod_ball = 2.5
        elif ball_name_clean == "timerball":
            mod_ball = min(4.0, 1.0 + (turn_count - 1) * 0.3)
        elif ball_name_clean == "nestball":
            mod_ball = max(1.0, min(4.0, (40 - defender_level) / 10.0))
        elif ball_name_clean == "levelball":
            level_ratio = attacker_level / max(1, defender_level)
            if level_ratio >= 4.0:
                mod_ball = 8.0
            elif level_ratio >= 2.0:
                mod_ball = 4.0
            elif level_ratio > 1.0:
                mod_ball = 2.0
            else:
                mod_ball = 1.0
        elif ball_name_clean == "repeatball":
            mod_ball = 2.5
        elif ball_name_clean == "ultraball":
            mod_ball = 2.0
        elif ball_name_clean == "greatball":
            mod_ball = 1.5
        else:
            mod_ball = 1.0

        # 3. Calculate 'a' index
        hp_factor = (300.0 - 2.0 * hp_percent) / 300.0
        a = hp_factor * catch_rate * mod_ball * mod_status
        
        if a >= 255.0:
            return 100.0

        # 4. Calculate 'b' index
        try:
            b = int(65536 * math.pow(a / 255.0, 0.25))
            prob = math.pow(b / 65536.0, 4) * 100.0
            return max(0.0, min(100.0, prob))
        except Exception:
            return max(0.0, min(100.0, (a / 255.0) * 100.0))

    def recommend_best_ball(self, species_name: str, hp_percent: float, status: str, 
                            turn_count: int = 1, is_cave: bool = False, is_night: bool = False,
                            attacker_level: int = 50, defender_level: int = 50,
                            inventory: dict = None) -> dict:
        """
        Recommends the best ball to use from inventory based on catch probability.
        """
        inventory = inventory or {}
        balls_in_stock = inventory.get("pokeballs", {})
        
        if not balls_in_stock:
            # Fallback to defaults if empty
            balls_in_stock = {"Poke Ball": 99}

        recommendations = []
        for ball_name, count in balls_in_stock.items():
            if count <= 0:
                continue
            prob = self.calculate_catch_probability(
                species_name, hp_percent, status, ball_name, turn_count,
                is_cave, is_night, attacker_level, defender_level
            )
            recommendations.append({
                "ball_name": ball_name,
                "probability": prob,
                "vietnamese_probability": f"{prob:.1f}%",
                "count": count
            })

        if not recommendations:
            return {"ball_name": "Poke Ball", "probability": 0.0, "reason": "Không có Pokéball trong túi đồ"}

        # Sort by probability descending
        recommendations.sort(key=lambda x: x["probability"], reverse=True)
        best = recommendations[0]
        
        # Check if cheaper balls are highly effective to save premium balls
        for rec in recommendations:
            if rec["ball_name"] in ["Poke Ball", "Great Ball"] and rec["probability"] >= 90.0:
                return {**rec, "reason": f"Sử dụng {rec['ball_name']} tiết kiệm do tỉ lệ bắt cao ({rec['probability']:.1f}%)"}

        return {**best, "reason": f"Tỉ lệ bắt tốt nhất với {best['ball_name']} ({best['probability']:.1f}%)"}
