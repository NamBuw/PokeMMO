"""
PokeMMO Bot Configuration
Hỗ trợ nhiều LLM providers: Mimo, Gemma 4 (Google), OpenAI-compatible
"""
import os
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class LLMConfig:
    """Cấu hình LLM - có thể tùy chỉnh endpoint và API key"""

    # === CHỌN PROVIDER ===
    # "mimo" | "gemma" | "openai" | "custom" | "local_vllm"
    provider: str = "local_vllm"

    # === MIMO CONFIG ===
    mimo_api_base: str = "https://token-plan-sgp.xiaomimimo.com/anthropic"
    mimo_api_key: str = os.getenv("MIMO_API_KEY", "")
    mimo_model: str = "mimo-v2.5-pro"

    # === GEMMA 4 CONFIG (Google AI) ===
    gemma_api_base: str = "https://generativelanguage.googleapis.com/v1beta"
    gemma_api_key: str = os.getenv("GEMMA_API_KEY", "")
    # gemma-4-31b-it (31B params) hoặc gemma-4-26b-a4b-it (26B, nhanh hơn)
    gemma_model: str = "gemma-4-26b-a4b-it"

    # === OPENAI-COMPATIBLE CONFIG ===
    openai_api_base: str = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = "gpt-4o-mini"

    # === LOCAL VLLM CONFIG ===
    vllm_api_base: str = "https://gemma.ctslab.net/v1"
    vllm_api_key: str = "gemma4-openclaw-2026"
    vllm_model: str = "gemma-4"

    # === CUSTOM ENDPOINT ===
    custom_api_base: str = os.getenv("CUSTOM_API_BASE", "")
    custom_api_key: str = os.getenv("CUSTOM_API_KEY", "")
    custom_model: str = ""
    custom_api_format: str = "openai"  # "openai" | "gemini"

    # === SHARED SETTINGS ===
    temperature: float = 0.3
    max_tokens: int = 1024
    timeout_seconds: int = 30

    def get_active_config(self) -> dict:
        """Trả về config của provider đang chọn"""
        if self.provider == "mimo":
            return {
                "api_base": self.mimo_api_base,
                "api_key": self.mimo_api_key,
                "model": self.mimo_model,
                "api_format": "openai",
            }
        elif self.provider == "gemma":
            return {
                "api_base": self.gemma_api_base,
                "api_key": self.gemma_api_key,
                "model": self.gemma_model,
                "api_format": "gemini",
            }
        elif self.provider == "openai":
            return {
                "api_base": self.openai_api_base,
                "api_key": self.openai_api_key,
                "model": self.openai_model,
                "api_format": "openai",
            }
        elif self.provider == "local_vllm":
            return {
                "api_base": self.vllm_api_base,
                "api_key": self.vllm_api_key,
                "model": self.vllm_model,
                "api_format": "openai",
            }
        elif self.provider == "custom":
            return {
                "api_base": self.custom_api_base,
                "api_key": self.custom_api_key,
                "model": self.custom_model,
                "api_format": self.custom_api_format,
            }
        else:
            raise ValueError(f"Unknown provider: {self.provider}")


@dataclass
class VisionConfig:
    """Cấu hình Computer Vision"""
    # Game window bounding box (calibrate khi chạy)
    game_bbox: Dict[str, int] = field(default_factory=lambda: {
        "top": 0, "left": 0, "width": 1920, "height": 1080
    })

    # OCR settings
    ocr_confidence_threshold: float = 0.6
    fuzzy_match_threshold: int = 80  # for rapidfuzz
    ocr_upscale: float = 2.0  # upscale ảnh trước OCR

    # Capture interval
    capture_interval_ms: int = 500

    # ROIs (fraction of game window: x%, y%, w%, h%)
    rois: Dict[str, tuple] = field(default_factory=lambda: {
        "enemy_name":    (0.10, 0.05, 0.30, 0.08),
        "enemy_hp_bar":  (0.15, 0.15, 0.25, 0.02),
        "player_name":   (0.55, 0.70, 0.20, 0.05),
        "player_hp_bar": (0.55, 0.76, 0.20, 0.02),
        "combat_menu":   (0.60, 0.75, 0.35, 0.20),
        "move_list":     (0.60, 0.80, 0.35, 0.15),
        "chat_box":      (0.05, 0.80, 0.40, 0.15),
        "party_indicator": (0.01, 0.45, 0.08, 0.25),
        "exp_bar":       (0.15, 0.72, 0.25, 0.01),
        "level_text":    (0.72, 0.70, 0.05, 0.04),
    })


