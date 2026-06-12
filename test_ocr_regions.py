"""
OCR region test — run this to visually verify loot regions on a screenshot.
Usage:
    python test_ocr_regions.py screenshot.png
or just run it and it will use the latest screenshot.png
"""

import sys
import cv2
import numpy as np

# Same regions as bot_engine.py
GOLD_REGION        = (95,  82, 260, 115)
ELIXIR_REGION      = (95, 112, 260, 145)
DARK_ELIXIR_REGION = (95, 142, 260, 175)

REGIONS = {
    "Gold":        (GOLD_REGION,        (0, 215, 255)),   # yellow
    "Elixir":      (ELIXIR_REGION,      (255, 0, 200)),   # purple
    "Dark Elixir": (DARK_ELIXIR_REGION, (50,  50,  50)),  # dark
}

def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "screenshot.png"
    img = cv2.imread(path)
    if img is None:
        print(f"Cannot load: {path}")
        return

    h, w = img.shape[:2]
    print(f"Screenshot size: {w}x{h}")

    # Draw rectangles and crop previews
    vis = img.copy()
    for name, (region, color) in REGIONS.items():
        x1, y1, x2, y2 = region
        cv2.rectangle(vis, (x1, y1), (x2, y2), color, 2)
        cv2.putText(vis, name, (x1, y1 - 4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

        crop = img[y1:y2, x1:x2]
        print(f"\n[{name}] region ({x1},{y1})-({x2},{y2}) — {crop.shape[1]}x{crop.shape[0]}px")

        # Also try OCR on this region
        try:
            import pytesseract
            from PIL import Image
            import re
            import os

            for p in ["C:/Program Files/Tesseract-OCR/tesseract.exe",
                      "C:/Program Files (x86)/Tesseract-OCR/tesseract.exe"]:
                if os.path.exists(p):
                    pytesseract.pytesseract.tesseract_cmd = p
                    break

            big = cv2.resize(crop, (crop.shape[1]*3, crop.shape[0]*3),
                             interpolation=cv2.INTER_CUBIC)
            gray = cv2.cvtColor(big, cv2.COLOR_BGR2GRAY)
            _, thresh = cv2.threshold(gray, 100, 255, cv2.THRESH_BINARY)
            pil_img = Image.fromarray(thresh)
            raw = pytesseract.image_to_string(
                pil_img, config="--psm 7 -c tessedit_char_whitelist=0123456789,"
            )
            digits = re.sub(r"[^0-9]", "", raw)
            value = int(digits) if digits else 0
            print(f"  OCR raw: '{raw.strip()}' → value: {value}")
        except Exception as e:
            print(f"  OCR skipped: {e}")

    # Save annotated image
    out = "ocr_regions_preview.png"
    cv2.imwrite(out, vis)
    print(f"\nAnnotated preview saved: {out}")
    print("Open it to verify the colored boxes are over the correct numbers.")

    # Show if display available
    try:
        cv2.imshow("OCR Regions Preview", vis)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    except Exception:
        pass

if __name__ == "__main__":
    main()
