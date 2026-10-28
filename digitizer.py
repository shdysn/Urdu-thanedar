import glob
import io
import json
import os
import re
import time
import fitz  # PyMuPDF
from google import genai
from PIL import Image
from src.pdf_utils import remove_red_watermark

INPUT_DIR = "input"
OUTPUT_DIR = "output"
TXT_DIR = os.path.join(OUTPUT_DIR, "pages_txt")
JSON_DIR = os.path.join(OUTPUT_DIR, "pages_json")
JSON_FILE = os.path.join(OUTPUT_DIR, "full_book.json")

os.makedirs(TXT_DIR, exist_ok=True)
os.makedirs(JSON_DIR, exist_ok=True)

PROMPT = """آپ ایک ماہر اردو اور عربی آرکائیول ڈیجیٹائزر ہیں۔
اس صفحے کے تمام متن کو ہو بہو (100% درستگی کے ساتھ) یونیکوڈ اردو/عربی میں لکھیں۔
ہدایات:
1. کوئی لفظ اپنی طرف سے نہ بڑھائیں اور نہ کم کریں۔
2. قرآنی آیات اور عربی عبارات کو اعراب کے ساتھ ﴿ ﴾ بریکٹس میں لکھیں۔
3. پیراگراف کے درمیان خالی لائن رکھیں، لیکن ایک ہی پیراگراف کی سطروں کو بیچ سے نہ توڑیں۔
4. صرف صفحے کا اصل متن لکھیں، کوئی تبصرہ یا ہیڈر/فوٹر نمبر شامل نہ کریں۔"""


def ocr_single_image(client, img):
    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model="gemini-1.5-flash", contents=[img, PROMPT]
            )
            if response and response.text:
                return response.text.strip()
        except Exception as e:
            print(f"API Retry ({attempt+1}/3): {e}")
            time.sleep(5)
    return ""


def process_inputs():
    raw_key = os.environ.get("GEMINI_API_KEY", "")
    api_key = raw_key.split(",")[0].strip().strip("'\"")
    if not api_key:
        print(
            "نوٹ: GEMINI_API_KEY موجود نہیں ہے، صرف موجودہ TXT فائلوں سے JSON بنائی جا رہی ہے۔"
        )
        return

    client = genai.Client(api_key=api_key)

    pdf_files = glob.glob(os.path.join(INPUT_DIR, "*.pdf")) + glob.glob("*.pdf")
    global_page_num = 0
    for pdf_path in pdf_files:
        print(f"Processing PDF: {pdf_path}")
        doc = fitz.open(pdf_path)
        for idx in range(len(doc)):
            global_page_num += 1
            txt_path = os.path.join(TXT_DIR, f"page_{global_page_num:04d}.txt")
            if os.path.exists(txt_path):
                continue

            print(f"OCR Page {global_page_num}...")
            page = doc.load_page(idx)
            pix = page.get_pixmap(dpi=200)
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            img = remove_red_watermark(img)

            text = ocr_single_image(client, img)
            if text:
                with open(txt_path, "w", encoding="utf-8") as f:
                    f.write(text)
                time.sleep(2)


def combine_all_txt_to_single_json():
    """صرف pages_txt فولڈر کی درست فائلوں سے full_book.json اور pages_json بناتا ہے"""
    txt_files = glob.glob(os.path.join(TXT_DIR, "*.txt"))
    if not txt_files:
        txt_files = glob.glob(
            os.path.join(OUTPUT_DIR, "**", "*.txt"), recursive=True
        )

    pages_dict = {}
    for file_path in sorted(txt_files):
        filename = os.path.basename(file_path)
        if "DOUBT_REPORT" in filename:
            continue
        nums = re.findall(r"\d+", filename)
        if not nums:
            continue

        page_num = int(nums[-1])
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
            if content:
                pages_dict[page_num] = content
        except Exception as e:
            print(f"Error reading {file_path}: {e}")

    book_list = []
    for p in sorted(pages_dict.keys()):
        book_list.append({"page": p, "content": pages_dict[p]})
        with open(
            os.path.join(JSON_DIR, f"page_{p:04d}.json"), "w", encoding="utf-8"
        ) as pj:
            json.dump(
                {"page": p, "content": pages_dict[p]},
                pj,
                ensure_ascii=False,
                indent=2,
            )

    with open(JSON_FILE, "w", encoding="utf-8") as jf:
        json.dump(book_list, jf, ensure_ascii=False, indent=2)

    print(
        f"✅ کامیابی! کل {len(book_list)} صفحات کی '{JSON_FILE}' اپڈیٹ ہو گئی۔"
    )


if __name__ == "__main__":
    process_inputs()
    combine_all_txt_to_single_json()
