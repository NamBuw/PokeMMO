import os
from bs4 import BeautifulSoup

files = {
    "Pokedex": "/home/namnx/.gemini/antigravity-ide/brain/31b60e99-b041-4e32-997f-b6d43eecefb2/.system_generated/steps/35/content.md",
    "Held Items": "/home/namnx/.gemini/antigravity-ide/brain/31b60e99-b041-4e32-997f-b6d43eecefb2/.system_generated/steps/63/content.md",
    "PokeBalls": "/home/namnx/.gemini/antigravity-ide/brain/31b60e99-b041-4e32-997f-b6d43eecefb2/.system_generated/steps/69/content.md",
    "Medicine": "/home/namnx/.gemini/antigravity-ide/brain/31b60e99-b041-4e32-997f-b6d43eecefb2/.system_generated/steps/71/content.md",
    "EvolutionItems": "/home/namnx/.gemini/antigravity-ide/brain/31b60e99-b041-4e32-997f-b6d43eecefb2/.system_generated/steps/73/content.md",
    "TMs": "/home/namnx/.gemini/antigravity-ide/brain/31b60e99-b041-4e32-997f-b6d43eecefb2/.system_generated/steps/75/content.md"
}

def inspect():
    for name, path in files.items():
        if not os.path.exists(path):
            print(f"{name} file not found!")
            continue
            
        with open(path, 'r', encoding='utf-8') as f:
            html = f.read()
            
        soup = BeautifulSoup(html, 'html.parser')
        tables = soup.find_all('table')
        
        print(f"\n=================== {name} ===================")
        print(f"Total tables found: {len(tables)}")
        
        # If it's a giant set of tables like Pokedex, let's just mention it
        if len(tables) > 10:
            print("Contains many tiny nested tables.")
            continue
            
        for i, table in enumerate(tables):
            rows = table.find_all('tr')
            print(f"Table {i}: {len(rows)} rows")
            if rows:
                headers = [th.get_text(strip=True) for th in rows[0].find_all(['th', 'td'])]
                print(f"  Header: {headers[:10]}")
                if len(rows) > 1:
                    sample = [td.get_text(strip=True) for td in rows[1].find_all(['td'])]
                    print(f"  Sample: {sample[:10]}")

if __name__ == '__main__':
    inspect()
