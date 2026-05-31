import json
import os

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
POKEMMO_DATA_PATH = os.path.join(BASE_DIR, "pokemmo-data", "data", "pokemon-data.json")
SPECIES_OUT_PATH = os.path.join(BASE_DIR, "data", "species.json")
LEARNSETS_OUT_PATH = os.path.join(BASE_DIR, "data", "learnsets.json")
COMPLETE_DB_PATH = os.path.join(BASE_DIR, "data", "pokemmo_complete_database.json")

def run_update():
    print("Reading custom PokeMMO-Data resources...")
    if not os.path.exists(POKEMMO_DATA_PATH):
        print(f"Error: Custom PokeMMO data not found at {POKEMMO_DATA_PATH}")
        return

    with open(POKEMMO_DATA_PATH, "r", encoding="utf-8") as f:
        pokemmo_raw = json.load(f)
        
    print("Reading existing species database...")
    if os.path.exists(SPECIES_OUT_PATH):
        with open(SPECIES_OUT_PATH, "r", encoding="utf-8") as f:
            existing_species = json.load(f)
    else:
        existing_species = []
        
    species_map = {spec["name"].lower(): spec for spec in existing_species}
    
    updated_species_list = []
    updated_learnsets = {}
    
    for pkmn_name, pkmn_data in pokemmo_raw.items():
        # Title case species name
        name_title = pkmn_data.get("name", pkmn_name)
        name_lower = pkmn_name.lower()
        
        # 1. Base Stats
        stats_list = pkmn_data.get("stats", [])
        stats_dict = {}
        for s in stats_list:
            stat_name = s["stat_name"]
            val = s["base_stat"]
            if stat_name == "hp": stats_dict["hp"] = val
            elif stat_name == "attack": stats_dict["atk"] = val
            elif stat_name == "defense": stats_dict["def"] = val
            elif stat_name == "special-attack": stats_dict["spa"] = val
            elif stat_name == "special-defense": stats_dict["spd"] = val
            elif stat_name == "speed": stats_dict["spe"] = val
            
        # 2. Types
        types = [t.capitalize() for t in pkmn_data.get("types", [])]
        
        # 3. Abilities (standard + hidden)
        abilities = []
        for a in pkmn_data.get("abilities", []):
            ab_name = a.get("ability_name", "")
            # Title case ability name (e.g. "chlorophyll" -> "Chlorophyll")
            ab_title = " ".join([w.capitalize() for w in ab_name.replace("-", " ").split()])
            if ab_title and ab_title not in abilities:
                abilities.append(ab_title)
        
        # 4. Fallback/Existing Spec metadata (weight, nfe, gender)
        exist_spec = species_map.get(name_lower) or species_map.get(name_title.lower())
        
        if exist_spec:
            weight = exist_spec.get("weightkg", 10.0)
            nfe = exist_spec.get("nfe", False)
            gender = exist_spec.get("gender", "N")
            spec_id = exist_spec.get("id", name_lower)
        else:
            weight = 10.0
            nfe = False
            gender = "N"
            spec_id = name_lower
            
        updated_spec = {
            "id": spec_id,
            "name": name_title,
            "baseStats": stats_dict,
            "types": types,
            "weightkg": weight,
            "nfe": nfe,
            "abilities": abilities,
            "gender": gender
        }
        updated_species_list.append(updated_spec)
        
        # 5. Learnsets (levels & moves)
        moves = pkmn_data.get("moves", [])
        lvl_moves = []
        for m in moves:
            if m.get("type") == "level":
                move_name = m.get("name", "")
                if move_name:
                    lvl_moves.append({
                        "level": m.get("level", 1),
                        "move": move_name
                    })
                    
        # Sort by level
        lvl_moves.sort(key=lambda x: x["level"])
        
        if lvl_moves:
            updated_learnsets[name_title] = {
                "gen5": lvl_moves,
                "gen8": lvl_moves,
                "pokemmo": lvl_moves
            }
            
    # Save back updated files
    print(f"Saving {len(updated_species_list)} updated species to data/species.json...")
    with open(SPECIES_OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(updated_species_list, f, ensure_ascii=False, indent=2)
        
    print(f"Saving {len(updated_learnsets)} updated learnsets to data/learnsets.json...")
    with open(LEARNSETS_OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(updated_learnsets, f, ensure_ascii=False, indent=2)
        
    # Also reload consolidated complete database
    print("Updating consolidated master database...")
    comp_db = {}
    if os.path.exists(COMPLETE_DB_PATH):
        try:
            with open(COMPLETE_DB_PATH, "r", encoding="utf-8") as f:
                comp_db = json.load(f)
        except Exception:
            pass
        
    comp_db["species"] = updated_species_list
    comp_db["learnsets"] = updated_learnsets
    
    with open(COMPLETE_DB_PATH, "w", encoding="utf-8") as f:
        json.dump(comp_db, f, ensure_ascii=False, indent=2)
        
    print("PokeMMO Database resources updated successfully!")

if __name__ == "__main__":
    run_update()
