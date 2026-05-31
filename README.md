# 🎮 PokeMMO Autonomous Bot

Bot chơi PokeMMO tự động dựa trên **LLM** + **Computer Vision**. Sử dụng Gemma 4 (local vLLM) để đưa ra quyết định chiến thuật, OpenCV + Tesseract để đọc màn hình.

## 📋 Mục lục

- [Tính năng](#-tính-năng)
- [Cấu trúc project](#-cấu-trúc-project)
- [Yêu cầu hệ thống](#-yêu-cầu-hệ-thống)
- [Cài đặt](#-cài-đặt)
- [Cấu hình](#-cấu-hình)
- [Sử dụng](#-sử-dụng)
- [Dữ liệu game](#-dữ-liệu-game)
- [Chi tiết kỹ thuật](#-chi-tiết-kỹ-thuật)

## 🚀 Tính năng

- **Auto Farming**: Tự động đánh Pokemon hoang dã để kiếm XP
- **Auto Catching**: Tự động bắt Pokemon (ưu tiên Quick Ball, tính catch rate)
- **Battle AI**: LLM chọn move tối ưu dựa trên type effectiveness, damage calc
- **Anti-Bot-Detection**: Timing randomization, session management, human-like behavior
- **Multi-Provider LLM**: Hỗ trợ Gemma 4 (local), Mimo, OpenAI, custom endpoints

## 📁 Cấu trúc project

```
PokeMMO/
├── bot/                        # Bot source code
│   ├── main.py                 # Entry point
│   ├── config.py               # Configuration (LLM, Vision, AntiDetection)
│   ├── pokemmo_api.py          # Game API controller
│   ├── llm/                    # LLM integration
│   │   ├── client.py           # Universal LLM client (OpenAI/Gemini/vLLM)
│   │   └── prompts.py          # System prompts & few-shot examples
│   ├── vision/                 # Computer Vision
│   │   ├── vision_engine.py    # Screen capture, OCR, HP detection
│   │   └── templates/          # Template images for matching
│   ├── knowledge/              # Game knowledge base
│   │   └── damage_calc.py      # Damage calculator (Gen 8 mechanics)
│   ├── action/                 # Input control
│   │   ├── input_engine.py     # Keyboard + Mouse control
│   │   └── mouse.py            # Mouse interaction
│   └── state/                  # Game state management
├── data/                       # Game data (JSON)
│   ├── species.json            # 729 Pokemon species
│   ├── moves.json              # 578 moves
│   ├── location_data.json      # 310 locations across 5 regions
│   ├── type_matrix.json        # 17x17 type effectiveness
│   ├── abilities.json          # 167 abilities
│   ├── held_items.json         # 117 held items
│   ├── pokeballs.json          # 13 ball types
│   ├── medicine.json           # Healing items
│   ├── learnsets.json          # Move learnsets
│   ├── natures.json            # 25 natures
│   ├── level_caps.json         # Badge level caps
│   ├── recommended_teams.json  # Team templates
│   └── pokemmo_complete_database.json  # Master database
├── scripts/                    # Utility scripts
│   ├── crawl_main.py           # Wiki scraper
│   ├── generate_datasets.py    # Data generator
│   └── damage_server.js        # Node.js damage calc server
├── docs/                       # Documentation
│   └── SPECIFICATION.md        # Full specification
├── tests/                      # Tests
├── .gitignore
├── package.json                # Node.js dependencies
└── README.md                   # This file
```

## 💻 Yêu cầu hệ thống

### Hardware
- **GPU**: NVIDIA với ≥8GB VRAM (L40S, RTX 3090, RTX 4090, etc.)
- **RAM**: ≥16GB
- **Storage**: ≥10GB

### Software
- **OS**: Linux (Ubuntu 20.04+) hoặc Windows
- **Python**: 3.10+
- **Node.js**: 18+ (cho data scripts)
- **CUDA**: 11.8+ (cho vLLM)

## 🔧 Cài đặt

### 1. Clone repository

```bash
git clone https://github.com/NamBuw/PokeMMO.git
cd PokeMMO
```

### 2. Cài Python dependencies

```bash
pip install opencv-python pytesseract mss numpy requests pyautogui pynput pillow rapidfuzz
```

### 3. Cài Tesseract OCR

```bash
# Ubuntu/Debian
sudo apt install tesseract-ocr

# Windows
# Download từ: https://github.com/UB-Mannheim/tesseract/wiki

# macOS
brew install tesseract
```

### 4. Cài Node.js dependencies (cho data scripts)

```bash
npm install
```

### 5. Cài vLLM (nếu chạy local)

```bash
pip install vllm
```

### 6. Chạy vLLM server với Gemma 4

```bash
# Download model (nếu chưa có)
# Gemma 4 available trên Hugging Face hoặc Google AI

# Chạy vLLM server
vllm serve /path/to/gemma-4 \
    --served-model-name gemma-4 \
    --max-model-len 16384 \
    --gpu-memory-utilization 0.65 \
    --api-key your-api-key-here \
    --port 8080 \
    --quantization modelopt \
    --dtype auto \
    --kv-cache-dtype fp8 \
    --trust-remote-code
```

## ⚙️ Cấu hình

### Config cơ bản (`bot/config.py`)

```python
from bot.config import Config

config = Config()

# LLM Provider
config.llm.provider = "local_vllm"  # "local_vllm" | "gemma" | "mimo" | "openai"
config.llm.vllm_api_base = "http://localhost:8080/v1"
config.llm.vllm_api_key = "your-api-key"
config.llm.vllm_model = "gemma-4"

# Game settings
config.game.current_region = "Kanto"
config.game.goal = "farm"  # "farm" | "catch" | "ev_train" | "progress"
config.game.catch_list = ["Garchomp", "Gyarados", "Scizor"]
```

### Config presets

```python
from bot.config import get_gemma_config, get_mimo_config, get_custom_config

# Gemma 4 (Google AI Studio)
config = get_gemma_config(api_key="AIzaSy...")

# Mimo
config = get_mimo_config(api_key="tp-...")

# Custom OpenAI-compatible endpoint
config = get_custom_config(
    api_base="https://your-endpoint.com/v1",
    api_key="your-key",
    model="your-model"
)
```

### Environment variables

```bash
export GEMMA_API_KEY="your-gemma-key"
export MIMO_API_KEY="your-mimo-key"
export OPENAI_API_KEY="your-openai-key"
```

## 🎯 Sử dụng

### Chạy bot

```bash
# Với local vLLM (default)
python -m bot.main

# Với Gemma 4 (Google AI)
python -m bot.main --provider gemma --api-key YOUR_KEY

# Với custom endpoint
python -m bot.main --provider custom --api-key YOUR_KEY

# Dry run (test LLM connection)
python -m bot.main --dry-run

# Chỉ định region và goal
python -m bot.main --region Kanto --goal farm
```

### Test LLM connection

```bash
python -m bot.llm.client local_vllm your-api-key
```

### Test damage calculator

```bash
python bot/knowledge/damage_calc.py
```

## 📊 Dữ liệu game

### Species (729 Pokemon)

```json
{
    "id": "garchomp",
    "name": "Garchomp",
    "types": ["Dragon", "Ground"],
    "baseStats": {"hp": 108, "atk": 130, "def": 95, "spa": 80, "spd": 85, "spe": 102},
    "abilities": ["Sand Veil", "Rough Skin"]
}
```

### Moves (578 moves)

```json
{
    "id": "earthquake",
    "name": "Earthquake",
    "type": "Ground",
    "category": "Physical",
    "basePower": 100
}
```

### Locations (310 locations)

```json
{
    "location": "Viridian Forest",
    "region": "Kanto",
    "encounters": [
        {"pokemon": "Caterpie", "min_level": 5, "max_level": 7, "rarity": "Common"},
        {"pokemon": "Pikachu", "min_level": 5, "max_level": 7, "rarity": "Uncommon"}
    ]
}
```

## 🧠 Chi tiết kỹ thuật

### Kiến trúc hệ thống

```
┌─────────────────────────────────────────────────────┐
│                    MAIN LOOP (2-4 Hz)                │
├──────────┬──────────┬──────────┬──────────┬──────────┤
│  VISION  │  STATE   │   LLM    │  ACTION  │   ANTI   │
│  ENGINE  │ MANAGER  │  ENGINE  │ EXECUTOR │ DETECTION│
├──────────┴──────────┴──────────┴──────────┴──────────┤
│              KNOWLEDGE BASE (Static Data)            │
└─────────────────────────────────────────────────────┘
```

### LLM Providers

| Provider | Model | Endpoint | API Format |
|----------|-------|----------|------------|
| **local_vllm** | `gemma-4` | `localhost:8080/v1` | OpenAI |
| **gemma** | `gemma-4-26b-a4b-it` | `generativelanguage.googleapis.com` | Gemini |
| **mimo** | `mimo-v2.5-pro` | `token-plan-sgp.xiaomimimo.com` | OpenAI |
| **openai** | `gpt-4o-mini` | `api.openai.com/v1` | OpenAI |

### Anti-Bot-Detection

- **Timing**: Gaussian random delays (button: 80±30ms, battle: 500±200ms)
- **Movement**: 3% idle pause, 1% wrong step, 15% micro-correction
- **Session**: 45-90 min play, 15-45 min break, max 6h/day
- **Behavior**: 5% suboptimal move, varied routes, occasional menu checks

### Damage Calculator

Implement Gen 8 PokeMMO mechanics:
- STAB (1.5x), Type effectiveness (0x/0.5x/1x/2x/4x)
- Weather boost (Rain: Water 1.5x, Sun: Fire 1.5x)
- Critical hits (1.5x), Item modifiers (Life Orb 1.3x, Choice 1.5x)
- 16 random damage rolls (85-100)

## 📝 Scripts

### Data generation

```bash
# Crawl wiki data
python scripts/crawl_main.py

# Generate datasets
python scripts/generate_datasets.js

# Export from pokemmo-calc library
node scripts/export_pokemmo_database.js
node scripts/export_learnsets.js

# Run damage calc server (port 3000)
node scripts/damage_server.js
```

## 🤝 Contributing

1. Fork repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📄 License

This project is for educational purposes only. PokeMMO is a registered trademark of their respective owners.

## 🔗 Links

- [PokeMMO Official](https://pokemmo.com)
- [PokeMMO Wiki](https://pokemmo.fandom.com)
- [Google AI Studio](https://aistudio.google.com) (for Gemma API key)
- [vLLM Documentation](https://docs.vllm.ai)
