import fitz  # PyMuPDF
import io
import numpy as np
from PIL import Image

def remove_red_watermark(pil_img):
    """Laal rang ke watermark ko bilkul safed (white) kar ke mita deta hai"""
    img = pil_img.convert("RGB")
    arr = np.array(img)
    
    r = arr[:, :, 0].astype(int)
    g = arr[:, :, 1].astype(int)
    b = arr[:, :, 2].astype(int)
    
    # Red watermark detection formula
    red_mask = (r > 120) & (r - g > 30) & (r - b > 30)
    arr[red_mask] = [255, 255, 255]
    
    return Image.fromarray(arr)

def extract_images_from_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    images = []
    for page_num in range(len(doc)):
        page = doc[page_num]
        pix = page.get_pixmap(dpi=300)
        raw_img = Image.open(io.BytesIO(pix.tobytes("png")))
        # Watermark filter apply karna
        cleaned_img = remove_red_watermark(raw_img)
        images.append((page_num + 1, cleaned_img))
    return images
