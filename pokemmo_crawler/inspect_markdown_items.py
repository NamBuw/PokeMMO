import os

def inspect():
    file_path = '/home/namnx/.gemini/antigravity-ide/brain/31b60e99-b041-4e32-997f-b6d43eecefb2/.system_generated/steps/49/content.md'
    if not os.path.exists(file_path):
        print("File not found")
        return
        
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    print(f"Total lines: {len(lines)}")
    
    # Print lines that look like markdown tables (containing '|')
    table_lines_count = 0
    in_table = False
    
    for i, line in enumerate(lines):
        if '|' in line:
            if not in_table:
                print(f"\n--- Markdown Table starting at line {i} ---")
                in_table = True
            print(f"{i}: {line.strip()}")
            table_lines_count += 1
            if table_lines_count >= 50:
                print("... truncated after 50 table lines")
                break
        else:
            in_table = False

if __name__ == '__main__':
    inspect()
