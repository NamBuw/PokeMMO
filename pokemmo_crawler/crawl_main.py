import os
import json
import urllib.parse
from bs4 import BeautifulSoup

def clean_element(element):
    """Remove unwanted elements like ads, edit links, and scripts."""
    if not element:
        return
    for tag in element.find_all(['script', 'style', 'noscript', 'iframe']):
        tag.decompose()
    # Remove edit section links
    for span in element.find_all('span', class_='mw-editsection'):
        span.decompose()

def extract_navigation_links(soup, base_url="https://pokemmo.fandom.com"):
    """Extract key links from the wiki navigation or main content table."""
    links_data = []
    main_content = soup.find(class_='mw-parser-output')
    if not main_content:
        return links_data
        
    for a in main_content.find_all('a', href=True):
        href = a['href']
        text = a.get_text(strip=True)
        if not text or href.startswith('#') or 'javascript:' in href:
            continue
            
        # Resolve relative URLs
        full_url = urllib.parse.urljoin(base_url, href)
        
        # We only want wiki links
        if "/wiki/" in full_url and not any(x in full_url.lower() for x in ['special:', 'file:', 'category:', 'talk:', 'help:', 'template:']):
            links_data.append({
                'title': text,
                'url': full_url,
                'path': full_url.replace(base_url, '')
            })
            
    # Remove duplicates preserving order
    seen = set()
    unique_links = []
    for link in links_data:
        if link['url'] not in seen:
            seen.add(link['url'])
            unique_links.append(link)
            
    return unique_links

def table_to_markdown(table):
    """Convert a BeautifulSoup table element to a Markdown table."""
    markdown = []
    rows = table.find_all('tr')
    if not rows:
        return ""
        
    headers_done = False
    for row in rows:
        cols = row.find_all(['th', 'td'])
        row_text = [col.get_text(strip=True).replace('\n', ' ') for col in cols]
        
        if not row_text:
            continue
            
        # Standardize empty cells
        row_text = [t if t else " " for t in row_text]
        
        markdown.append("| " + " | ".join(row_text) + " |")
        
        # Add separator after header row
        if not headers_done:
            has_th = any(col.name == 'th' for col in cols)
            if has_th or len(rows) > 1:
                markdown.append("| " + " | ".join(['---'] * len(row_text)) + " |")
            headers_done = True
            
    return "\n".join(markdown) + "\n"

def crawl_pokemmo_wiki():
    local_html_path = '/home/namnx/.gemini/antigravity-ide/brain/31b60e99-b041-4e32-997f-b6d43eecefb2/.system_generated/steps/7/content.md'
    url = "https://pokemmo.fandom.com/wiki/PokeMMO_Wiki"
    
    print(f"Reading local HTML from {local_html_path}...")
    if not os.path.exists(local_html_path):
        print(f"Error: Local file {local_html_path} not found!")
        return
        
    with open(local_html_path, 'r', encoding='utf-8') as f:
        # Fandom content.md includes header lines (Title: ..., Description: ..., Source: ...)
        # we skip metadata until we find the actual HTML
        lines = f.readlines()
        html_content = ""
        html_start = False
        for line in lines:
            if "<html" in line or "<!DOCTYPE" in line:
                html_start = True
            if html_start:
                html_content += line
                
    if not html_content:
        # Fallback if parsing headers failed
        with open(local_html_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
            
    soup = BeautifulSoup(html_content, 'html.parser')
    
    title = soup.find('h1', id='firstHeading')
    title_text = title.get_text(strip=True) if title else "PokeMMO Wiki"
    
    main_content = soup.find(class_='mw-parser-output')
    if not main_content:
        print("Could not find main content div (.mw-parser-output)")
        return
        
    clean_element(main_content)
    
    # Extract structural components
    sections = []
    current_section = {
        "title": "Introduction",
        "content": []
    }
    
    # We iterate through children of main_content
    for child in main_content.children:
        if child.name in ['h2', 'h3', 'h4']:
            if current_section["content"]:
                sections.append(current_section)
            current_section = {
                "title": child.get_text(strip=True),
                "content": []
            }
        elif child.name == 'p':
            p_text = child.get_text(strip=True)
            if p_text:
                current_section["content"].append({"type": "paragraph", "text": p_text})
        elif child.name == 'table':
            md_table = table_to_markdown(child)
            if md_table.strip():
                current_section["content"].append({"type": "table", "markdown": md_table})
        elif child.name in ['ul', 'ol']:
            items = [li.get_text(strip=True) for li in child.find_all('li') if li.get_text(strip=True)]
            if items:
                current_section["content"].append({"type": "list", "items": items})
                
    if current_section["content"]:
        sections.append(current_section)
        
    # Extract links
    key_links = extract_navigation_links(soup)
    
    # Save to JSON format
    wiki_data = {
        "title": title_text,
        "url": url,
        "sections": sections,
        "key_links": key_links
    }
    
    output_dir = '/home/namnx/pokemmo_crawler'
    os.makedirs(output_dir, exist_ok=True)
    
    json_path = os.path.join(output_dir, 'pokemmo_wiki_home.json')
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(wiki_data, f, ensure_ascii=False, indent=2)
    print(f"Saved JSON data to {json_path}")
    
    # Save to Markdown format
    md_path = os.path.join(output_dir, 'pokemmo_wiki_home.md')
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(f"# {title_text}\n\n")
        f.write(f"Source: {url}\n\n")
        
        for sec in sections:
            if sec["title"] != "Introduction":
                f.write(f"## {sec['title']}\n\n")
                
            for item in sec["content"]:
                if item["type"] == "paragraph":
                    f.write(f"{item['text']}\n\n")
                elif item["type"] == "table":
                    f.write(f"{item['markdown']}\n")
                elif item["type"] == "list":
                    for li in item["items"]:
                        f.write(f"- {li}\n")
                    f.write("\n")
                    
        f.write("## Key Navigational Links\n\n")
        for link in key_links:
            f.write(f"- [{link['title']}]({link['url']})\n")
            
    print(f"Saved Markdown data to {md_path}")
    print("Scraping completed successfully!")

if __name__ == '__main__':
    crawl_pokemmo_wiki()
