import os
import time

from PIL import Image

from src.ai_verifier import run_multi_agent_pipeline
from src.pdf_utils import extract_images_from_pdf

INPUT_DIR = "input"
OUTPUT_DIR = "output"
SUPPORTED_IMAGES = (".png", ".jpg", ".jpeg", ".webp")


def process_file(file_name):
    file_path = os.path.join(INPUT_DIR, file_name)
    if file_name.lower().endswith(".pdf"):
        print(f"PDF extract ho rahi hai: {file_name}")
        pages = extract_images_from_pdf(file_path)
    elif file_name.lower().endswith(SUPPORTED_IMAGES):
        pages = [(1, Image.open(file_path))]
    else:
        return

    for page_num, image in pages:
        print(f"\n==========================================")
        print(f"Page {page_num} process ho raha hai")
        print("==========================================")

        try:
            print("[Key 1 - Munshi]: Pehla kacha draft bana raha hai...")
            print("[Key 2 - Inspector]: Ghaltiyan dhoond kar audit kar raha hai...")
            print("[Key 3 - Thanedar]: Aakhri faisla kar raha hai...")
            final_text = run_multi_agent_pipeline(image)

            output_file = os.path.join(
                OUTPUT_DIR, f"{file_name}_page_{page_num}.txt"
            )
            with open(output_file, "w", encoding="utf-8") as output:
                output.write(final_text)
            print(f"Thanedar ki mohar lag gayi! Saved: {output_file}")
        except Exception as error:
            print(f"Page {page_num} par masla: {error}")
        finally:
            image.close()
            time.sleep(3)


if __name__ == "__main__":
    os.makedirs(INPUT_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    files = [name for name in os.listdir(INPUT_DIR) if not name.startswith(".")]
    if not files:
        print("input/ folder khali hai! Koi image ya PDF upload karein.")
    else:
        for file_name in files:
            process_file(file_name)
