"""
Run this while the opponent preview screen is visible in your emulator.
It will: take a screenshot via ADB, show its size, and draw the loot regions.
"""
import subprocess
import cv2
import sys
import os

ADB = "e:/coc auto bot/adb_tools/platform-tools/adb.exe"
DEVICE = "127.0.0.1:5555"
OUT = "check_screenshot.png"

def take_screenshot():
    subprocess.run([ADB, "connect", DEVICE], capture_output=True)
    r = subprocess.run([ADB, "-s", DEVICE, "exec-out", "screencap", "-p"],
                       capture_output=True)
    if r.returncode != 0 or len(r.stdout) < 1000:
        print("ADB screenshot failed — using existing screenshot.png if available")
        return False
    with open(OUT, "wb") as f:
        f.write(r.stdout)
    print(f"Screenshot saved: {OUT}")
    return True

def main():
    path = OUT if take_screenshot() else "screenshot.png"
    img = cv2.imread(path)
    if img is None:
        print(f"Cannot load image: {path}")
        return

    h, w = img.shape[:2]
    print(f"\nActual screenshot resolution: {w} x {h}")
    print("Update config.yaml emulator section if different from 1280x720\n")

    # Draw current loot regions
    regions = {
        "Gold":        ((95,  82, 260, 115), (0, 215, 255)),
        "Elixir":      ((95, 112, 260, 145), (255, 0, 200)),
        "Dark Elixir": ((95, 142, 260, 175), (80,  80,  80)),
    }
    vis = img.copy()
    for name, (region, color) in regions.items():
        x1, y1, x2, y2 = region
        cv2.rectangle(vis, (x1, y1), (x2, y2), color, 2)
        cv2.putText(vis, name, (x1, max(y1-4, 10)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

    # Also mark top-left corner for reference
    cv2.rectangle(vis, (0, 0), (300, 200), (0,255,0), 1)
    cv2.putText(vis, "Loot area (top-left)", (5, 15),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,0), 1)

    out_path = "resolution_check.png"
    cv2.imwrite(out_path, vis)
    print(f"Preview saved: {out_path}")
    print("Send this image to see if colored boxes cover the loot numbers.")

    try:
        cv2.imshow("Resolution Check", vis)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    except Exception:
        pass

if __name__ == "__main__":
    main()
