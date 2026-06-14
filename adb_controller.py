"""ADB Controller — handles all Android Debug Bridge communication."""

import subprocess
import os
import time
import psutil
from pathlib import Path

import cv2
import numpy as np
from loguru import logger


class ADBController:
    def __init__(self, device_id: str = "127.0.0.1:5555", adb_port: int = 5555, adb_path: str | None = None):
        self.device_id = device_id
        self.adb_port = adb_port
        self.adb_exe = self._resolve_adb(adb_path)
        self._check_adb_works()

    # ─────────────────────────── ADB discovery ────────────────────────────────

    def _resolve_adb(self, explicit: str | None) -> str:
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

    # ─────────────────────────── Terminal Cleanup ──────────────────────────────

    def kill_all_terminals(self) -> bool:
        """Kill all cmd.exe, powershell, and adb processes. Returns True if successful."""
        try:
            processes_to_kill = ["cmd.exe", "powershell.exe", "adb.exe", "LDPlayer.exe"]
            killed_count = 0
            
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    if proc.info['name'].lower() in [p.lower() for p in processes_to_kill]:
                        proc.terminate()
                        killed_count += 1
                        logger.debug(f"Terminated: {proc.info['name']} (PID: {proc.info['pid']})")
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            
            time.sleep(1)  # Allow processes to terminate
            
            if killed_count > 0:
                logger.info(f"Killed {killed_count} terminal/ADB processes")
            return True
        except Exception as e:
            logger.warning(f"Kill terminals error: {e}")
            return True  # Continue anyway

    def find_ldplayer_adb(self) -> tuple[str, int] | None | None:
        """Detect LDPlayer emulator ADB host:port. Returns (host, port) or None."""
        common_ports = [5555, 5554, 5037, 16384, 16416]
        common_ips = ["127.0.0.1", "localhost", "192.168.1.1"]
        
        for ip in common_ips:
            for port in common_ports:
                try:
                    r = subprocess.run(
                        [self.adb_exe, "connect", f"{ip}:{port}"],
                        capture_output=True, timeout=3, text=True
                    )
                    time.sleep(0.5)
                    
                    # Check if connected
                    r2 = subprocess.run(
                        [self.adb_exe, "devices"], capture_output=True, timeout=3, text=True
                    )
                    if f"{ip}:{port}" in r2.stdout and "device" in r2.stdout:
                        logger.info(f"Found LDPlayer at {ip}:{port}")
                        return (ip, port)
                except Exception:
                    pass
        
        return None

    def auto_connect_ldplayer(self) -> bool:
        """Kill terminals, find LDPlayer ADB, and connect. Returns True if successful."""
        try:
            logger.info("Starting auto-connect to LDPlayer...")
            
            # Step 1: Kill existing terminals
            logger.info("Cleaning up existing processes...")
            self.kill_all_terminals()
            time.sleep(2)
            
            # Step 2: Start ADB server
            logger.info("Starting ADB server...")
            try:
                subprocess.run([self.adb_exe, "start-server"], capture_output=True, timeout=5)
                time.sleep(1)
            except Exception as e:
                logger.warning(f"ADB start-server: {e}")
            
            # Step 3: Try to find LDPlayer
            logger.info("Scanning for LDPlayer emulator...")
            result = self.find_ldplayer_adb()
            
            if result:
                host, port = result
                self.device_id = f"{host}:{port}"
                self.adb_port = port
                logger.info(f"Auto-connected to {self.device_id}")
                return True
            else:
                logger.error("Could not find LDPlayer ADB. Make sure LDPlayer is running.")
                return False
                
        except Exception as e:
            logger.error(f"Auto-connect error: {e}")
            return False

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

    def screenshot_np(self) -> np.ndarray | None:
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
