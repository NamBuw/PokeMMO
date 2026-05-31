# PokeMMO Autonomous Bot — Final Specification
## Tổng hợp từ 2 LLM Debate

---

## 1. TỔNG QUAN HỆ THỐNG

Bot chơi PokeMMO tự động dựa trên **1 LLM runtime** + **Computer Vision**. Kiến trúc Sense-Think-Act loop:

```
Screen Capture → Vision → GameState → LLM Decision → Action Executor → Keyboard Input
```

### LLM Providers hỗ trợ

| Provider | Model | Endpoint | API Key |
|----------|-------|----------|---------|
| **Gemma 4** (Google) | `gemma-4-26b-a4b-it` | `generativelanguage.googleapis.com/v1beta` | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) |
| **Mimo** (Xiaomi) | `mimo-v2.5-pro` | `token-plan-sgp.xiaomimimo.com/anthropic` | Custom |
| **OpenAI** | `gpt-4o-mini` | `api.openai.com/v1` | Platform key |
| **Custom** | Any | Any OpenAI-compatible | Any |

**Config nhanh:**
```python
# Gemma 4
config = get_gemma_config(api_key="your-key-here")

# Mimo
config = get_mimo_config(api_key="your-key-here")

# Custom endpoint
config = get_custom_config(
    api_base="https://your-endpoint.com/v1",
    api_key="your-key",
    model="your-model",
    api_format="openai"  # hoặc "gemini"
)
```

**Dữ liệu hiện có** (`/home/namnx/pokemmo_crawler/data/`):
- 729 species, 578 moves, 310 locations, 167 abilities, 117 held items
- Full type matrix, damage calculator, learnsets, natures, pokeballs, medicine
- Framework skeleton: vision_engine.py, input_engine.py, pokemmo_api.py

---

## 2. KIẾN TRÚC MODULE

```
┌─────────────────────────────────────────────────────────┐
│                    MAIN LOOP (2-4 Hz)                    │
├──────────┬──────────┬──────────┬──────────┬──────────────┤
│  VISION  │  STATE   │   LLM    │  ACTION  │    ANTI      │
│  ENGINE  │ MANAGER  │  ENGINE  │ EXECUTOR │  DETECTION   │
│          │          │          │          │              │
│ Capture  │ GameState│ Mimo API │ KeyPress │ Timing Jitter│
│ OCR      │ Machine  │ Prompts  │ Sequences│ Session Mgmt │
│ Template │ History  │ Context  │ Navigation│ Randomization│
│ HP Bar   │          │ Builder  │          │              │
├──────────┴──────────┴──────────┴──────────┴──────────────┤
│              KNOWLEDGE BASE (Static Data)                │
│  species | moves | types | abilities | items | locations │
└─────────────────────────────────────────────────────────┘
```

---

## 3. LLM PROMPT CHÍNH (System Prompt cho runtime bot)

```
You are an autonomous PokeMMO player bot. You receive game state observations
and must output a single action in JSON format.

## GAME RULES
- PokeMMO has 5 regions: Kanto, Hoenn, Sinnoh, Unova, Johto
- Each region has 8 gym badges with level caps per badge
- Level caps (Kanto): 0 badges=20, 4=46, 8=62, post-E4=100
- STAB = 1.5x damage when move type matches attacker type
- Type effectiveness: 0x (immune), 0.25x, 0.5x (resist), 1x, 2x (SE), 4x (double weak)
- Critical hits = 1.5x damage
- EVs: max 510 total, 252 per stat. Gained from defeating Pokemon.

## DAMAGE FORMULA
Damage = (((2*L/5+2) * BP * Atk/Def) / 50 + 2) * random(0.85-1.0) * weather * crit * STAB * type * item

## DECISION PRIORITIES (in order)
1. SURVIVAL: HP < 25% and opponent can KO → switch or priority move
2. KO OPPORTUNITY: Any move can KO → use it (prefer highest accuracy)
3. CATCH: Shiny or on catch_list → Quick Ball turn 1, then status + False Swipe + Timer Ball
4. SETUP: Opponent cannot 3HKO → use Swords Dance / Calm Mind / Dragon Dance
5. DAMAGE: Highest effective power (BP × type × STAB)
6. STATUS: Sleep/Paralysis for catch targets
7. HEAL: HP < 40% → use potion

## CATCH STRATEGY
- Quick Ball first (x5 on turn 1)
- Status (Sleep x2.5 > Paralysis x1.5) + False Swipe to 1 HP
- Timer Ball after 10 turns (x4), Ultra Ball (x2), specialized balls
- Shiny: ALWAYS catch. NEVER run from shiny.

## OUTPUT FORMAT
{"action": "move", "slot": 1-4}
{"action": "switch", "slot": 1-6}
{"action": "item", "item_name": "Ultra Ball", "target": "opponent"}
{"action": "item", "item_name": "Hyper Potion", "target": "self"}
{"action": "run"}
{"action": "walk", "direction": "up|down|left|right", "duration": 0.3}
{"action": "interact"}
{"action": "heal_at_center"}
```

