import os
import time
from PIL import Image
from src.pdf_utils import extract_images_from_pdf, remove_red_watermark
from src.ai_verifier import run_multi_agent_pipeline

INPUT_DIR = "input"
OUTPUT_DIR = "output"
DOUBT_FILE = os.path.join(OUTPUT_DIR, "DOUBT_REPORT.txt")

def process_file(file_name):
    file_path = os.path.join(INPUT_DIR, file_name)
    pages = []

    if file_name.lower().endswith(".pdf"):
        print(f"📄 PDF Process ho rahi hai (Watermark filter active): {file_name}")
        pages = extract_images_from_pdf(file_path)
    elif file_name.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
        raw_img = Image.open(file_path)
        pages = [(1, remove_red_watermark(raw_img))]
    else:
        return

    for page_num, img in pages:
        print(f"\n==========================================")
        print(f"📖 Processing Page {page_num} (Anti-Hallucination Mode)")
        print(f"==========================================")
        
        try:
            final_text, doubts = run_multi_agent_pipeline(img)
            
            # 1. Page Text Save
            out_file = os.path.join(OUTPUT_DIR, f"{file_name}_page_{page_num}.txt")
            with open(out_file, "w", encoding="utf-8") as f:
                f.write(final_text)
            print(f"✅ Text Saved: {out_file}")

            # 2. Doubt Log Save (Agar Thanedar ko shak ho)
            if doubts and doubts != "None":
                with open(DOUBT_FILE, "a", encoding="utf-8") as df:
                    df.write(f"\n--- {file_name} Page {page_num} ---\n{doubts}\n")
                print(f"⚠️ Shak note ho gaya hai (Saved in DOUBT_REPORT.txt)")

        except Exception as e:
            print(f"❌ Error page {page_num} par: {e}")

        time.sleep(3)

if __name__ == "__main__":
    os.makedirs(INPUT_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    files = [f for f in os.listdir(INPUT_DIR) if not f.startswith(".")]
    if not files:
        print("input/ folder khali hai! PDF upload karein.")
    else:
        for f in files:
            process_file(f)
