"""
CoCBot — core farming engine.

Cycle (প্রতিটা step confirm হলে তবেই পরের step):
  1. Home screen এ attack_icon দেখা যাচ্ছে — tap করো
  2. find_match_btn দেখা যাচ্ছে — tap করো
  3. attack_btn (opponent screen) দেখা যাচ্ছে — loot check করো
       → loot match → attack_btn tap করো → deploy screen এ confirm হও
       → loot no match → next_btn tap করো → নতুন opponent load হওয়ার confirm
  4. Deploy screen confirm হলে — সব troop deploy করো
  5. Return Home button দেখা গেলে — tap করো → home screen confirm
  6. Home screen confirm হলে — আবার cycle 1 থেকে শুরু
"""

import time
import threading
from loguru import logger

from adb_controller import ADBController
from vision import TemplateMatcher, OCRReader
from troop_detector import SmartTroopDeployer


# Loot OCR regions for 1920×1080
# Gold number:   right of gold icon,   y=143-185, x=65-280
# Elixir number: right of elixir icon, y=193-235, x=65-280
# Dark number:   right of dark icon,   y=243-285, x=65-280
GOLD_REGION        = (55, 143, 285, 185)
ELIXIR_REGION      = (55, 195, 285, 242)
DARK_ELIXIR_REGION = (55, 245, 285, 292)

# Template confidence levels (high→low, tries each until found)
_CONF_LEVELS = [0.70, 0.60, 0.50, 0.40, 0.35, 0.30]

# Return Home button — higher confidence to avoid false positives
_RETURN_HOME_CONF = 0.60

# Battle check interval
BATTLE_CHECK_INTERVAL = 7  # seconds


