"""
Quick verify — draws the new OCR regions on any screenshot.
Usage: python verify_loot_regions.py <image_path>
"""
import sys, cv2

REGIONS = [
    ("Gold",        (65, 118, 260, 155), (0, 215, 255)),
    ("Elixir",      (65, 158, 260, 195), (255, 0, 200)),
    ("Dark Elixir", (65, 198, 260, 235), (100, 100, 255)),
]

path = sys.argv[1] if len(sys.argv) > 1 else "screenshot.png"
img  = cv2.imread(path)
if img is None:
    print(f"Cannot load: {path}"); exit()

h, w = img.shape[:2]
print(f"Image size: {w}x{h}")

vis = img.copy()
for name, (x1,y1,x2,y2), col in REGIONS:
    cv2.rectangle(vis, (x1,y1),(x2,y2), col, 2)
    cv2.putText(vis, name, (x1, y1-5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, col, 2)

    crop = img[y1:y2, x1:x2]
    try:
        import pytesseract, re
        from PIL import Image as PILImage
        import os, numpy as np
        for p in ["C:/Program Files/Tesseract-OCR/tesseract.exe",
                  "C:/Program Files (x86)/Tesseract-OCR/tesseract.exe"]:
            if os.path.exists(p):
                pytesseract.pytesseract.tesseract_cmd = p; break
        big   = cv2.resize(crop, (crop.shape[1]*3, crop.shape[0]*3), interpolation=cv2.INTER_CUBIC)
        gray  = cv2.cvtColor(big, cv2.COLOR_BGR2GRAY)
        _, th = cv2.threshold(gray, 100, 255, cv2.THRESH_BINARY)
        raw   = pytesseract.image_to_string(PILImage.fromarray(th),
                    config="--psm 7 -c tessedit_char_whitelist=0123456789,")
        val   = int(re.sub(r"[^0-9]","",raw)) if re.sub(r"[^0-9]","",raw) else 0
        print(f"  {name}: OCR='{raw.strip()}' → {val}")
    except Exception as e:
        print(f"  {name}: OCR skipped ({e})")

cv2.imwrite("verify_output.png", vis)
print("\nSaved: verify_output.png — check if colored boxes cover the numbers.")
try:
    cv2.imshow("Verify", vis); cv2.waitKey(0); cv2.destroyAllWindows()
except Exception:
    pass
