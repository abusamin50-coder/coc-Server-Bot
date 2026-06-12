"""
Run this WHILE the opponent preview screen is visible
(the screen that shows Available Loot before you tap Attack).

It saves the screenshot and draws a grid so you can read exact coordinates.
"""
import subprocess, cv2, sys, os

ADB   = r"e:\coc auto bot\adb_tools\platform-tools\adb.exe"
DEV   = "127.0.0.1:5555"
OUT   = "loot_pos_check.png"

def grab():
    subprocess.run([ADB, "connect", DEV], capture_output=True)
    r = subprocess.run([ADB, "-s", DEV, "exec-out", "screencap", "-p"],
                       capture_output=True)
    if r.returncode == 0 and len(r.stdout) > 5000:
        with open(OUT, "wb") as f:
            f.write(r.stdout)
        return True
    return False

def main():
    if not grab():
        print("ADB grab failed — place screenshot.png manually and re-run")
        src = "screenshot.png"
    else:
        src = OUT

    img = cv2.imread(src)
    if img is None:
        print("No image found"); return

    h, w = img.shape[:2]
    print(f"Resolution: {w}x{h}")

    vis = img.copy()

    # Draw 50px grid
    for x in range(0, w, 50):
        cv2.line(vis, (x,0),(x,h),(60,60,60),1)
        if x % 100 == 0:
            cv2.putText(vis, str(x),(x+2,12),cv2.FONT_HERSHEY_SIMPLEX,0.35,(180,180,180),1)
    for y in range(0, h, 50):
        cv2.line(vis, (0,y),(w,y),(60,60,60),1)
        if y % 100 == 0:
            cv2.putText(vis, str(y),(2,y+10),cv2.FONT_HERSHEY_SIMPLEX,0.35,(180,180,180),1)

    # Draw current OCR regions
    regions = [
        ("Gold",        (95,  82, 260, 115), (0,215,255)),
        ("Elixir",      (95, 112, 260, 145), (255,0,200)),
        ("Dark Elixir", (95, 142, 260, 175), (100,100,255)),
    ]
    for name,(x1,y1,x2,y2),col in regions:
        cv2.rectangle(vis,(x1,y1),(x2,y2),col,2)
        cv2.putText(vis,name,(x1,y1-4),cv2.FONT_HERSHEY_SIMPLEX,0.5,col,1)

    cv2.imwrite("loot_grid.png", vis)
    print("Saved: loot_grid.png")
    print("Open it — find where the gold/elixir numbers are and note their Y coordinates.")

    try:
        cv2.imshow("Loot grid — press any key to close", vis)
        cv2.waitKey(0); cv2.destroyAllWindows()
    except Exception:
        pass

if __name__=="__main__":
    main()
