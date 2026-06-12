"""Vision module — template matching (OpenCV) and loot OCR (Tesseract)."""

import re
from pathlib import Path

import cv2
import numpy as np
from loguru import logger

try:
    import pytesseract
    from PIL import Image
    _PYTESSERACT_AVAILABLE = True
except ImportError:
    _PYTESSERACT_AVAILABLE = False


# ══════════════════════════════════════════════════════════════
#  Template Matcher
# ══════════════════════════════════════════════════════════════

class TemplateMatcher:
    """
    Loads PNG templates from a directory and matches them against screenshots
    using multi-scale normalised cross-correlation.
    """

    SCALES = [0.80, 0.90, 1.00, 1.10, 1.20]

    def __init__(self, config_or_dir="templates", confidence: float = None):
        if isinstance(config_or_dir, dict):
            templates_dir = config_or_dir.get("templates_dir", "templates")
            if confidence is None:
                confidence = config_or_dir.get("bot", {}).get("template_confidence", 0.35)
        else:
            templates_dir = config_or_dir
            if confidence is None:
                confidence = 0.35

        self.templates_dir = Path(templates_dir)
        self.default_confidence = confidence
        self._cache: dict[str, np.ndarray] = {}
        self._load_all()

    # ── Loading ──────────────────────────────────────────────────────────────

    def _load_all(self):
        if not self.templates_dir.exists():
            logger.warning(f"Templates directory not found: {self.templates_dir}")
            return

        loaded = 0
        for fp in self.templates_dir.glob("*.png"):
            img = cv2.imread(str(fp))
            if img is not None:
                self._cache[fp.stem] = img
                loaded += 1
                logger.info(f"  Template loaded: {fp.stem} ({img.shape[1]}x{img.shape[0]})")
            else:
                logger.warning(f"  Could not load template: {fp}")

        logger.info(f"Templates ready: {loaded} loaded from {self.templates_dir}")

    def reload(self):
        self._cache.clear()
        self._load_all()

    def available(self) -> list[str]:
        return list(self._cache.keys())

    # ── Matching ─────────────────────────────────────────────────────────────

    def find(self, screenshot_path: str, template_name: str, confidence: float = None,
             region: tuple = None):
        """
        Search for template_name in screenshot.
        region=(x1,y1,x2,y2) to limit search area (e.g. bottom 40% for buttons).
        Returns (center_x, center_y, score) or (None, None, 0.0).
        """
        conf = confidence if confidence is not None else self.default_confidence

        screen = cv2.imread(screenshot_path)
        if screen is None:
            logger.error(f"Cannot load screenshot: {screenshot_path}")
            return None, None, 0.0

        tmpl = self._cache.get(template_name)
        if tmpl is None:
            logger.error(f"Template not found: '{template_name}'. Available: {self.available()}")
            return None, None, 0.0

        sh, sw = screen.shape[:2]
        th, tw = tmpl.shape[:2]

        # Crop search area if region specified
        if region:
            rx1, ry1, rx2, ry2 = region
            search = screen[ry1:ry2, rx1:rx2]
            offset_x, offset_y = rx1, ry1
        else:
            search = screen
            offset_x, offset_y = 0, 0

        srh, srw = search.shape[:2]

        # Auto-shrink oversized templates
        if (tw * th) / (sw * sh) > 0.35:
            scale = 0.3
            tmpl = cv2.resize(tmpl, (max(20, int(tw * scale)), max(20, int(th * scale))))
            th, tw = tmpl.shape[:2]
            logger.warning(f"Template '{template_name}' was oversized — auto-scaled to {tw}x{th}")

        best_score = 0.0
        best_loc   = None
        best_scale = 1.0

        for s in self.SCALES:
            rw, rh = int(tw * s), int(th * s)
            if rw <= 0 or rh <= 0 or rw > srw or rh > srh:
                continue
            resized = cv2.resize(tmpl, (rw, rh))
            result  = cv2.matchTemplate(search, resized, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(result)
            if max_val > best_score:
                best_score = max_val
                best_loc   = max_loc
                best_scale = s

        if best_score >= conf and best_loc is not None:
            rw = int(tw * best_scale)
            rh = int(th * best_scale)
            cx = offset_x + best_loc[0] + rw // 2
            cy = offset_y + best_loc[1] + rh // 2
            logger.debug(f"'{template_name}' → ({cx},{cy}) score={best_score:.2f}")
            return cx, cy, best_score

        logger.debug(f"'{template_name}' not found (best={best_score:.2f} < {conf:.2f})")
        return None, None, 0.0

    # Keep old method name for backward compat
    def find_template(self, screenshot_path, template_name, confidence=None):
        return self.find(screenshot_path, template_name, confidence)


# ══════════════════════════════════════════════════════════════
#  OCR Reader
# ══════════════════════════════════════════════════════════════

class OCRReader:
    """Reads Gold / Elixir / Dark-Elixir numbers from a CoC screenshot."""

    _TESSERACT_PATHS = [
        "C:/Program Files/Tesseract-OCR/tesseract.exe",
        "C:/Program Files (x86)/Tesseract-OCR/tesseract.exe",
    ]

    def __init__(self):
        self.available = self._init_tesseract()

    def _init_tesseract(self) -> bool:
        if not _PYTESSERACT_AVAILABLE:
            logger.warning("pytesseract not installed — OCR disabled")
            return False
        for p in self._TESSERACT_PATHS:
            if Path(p).exists():
                pytesseract.pytesseract.tesseract_cmd = p
                break
        try:
            pytesseract.get_tesseract_version()
            logger.info("Tesseract OCR ready")
            return True
        except Exception as e:
            logger.warning(f"Tesseract not found: {e} — loot check disabled")
            return False

    def read_loot(self, screenshot_path: str,
                  gold_region=None, elixir_region=None, dark_elixir_region=None):
        """
        Fixed region দেওয়া থাকলে সেটা দিয়ে OCR করো।
        Returns (gold, elixir, dark_elixir) as ints.
        """
        if not self.available:
            return 0, 0, 0
        try:
            img = cv2.imread(screenshot_path)
            if img is None:
                return 0, 0, 0

            if gold_region and elixir_region:
                # Fixed region mode — direct OCR
                x1,y1,x2,y2 = gold_region
                gold   = self._ocr_region(img, x1, y1, x2, y2, "Gold")
                x1,y1,x2,y2 = elixir_region
                elixir = self._ocr_region(img, x1, y1, x2, y2, "Elixir")
                dark = 0
                if dark_elixir_region:
                    x1,y1,x2,y2 = dark_elixir_region
                    dark = self._ocr_region(img, x1, y1, x2, y2, "Dark")
            else:
                # Icon template matching mode
                gold   = self._read_by_icon(img, "loot_gold",   "Gold")
                elixir = self._read_by_icon(img, "loot_elixir", "Elixir")
                dark   = self._read_by_icon(img, "loot_dark",   "Dark")

            logger.info(f"OCR loot — Gold={gold}  Elixir={elixir}  Dark={dark}")
            return gold, elixir, dark

        except Exception as e:
            logger.error(f"OCR read error: {e}")
            return 0, 0, 0

    def _read_by_icon(self, img: np.ndarray, template_name: str, label: str) -> int:
        """
        Find the loot icon on the LEFT half of screen only (Available Loot block),
        then OCR the number immediately to its right.
        Left half = opponent's loot. Right side = player's own resources (ignored).
        """
        tmpl = self._cache.get(template_name)
        if tmpl is None:
            logger.debug(f"  No template '{template_name}' — skipping {label}")
            return 0

        sh, sw = img.shape[:2]
        th, tw = tmpl.shape[:2]

        # Search only in top-left area — Available Loot is always top-left
        # Left 35%, top 50% of screen
        search_region = img[: sh * 50 // 100, : sw * 35 // 100]
        rh, rw = search_region.shape[:2]

        best_val   = 0.0
        best_loc   = None
        best_scale = 1.0

        for s in [0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2]:
            scaled_w = int(tw * s)
            scaled_h = int(th * s)
            if scaled_w <= 0 or scaled_h <= 0 or scaled_w > rw or scaled_h > rh:
                continue
            scaled = cv2.resize(tmpl, (scaled_w, scaled_h))
            result = cv2.matchTemplate(search_region, scaled, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(result)
            if max_val > best_val:
                best_val   = max_val
                best_loc   = max_loc
                best_scale = s

        if best_val < 0.25 or best_loc is None:
            logger.debug(f"  Icon '{template_name}' not found in left 30% (best={best_val:.2f})")
            return 0

        iw = int(tw * best_scale)
        ih = int(th * best_scale)
        ix, iy = best_loc

        logger.debug(f"  Icon '{template_name}' found at ({ix},{iy}) score={best_val:.2f}")

        # Number is immediately to the right of the icon, same row
        nx1 = ix + iw
        ny1 = iy
        nx2 = min(sw * 35 // 100, nx1 + iw * 5)
        ny2 = iy + ih

        if nx2 <= nx1 or ny2 <= ny1:
            return 0

        return self._ocr_region(img, nx1, ny1, nx2, ny2, label)

    def _ocr_region(self, img: np.ndarray,
                    x1: int, y1: int, x2: int, y2: int, label: str) -> int:
        roi = img[y1:y2, x1:x2]
        if roi.size == 0:
            return 0
        try:
            h, w = roi.shape[:2]
            big  = cv2.resize(roi, (w * 4, h * 4), interpolation=cv2.INTER_CUBIC)
            gray = cv2.cvtColor(big, cv2.COLOR_BGR2GRAY)

            # Multiple thresholds — pick the result with most digits (longest number)
            best_value = 0
            best_digits = ""
            for thr in [150, 170, 180, 200]:
                _, thresh = cv2.threshold(gray, thr, 255, cv2.THRESH_BINARY)
                pil_img = Image.fromarray(thresh)
                raw = pytesseract.image_to_string(
                    pil_img, config="--psm 7 -c tessedit_char_whitelist=0123456789,"
                )
                digits = re.sub(r"[^0-9]", "", raw)
                if len(digits) > len(best_digits):
                    best_digits = digits
                    best_value  = int(digits)
                    logger.debug(f"  OCR {label} thr={thr}: '{raw.strip()}' → {best_value} (new best)")
                else:
                    logger.debug(f"  OCR {label} thr={thr}: '{raw.strip()}' → {int(digits) if digits else 0}")

            logger.debug(f"  OCR {label} final → {best_value}")
            return best_value
        except Exception as e:
            logger.debug(f"  OCR {label} error: {e}")
            return 0

    # Backward compat
    def read_loot_values(self, screenshot_path, gold_region=None,
                         elixir_region=None, dark_elixir_region=None):
        return self.read_loot(screenshot_path)