class CoCBot:
    def __init__(self, adb: ADBController, vision: TemplateMatcher,
                 config: dict, status_callback=None):
        self.adb    = adb
        self.vision = vision
        self.config = config
        self._cb    = status_callback

        self.running     = False
        self._stop_event = threading.Event()
        self._screen     = "screenshot.png"

        emu = config.get("emulator", {})
        self.width  = emu.get("resolution_width",  1280)
        self.height = emu.get("resolution_height",  720)

        b = config.get("bot", {})
        self.max_next = b.get("max_next_attempts", 50)

        self.ocr = OCRReader()
        self._last_ocr = (0, 0, 0)

        self.stats = {"cycles": 0, "attacks": 0, "skipped": 0,
                      "gold": 0, "elixir": 0, "dark_elixir": 0}

        self._load_loot_config()
        logger.info("CoCBot initialised")

    # ── Properties ──────────────────────────────────────────────────────────

    @property
    def should_stop(self) -> bool:
        return self._stop_event.is_set()

    # ── Config ───────────────────────────────────────────────────────────────

    def _load_loot_config(self):
        loot = self.config.get("loot", {})
        self._gold_thr   = loot.get("gold_thresholds",        [0])
        self._elixir_thr = loot.get("elixir_thresholds",      [0])
        self._dark_thr   = loot.get("dark_elixir_thresholds", [0])
        self._gold_pri   = loot.get("gold_priority",          False)
        self._elixir_pri = loot.get("elixir_priority",        False)
        self._dark_pri   = loot.get("dark_elixir_priority",   False)

    def update_loot_config(self, loot_cfg: dict):
        self.config["loot"] = loot_cfg
        self._load_loot_config()
        logger.info(f"Loot config updated: G={self._gold_thr} "
                    f"E={self._elixir_thr} DE={self._dark_thr} "
                    f"pri=G{self._gold_pri}/E{self._elixir_pri}/D{self._dark_pri}")

    # ── Low-level helpers ────────────────────────────────────────────────────

    def _log(self, msg: str, level: str = "info"):
        getattr(logger, level)(msg)
        if self._cb:
            self._cb(msg, level)

    def _sleep(self, seconds: float):
        """Sleep that wakes immediately when stop is requested."""
        self._stop_event.wait(timeout=seconds)

    def _screenshot(self) -> bool:
        if self.should_stop:
            return False
        ok = self.adb.screenshot(self._screen)
        if not ok:
            logger.warning("Screenshot failed")
        return ok

    def _find_button(self, template: str,
                     conf_levels=None,
                     region: tuple = None) -> tuple[int, int] | tuple[None, None]:
        """
        Take screenshot, find template.
        region=(x1,y1,x2,y2) to restrict search area.
        Returns (x, y) if found, (None, None) if not.
        """
        if self.should_stop:
            return None, None
        levels = conf_levels or _CONF_LEVELS
        if not self._screenshot():
            return None, None
        for conf in levels:
            x, y, score = self.vision.find(self._screen, template, conf, region=region)
            if x is not None:
                logger.info(f"  Found '{template}' at ({x},{y}) score={score:.2f}")
                return x, y
        logger.debug(f"  '{template}' not found")
        return None, None

    def _attack_btn_region(self) -> tuple:
        """attack_btn is always in the bottom 40% of screen."""
        return (0, self.height * 60 // 100, self.width, self.height)

    def _wait_until_visible(self, template: str,
                            timeout: int = 20,
                            conf: float = 0.35,
                            interval: float = 1.0,
                            region: tuple = None) -> bool:
        deadline = time.time() + timeout
        while not self.should_stop and time.time() < deadline:
            if self._screenshot():
                x, y, _ = self.vision.find(self._screen, template, conf, region=region)
                if x is not None:
                    logger.info(f"  Confirmed: '{template}' visible")
                    return True
            self._sleep(interval)
        if not self.should_stop:
            logger.warning(f"  Timeout ({timeout}s) waiting for '{template}'")
        return False

    def _tap(self, x: int, y: int):
        self.adb.tap(x, y)

    # ── Screen wait helpers ──────────────────────────────────────────────────


    def _wait_until_gone(self, template: str,
                         timeout: int = 30,
                         conf: float = 0.35,
                         interval: float = 1.0) -> bool:
        """Wait until a template disappears from screen."""
        deadline = time.time() + timeout
        while not self.should_stop and time.time() < deadline:
            if self._screenshot():
                x, _, _ = self.vision.find(self._screen, template, conf)
                if x is None:
                    return True
            self._sleep(interval)
        return False

    # ── Loot check ───────────────────────────────────────────────────────────

    def _read_loot(self) -> tuple[int, int, int]:
        if not self._screenshot():
            return 0, 0, 0
        g, e, d = self.ocr.read_loot(
            self._screen, GOLD_REGION, ELIXIR_REGION, DARK_ELIXIR_REGION
        )
        self._log(f"  OCR loot → Gold:{g}  Elixir:{e}  Dark:{d}")
        return g, e, d

    def _loot_matches(self, gold: int, elixir: int, dark: int) -> tuple[bool, str]:
        """
        Priority mode (tick ✓):
            Only ticked resources checked. ALL ticked must be >= threshold.

        Normal mode (no tick):
            ALL resources with threshold > 0 must be >= threshold (AND).
        """
        all_res = {
            "Gold":   (gold,   self._gold_thr,   self._gold_pri),
            "Elixir": (elixir, self._elixir_thr, self._elixir_pri),
            "Dark":   (dark,   self._dark_thr,   self._dark_pri),
        }

        # Resources that have a threshold set (> 0)
        active = {k: v for k, v in all_res.items() if any(t > 0 for t in v[1])}

        if not active:
            return True, "No thresholds set — attack any base"

        any_pri = any(v[2] for v in active.values())

        if any_pri:
            to_check = {k: v for k, v in active.items() if v[2]}
            mode = "PRIORITY"
        else:
            to_check = active
            mode = "ALL"

        results = []
        for name, (value, thresholds, _) in to_check.items():
            thr = thresholds[0]
            met = value >= thr
            results.append((name, value, thr, met))
            self._log(f"  [{mode}] {name}: {value} >= {thr}? {'YES' if met else 'NO'}")

        attack = all(r[3] for r in results)
        passed = [f"{n}({v}>={t})" for n, v, t, ok in results if ok]
        failed = [f"{n}({v}<{t})"  for n, v, t, ok in results if not ok]
        reason = (f"[{mode}] ATTACK: " + ", ".join(passed)) if attack \
            else (f"[{mode}] SKIP: " + ", ".join(failed))

        return attack, reason

    # ════════════════════════════════════════════════════════════════════════
    #  STEP 1: Tap Attack icon — confirm Find Match screen appears
    # ════════════════════════════════════════════════════════════════════════

    def _step1_tap_attack_icon(self) -> bool:
        self._log("Step 1: Looking for Attack icon on home screen…")

        # Must see attack_icon before tapping
        if not self._wait_until_visible("attack_icon", timeout=15):
            self._log("  Attack icon not found on home screen", "error")
            return False

        x, y = self._find_button("attack_icon")
        if x is None:
            return False
        self._tap(x, y)
        self._log("  Attack icon tapped")

        # Confirm: find_match_btn must appear
        self._log("  Waiting for Find Match button…")
        if not self._wait_until_visible("find_match_btn", timeout=15):
            self._log("  Find Match screen did not load", "error")
            return False

        self._log("  Step 1 complete — Find Match screen loaded")
        return True

    # ════════════════════════════════════════════════════════════════════════
    #  STEP 2: Tap Find Match — confirm opponent preview screen
    # ════════════════════════════════════════════════════════════════════════

    def _step2_tap_find_match(self) -> bool:
        self._log("Step 2: Tapping Find a Match…")

        x, y = self._find_button("find_match_btn")
        if x is None:
            self._log("  Find Match button not found", "error")
            return False
        self._tap(x, y)
        self._log("  Find Match tapped — waiting for Attack! button…")

        # Attack! button পুরো screen এ খুঁজবো (region restriction নেই)
        if not self._wait_until_visible("attack_btn", timeout=40, conf=0.40):
            self._log("  Attack button did not appear", "error")
            return False

        ax, ay = self._find_button("attack_btn", [0.50, 0.45, 0.40, 0.35])
        if ax is None:
            self._log("  Attack button not found to click", "error")
            return False
        self._tap(ax, ay)
        self._log("  Attack! clicked — waiting 2s for enemy village to load…")
        self._sleep(2.0)
        self._log("  Step 2 complete — enemy village loaded")
        return True

    # ════════════════════════════════════════════════════════════════════════
    #  STEP 3: OCR loot → match → deploy  /  no match → Next → repeat
    # ════════════════════════════════════════════════════════════════════════

    def _step3_loot_check(self) -> bool:
        self._log(f"Step 3: Loot check (max {self.max_next} attempts)…")
        self._last_ocr = (0, 0, 0)

        for attempt in range(self.max_next + 1):
            if self.should_stop:
                return False

            self._log(f"  Attempt {attempt + 1}/{self.max_next + 1}")

            # ── OCR read ───────────────────────────────────────────────────
            # _tap_next_and_load এ already OCR করা থাকলে সেটা use করো
            if self._last_ocr[0] > 0 or self._last_ocr[1] > 0 or self._last_ocr[2] > 0:
                gold, elixir, dark = self._last_ocr
                self._last_ocr = (0, 0, 0)
                self._log(f"  Using cached OCR — G:{gold} E:{elixir} D:{dark}")
            else:
                # নতুন করে OCR read করো — 3 বার retry
                gold, elixir, dark = 0, 0, 0
                for ocr_try in range(3):
                    g, e, d = self._read_loot()
                    if g > 0 or e > 0 or d > 0:
                        gold, elixir, dark = g, e, d
                        break
                    self._log(f"  OCR zero (try {ocr_try+1}/3) — retrying 1.5s…", "warning")
                    self._sleep(1.5)

            # OCR সম্পূর্ণ fail → Next চাপো
            if gold == 0 and elixir == 0 and dark == 0:
                self._log("  OCR failed — skipping base", "warning")
                if attempt >= self.max_next:
                    # সব attempt শেষ — End Battle click করে home এ ফিরো
                    self._log("  OCR failed 6 times — clicking End Battle to go home", "warning")
                    self._click_end_battle()
                    return False
                if not self._tap_next_and_load():
                    self._cancel_search()
                    return False
                continue

            # ── Loot check ─────────────────────────────────────────────────
            ok, reason = self._loot_matches(gold, elixir, dark)

            if ok:
                self._log(f"  Loot matched! {reason}", "success")
                self.stats["gold"]        += gold
                self.stats["elixir"]      += elixir
                self.stats["dark_elixir"] += dark
                self._log("  Step 3 complete — starting deploy")
                return True

            else:
                self._log(f"  No match — {reason}", "warning")
                self.stats["skipped"] += 1

                if attempt >= self.max_next:
                    break

                if not self._tap_next_and_load():
                    self._cancel_search()
                    return False

        self._log(f"  No match after {self.max_next + 1} attempts", "warning")
        self._cancel_search()
        return False

    def _tap_next_and_load(self) -> bool:
        """
        Next click করলে সরাসরি নতুন village load হয়।
        Attack! button আসে না — শুধু 4s wait করো।
        """
        x, y = self._find_button("next_btn", [0.70, 0.60, 0.50, 0.40, 0.30])
        if x is None:
            self._log("  Next button not found", "warning")
            return False
        self._tap(x, y)
        self._log("  Next tapped — waiting 4s for new village to load…")
        self._sleep(4.0)
        self._last_ocr = (0, 0, 0)
        return True

    def _click_end_battle(self):
        """End Battle button click করে home village এ ফিরে যাও।"""
        if self.should_stop:
            return
        self._log("  Clicking End Battle button…", "warning")
        x, y = self._find_button("end_battle_btn", [0.70, 0.60, 0.50, 0.40, 0.35])
        if x is not None:
            self._tap(x, y)
            self._sleep(1.0)
            # Confirm popup আসতে পারে — আবার End Battle বা OK খুঁজো
            for tmpl in ["end_battle_btn", "return_home_btn", "home_icon"]:
                cx, cy = self._find_button(tmpl, [0.60, 0.50, 0.40, 0.35])
                if cx is not None:
                    self._tap(cx, cy)
                    break
            self._wait_until_visible("attack_icon", timeout=20)
            self._log("  Home screen reached after End Battle")
        else:
            self._log("  End Battle button not found — trying cancel", "warning")
            self._cancel_search()

    def _cancel_search(self):
        """Cancel opponent search and return to home screen."""
        if self.should_stop:
            return
        self._log("  Cancelling — looking for return/home button…", "warning")

        # Try the cancel / return home button on opponent screen
        for tmpl in ["return_home_btn", "home_icon"]:
            x, y = self._find_button(tmpl, [0.60, 0.50, 0.40, 0.30])
            if x is not None:
                self._tap(x, y)
                self._log(f"  Tapped '{tmpl}' to go home")
                self._wait_until_visible("attack_icon", timeout=20)
                return

        self._log("  Could not find cancel button", "warning")

    # ════════════════════════════════════════════════════════════════════════
    #  STEP 4: Deploy all troops
    # ════════════════════════════════════════════════════════════════════════

    def _step4_deploy_troops(self) -> bool:
        self._log("Step 4: Starting troop deployment…")

        deployer = SmartTroopDeployer(
            adb=self.adb,
            screenshot_fn=self.adb.screenshot_np,
            config=self.config,
            status_cb=self._cb,
            stop_event=self._stop_event,
        )

        result = deployer.deploy()

        if result:
            self._log("  Step 4 complete — all troops deployed")
        else:
            self._log("  Step 4 — no troops deployed (already empty?)", "warning")

        return result

    # ════════════════════════════════════════════════════════════════════════
    #  STEP 5: Wait for battle end — Return Home every 7s
    # ════════════════════════════════════════════════════════════════════════

    def _step5_wait_battle_end(self) -> bool:
        """
        Check immediately & every 7 seconds for Return Home button.
        Click it immediately when found.
        Max wait: 3 minutes (180s).
        """
        self._log(f"Step 5: Battle in progress — "
                  f"checking Return Home every {BATTLE_CHECK_INTERVAL}s (max 180s)…")
        start = time.time()
        check_num = 0
        MAX_WAIT = 180  # 3 minutes

        while not self.should_stop:
            elapsed = int(time.time() - start)

            # Check if 3 minutes passed
            if elapsed >= MAX_WAIT:
                self._log(f"  Reached 3 minute limit — no Return Home found")
                return False

            check_num += 1
            self._log(f"  Check #{check_num} at {elapsed}s — looking for Return Home…")

            if not self._screenshot():
                self._sleep(BATTLE_CHECK_INTERVAL)
                continue

            # Check ONLY for Return Home button during battle
            x, y, score = self.vision.find(
                self._screen, "return_home_btn", _RETURN_HOME_CONF
            )
            if x is not None:
                self._log(f"  Return Home found at {elapsed}s "
                          f"(score={score:.2f}) — tapping!")
                return self._step5b_click_return_home(x, y)

            # Not found yet — sleep before next check
            self._sleep(BATTLE_CHECK_INTERVAL)

        return False

    def _step5b_click_return_home(self, x: int, y: int) -> bool:
        """Tap Return Home and wait until home screen confirmed."""
        for i in range(3):
            self._tap(x + i - 1, y + i - 1)
            time.sleep(0.05)

        self._log("  Waiting for home screen to load…")

        # Keep checking until attack_icon appears (home screen confirmed)
        if self._wait_until_visible("attack_icon", timeout=30, conf=0.35):
            self._log("  Step 5 complete — home screen confirmed")
            return True

        self._log("  Home screen not confirmed — continuing anyway", "warning")
        return True

    # ════════════════════════════════════════════════════════════════════════
    #  Main cycle
    # ════════════════════════════════════════════════════════════════════════

    def execute_cycle(self) -> bool:
        if self.should_stop:
            return False

        self.stats["cycles"] += 1
        self._load_loot_config()
        self._log(f"═══ Cycle {self.stats['cycles']} start ═══")

        # Step 1: Tap attack icon → Find Match screen
        if not self._step1_tap_attack_icon():
            return False
        if self.should_stop:
            return False

        # Step 2: Tap Find Match → opponent preview screen
        if not self._step2_tap_find_match():
            return False
        if self.should_stop:
            return False

        # Step 3: Loot check loop → tap Attack → deploy screen confirmed
        if not self._step3_loot_check():
            if self.should_stop:
                return False
            # _step3 already returned home on failure — restart cycle
            return False
        if self.should_stop:
            return False

        # Step 4: Deploy all troops
        self._step4_deploy_troops()
        # Even if deploy fails, battle has started — must wait for end
        self.stats["attacks"] += 1
        if self.should_stop:
            return False

        # Step 5: Wait for Return Home, click it, confirm home screen
        battle_ok = self._step5_wait_battle_end()
        if not battle_ok and not self.should_stop:
            self._log("  Battle end not confirmed — restarting cycle", "warning")

        if self.should_stop:
            return False

        self._log(f"═══ Cycle {self.stats['cycles']} complete ═══")
        return True

    # ── Public API ────────────────────────────────────────────────────────────

    def run(self):
        self.running = True
        self._stop_event.clear()
        self._log("Bot starting…")

        if not self.adb.connect_device():
            self._log("ADB connection failed", "error")
            self.running = False
            return

        if not self.adb.verify_device_connected():
            self._log("Device not ready", "error")
            self.running = False
            return

        self._log("ADB connected — starting farm loop")

        while self.running and not self.should_stop:
            try:
                ok = self.execute_cycle()
                if not ok:
                    if self.should_stop:
                        break
                    self._log("Cycle failed — retrying in 5s…", "warning")
                    self._stop_event.wait(timeout=5)
            except Exception as e:
                if self.should_stop:
                    break
                logger.error(f"Cycle exception: {e}", exc_info=True)
                self._log(f"Unexpected error: {e}", "error")
                self._stop_event.wait(timeout=5)

        self.running = False
        self._log("Bot stopped")

    def stop(self):
        """Immediately wake all sleeping/waiting code and halt."""
        self._stop_event.set()
        self.running = False

    def get_stats(self) -> dict:
        return dict(self.stats)
