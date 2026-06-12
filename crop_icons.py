"""
Crops loot icons from a screenshot and saves them as templates.
Run while opponent preview screen is visible.
"""
import subprocess, cv2, sys

ADB  = r"e:\coc auto bot\adb_tools\platform-tools\adb.exe"
DEV  = "127.0.0.1:5555"
OUT  = "live_screen.png"

def grab():
    subprocess.run([ADB, "connect", DEV], capture_output=True)
    r = subprocess.run([ADB, "-s", DEV, "exec-out", "screencap", "-p"], capture_output=True)
    if r.returncode == 0 and len(r.stdout) > 5000:
        with open(OUT, "wb") as f:
            f.write(r.stdout)
        return True
    return False

src = OUT if grab() else (sys.argv[1] if len(sys.argv) > 1 else "screenshot.png")
img = cv2.imread(src)
if img is None:
    print(f"Cannot load {src}"); exit()

h, w = img.shape[:2]
print(f"Screenshot: {w}x{h}")

# Icon positions for 1456x816
# Adjust these if icons are in wrong place
ICONS = {
    "loot_gold":   (18, 118, 65, 160),   # x1,y1,x2,y2
    "loot_elixir": (18, 160, 65, 202),
    "loot_dark":   (18, 202, 65, 244),
}

for name, (x1, y1, x2, y2) in ICONS.items():
    crop = img[y1:y2, x1:x2]
    if crop.size == 0:
        print(f"  {name}: empty crop, skip")
        continue
    path = f"templates/{name}.png"
    cv2.imwrite(path, crop)
    print(f"  Saved: {path}  ({crop.shape[1]}x{crop.shape[0]})")

# Save annotated preview
vis = img.copy()
import cv2
for name, (x1,y1,x2,y2) in ICONS.items():
    cv2.rectangle(vis,(x1,y1),(x2,y2),(0,255,0),2)
cv2.imwrite("icon_crop_preview.png", vis)
print("\nSaved: icon_crop_preview.png — check if green boxes are on icons")
