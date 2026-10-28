import os
import glob
import re
import json

OUTPUT_DIR = "output"
TXT_DIR = os.path.join(OUTPUT_DIR, "pages_txt")
JSON_DIR = os.path.join(OUTPUT_DIR, "pages_json")
JSON_FILE = os.path.join(OUTPUT_DIR, "full_book.json")

def parse_corrections_file(filepath):
    corrections = []
    if not os.path.exists(filepath):
        print(f"{filepath} not found.")
        return corrections

    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # 1) CSV format
        if ',' in line and not line.startswith('|') and not line.startswith('صفحہ'):
            parts = []
            current_part = []
            in_quotes = False
            for char in line:
                if char == '"':
                    in_quotes = not in_quotes
                elif char == ',' and not in_quotes:
                    parts.append("".join(current_part).strip(' "'))
                    current_part = []
                else:
                    current_part.append(char)
            if current_part:
                parts.append("".join(current_part).strip(' "'))

            if len(parts) >= 5:
                page_str, _, _, wrong_text, correct_text = parts[:5]
                corrections.append((page_str, wrong_text, correct_text))

        # 2) Markdown tables format: | Page | Wrong Text | Correct Text |
        elif line.startswith('|'):
            parts = [p.strip() for p in line.split('|')]
            if len(parts) >= 4 and 'Page' not in parts[1]: # skip header
                page_str = parts[1]
                wrong_text = parts[2]
                correct_text = parts[3]
                corrections.append((page_str, wrong_text, correct_text))

        # 3) Bullet lists format
        elif line.startswith('صفحہ'):
            # Example: صفحہ X: اصل متن: Y فائل میں: Z
            match = re.search(r'صفحہ\s*([\d\-]+).*?فائل میں:\s*(.*?)\s*اصل متن:\s*(.*)', line)
            if match:
                page_str = match.group(1).strip()
                wrong_text = match.group(2).strip()
                correct_text = match.group(3).strip()
                corrections.append((page_str, wrong_text, correct_text))

    return corrections

def clean_text(text):
    # Strip Devanagari/Hindi characters
    text = re.sub(r'[\u0900-\u097F]+', '', text)
    # Strip English meta-notes
    text = re.sub(r'\([a-zA-Z\s,.\']+\)', '', text)
    # Strip VERDICT tags
    text = re.sub(r'\[VERDICT_START.*?$', '', text, flags=re.MULTILINE | re.IGNORECASE)
    text = re.sub(r'\[VERDICT_END.*?$', '', text, flags=re.MULTILINE | re.IGNORECASE)
    text = re.sub(r'\[\w+.*?$', '', text, flags=re.MULTILINE)
    return text.strip()

def apply_corrections(book_data, corrections):
    # pages should be accessible as strings internally
    page_texts = {str(item['page']): item['content'] for item in book_data}

    for page_str, wrong_text, correct_text in corrections:
        wrong_variants = [v.strip() for v in wrong_text.split('/')]
        pages_to_apply = []

        if '-' in page_str:
            start, end = map(int, page_str.split('-'))
            pages_to_apply = [str(p) for p in range(start, end + 1)]
        else:
            pages_to_apply = [page_str]

        for page in pages_to_apply:
            if page in page_texts:
                for variant in wrong_variants:
                    if not variant:
                        continue
                    if variant in page_texts[page]:
                        # Handle watermark removal (when Correct_Text_in_PDF is empty)
                        if not correct_text:
                            page_texts[page] = page_texts[page].replace(variant, "")
                        else:
                            page_texts[page] = page_texts[page].replace(variant, correct_text)

    # Global cleanup for all pages
    for page in list(page_texts.keys()):
        page_texts[page] = clean_text(page_texts[page])

    return page_texts

def sync_files(page_texts):
    os.makedirs(TXT_DIR, exist_ok=True)
    os.makedirs(JSON_DIR, exist_ok=True)

    import difflib
    # Cross-page duplicate text cleanup for explicit page 155 check
    if '155' in page_texts and '154' in page_texts:
        ratio = difflib.SequenceMatcher(None, page_texts['155'].strip(), page_texts['154'].strip()).ratio()
        if ratio > 0.95:  # High similarity indicates it's a duplicate with minor OCR differences
            print(f"Removing duplicate page 155 (Similarity: {ratio})")
            del page_texts['155']
            # Also clean up the physical files if they exist
            txt_155 = os.path.join(TXT_DIR, "page_0155.txt")
            json_155 = os.path.join(JSON_DIR, "page_0155.json")
            if os.path.exists(txt_155): os.remove(txt_155)
            if os.path.exists(json_155): os.remove(json_155)

    # Check for trailing duplicate pages
    pages = sorted([int(p) for p in page_texts.keys()])
    if len(pages) >= 2:
        last_page = str(pages[-1])
        prev_page = str(pages[-2])
        if page_texts[last_page] == page_texts[prev_page]:
            del page_texts[last_page]
            pages = sorted([int(p) for p in page_texts.keys()])

    # Save pages_txt and pages_json
    book_list = []
    for p in pages:
        p_str = str(p)
        content = page_texts[p_str]
        book_list.append({"page": p, "content": content})

        txt_path = os.path.join(TXT_DIR, f"page_{p:04d}.txt")
        json_path = os.path.join(JSON_DIR, f"page_{p:04d}.json")

        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(content)

        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump({"page": p, "content": content}, f, ensure_ascii=False, indent=2)

    # Save full_book.json
    with open(JSON_FILE, 'w', encoding='utf-8') as f:
        json.dump(book_list, f, ensure_ascii=False, indent=2)

    # Delete legacy raw output/*_page_*.txt files
    legacy_files = glob.glob(os.path.join(OUTPUT_DIR, "*_page_*.txt"))
    for lf in legacy_files:
        if os.path.isfile(lf):
            os.remove(lf)

def main():
    corrections = parse_corrections_file("corrections.txt")
    print(f"Parsed {len(corrections)} corrections.")

    book_data = []
    if os.path.exists(JSON_FILE):
        with open(JSON_FILE, 'r', encoding='utf-8') as f:
            book_data = json.load(f)
    else:
        # Load from pages_txt if full_book.json is missing
        txt_files = glob.glob(os.path.join(TXT_DIR, "page_*.txt"))
        for tf in txt_files:
            num = int(re.findall(r'\d+', os.path.basename(tf))[0])
            with open(tf, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            book_data.append({"page": num, "content": content})

    if not book_data:
        print("No book data found.")
        return

    updated_pages = apply_corrections(book_data, corrections)
    sync_files(updated_pages)
    print("Files synced and updated.")

if __name__ == "__main__":
    main()