---

## 4. GAME STATE CONTEXT FORMAT

```json
{
  "game_state": "BATTLE|OVERWORLD|DIALOG|MENU",
  "current_region": "Kanto",
  "badges": 3,
  "level_cap": 37,
  "money": 15000,
  "weather": "Normal",
  "party": [
    {
      "name": "Garchomp",
      "level": 37,
      "hp_percent": 85.0,
      "types": ["Dragon", "Ground"],
      "ability": "Rough Skin",
      "nature": "Jolly",
      "moves": [
        {"name": "Earthquake", "type": "Ground", "category": "Physical", "power": 100, "pp": 10},
        {"name": "Dragon Claw", "type": "Dragon", "category": "Physical", "power": 80, "pp": 15},
        {"name": "Swords Dance", "type": "Normal", "category": "Status", "power": 0, "pp": 20},
        {"name": "Fire Fang", "type": "Fire", "category": "Physical", "power": 65, "pp": 15}
      ],
      "evs": {"atk": 252, "spe": 252, "hp": 4}
    }
  ],
  "enemy": {
    "name": "Gyarados",
    "types": ["Water", "Flying"],
    "hp_percent": 100.0,
    "level": 40,
    "status": null,
    "is_shiny": false
  },
  "inventory": {
    "pokeballs": {"Quick Ball": 5, "Ultra Ball": 12, "Timer Ball": 8},
    "medicine": {"Hyper Potion": 10, "Full Restore": 2, "Revive": 5}
  },
  "catch_list": ["Gyarados", "Garchomp", "Scizor"],
  "turn_count": 0
}
```

---

## 5. FARMING ROUTES TỐI ƯU

### Giai đoạn đầu (Lv5-20)
| Route | Region | Pokemon | Ghi chú |
|-------|--------|---------|---------|
| Viridian Forest | Kanto | Caterpie, Weedle, Pikachu | Bug dễ kill |
| Route 3 | Kanto | Jigglypuff, Mankey, Nidoran | XP tốt |
| Granite Cave | Hoenn | Zubat, Makuhita, Aron | Horde encounters |
| Route 116 | Hoenn | Whismur, Taillow | Whismur hordes |

### Giai đoạn giữa (Lv20-35)
| Route | Region | Pokemon | Ghi chú |
|-------|--------|---------|---------|
| Pokemon Tower | Kanto | Gastly, Haunter, Cubone | Ghost hordes |
| Route 16-18 | Kanto | Doduo, Fearow | Doduo hordes |
| Fiery Path | Hoenn | Numel, Torkoal | Numel dễ KO |
| Route 215 | Sinnoh | Staravia, Buizel, Ponyta | Hordes |

### Giai đoạn cuối (Lv35-55)
| Route | Region | Pokemon | Ghi chú |
|-------|--------|---------|---------|
| Victory Road | Kanto | Golbat, Machoke, Onix | Onix hordes |
| Sky Pillar | Hoenn | Altaria, Flygon | Flygon hordes |
| Stark Mountain | Sinnoh | Golbat, Rhydon | Cấp cao nhất |

