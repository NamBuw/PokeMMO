import os
import json
import re
from bs4 import BeautifulSoup

def clean_text(text):
    """Clean text by removing excessive whitespace and wiki templates."""
    if not text:
        return ""
    text = text.replace('\n', ' ').strip()
    # Remove wiki templates like "Template:Silph Co."
    text = re.sub(r'Template:', '', text)
    # Remove duplicate spaces
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def get_image_url(td_or_img):
    """Extract actual image URL, supporting lazy loading (data-src)."""
    if not td_or_img:
        return ""
    img = td_or_img if td_or_img.name == 'img' else td_or_img.find('img')
    if img:
        # Check standard lazy load attributes
        for attr in ['data-src', 'src']:
            val = img.get(attr)
            if val and not val.startswith('data:image'):
                return val
    return ""

def parse_pokedex(soup):
    pokemon_entries = []
    # Loop through tables to find visual pokedex entries
    for table in soup.find_all('table'):
        rows = table.find_all('tr')
        if len(rows) == 2:
            img_td = rows[0].find('td')
            num_td = rows[1].find('td')
            if img_td and num_td:
                img_url = get_image_url(img_td)
                link = num_td.find('a')
                if link:
                    pokedex_num = num_td.get_text(strip=True)
                    name = link.get('title')
                    url_path = link.get('href')
                    
                    if pokedex_num.isdigit() and name:
                        pokemon_entries.append({
                            "dex_number": pokedex_num,
                            "name": clean_text(name),
                            "url": "https://pokemmo.fandom.com" + url_path,
                            "sprite_url": img_url
                        })
                        
    # De-duplicate
    unique_pokemon = []
    seen = set()
    for p in pokemon_entries:
        if p["name"] not in seen:
            seen.add(p["name"])
            unique_pokemon.append(p)
    return unique_pokemon

def parse_held_items(soup):
    held_items = []
    table = soup.find('table') # Held items has exactly 1 main table
    if not table:
        return held_items
        
    rows = table.find_all('tr')[1:] # Skip header
    for row in rows:
        cols = row.find_all(['td', 'th'])
        if len(cols) >= 4:
            item_name = clean_text(cols[0].get_text())
            price = clean_text(cols[1].get_text())
            effect = clean_text(cols[2].get_text())
            acquisition = clean_text(cols[3].get_text())
            
            # Wild drops are often comma-separated lists of pokemon
            wild_drops = [x.strip() for x in acquisition.split(',') if x.strip()]
            
            held_items.append({
                "name": item_name,
                "price": price,
                "effect": effect,
                "wild_drops": wild_drops,
                "sprite_url": get_image_url(cols[0])
            })
    return held_items

def parse_pokeballs(soup):
    pokeballs = []
    tables = soup.find_all('table')
    # Table 1 contains the actual Poke Balls database
    if len(tables) < 2:
        return pokeballs
        
    table = tables[1]
    rows = table.find_all('tr')[1:] # Skip header
    for row in rows:
        cols = row.find_all(['td', 'th'])
        if len(cols) >= 4:
            # First column is image, second is name, third is description, fourth is catch rate
            img_url = get_image_url(cols[0])
            name = clean_text(cols[1].get_text())
            desc = clean_text(cols[2].get_text())
            catch_rate = clean_text(cols[3].get_text())
            
            pokeballs.append({
                "name": name,
                "description": desc,
                "catch_rate": catch_rate,
                "sprite_url": img_url
            })
    return pokeballs

def parse_medicine(soup):
    medicine_items = []
    tables = soup.find_all('table')
    categories = [
        "Potions & HP Recovery",
        "Status Condition Cures",
        "Revives",
        "PP Restorers",
        "Vitamins & EV Boosters",
        "Herbal Medicine",
        "Special & Candies"
    ]
    
    for idx, table in enumerate(tables):
        if idx >= len(categories):
            break
            
        rows = table.find_all('tr')[1:] # Skip header
        category = categories[idx]
        
        for row in rows:
            cols = row.find_all(['td', 'th'])
            if len(cols) >= 4:
                img_url = get_image_url(cols[0])
                name = clean_text(cols[0].get_text())
                price = clean_text(cols[1].get_text())
                effect = clean_text(cols[2].get_text())
                acquisition = clean_text(cols[3].get_text())
                
                medicine_items.append({
                    "name": name,
                    "category": category,
                    "price": price,
                    "effect": effect,
                    "acquisition": acquisition,
                    "sprite_url": img_url
                })
    return medicine_items

def parse_evolution_items(soup):
    evolution_items = []
    tables = soup.find_all('table')
    
    # Table 0: Evolution Stones
    if len(tables) > 0:
        rows = tables[0].find_all('tr')[1:]
        for row in rows:
            cols = row.find_all(['td', 'th'])
            if len(cols) >= 3:
                # Column 0 is sprite, Column 1 is name, Column 2 is applicable pokemon
                img_url = get_image_url(cols[0])
                name = clean_text(cols[1].get_text())
                pokemon_str = clean_text(cols[2].get_text())
                applicable_pokemon = [x.strip() for x in pokemon_str.split(',') if x.strip()]
                
                evolution_items.append({
                    "name": name,
                    "type": "Evolution Stone",
                    "trigger": "Use Item",
                    "applicable_pokemon": applicable_pokemon,
                    "sprite_url": img_url
                })
                
    # Table 1: Evolution Held Items & Trade Items
    if len(tables) > 1:
        rows = tables[1].find_all('tr')[1:]
        for row in rows:
            cols = row.find_all(['td', 'th'])
            if len(cols) >= 4:
                # Column 0 is sprite, Column 1 is name, Column 2 is applicable pokemon, Column 3 is trigger
                img_url = get_image_url(cols[0])
                name = clean_text(cols[1].get_text())
                pokemon_str = clean_text(cols[2].get_text())
                trigger = clean_text(cols[3].get_text())
                applicable_pokemon = [x.strip() for x in pokemon_str.split(',') if x.strip()]
                
                evolution_items.append({
                    "name": name,
                    "type": "Evolution Held/Trade Item",
                    "trigger": trigger,
                    "applicable_pokemon": applicable_pokemon,
                    "sprite_url": img_url
                })
                
    return evolution_items

