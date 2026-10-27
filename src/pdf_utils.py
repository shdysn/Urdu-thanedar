import io

import fitz
from PIL import Image


def extract_images_from_pdf(pdf_path):
    images = []
    with fitz.open(pdf_path) as document:
        for page_num, page in enumerate(document, start=1):
            pixmap = page.get_pixmap(dpi=300)
            image = Image.open(io.BytesIO(pixmap.tobytes("png")))
            images.append((page_num, image))
    return images
