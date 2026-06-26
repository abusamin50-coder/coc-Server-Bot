"""
Troop Detection & Smart Deployment
====================================
Logic based on visual difference between available and deployed troops:

  AVAILABLE  → icon is COLORFUL (high HSV saturation)
  DEPLOYED   → icon is GRAY/DARK (low HSV saturation)

Flow:
  1. Take screenshot of troop bar
  2. For each configured troop: find icon, check saturation
  3. If colorful → select → deploy to zones (quantity times)
  4. If gray     → already empty, skip (do NOT tap it)
  5. Repeat until ALL slots are gray (all troops deployed)
"""

import time
import threading
import cv2
import numpy as np
from pathlib import Path
from loguru import logger


# ── Constants ──────────────────────────────────────────────────────────────────

SAT_THRESHOLD     = 40
CROP_TOP_RATIO    = 0.22
CROP_BOTTOM_RATIO = 0.15
CROP_SIDE_RATIO   = 0.10


# ══════════════════════════════════════════════════════════════════════════════
#  Core helpers
# ══════════════════════════════════════════════════════════════════════════════

def _crop_inner(template: np.ndarray) -> np.ndarray:
    h, w = template.shape[:2]
    y1 = int(h * CROP_TOP_RATIO)
    y2 = int(h * (1 - CROP_BOTTOM_RATIO))
    x1 = int(w * CROP_SIDE_RATIO)
    x2 = int(w * (1 - CROP_SIDE_RATIO))
    cropped = template[y1:y2, x1:x2]
    if cropped.size == 0:
        return template
    return cropped


def _mean_saturation(image: np.ndarray) -> float:
    if image is None or image.size == 0:
        return 0.0
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    return float(np.mean(hsv[:, :, 1]))


def is_slot_colorful(screenshot: np.ndarray, cx: int, cy: int, radius: int = 35) -> bool:
    h, w = screenshot.shape[:2]
    x1 = max(0, cx - radius)
    x2 = min(w, cx + radius)
    y_top    = max(0, cy - radius + int(radius * 0.3))
    y_bottom = min(h, cy + radius - int(radius * 0.3))
    region = screenshot[y_top:y_bottom, x1:x2]
    sat = _mean_saturation(region)
    logger.debug(f"  Saturation at ({cx},{cy}): {sat:.1f} → {'AVAILABLE' if sat > SAT_THRESHOLD else 'EMPTY'}")
    return sat > SAT_THRESHOLD


# ══════════════════════════════════════════════════════════════════════════════
#  Template-based troop finder
# ══════════════════════════════════════════════════════════════════════════════