@dataclass
class AntiDetectionConfig:
    """Cấu hình anti-bot-detection"""
    # Timing profiles: (base_ms, std_ms, min_ms, max_ms)
    timing_profiles: Dict[str, tuple] = field(default_factory=lambda: {
        "button_press":   (80,  30,  40,  200),
        "walk_step":      (250, 80,  100, 600),
        "menu_nav":       (150, 50,  80,  400),
        "battle_action":  (500, 200, 200, 1200),
        "dialog_advance": (300, 100, 150, 800),
    })

    # Session management
    session_max_minutes: int = 90
    session_min_minutes: int = 45
    break_min_minutes: int = 15
    break_max_minutes: int = 45
    micro_break_interval_min: int = 20
    micro_break_interval_max: int = 30
    micro_break_duration_min: int = 30  # seconds
    micro_break_duration_max: int = 120  # seconds

    # Randomization probabilities
    idle_pause_probability: float = 0.03  # 3% mỗi bước
    wrong_step_probability: float = 0.01  # 1% mỗi bước
    suboptimal_move_probability: float = 0.05  # 5% trong wild battle
    micro_correction_probability: float = 0.15  # 15% sau mỗi bước

    # Daily limits
    max_daily_hours: float = 8.0
    no_play_start_hour: int = 2  # 2AM
    no_play_end_hour: int = 6    # 6AM


@dataclass
class GameConfig:
    """Cấu hình game"""
    # Region đang chơi
    current_region: str = "Kanto"

    # Mục tiêu
    goal: str = "farm"  # "farm" | "catch" | "ev_train" | "progress" | "competitive"

    # Catch list (Pokemon muốn bắt)
    catch_list: list = field(default_factory=lambda: [
        "Garchomp", "Gyarados", "Scizor", "Alakazam",
        "Tyranitar", "Dragonite", "Metagross", "Salamence",
        "Arcanine", "Gengar",
    ])

    # Team template
    team_template: str = "rain"  # "rain" | "sun" | "sand" | "custom"

    # HP thresholds
    heal_hp_threshold: float = 0.35  # Heal khi HP < 35%
    critical_hp_threshold: float = 0.25  # Critical = cần switch/heal ngay

    # Pokecenter
    visit_center_after_battles: int = 20  # Về center sau N battle


@dataclass
class Config:
    """Config tổng"""
    llm: LLMConfig = field(default_factory=LLMConfig)
    vision: VisionConfig = field(default_factory=VisionConfig)
    anti_detection: AntiDetectionConfig = field(default_factory=AntiDetectionConfig)
    game: GameConfig = field(default_factory=GameConfig)

    # Paths
    data_dir: str = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "pokemmo_crawler", "data")
    log_dir: str = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
    template_dir: str = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vision", "templates")
    log_level: str = "INFO"


# === QUICK CONFIG PRESETS ===

def get_gemma_config(api_key: str) -> Config:
    """Config preset cho Gemma 4"""
    config = Config()
    config.llm.provider = "gemma"
    config.llm.gemma_api_key = api_key
    config.llm.gemma_model = "gemma-4-26b-a4b-it"
    return config


def get_mimo_config(api_key: str) -> Config:
    """Config preset cho Mimo"""
    config = Config()
    config.llm.provider = "mimo"
    config.llm.mimo_api_key = api_key
    return config


def get_custom_config(api_base: str, api_key: str, model: str,
                      api_format: str = "openai") -> Config:
    """Config preset cho custom endpoint (OpenAI-compatible hoặc Gemini)"""
    config = Config()
    config.llm.provider = "custom"
    config.llm.custom_api_base = api_base
    config.llm.custom_api_key = api_key
    config.llm.custom_model = model
    config.llm.custom_api_format = api_format
    return config