### Post-Game (Lv55-100)
| Route | Region | Pokemon | Ghi chú |
|-------|--------|---------|---------|
| Cerulean Cave | Kanto | Chansey | XP khổng lồ |
| Mt. Silver Cave | Johto | Ursaring, Larvitar | Lv73 max |
| Giant Chasm | Unova | Ditto, Metang | Lv70 max |

**Best horde-clearing moves**: Surf, Earthquake, Discharge, Heat Wave, Rock Slide, Blizzard

---

## 6. CATCH STRATEGY

### Ball Selection Priority
```
Turn 1 → Quick Ball (x5)
Water/Bug target → Net Ball (x2.5)
Cave/Night → Dusk Ball (x2.5)
Level < 31 → Nest Ball (x4 max)
Turns ≥ 10 → Timer Ball (x4)
Already caught → Repeat Ball (x2.5)
Default → Ultra Ball (x2)
```

### Khi nào bắt vs đánh
```
Shiny → LUÔN BẮT
Trong catch_list → BẮT
Rare (rarity == "Rare") + chưa có Pokedex → BẮT
BST ≥ 480 + chưa có → BẮT 1 con
Farming XP → ĐÁNH (maximize XP/hr)
```

### Pokemon đáng bắt (competitive)
- **Garchomp**: BST 600, Dragon/Ground, 130 Atk, 102 Spe
- **Tyranitar**: BST 600, Rock/Dark, Sand Stream
- **Gyarados**: BST 540, Water/Flying, Intimidate
- **Scizor**: BST 500, Bug/Steel, Technician
- **Alakazam**: BST 500, Psychic, 135 SpA
- **Darmanitan**: BST 540, Fire, Sheer Force (140 Atk)

---

## 7. BATTLE DECISION FRAMEWORK

### Move Selection Algorithm
```
PRIORITY 1: KO this turn?
  → For each move: calc damage, if max_dmg ≥ enemy_HP → KO option
  → Multiple KOs → highest accuracy → no recoil

PRIORITY 2: Can I be KO'd next turn?
  → My HP < estimated enemy damage → priority move (Aqua Jet, Bullet Punch, Ice Shard)
  → Or switch to resist

PRIORITY 3: Should I set up?
  → Enemy cannot 3HKO → Swords Dance / Calm Mind / Dragon Dance

PRIORITY 4: Type effectiveness
  → effective_power = base_power × type_mult × (1.5 if STAB)
  → Choose highest effective_power

PRIORITY 5: Status
  → Catch target → Sleep Powder / Spore / Thunder Wave
  → Physical attacker → Will-O-Wisp
  → Long battle → Toxic
```

### Weather Teams (từ recommended_teams.json)
- **Rain**: Pelipper (Drizzle) + Kingdra/Kabutops/Ludicolo (Swift Swim) + Scizor + Garchomp
- **Sand**: Tyranitar (Sand Stream) + Excadrill (Sand Rush) + Garchomp + Reuniclus + Skarmory
- **Sun**: Torkoal (Drought) + Venusaur (Chlorophyll) + Darmanitan + Charizard + Rotom-Wash

---

## 8. ANTI-BOT-DETECTION

### Timing Randomization
```python
# Mỗi action có Gaussian delay riêng
button_press:   base=80ms,  std=30ms,  min=40ms,  max=200ms
walk_step:      base=250ms, std=80ms,  min=100ms, max=600ms
menu_nav:       base=150ms, std=50ms,  min=80ms,  max=400ms
battle_action:  base=500ms, std=200ms, min=200ms, max=1200ms
dialog_advance: base=300ms, std=100ms, min=150ms, max=800ms
```

### Movement Randomization
- 3% chance dừng 0.5-2s giữa walk (giả vờ nhìn xung quanh)
- 1% chance đi sai 1 bước rồi sửa lại
- 15% chance micro-correction sau mỗi bước
- Không bao giờ đi đúng path 2 lần liên tiếp

### Session Management
- Phiên chơi: 45-90 phút (random)
- Nghỉ: 15-45 phút giữa các phiên
- Mỗi 20-30 phút: idle 30-120s (mở menu, check PC)
- Max 6 giờ/ngày, không chơi 2-6AM
- 5% chance move suboptimal trong wild battle

