import subprocess, cv2, sys

ADB = "e:\\coc bot\\adb_tools\\platform-tools\\adb.exe"
r = subprocess.run([ADB, "connect", "127.0.0.1:5555"], capture_output=True, text=True)
print("connect:", r.stdout.strip())

r2 = subprocess.run([ADB, "-s", "127.0.0.1:5555", "exec-out", "screencap", "-p"], capture_output=True)
print("bytes:", len(r2.stdout))

if len(r2.stdout) > 5000:
    with open("live_ss.png", "wb") as f:
        f.write(r2.stdout)
    img = cv2.imread("live_ss.png")
    h, w = img.shape[:2]
    print(f"Size: {w}x{h}")
    # Save top-left 320x280 — loot area
    cv2.imwrite("topleft.png", img[60:280, 0:320])
    print("Saved topleft.png")
else:
    print("ADB screenshot failed")
