import glob
import io
import json
import os
import re
import time
import fitz  # PyMuPDF
import google.generativeai as genai
from PIL import Image

# فولڈرز کی سیٹنگ
INPUT_DIR = "input"
OUTPUT_DIR = "output"
TXT_DIR = os.path.join(OUTPUT_DIR, "pages_txt")
JSON_FILE = os.path.join(OUTPUT_DIR, "full_book.json")

os.makedirs(TXT_DIR, exist_ok=True)

PROMPT = """آپ ایک ماہر اردو اور عربی آرکائیول ڈیجیٹائزر ہیں۔
اس صفحے کے تمام متن کو ہو بہو (100% درستگی کے ساتھ) یونیکوڈ اردو/عربی میں لکھیں۔
ہدایات:
1. کوئی لفظ اپنی طرف سے نہ بڑھائیں اور نہ کم کریں۔
2. قرآنی آیات اور عربی عبارات کو اعراب کے ساتھ ﴿ ﴾ بریکٹس میں لکھیں۔
3. پیراگراف کے درمیان خالی لائن رکھیں، لیکن ایک ہی پیراگراف کی سطروں کو بیچ سے نہ توڑیں۔
4. صرف صفحے کا اصل متن لکھیں، کوئی تبصرہ یا ہیڈر/فوٹر نمبر شامل نہ کریں۔"""


def ocr_single_image(model, img):
    for attempt in range(3):
        try:
            response = model.generate_content([PROMPT, img])
            if response and response.text:
                return response.text.strip()
        except Exception as e:
            print(f"API Retry ({attempt+1}/3): {e}")
            time.sleep(5)
    return ""


def process_inputs():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print(
            "نوٹ: GEMINI_API_KEY موجود نہیں ہے یا صرف پرانی TXT فائلوں کو JSON میں بدلا جا رہا ہے۔"
        )
        return

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.5-flash")

    # 1. اگر ریپوزٹری یا input فولڈر میں کوئی PDF فائل موجود ہو
    pdf_files = glob.glob(os.path.join(INPUT_DIR, "*.pdf")) + glob.glob("*.pdf")
    for pdf_path in pdf_files:
        print(f"Processing PDF: {pdf_path}")
        doc = fitz.open(pdf_path)
        for idx in range(len(doc)):
            page_num = idx + 1
            # چیک کریں کہ کہیں یہ صفحہ پہلے سے output میں موجود تو نہیں؟
            existing_1 = os.path.join(TXT_DIR, f"page_{page_num:04d}.txt")
            existing_2 = os.path.join(OUTPUT_DIR, f"page_{page_num}.txt")
            existing_3 = os.path.join(OUTPUT_DIR, f"page_{page_num:04d}.txt")

            if (
                os.path.exists(existing_1)
                or os.path.exists(existing_2)
                or os.path.exists(existing_3)
            ):
                continue

            print(f"OCR Page {page_num}...")
            page = doc.load_page(idx)
            pix = page.get_pixmap(dpi=200)
            img = Image.open(io.BytesIO(pix.tobytes("png")))

            text = ocr_single_image(model, img)
            if text:
                with open(existing_1, "w", encoding="utf-8") as f:
                    f.write(text)
                time.sleep(2)

    # 2. اگر input فولڈر میں تصاویر (JPG/PNG) موجود ہوں
    img_files = []
    if os.path.exists(INPUT_DIR):
        for ext in ("*.png", "*.jpg", "*.jpeg", "*.webp"):
            img_files.extend(glob.glob(os.path.join(INPUT_DIR, "**", ext), recursive=True))

    img_files.sort()
    for idx, img_path in enumerate(img_files, start=1):
        nums = re.findall(r"\d+", os.path.basename(img_path))
        page_num = int(nums[-1]) if nums else idx

        txt_path = os.path.join(TXT_DIR, f"page_{page_num:04d}.txt")
        if os.path.exists(txt_path):
            continue

        print(f"OCR Image Page {page_num}...")
        img = Image.open(img_path)
        text = ocr_single_image(model, img)
        if text:
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(text)
            time.sleep(2)


def combine_all_txt_to_single_json():
    """output فولڈر میں موجود تمام .txt فائلوں کو برقرار رکھتے ہوئے ایک سنگل full_book.json بناتا ہے"""
    txt_files = glob.glob(os.path.join(OUTPUT_DIR, "**", "*.txt"), recursive=True)

    if not txt_files:
        print("output فولڈر میں کوئی .txt فائل نہیں ملی!")
        return

    pages_dict = {}

    for file_path in sorted(txt_files):
        filename = os.path.basename(file_path)
        nums = re.findall(r"\d+", filename)
        if not nums:
            continue

        page_num = int(nums[-1])

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            continue

        if content:
            pages_dict[page_num] = content

    # تمام صفحات کو 1، 2، 3 کی ترتیب میں لگانا
    book_list = [
        {"page": p, "content": pages_dict[p]}
        for p in sorted(pages_dict.keys())
    ]

    # سنگل JSON فائل سیو کرنا
    with open(JSON_FILE, "w", encoding="utf-8") as jf:
        json.dump(book_list, jf, ensure_ascii=False, indent=2)

    print(f"✅ کامیابی! کل {len(book_list)} صفحات کی سنگل فائل '{JSON_FILE}' بن گئی ہے، اور تمام پیج وائز .txt فائلیں بھی محفوظ ہیں۔")


if __name__ == "__main__":
    process_inputs()
    combine_all_txt_to_single_json()