### Anti-Pattern
- Theo dõi: tổng bước, số battle, thời gian trung bình/battle, số lần lặp route
- Nếu quá robot → inject variance: đổi route, thăm Pokecenter, đánh species khác

---

## 9. VISION PIPELINE

### ROIs cần thiết
| ROI | Vị trí | Chức năng |
|-----|--------|-----------|
| enemy_name | top-left 10% | OCR tên Pokemon địch |
| enemy_hp_bar | top 15% | HP% qua HSV color |
| player_name | bottom-left | Tên Pokemon mình |
| player_hp_bar | bottom 15% | HP% của mình |
| combat_menu | bottom-right 60% | Fight/Bag/Pokemon/Run |
| move_list | bottom-right | 4 move slots + PP |
| chat_box | bottom 80% | Dialog text |
| party_indicator | | Pokeball icons |
| exp_bar | | Thanh EXP |
| level_text | | Level number |

### OCR Config cho PokeMMO pixel font
```
--psm 7 (single line) cho tên Pokemon
--psm 6 (block) cho dialog
--psm 8 (single word) cho menu items
Upscale 2x → grayscale → adaptive threshold → morphological cleanup
Fuzzy match kết quả OCR với species/moves database
```

---

## 10. CẤU TRÚC THƯ MỤC

```
/home/namnx/pokemmo_bot/
├── main.py                    # Entry point, main loop
├── config.py                  # LLM, Vision, AntiDetection config
├── SPECIFICATION.md           # Document này
├── llm/
│   ├── client.py              # Mimo API client (OpenAI-compatible)
│   ├── prompts.py             # System prompt + few-shot examples
│   └── context_builder.py     # Build game state JSON cho LLM
├── vision/
│   ├── capture.py             # Screen capture (MSS)
│   ├── ocr_engine.py          # Tesseract + fuzzy match
│   ├── state_extractor.py     # Vision → GameState
│   ├── rois.py                # ROI definitions
│   └── templates/             # Template images
├── knowledge/
│   ├── data_store.py          # Load tất cả JSON data
│   ├── damage_calc.py         # Port từ damage_calc.py
│   └── move_recommender.py    # Rule-based move suggestions
├── action/
│   ├── executor.py            # Action enum → keypress sequence
│   ├── input_engine.py        # Port từ input_engine.py
│   ├── anti_detection.py      # Timing randomization
│   └── navigation.py          # Pathfinding
├── state/
│   ├── machine.py             # GameStateMachine
│   ├── game_state.py          # GameState dataclass
│   └── history.py             # Decision history
├── data/                      # Symlink → pokemmo_crawler/data/
└── logs/                      # Structured JSON logs
```

---

## 11. IMPLEMENTATION PHASES

| Phase | Nội dung | Thời gian |
|-------|----------|-----------|
| 1 | Data Layer: config.py, data_store.py, damage_calc port | 1-2 ngày |
| 2 | Vision: capture, OCR, state_extractor, ROIs | 2-3 ngày |
| 3 | Action: input_engine, anti_detection, navigation | 1 ngày |
| 4 | State Machine: game_state, transitions | 1 ngày |
| 5 | LLM Integration: client, prompts, context_builder | 2-3 ngày |
| 6 | Main Loop: wire all, session management, logging | 1 ngày |
| 7 | Tuning: ROIs, OCR params, timing, prompts | ongoing |

---

## 12. EDGE CASES

- **White Out**: Mất 50% money, hồi sinh ở Pokecenter → farm route thấp hơn nếu tiền < 1000
- **Shiny**: LUÔN BẮT, Quick Ball → Sleep → False Swipe → Timer Ball
- **NPC Battle**: Không bắt, không chạy, dùng SE moves, tiết kiệm PP
- **Level Cap**: Đạt cap → chuyển sang EV training hoặc money farming
- **PP hết**: Switch Pokemon khác → dùng Ether → về Pokecenter
- **Trade Evolution**: Cần người chơi thật (giới hạn bot)
- **Stuck**: Press B×3 → Enter → Esc → restart session
