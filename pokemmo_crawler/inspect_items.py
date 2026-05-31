import os
from bs4 import BeautifulSoup

def inspect():
    file_path = '/home/namnx/.gemini/antigravity-ide/brain/31b60e99-b041-4e32-997f-b6d43eecefb2/.system_generated/steps/49/content.md'
    if not os.path.exists(file_path):
        print("File not found")
        return
        
    with open(file_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
        
    soup = BeautifulSoup(html_content, 'html.parser')
    tables = soup.find_all('table')
    print(f"Found {len(tables)} tables on the Items page.")
    
    for i, table in enumerate(tables):
        classes = table.get('class', [])
        rows = table.find_all('tr')
        print(f"\nTable {i}: class={classes}, rows={len(rows)}")
        if rows:
            # Let's inspect the headers or row text
            headers = [th.get_text(strip=True) for th in rows[0].find_all(['th', 'td'])]
            print(f"  Header/First Row: {headers[:10]}")
            if len(rows) > 1:
                sample = [td.get_text(strip=True) for td in rows[1].find_all(['td'])]
                print(f"  Sample Row 1: {sample[:10]}")
                if i >= 10:
                    print("... stopping here")
                    break

if __name__ == '__main__':
    inspect()
