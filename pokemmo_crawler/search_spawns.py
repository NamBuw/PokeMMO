import json
import os
import sys

def search_pokemon_spawns(pokemon_name: str, database_path: str = "data/location_data.json"):
    """
    Queries the PokeMMO-specific wild spawn database for a specific Pokémon.
    Filters and returns location, region, min/max level, rarity (Lure/Horde/Standard), and active Time of Day.
    """
    pokemon_name = pokemon_name.strip().lower()
    
    if not os.path.exists(database_path):
        # Handle pathing when run from different directories
        alternative_path = os.path.join(os.path.dirname(__file__), database_path)
        if os.path.exists(alternative_path):
            database_path = alternative_path
        else:
            return {"error": f"Database file not found at {database_path}"}

    with open(database_path, "r", encoding="utf-8") as f:
        location_db = json.load(f)

    results = []
    
    for loc_key, loc_data in location_db.items():
        name = loc_data.get("name", "Unknown Area")
        region = loc_data.get("region", "Unknown Region")
        encounters = loc_data.get("encounters", [])
        
        for enc in encounters:
            if enc.get("pokemon", "").lower() == pokemon_name:
                results.append({
                    "region": region,
                    "location": name,
                    "type": enc.get("type", "Grass"),
                    "levels": f"{enc.get('min_level')}-{enc.get('max_level')}",
                    "rarity": enc.get("rarity", "Common"),
                    "time": enc.get("time", "ALL")
                })
                
    return results

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python search_spawns.py <pokemon_name>")
        print("Example: python search_spawns.py bulbasaur")
        sys.exit(1)
        
    target = sys.argv[1]
    spawns = search_pokemon_spawns(target)
    
    if "error" in spawns:
        print(spawns["error"])
        sys.exit(1)
        
    if not spawns:
        print(f"\nNo PokeMMO wild encounters found for '{target}'.")
        print("This Pokemon might be Gift-only, Evolve-only, Egg-only, or Safari-exclusive.")
        sys.exit(0)
        
    print(f"\n🔍 PokeMMO Wild Spawns for '{target.upper()}':")
    print("-" * 80)
    print(f"{'REGION':<10} | {'LOCATION':<25} | {'METHOD':<10} | {'LEVELS':<8} | {'RARITY':<10} | {'TIME'}")
    print("-" * 80)
    for spawn in spawns:
        print(f"{spawn['region']:<10} | {spawn['location']:<25} | {spawn['type']:<10} | {spawn['levels']:<8} | {spawn['rarity']:<10} | {spawn['time']}")
    print("-" * 80)
