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
    tables = soup.find_all('table')
    
    # Let's find tables that look like Pokemon data.
    # The output from the previous script shows Table 501 has "0536", etc.
    # Let's look at the first 3 tables that have rows.
    count = 0
    for i, table in enumerate(tables):
        rows = table.find_all('tr')
        if len(rows) >= 2:
            first_col_text = rows[1].find_all(['td', 'th'])[0].get_text(strip=True)
            # If the first column text is a number (like '0001' or '0536')
            if first_col_text.isdigit() and len(first_col_text) >= 3:
                print(f"\n--- TABLE {i} DETAILED HTML ---")
                print(table.prettify()[:2000]) # Print first 2000 chars of the table HTML
                count += 1
                if count >= 3:
                    break

if __name__ == '__main__':
    inspect()