class TroopFinder:
    SCALES = [0.7, 0.8, 0.9, 1.0, 1.1]
    CONFIDENCES = [0.55, 0.45, 0.35, 0.25, 0.18]

    def __init__(self):
        self._cache: dict[str, np.ndarray] = {}

    def _load(self, image_path: str) -> np.ndarray | None:
        if image_path in self._cache:
            return self._cache[image_path]
        img = cv2.imread(image_path)
        if img is None:
            logger.error(f"Cannot load troop image: {image_path}")
            return None
        cropped = _crop_inner(img)
        self._cache[image_path] = cropped
        return cropped

    def find(self, screenshot: np.ndarray, image_path: str,
             search_y_start_ratio: float = 0.75) -> tuple[int, int, float]:
        tmpl = self._load(image_path)
        if tmpl is None:
            return None, None, 0.0

        sh, sw = screenshot.shape[:2]
        th, tw = tmpl.shape[:2]

        y_offset = int(sh * search_y_start_ratio)
        region = screenshot[y_offset:, :]
        rh, rw = region.shape[:2]

        best_val   = 0.0
        best_loc   = None
        best_scale = 1.0

        for s in self.SCALES:
            sw2 = int(tw * s)
            sh2 = int(th * s)
            if sw2 <= 0 or sh2 <= 0 or sw2 > rw or sh2 > rh:
                continue
            scaled = cv2.resize(tmpl, (sw2, sh2))
            result = cv2.matchTemplate(region, scaled, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(result)
            if max_val > best_val:
                best_val   = max_val
                best_loc   = max_loc
                best_scale = s

        for conf in self.CONFIDENCES:
            if best_val >= conf and best_loc is not None:
                sw2 = int(tw * best_scale)
                sh2 = int(th * best_scale)
                cx = best_loc[0] + sw2 // 2
                cy = y_offset + best_loc[1] + sh2 // 2
                return cx, cy, best_val

        return None, None, 0.0


# ══════════════════════════════════════════════════════════════════════════════
#  Smart deployment controller
# ══════════════════════════════════════════════════════════════════════════════

class SmartTroopDeployer:
    """
    Deploys troops intelligently:
    - Finds each troop icon, checks colour saturation
    - Colorful = available → select and deploy to zones
    - Gray = empty → skip entirely (no tap)
    - Loops until ALL slots are gray (all deployed)
    """

    def __init__(self, adb, screenshot_fn, config: dict,
                 status_cb=None, stop_event: threading.Event = None):
        self.adb          = adb
        self._snap        = screenshot_fn
        self.config       = config
        self._cb          = status_cb
        self.finder       = TroopFinder()
        # Accept a shared Event so bot_engine.stop() wakes us immediately
        self._stop_event  = stop_event if stop_event is not None else threading.Event()

        emu = config.get("emulator", {})
        self.width  = emu.get("resolution_width",  1280)
        self.height = emu.get("resolution_height",  720)
        self.deploy_speed = config.get("troops", {}).get("deploy_speed", 0.08)

    @property
    def _should_stop(self) -> bool:
        return self._stop_event.is_set()

    def stop(self):
        self._stop_event.set()

    def _log(self, msg: str, level: str = "info"):
        getattr(logger, level)(msg)
        if self._cb:
            self._cb(msg, level)

    def _sleep(self, seconds: float):
        self._stop_event.wait(timeout=seconds)

    # ── Deploy zones ──────────────────────────────────────────────────────────

    def _find_deploy_zone_on_screen(self, screenshot: np.ndarray) -> tuple[int, int] | None:
        zone_image_path = self.config.get("deploy_zone_image", "")
        if not zone_image_path or not Path(zone_image_path).exists():
            return None

        tmpl = cv2.imread(zone_image_path)
        if tmpl is None:
            logger.error(f"Cannot load deploy zone image: {zone_image_path}")
            return None

        sh, sw = screenshot.shape[:2]
        th, tw = tmpl.shape[:2]

        best_val   = 0.0
        best_loc   = None
        best_scale = 1.0

        for s in [0.8, 0.9, 1.0, 1.1, 1.2]:
            rw, rh = int(tw * s), int(th * s)
            if rw <= 0 or rh <= 0 or rw > sw or rh > sh:
                continue
            scaled = cv2.resize(tmpl, (rw, rh))
            result = cv2.matchTemplate(screenshot, scaled, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(result)
            if max_val > best_val:
                best_val   = max_val
                best_loc   = max_loc
                best_scale = s

        if best_val >= 0.25 and best_loc is not None:
            rw = int(tw * best_scale)
            rh = int(th * best_scale)
            cx = best_loc[0] + rw // 2
            cy = best_loc[1] + rh // 2
            logger.info(f"Deploy zone found at ({cx},{cy}) conf={best_val:.2f}")
            return cx, cy

        logger.warning(f"Deploy zone image not found on screen (best={best_val:.2f})")
        return None

    def _deploy_zones(self, screenshot: np.ndarray = None, cached_x: int = None, cached_y: int = None) -> list[tuple[int, int]]:
        """
        Deploy zones priority:
        1. Use cached (x,y) if provided
        2. Auto-detect from screenshot if available
        3. Fall back to custom zones from config
        4. Use default left-side grid
        """
        # Priority 1: Use cached values
        if cached_x is not None and cached_y is not None:
            cx, cy = cached_x, cached_y
            offsets = [
                (0, 0),
                (-20, 0), (20, 0),
                (0, -20), (0, 20),
                (-15, -15), (15, -15),
                (-15, 15), (15, 15),
            ]
            zones = [(cx + dx, cy + dy) for dx, dy in offsets]
            logger.info(f"Using CACHED deploy zone at ({cx},{cy}) — {len(zones)} spread points")
            return zones

        # Priority 2: Try to detect from screenshot
        if screenshot is not None:
            center = self._find_deploy_zone_on_screen(screenshot)
            if center is not None:
                cx, cy = center
                offsets = [
                    (0, 0),
                    (-20, 0), (20, 0),
                    (0, -20), (0, 20),
                    (-15, -15), (15, -15),
                    (-15, 15), (15, 15),
                ]
                zones = [(cx + dx, cy + dy) for dx, dy in offsets]
                logger.info(f"Deploy zone DETECTED at ({cx},{cy}) — {len(zones)} spread points")
                return zones

        # Priority 3: Use custom zones from config
        custom = self.config.get("deploy_zones", [])
        if custom:
            zones = [(z["x"], z["y"]) for z in custom]
            logger.info(f"Using {len(zones)} custom deploy zones from config")
            return zones

        # Priority 4: Default grid
        w, h = self.width, self.height
        zones = []
        for col in [0.08, 0.14, 0.20]:
            for row in [0.08, 0.16, 0.24, 0.32, 0.40, 0.48, 0.56, 0.64]:
                zones.append((int(w * col), int(h * row)))
        logger.info(f"Using DEFAULT {len(zones)} deploy zones (left-side grid)")
        return zones

    # ── Single troop — deploy until gray ────────────────────────────────────────

    def _deploy_until_gray(self, cx: int, cy: int, name: str, zones: list):
        """
        Select troop at (cx, cy), then keep tapping deploy zones
        until the slot turns gray (empty).

        Optimized: Check saturation every 10-15 taps (not every 3)
        to reduce screenshot frequency by ~70%.

        Loop:
          1. Tap slot to select
          2. Tap next deploy zone (10-15 times per check)
          3. Re-screenshot and check saturation (less frequently)
          4. Still colorful → repeat from step 2
          5. Gray → done
        """
        # Select the troop (triple-tap)
        for _ in range(3):
            self.adb.tap(cx, cy)
            time.sleep(0.08)
        time.sleep(0.15)

        zone_idx  = 0
        tap_count = 0
        max_taps  = 300  # safety — never loop forever
        check_interval = 12  # Check saturation every 12 taps (was 3) — 75% fewer screenshots

        self._log(f"  Deploying '{name}' until gray…")

        while not self._should_stop and tap_count < max_taps:
            # Tap one deploy zone
            zx, zy = zones[zone_idx % len(zones)]
            self.adb.tap(zx, zy)
            zone_idx  += 1
            tap_count += 1
            self._sleep(self.deploy_speed)

            # Check saturation every N taps (reduced frequency)
            if tap_count % check_interval == 0:
                shot = self._snap()
                if shot is None:
                    continue
                if not is_slot_colorful(shot, cx, cy):
                    self._log(f"  '{name}': gray after {tap_count} taps — done")
                    return

        # Final check
        shot = self._snap()
        if shot is not None and not is_slot_colorful(shot, cx, cy):
            self._log(f"  '{name}': gray — done")
        else:
            self._log(f"  '{name}': reached max taps ({max_taps}) — moving on", "warning")

    # ── Main deploy loop ──────────────────────────────────────────────────────

    def deploy(self) -> bool:
        """
        Deploy all configured troops one by one.

        For each troop:
          - Find icon in troop bar
          - If colorful → deploy until gray (tap zones repeatedly)
          - If gray     → already empty, skip

        After going through all troops once, do a final scan.
        If any slot is still colorful → do another pass (max 3 full passes).
        """
        custom_troops = self.config.get("troops", {}).get("custom_troops", [])
        if not custom_troops:
            self._log("No custom troops configured — skipping deployment", "warning")
            return False

        self._log(f"Starting troop deployment ({len(custom_troops)} troop type(s))…")

        deployed_any = False
        max_passes   = 3  # full rescan passes

        for pass_num in range(1, max_passes + 1):
            if self._should_stop:
                break

            self._log(f"  Pass {pass_num} — scanning troop bar…")
            screenshot = self._snap()
            if screenshot is None:
                self._log("  Screenshot failed", "error")
                break

            zones     = self._deploy_zones(screenshot)
            all_empty = True

            for troop_cfg in custom_troops:
                if self._should_stop:
                    break

                name       = troop_cfg.get("name", "Unknown")
                image_path = troop_cfg.get("image", "")

                if not image_path or not Path(image_path).exists():
                    self._log(f"  '{name}': image not found — skipping", "warning")
                    continue

                # Find icon in troop bar
                cx, cy, _ = self.finder.find(screenshot, image_path)
                if cx is None:
                    self._log(f"  '{name}': not found in bar", "warning")
                    all_empty = False  # might be there, try again next pass
                    continue

                # Check color
                if not is_slot_colorful(screenshot, cx, cy):
                    self._log(f"  '{name}': gray — already empty, skip")
                    continue

                # Colorful → deploy until gray
                all_empty = False
                deployed_any = True
                self._deploy_until_gray(cx, cy, name, zones)

                if self._should_stop:
                    break

                # Refresh screenshot for next troop check
                screenshot = self._snap()
                if screenshot is None:
                    break

            if self._should_stop:
                break

            if all_empty:
                self._log("  All slots gray — deployment complete!")
                break

            if pass_num < max_passes:
                self._log(f"  Pass {pass_num} done — rescanning for remaining troops…")

        if deployed_any:
            self._log("Troop deployment finished")
        else:
            self._log("No troops deployed (all slots already empty)", "warning")

        return deployed_any


# ══════════════════════════════════════════════════════════════════════════════
#  Deploy zones (used by other parts of the bot)
# ══════════════════════════════════════════════════════════════════════════════

class DeployZones:
    @staticmethod
    def left_side(width: int, height: int) -> list[tuple[int, int]]:
        zones = []
        for col in [0.08, 0.14, 0.20]:
            for row in [0.08, 0.16, 0.24, 0.32, 0.40, 0.48, 0.56, 0.64]:
                zones.append((int(width * col), int(height * row)))
        return zones

    @staticmethod
    def get_deploy_zones(height: int, width: int) -> list[tuple[int, int]]:
        return DeployZones.left_side(width, height)
