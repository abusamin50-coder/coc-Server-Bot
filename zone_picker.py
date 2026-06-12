"""
Deploy Zone Picker
==================
Run this tool to visually select where troops will be deployed.

Usage:
  py zone_picker.py

Instructions:
  - LEFT CLICK  : add a deploy point
  - RIGHT CLICK : remove last point
  - ENTER       : save zones and exit
  - ESC         : cancel (don't save)
"""

import cv2
import numpy as np
import yaml
import sys
import os
from pathlib import Path
from adb_controller import ADBController
from config import load_config

CONFIG_FILE = "config.yaml"
WINDOW_NAME = "Deploy Zone Picker  |  LEFT=Add  RIGHT=Undo  ENTER=Save  ESC=Cancel"


def draw_zones(image: np.ndarray, points: list) -> np.ndarray:
    display = image.copy()
    for i, (x, y) in enumerate(points):
        # Draw circle
        cv2.circle(display, (x, y), 12, (0, 255, 0), -1)
        cv2.circle(display, (x, y), 12, (255, 255, 255), 2)
        # Draw number label
        cv2.putText(display, str(i + 1), (x - 6, y + 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)

    # Instructions overlay
    h, w = display.shape[:2]
    overlay = display.copy()
    cv2.rectangle(overlay, (0, 0), (w, 36), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.6, display, 0.4, 0, display)
    cv2.putText(display,
                f"Points: {len(points)}  |  LEFT=Add  RIGHT=Undo  ENTER=Save  ESC=Cancel",
                (10, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 1)
    return display


def main():
    config = load_config(CONFIG_FILE)

    # ── Get screenshot ──────────────────────────────────────────────────────
    screenshot_path = "zone_picker_screen.png"

    # Try to load an existing image passed as argument
    if len(sys.argv) > 1 and os.path.exists(sys.argv[1]):
        screenshot_path = sys.argv[1]
        image = cv2.imread(screenshot_path)
        print(f"Using provided image: {screenshot_path}")

    elif os.path.exists("screenshot.png"):
        # Use last screenshot if available
        image = cv2.imread("screenshot.png")
        screenshot_path = "screenshot.png"
        print("Using existing screenshot.png")

    else:
        # Take live screenshot from device
        print("Taking screenshot from device…")
        adb_cfg = config.get("adb", {})
        adb = ADBController(
            device_id=adb_cfg.get("device_id", "127.0.0.1:5555"),
            adb_port=adb_cfg.get("port", 5555),
            adb_path=adb_cfg.get("adb_path"),
        )
        adb.connect_device()
        if not adb.screenshot(screenshot_path):
            print("ERROR: Could not take screenshot. Make sure LDPlayer is running.")
            print("       Or drag a battlefield screenshot onto this script.")
            input("Press Enter to exit…")
            return
        image = cv2.imread(screenshot_path)

    if image is None:
        print("ERROR: Could not load image.")
        input("Press Enter to exit…")
        return

    h, w = image.shape[:2]
    print(f"Image loaded: {w}x{h}")
    print()
    print("  LEFT CLICK  → Add deploy point")
    print("  RIGHT CLICK → Remove last point")
    print("  ENTER       → Save & exit")
    print("  ESC         → Cancel")
    print()

    # Load existing zones so user can see/edit them
    existing = config.get("deploy_zones", [])
    points: list[tuple[int, int]] = [(z["x"], z["y"]) for z in existing]

    def on_mouse(event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            points.append((x, y))
            print(f"  + Point {len(points)}: ({x}, {y})")
        elif event == cv2.EVENT_RBUTTONDOWN:
            if points:
                removed = points.pop()
                print(f"  - Removed: {removed}")

    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(WINDOW_NAME, min(w, 1280), min(h, 720))
    cv2.setMouseCallback(WINDOW_NAME, on_mouse)

    while True:
        frame = draw_zones(image, points)
        cv2.imshow(WINDOW_NAME, frame)
        key = cv2.waitKey(30) & 0xFF

        if key == 13:   # ENTER — save
            break
        elif key == 27: # ESC — cancel
            print("Cancelled — zones not saved.")
            cv2.destroyAllWindows()
            return

    cv2.destroyAllWindows()

    if not points:
        print("No points selected — zones not saved.")
        return

    # Save to config.yaml
    config["deploy_zones"] = [{"x": x, "y": y} for x, y in points]
    with open(CONFIG_FILE, "w") as f:
        yaml.safe_dump(config, f, default_flow_style=False)

    print()
    print(f"Saved {len(points)} deploy zone(s) to config.yaml")
    for i, (x, y) in enumerate(points):
        print(f"  Zone {i+1}: ({x}, {y})")
    print()
    print("The bot will now deploy troops to ONLY these points.")
    input("Press Enter to exit…")


if __name__ == "__main__":
    main()
