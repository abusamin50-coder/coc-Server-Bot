"""
Debug OCR — crops the loot regions and shows exactly what Tesseract reads.
Place the opponent-preview screenshot as 'test_loot.png' and run.
"""
import cv2, re, os
import numpy as np
from PIL import Image
import pytesseract

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

IMG = "test_loot.png"   # <-- put your screenshot here

img = cv2.imread(IMG)
if img is None:
    print(f"Cannot load {IMG}"); exit()

h, w = img.shape[:2]
print(f"Image size: {w} x {h}")

# Current regions
REGIONS = {
    "Gold":        (60, 112, 230, 150),
    "Elixir":      (60, 152, 230, 190),
    "Dark Elixir": (60, 192, 230, 230),
}

# Draw and save annotated preview
vis = img.copy()
for name, (x1,y1,x2,y2) in REGIONS.items():
    color = {"Gold":(0,215,255),"Elixir":(255,0,200),"Dark Elixir":(100,100,255)}[name]
    cv2.rectangle(vis, (x1,y1),(x2,y2), color, 2)
    cv2.putText(vis, name, (x1, y1-5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

cv2.imwrite("debug_regions.png", vis)
print("Saved annotated image: debug_regions.png\n")

# OCR each region with multiple threshold attempts
for name, (x1,y1,x2,y2) in REGIONS.items():
    crop = img[y1:y2, x1:x2]
    cv2.imwrite(f"crop_{name.replace(' ','_')}.png", crop)

    print(f"── {name} region ({x1},{y1})-({x2},{y2}) size={crop.shape[1]}x{crop.shape[0]} ──")

    for thresh_val in [80, 100, 120, 150]:
        big  = cv2.resize(crop, (crop.shape[1]*4, crop.shape[0]*4),
                          interpolation=cv2.INTER_CUBIC)
        gray = cv2.cvtColor(big, cv2.COLOR_BGR2GRAY)
        _, th = cv2.threshold(gray, thresh_val, 255, cv2.THRESH_BINARY)
        raw  = pytesseract.image_to_string(
            Image.fromarray(th),
            config="--psm 7 -c tessedit_char_whitelist=0123456789, "
        )
        digits = re.sub(r"[^0-9]", "", raw)
        val = int(digits) if digits else 0
        print(f"  thresh={thresh_val}: raw='{raw.strip()}' → {val}")

    print()