def parse_tms(soup):
    tms = []
    table = soup.find('table')
    if not table:
        return tms
        
    rows = table.find_all('tr')[1:] # Skip header
    for row in rows:
        cols = row.find_all(['td', 'th'])
        if len(cols) >= 4:
            tm_name = clean_text(cols[0].get_text())
            move_type = clean_text(cols[1].get_text())
            category = clean_text(cols[2].get_text())
            locations = clean_text(cols[3].get_text())
            
            tms.append({
                "tm": tm_name,
                "type": move_type,
                "category": category,
                "locations_and_prices": locations,
                "sprite_url": get_image_url(cols[0])
            })
    return tms

def build_database():
    files = {
        "Pokedex": "/home/namnx/.gemini/antigravity-ide/brain/31b60e99-b041-4e32-997f-b6d43eecefb2/.system_generated/steps/35/content.md",
        "Held Items": "/home/namnx/.gemini/antigravity-ide/brain/31b60e99-b041-4e32-997f-b6d43eecefb2/.system_generated/steps/63/content.md",
        "PokeBalls": "/home/namnx/.gemini/antigravity-ide/brain/31b60e99-b041-4e32-997f-b6d43eecefb2/.system_generated/steps/69/content.md",
        "Medicine": "/home/namnx/.gemini/antigravity-ide/brain/31b60e99-b041-4e32-997f-b6d43eecefb2/.system_generated/steps/71/content.md",
        "EvolutionItems": "/home/namnx/.gemini/antigravity-ide/brain/31b60e99-b041-4e32-997f-b6d43eecefb2/.system_generated/steps/73/content.md",
        "TMs": "/home/namnx/.gemini/antigravity-ide/brain/31b60e99-b041-4e32-997f-b6d43eecefb2/.system_generated/steps/75/content.md"
    }
    
    datasets = {}
    
    print("Starting unified PokeMMO database parser...")
    
    # 1. Pokedex
    if os.path.exists(files["Pokedex"]):
        print("Parsing Pokedex...")
        with open(files["Pokedex"], 'r', encoding='utf-8') as f:
            soup = BeautifulSoup(f.read(), 'html.parser')
            datasets["pokedex"] = parse_pokedex(soup)
            print(f"  -> Extracted {len(datasets['pokedex'])} Pokémon entries")
            
    # 2. Held Items
    if os.path.exists(files["Held Items"]):
        print("Parsing Held Items...")
        with open(files["Held Items"], 'r', encoding='utf-8') as f:
            soup = BeautifulSoup(f.read(), 'html.parser')
            datasets["held_items"] = parse_held_items(soup)
            print(f"  -> Extracted {len(datasets['held_items'])} Held Items")
            
    # 3. PokeBalls
    if os.path.exists(files["PokeBalls"]):
        print("Parsing Poké Balls...")
        with open(files["PokeBalls"], 'r', encoding='utf-8') as f:
            soup = BeautifulSoup(f.read(), 'html.parser')
            datasets["pokeballs"] = parse_pokeballs(soup)
            print(f"  -> Extracted {len(datasets['pokeballs'])} Poké Balls")
            
    # 4. Medicine
    if os.path.exists(files["Medicine"]):
        print("Parsing Medicine...")
        with open(files["Medicine"], 'r', encoding='utf-8') as f:
            soup = BeautifulSoup(f.read(), 'html.parser')
            datasets["medicine"] = parse_medicine(soup)
            print(f"  -> Extracted {len(datasets['medicine'])} Medicine Items")
            
    # 5. EvolutionItems
    if os.path.exists(files["EvolutionItems"]):
        print("Parsing Evolution Items...")
        with open(files["EvolutionItems"], 'r', encoding='utf-8') as f:
            soup = BeautifulSoup(f.read(), 'html.parser')
            datasets["evolution_items"] = parse_evolution_items(soup)
            print(f"  -> Extracted {len(datasets['evolution_items'])} Evolution Items")
            
    # 6. TMs
    if os.path.exists(files["TMs"]):
        print("Parsing TMs...")
        with open(files["TMs"], 'r', encoding='utf-8') as f:
            soup = BeautifulSoup(f.read(), 'html.parser')
            datasets["tms"] = parse_tms(soup)
            print(f"  -> Extracted {len(datasets['tms'])} TMs")
            
    # Create output directories
    output_dir = '/home/namnx/pokemmo_crawler/data'
    os.makedirs(output_dir, exist_ok=True)
    
    # Save individual JSON files
    for name, data in datasets.items():
        file_path = os.path.join(output_dir, f"{name}.json")
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"Saved {name}.json dataset to {file_path}")
        
    # Save consolidated complete database
    complete_db_path = os.path.join(output_dir, "pokemmo_complete_database.json")
    with open(complete_db_path, 'w', encoding='utf-8') as f:
        json.dump(datasets, f, ensure_ascii=False, indent=2)
        
    print(f"\nSaved consolidated complete database to {complete_db_path}")
    print("Database extraction complete!")

if __name__ == '__main__':
    build_database()
