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
    
    # Check for basic tags
    print(f"HTML Length: {len(html_content)} chars")
    print(f"Title tag: {soup.title}")
    
    # Check for div with class mw-parser-output
    mw_output = soup.find(class_='mw-parser-output')
    if mw_output:
        print("Found mw-parser-output div!")
        # Let's count some elements inside it
        print(f"  - paragraphs: {len(mw_output.find_all('p'))}")
        print(f"  - links: {len(mw_output.find_all('a'))}")
        print(f"  - tables: {len(mw_output.find_all('table'))}")
        print(f"  - lists: {len(mw_output.find_all('ul')) + len(mw_output.find_all('ol'))}")
        
        # Let's print the first 500 characters of its text
        print(f"\nSample Text Content:\n{mw_output.get_text()[:1000].strip()}")
    else:
        print("Could not find mw-parser-output div!")
        # Let's check what main divs exist
        divs = soup.find_all('div')
        print(f"Total divs in page: {len(divs)}")

if __name__ == '__main__':
    inspect()
