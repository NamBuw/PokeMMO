import os
from bs4 import BeautifulSoup

def inspect():
    file_path = '/home/namnx/.gemini/antigravity-ide/brain/31b60e99-b041-4e32-997f-b6d43eecefb2/.system_generated/steps/35/content.md'
    if not os.path.exists(file_path):
        print("File not found")
        return
        
    with open(file_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
        
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Let's count how many links to Pokémon we can extract from this visual grid.
    pokemon_entries = []
    
    # We saw nested tables with border: 1px solid grey; background: #555555;
    for table in soup.find_all('table'):
        rows = table.find_all('tr')
        if len(rows) == 2:
            # Row 0: Image link
            # Row 1: Number and name link
            img_td = rows[0].find('td')
            num_td = rows[1].find('td')
            if img_td and num_td:
                img = img_td.find('img')
                link = num_td.find('a')
                if img and link:
                    pokedex_num = num_td.get_text(strip=True)
                    name = link.get('title')
                    url_path = link.get('href')
                    image_url = img.get('src')
                    
                    if pokedex_num.isdigit() and name:
                        pokemon_entries.append({
                            "dex_number": pokedex_num,
                            "name": name,
                            "url": "https://pokemmo.fandom.com" + url_path,
                            "image_url": image_url
                        })
                        
    # Remove duplicates preserving order
    unique_pokemon = []
    seen = set()
    for p in pokemon_entries:
        if p["name"] not in seen:
            seen.add(p["name"])
            unique_pokemon.append(p)
            
    print(f"Successfully extracted {len(unique_pokemon)} unique Pokémon entries from the Pokédex grid!")
    if unique_pokemon:
        print("Sample entries:")
        for p in unique_pokemon[:10]:
            print(p)
            
if __name__ == '__main__':
    inspect()
