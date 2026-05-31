import os
import json
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class WeatherStrategyEngine:
    def __init__(self, data_dir='d:/PokeMMO/pokemmo_crawler/data'):
        self.data_dir = data_dir
        self.teams = []
        self.load_teams_database()

    def load_teams_database(self):
        try:
            filepath = os.path.join(self.data_dir, 'recommended_teams.json')
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    self.teams = json.load(f)
                logger.info(f"WeatherStrategyEngine loaded {len(self.teams)} weather templates.")
        except Exception as e:
            logger.error(f"Error loading recommended teams database: {e}")

    def to_id(self, name: str) -> str:
        import re
        return re.sub(r'[^a-z0-9]', '', name.lower())

    def detect_party_strategy(self, party: List[dict]) -> Optional[str]:
        """
        Scans the party list and detects if we are running a recommended weather strategy.
        Requires at least 2 weather-related members including the weather setter to trigger.
        """
        if not party:
            return None

        party_names = [self.to_id(p.get("name", "")) for p in party]
        
        # Weather setter mappings
        setters = {
            "Rain": "pelipper",
            "Sun": "torkoal",
            "Sandstorm": "tyranitar"
        }
        
        # Core member lists (lowercase)
        core_members = {
            "Rain": ["pelipper", "kingdra", "kabutops", "ludicolo", "scizor", "garchomp"],
            "Sun": ["torkoal", "venusaur", "darmanitan", "charizard", "rotomwash", "garchomp"],
            "Sandstorm": ["tyranitar", "excadrill", "garchomp", "reuniclus", "skarmory", "rotomwash"]
        }

        for weather, setter in setters.items():
            # Check if setter is in party
            if setter in party_names:
                # Count how many core members are present
                core_count = sum(1 for name in party_names if name in core_members[weather])
                if core_count >= 2:
                    return weather

        return None

    def evaluate_weather_tactics(self, party: List[dict], current_weather: str) -> Optional[dict]:
        """
        Evaluates weather-related tactical decisions and provides clear strategic advice and switch recommendations.
        """
        strategy = self.detect_party_strategy(party)
        if not strategy:
            return None

        current_weather = (current_weather or "Normal").lower()
        party_names = [self.to_id(p.get("name", "")) for p in party]
        
        # 1. RAIN STRATEGY
        if strategy == "Rain":
            if current_weather != "rain":
                # Find healthy Pelipper in reserves (slot 2-6)
                pelipper_slot = None
                for i in range(1, len(party)):
                    member = party[i]
                    if self.to_id(member.get("name", "")) == "pelipper" and member.get("hp_percent", 100.0) > 0:
                        pelipper_slot = i + 1
                        break
                
                if pelipper_slot:
                    return {
                        "strategy": "Rain",
                        "vietnamese_strategy": "Đội hình Mưa",
                        "weather_active": False,
                        "strategic_advice": "Thời tiết Mưa chưa hoạt động. Khuyên nghị hoán đổi ngay sang Pelipper để kích hoạt nội tại Drizzle tạo mưa tự động kéo dài 8 lượt (Damp Rock).",
                        "recommended_action": {"action": "switch", "slot": pelipper_slot}
                    }
                else:
                    return {
                        "strategy": "Rain",
                        "vietnamese_strategy": "Đội hình Mưa",
                        "weather_active": False,
                        "strategic_advice": "Thời tiết Mưa chưa hoạt động và Pelipper đã ngất hoặc đang ra trận. Hãy tìm cách duy trì nhịp độ chiến đấu.",
                        "recommended_action": None
                    }
            else:
                return {
                    "strategy": "Rain",
                    "vietnamese_strategy": "Đội hình Mưa",
                    "weather_active": True,
                    "strategic_advice": "Thời tiết Mưa đang hoạt động! Kingdra, Kabutops, và Ludicolo được nhân đôi Tốc độ (Swift Swim). Các chiêu thức hệ Nước của ta được tăng 1.5x sát thương. Ưu tiên quét sạch bằng chiêu hệ Nước!",
                    "recommended_action": None
                }

        # 2. SUN STRATEGY
        elif strategy == "Sun":
            if current_weather != "sun" and current_weather != "sunny":
                # Find healthy Torkoal in reserves (slot 2-6)
                torkoal_slot = None
                for i in range(1, len(party)):
                    member = party[i]
                    if self.to_id(member.get("name", "")) == "torkoal" and member.get("hp_percent", 100.0) > 0:
                        torkoal_slot = i + 1
                        break
                
                if torkoal_slot:
                    return {
                        "strategy": "Sun",
                        "vietnamese_strategy": "Đội hình Nắng",
                        "weather_active": False,
                        "strategic_advice": "Thời tiết Nắng chưa hoạt động. Khuyên nghị hoán đổi ngay sang Torkoal để kích hoạt nội tại Drought tạo nắng kéo dài 8 lượt (Heat Rock).",
                        "recommended_action": {"action": "switch", "slot": torkoal_slot}
                    }
            else:
                return {
                    "strategy": "Sun",
                    "vietnamese_strategy": "Đội hình Nắng",
                    "weather_active": True,
                    "strategic_advice": "Thời tiết Nắng đang hoạt động! Venusaur được nhân đôi Tốc độ (Chlorophyll). Chiêu hệ Lửa tăng 1.5x sát thương (Flare Blitz của Darmanitan cực mạnh). Chiêu Weather Ball chuyển thành Lửa (100 BP).",
                    "recommended_action": None
                }

        # 3. SANDSTORM STRATEGY
        elif strategy == "Sandstorm":
            if current_weather != "sandstorm":
                # Find healthy Tyranitar in reserves (slot 2-6)
                ttar_slot = None
                for i in range(1, len(party)):
                    member = party[i]
                    if self.to_id(member.get("name", "")) == "tyranitar" and member.get("hp_percent", 100.0) > 0:
                        ttar_slot = i + 1
                        break
                
                if ttar_slot:
                    return {
                        "strategy": "Sandstorm",
                        "vietnamese_strategy": "Đội hình Bão Cát",
                        "weather_active": False,
                        "strategic_advice": "Thời tiết Bão Cát chưa hoạt động. Khuyên nghị hoán đổi sang Tyranitar để kích hoạt Sand Stream tạo bão cát tự động kéo dài 8 lượt.",
                        "recommended_action": {"action": "switch", "slot": ttar_slot}
                    }
            else:
                return {
                    "strategy": "Sandstorm",
                    "vietnamese_strategy": "Đội hình Bão Cát",
                    "weather_active": True,
                    "strategic_advice": "Thời tiết Bão Cát đang hoạt động! Excadrill được nhân đôi Tốc độ (Sand Rush). Hệ Đá (Tyranitar) được tăng 1.5x Thủ đặc biệt. Đối phương chịu sát thương bào mòn 1/16 HP mỗi lượt (trừ Đá/Đất/Thép).",
                    "recommended_action": None
                }

        return None
