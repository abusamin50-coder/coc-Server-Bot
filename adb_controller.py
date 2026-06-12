"""ADB Controller — handles all Android Debug Bridge communication."""

import subprocess
import os
import time
from pathlib import Path

import cv2
import numpy as np
from loguru import logger


class ADBController:
    def __init__(self, device_id: str = "127.0.0.1:5555", adb_port: int = 5555, adb_path: str = None):
        self.device_id = device_id
        self.adb_port = adb_port
        self.adb_exe = self._resolve_adb(adb_path)
        self._check_adb_works()

    # ─────────────────────────── ADB discovery ────────────────────────────────

    def _resolve_adb(self, explicit: str) -> str:
        candidates = []

        if explicit:
            candidates += [
                Path(explicit),
                Path(str(explicit).replace("/", "\\")),
                Path(__file__).parent / explicit,
            ]

        candidates += [
            Path("C:/Program Files/LDPlayer/LDPlayer4.0/adb.exe"),
            Path("C:/Program Files/LDPlayer/LDPlayer9/adb.exe"),
            Path("C:/Program Files/LDPlayer/adb.exe"),
            Path.home() / "AppData/Local/LDPlayer/adb.exe",
            Path.home() / "AppData/Local/Android/Sdk/platform-tools/adb.exe",
            Path("C:/Android/Sdk/platform-tools/adb.exe"),
        ]

        for p in candidates:
            try:
                if Path(p).exists():
                    logger.info(f"ADB found: {p}")
                    return str(Path(p).resolve())
            except Exception:
                pass

        # Try PATH
        try:
            r = subprocess.run(["where", "adb"], capture_output=True, timeout=5, text=True)
            if r.returncode == 0:
                path = r.stdout.strip().split("\n")[0].strip()
                logger.info(f"ADB found in PATH: {path}")
                return path
        except Exception:
            pass

        logger.warning("ADB not found — using 'adb' and hoping it's on PATH")
        return "adb"

    def _check_adb_works(self):
        try:
            r = subprocess.run([self.adb_exe, "version"], capture_output=True, timeout=5, text=True)
            if r.returncode == 0:
                logger.info(f"ADB ready: {r.stdout.splitlines()[0]}")
            else:
                logger.error("ADB check failed — verify adb_path in config.yaml")
        except FileNotFoundError:
            logger.error(f"ADB executable not found at: {self.adb_exe}")
        except Exception as e:
            logger.error(f"ADB check error: {e}")

    # ─────────────────────────── Connection ───────────────────────────────────

    def connect_device(self, retries: int = 5, delay: float = 2.0) -> bool:
        for attempt in range(1, retries + 1):
            try:
                if self._is_connected():
                    logger.info(f"Device {self.device_id} already connected")
                    return True

                subprocess.run(
                    [self.adb_exe, "connect", f"127.0.0.1:{self.adb_port}"],
                    capture_output=True, timeout=10,
                )
                time.sleep(2)

                if self._is_connected():
                    logger.info(f"Connected to {self.device_id}")
                    return True

                logger.warning(f"[{attempt}/{retries}] Not connected yet, retrying…")
                time.sleep(delay)

            except Exception as e:
                logger.error(f"[{attempt}/{retries}] Connect error: {e}")
                time.sleep(delay)

        logger.error("Could not connect to device. Make sure LDPlayer is running.")
        return False

    def verify_device_connected(self) -> bool:
        return self._is_connected()

    def _is_connected(self) -> bool:
        for dev_id, status in self._device_list():
            if dev_id == self.device_id and status == "device":
                return True
        return False

    def _device_list(self) -> list:
        try:
            r = subprocess.run([self.adb_exe, "devices"], capture_output=True, timeout=5, text=True)
            devices = []
            for line in r.stdout.splitlines()[1:]:
                if "\t" in line:
                    dev, st = line.split("\t")
                    devices.append((dev.strip(), st.strip()))
            return devices
        except Exception:
            return []

    def disconnect(self):
        try:
            subprocess.run([self.adb_exe, "disconnect"], capture_output=True, timeout=5)
            logger.info("ADB disconnected")
        except Exception:
            pass

    # ─────────────────────────── Input ────────────────────────────────────────

    def tap(self, x: int, y: int) -> bool:
        try:
            r = subprocess.run(
                [self.adb_exe, "-s", self.device_id, "shell", "input", "tap", str(x), str(y)],
                capture_output=True, timeout=5, text=True,
            )
            return r.returncode == 0
        except Exception as e:
            logger.error(f"Tap ({x},{y}) error: {e}")
            return False

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300) -> bool:
        try:
            r = subprocess.run(
                [self.adb_exe, "-s", self.device_id, "shell", "input", "swipe",
                 str(x1), str(y1), str(x2), str(y2), str(duration_ms)],
                capture_output=True, timeout=5, text=True,
            )
            return r.returncode == 0
        except Exception as e:
            logger.error(f"Swipe error: {e}")
            return False

    # ─────────────────────────── Screenshots ──────────────────────────────────

    def screenshot(self, save_path: str = "screenshot.png") -> bool:
        """Capture screenshot to disk. Returns True on success."""
        try:
            device_tmp = "/data/local/tmp/coc_snap.png"

            r = subprocess.run(
                [self.adb_exe, "-s", self.device_id, "shell", f"screencap -p {device_tmp}"],
                capture_output=True, timeout=15,
            )

            if r.returncode == 0:
                pull = subprocess.run(
                    [self.adb_exe, "-s", self.device_id, "pull", device_tmp, save_path],
                    capture_output=True, timeout=15,
                )
                if pull.returncode != 0:
                    return False
            else:
                # Fallback: exec-out
                r2 = subprocess.run(
                    [self.adb_exe, "-s", self.device_id, "exec-out", "screencap", "-p"],
                    capture_output=True, timeout=15,
                )
                if r2.returncode != 0 or len(r2.stdout) < 5000:
                    return False
                with open(save_path, "wb") as f:
                    f.write(r2.stdout)

            if not os.path.exists(save_path) or os.path.getsize(save_path) < 5000:
                return False

            # Verify it's a valid image
            img = cv2.imread(save_path)
            if img is None:
                return False

            logger.debug(f"Screenshot saved: {save_path} ({img.shape[1]}x{img.shape[0]})")
            return True

        except Exception as e:
            logger.error(f"Screenshot error: {e}")
            return False

    def screenshot_np(self) -> np.ndarray:
        """Capture screenshot directly into memory as numpy array."""
        try:
            r = subprocess.run(
                [self.adb_exe, "-s", self.device_id, "exec-out", "screencap", "-p"],
                capture_output=True, timeout=15,
            )
            if r.returncode != 0 or len(r.stdout) < 5000:
                return None

            buf = np.frombuffer(r.stdout, dtype=np.uint8)
            img = cv2.imdecode(buf, cv2.IMREAD_COLOR)
            if img is None:
                return None

            logger.debug(f"Screenshot in memory: {img.shape[1]}x{img.shape[0]}")
            return img

        except Exception as e:
            logger.error(f"screenshot_np error: {e}")
            return None
