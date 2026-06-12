"""
Professional GUI for CoCBot.
Tabs: Control | Loot | Troops | Stats
"""

import os
import shutil
import threading
import time
from pathlib import Path
from queue import Queue, Empty
from tkinter import filedialog

import customtkinter as ctk
from PIL import Image
import yaml
from loguru import logger

from bot_engine import CoCBot
from adb_controller import ADBController
from vision import TemplateMatcher
from config import load_config, save_config

TROOP_IMAGES_DIR = "troop_images"
CONFIG_FILE      = "config.yaml"

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


# ══════════════════════════════════════════════════════════════
#  Main GUI window
# ══════════════════════════════════════════════════════════════

class BotGUI:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("CoC Auto Farming Bot")
        self.root.geometry("820x640")
        self.root.resizable(True, True)

        # State
        self.config   = load_config(CONFIG_FILE)
        self.adb      = None
        self.vision   = None
        self.engine   = None
        self.bot_thread = None
        self.running  = False

        self._log_lines: list[str] = []
        self._max_log = 30
        self._status_q: Queue = Queue()

        self.troop_rows: list[dict] = []

        Path(TROOP_IMAGES_DIR).mkdir(exist_ok=True)
        Path("templates").mkdir(exist_ok=True)
        Path("logs").mkdir(exist_ok=True)

        self._build()
        self._poll()

    # ── Build UI ─────────────────────────────────────────────────────────────

    def _build(self):
        # Title bar
        ctk.CTkLabel(
            self.root,
            text="CoC Auto Farming Bot",
            font=("Arial", 22, "bold"),
            text_color="#f59e0b",
        ).pack(pady=(12, 4))

        # Tabs
        self.tabs = ctk.CTkTabview(self.root, height=540)
        self.tabs.pack(fill="both", expand=True, padx=16, pady=6)

        self._build_control_tab(self.tabs.add("Control"))
        self._build_loot_tab(self.tabs.add("Loot"))
        self._build_troops_tab(self.tabs.add("Troops"))
        self._build_stats_tab(self.tabs.add("Stats"))

    # ── Control tab ──────────────────────────────────────────────────────────

    def _build_control_tab(self, tab):
        top = ctk.CTkFrame(tab, fg_color="#1e293b", corner_radius=10)
        top.pack(fill="x", padx=10, pady=10)

        self.start_btn = ctk.CTkButton(
            top, text="START BOT", font=("Arial", 15, "bold"),
            height=52, width=180, fg_color="#22c55e", hover_color="#16a34a",
            command=self._toggle_bot,
        )
        self.start_btn.pack(side="left", padx=14, pady=12)

        right = ctk.CTkFrame(top, fg_color="transparent")
        right.pack(side="left", fill="both", expand=True, padx=10)

        self.status_dot = ctk.CTkLabel(right, text="● Idle", font=("Arial", 12),
                                       text_color="#94a3b8")
        self.status_dot.pack(anchor="w", pady=(8, 2))

        self.status_msg = ctk.CTkLabel(right, text="Press START to begin farming",
                                       font=("Arial", 10), text_color="#64748b",
                                       wraplength=500, justify="left")
        self.status_msg.pack(anchor="w")

        # Log box
        log_frame = ctk.CTkFrame(tab, fg_color="#0f172a", corner_radius=8)
        log_frame.pack(fill="both", expand=True, padx=10, pady=(4, 10))

        ctk.CTkLabel(log_frame, text="Activity Log", font=("Arial", 10, "bold"),
                     text_color="#475569").pack(anchor="w", padx=10, pady=(6, 2))

        self.log_box = ctk.CTkTextbox(
            log_frame, font=("Courier New", 9),
            text_color="#94a3b8", fg_color="#0f172a",
        )
        self.log_box.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.log_box.configure(state="disabled")

        self._log("Bot ready. Configure Loot & Troops then press START.")

    # ── Loot tab ─────────────────────────────────────────────────────────────

    def _build_loot_tab(self, tab):
        card = ctk.CTkFrame(tab, fg_color="#1e293b", corner_radius=10)
        card.pack(fill="x", padx=10, pady=12)

        ctk.CTkLabel(card, text="Loot Thresholds", font=("Arial", 13, "bold")).pack(pady=10)
        ctk.CTkLabel(
            card,
            text="No tick = ALL active resources must match (AND)\n"
                 "Tick ✓ = ONLY ticked resources checked (priority mode)\n"
                 "Multiple values separated by comma:  1000000,2000000",
            font=("Arial", 9), text_color="#64748b",
        ).pack(pady=(0, 8))

        loot = self.config.get("loot", {})

        def _row(parent, label, color, pri_key, thr_key, default_thr):
            row = ctk.CTkFrame(parent, fg_color="transparent")
            row.pack(fill="x", padx=14, pady=6)
            var = ctk.BooleanVar(value=loot.get(pri_key, False))
            ctk.CTkCheckBox(row, text="", variable=var, width=26,
                            checkbox_width=20, checkbox_height=20,
                            fg_color=color, hover_color=color).pack(side="left", padx=(0, 6))
            ctk.CTkLabel(row, text=label, width=100, anchor="w").pack(side="left")
            entry = ctk.CTkEntry(row, width=220)
            entry.pack(side="left", padx=6)
            entry.insert(0, ",".join(str(t) for t in loot.get(thr_key, [default_thr])))
            return var, entry

        self._gold_pri_var,  self._gold_entry  = _row(card, "Gold:",       "#f59e0b", "gold_priority",       "gold_thresholds",       5000)
        self._elixir_pri_var,self._elixir_entry = _row(card, "Elixir:",    "#a855f7", "elixir_priority",     "elixir_thresholds",     6000)
        self._dark_pri_var,  self._dark_entry   = _row(card, "Dark Elixir:","#1d4ed8","dark_elixir_priority","dark_elixir_thresholds",300)

        ctk.CTkButton(
            card, text="Save Loot Settings",
            fg_color="#3b82f6", hover_color="#2563eb",
            command=self._save_loot,
        ).pack(pady=14)

    # ── Troops tab ───────────────────────────────────────────────────────────

    def _build_troops_tab(self, tab):
        # ── Deploy Zone Image row ─────────────────────────────────────────────
        zone_card = ctk.CTkFrame(tab, fg_color="#1e293b", corner_radius=8)
        zone_card.pack(fill="x", padx=10, pady=(10, 4))

        ctk.CTkLabel(
            zone_card,
            text="Deploy Zone Image",
            font=("Arial", 11, "bold"),
        ).pack(anchor="w", padx=12, pady=(8, 2))
        ctk.CTkLabel(
            zone_card,
            text="Upload a cropped image of the area where troops should be deployed.\n"
                 "Bot will find it on screen (same as attack_icon.png) and deploy there.",
            font=("Arial", 9), text_color="#64748b", justify="left",
        ).pack(anchor="w", padx=12)

        zone_row = ctk.CTkFrame(zone_card, fg_color="transparent")
        zone_row.pack(fill="x", padx=10, pady=8)

        # Thumbnail
        self._zone_thumb = ctk.CTkLabel(zone_row, text="No image", width=62, height=62,
                                        font=("Arial", 9), fg_color="#0f172a",
                                        corner_radius=6)
        self._zone_thumb.pack(side="left", padx=6)

        # Path label
        zone_path = self.config.get("deploy_zone_image", "")
        self._zone_path_var = ctk.StringVar(value=zone_path if zone_path else "Not set")
        ctk.CTkLabel(zone_row, textvariable=self._zone_path_var,
                     font=("Arial", 9), text_color="#94a3b8",
                     wraplength=380, justify="left").pack(side="left", padx=8, fill="x", expand=True)

        ctk.CTkButton(
            zone_row, text="Select Image",
            fg_color="#f59e0b", hover_color="#d97706", width=110,
            command=self._pick_deploy_zone_image,
        ).pack(side="right", padx=6)

        # Load existing thumbnail if set
        if zone_path and os.path.exists(zone_path):
            self._set_zone_thumb(zone_path)

        # ── Speed + Add Troop row ─────────────────────────────────────────────
        top = ctk.CTkFrame(tab, fg_color="transparent")
        top.pack(fill="x", padx=10, pady=(6, 4))

        ctk.CTkLabel(top, text="Deploy Speed:").pack(side="left", padx=(4, 4))
        self._speed_var = ctk.StringVar(value="INSTANT (0.02s)")
        ctk.CTkComboBox(
            top,
            values=["INSTANT (0.02s)", "ULTRA FAST (0.05s)", "FAST (0.08s)", "NORMAL (0.12s)"],
            variable=self._speed_var, width=200, state="readonly",
        ).pack(side="left")

        ctk.CTkButton(
            top, text="+ Add Troop", command=self._add_troop,
            fg_color="#10b981", hover_color="#059669", width=120,
        ).pack(side="right", padx=8)

        # Headers
        hdr = ctk.CTkFrame(tab, fg_color="transparent")
        hdr.pack(fill="x", padx=14, pady=(4, 0))
        for label, w in [("", 30), ("Image", 62), ("Troop Name", 180), ("Order", 70), ("", 40)]:
            ctk.CTkLabel(hdr, text=label, width=w, font=("Arial", 9, "bold"),
                         anchor="w").pack(side="left", padx=2)

        self._troop_scroll = ctk.CTkScrollableFrame(tab, height=220)
        self._troop_scroll.pack(fill="both", expand=True, padx=10, pady=4)

        ctk.CTkButton(
            tab, text="Save Troops",
            fg_color="#3b82f6", hover_color="#2563eb",
            command=self._save_troops,
        ).pack(pady=6)

        self._load_existing_troops()

    def _pick_deploy_zone_image(self):
        path = filedialog.askopenfilename(
            title="Select Deploy Zone Image",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp")],
        )
        if not path:
            return
        dest = os.path.join(TROOP_IMAGES_DIR, "deploy_zone_" + Path(path).name)
        if not os.path.exists(dest):
            shutil.copy2(path, dest)
        self.config["deploy_zone_image"] = dest
        self._zone_path_var.set(dest)
        self._set_zone_thumb(dest)
        save_config(self.config, CONFIG_FILE)
        self._log(f"Deploy zone image set: {Path(dest).name}")

    def _set_zone_thumb(self, path: str):
        try:
            pil = Image.open(path).resize((56, 56))
            cimg = ctk.CTkImage(light_image=pil, dark_image=pil, size=(56, 56))
            self._zone_thumb.configure(image=cimg, text="")
            self._zone_thumb.image = cimg
        except Exception:
            pass

    # ── Stats tab ────────────────────────────────────────────────────────────

    def _build_stats_tab(self, tab):
        card = ctk.CTkFrame(tab, fg_color="#1e293b", corner_radius=10)
        card.pack(fill="both", expand=True, padx=10, pady=12)

        ctk.CTkLabel(card, text="Session Statistics", font=("Arial", 13, "bold")).pack(pady=12)

        self._stat_labels = {}
        rows = [
            ("Cycles completed", "cycles"),
            ("Attacks launched",  "attacks"),
            ("Bases skipped",     "skipped"),
            ("Gold collected",    "gold"),
            ("Elixir collected",  "elixir"),
            ("Dark Elixir",       "dark_elixir"),
        ]
        for display, key in rows:
            row = ctk.CTkFrame(card, fg_color="transparent")
            row.pack(fill="x", padx=20, pady=4)
            ctk.CTkLabel(row, text=display + ":", width=180, anchor="w",
                         text_color="#94a3b8").pack(side="left")
            lbl = ctk.CTkLabel(row, text="0", font=("Arial", 12, "bold"),
                               text_color="#f1f5f9")
            lbl.pack(side="left")
            self._stat_labels[key] = lbl

        ctk.CTkButton(
            card, text="Reset Stats", width=130,
            fg_color="#475569", hover_color="#334155",
            command=self._reset_stats,
        ).pack(pady=14)

    # ── Troop rows ────────────────────────────────────────────────────────────

    def _load_existing_troops(self):
        for t in self.config.get("troops", {}).get("custom_troops", []):
            self._create_troop_row(t.get("image", ""), t.get("name", ""))

    def _add_troop(self):
        path = filedialog.askopenfilename(
            title="Select Troop Icon",
            filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp")],
        )
        if not path:
            return
        dest = os.path.join(TROOP_IMAGES_DIR, Path(path).name)
        if not os.path.exists(dest):
            shutil.copy2(path, dest)
        auto_name = Path(path).stem.replace("_", " ").replace("-", " ").title()
        self._create_troop_row(dest, auto_name)
        self._save_troops()  # auto-save immediately after adding

    def _create_troop_row(self, image_path: str, name: str):
        row = ctk.CTkFrame(self._troop_scroll, fg_color="#1e293b", corner_radius=6)
        row.pack(fill="x", pady=3, padx=4)

        row_data = {"frame": row, "name_var": None, "image_path": image_path}

        # ↑↓ move buttons
        move_frame = ctk.CTkFrame(row, fg_color="transparent", width=30)
        move_frame.pack(side="left", padx=(4, 0))
        ctk.CTkButton(move_frame, text="↑", width=26, height=22, font=("Arial", 11),
                      fg_color="#334155", hover_color="#475569",
                      command=lambda rd=row_data: self._move_troop(rd, -1),
                      ).pack(pady=(4, 1))
        ctk.CTkButton(move_frame, text="↓", width=26, height=22, font=("Arial", 11),
                      fg_color="#334155", hover_color="#475569",
                      command=lambda rd=row_data: self._move_troop(rd, +1),
                      ).pack(pady=(1, 4))

        # Thumbnail
        thumb = ctk.CTkLabel(row, text="?", width=56, height=56, font=("Arial", 18))
        thumb.pack(side="left", padx=6, pady=6)
        if image_path and os.path.exists(image_path):
            try:
                pil = Image.open(image_path).resize((50, 50))
                cimg = ctk.CTkImage(light_image=pil, dark_image=pil, size=(50, 50))
                thumb.configure(image=cimg, text="")
                thumb.image = cimg
            except Exception:
                pass

        name_var = ctk.StringVar(value=name)
        row_data["name_var"] = name_var
        ctk.CTkEntry(row, textvariable=name_var, width=180).pack(side="left", padx=6)

        # Order label (shows position number)
        order_lbl = ctk.CTkLabel(row, text="", width=30, font=("Arial", 10),
                                 text_color="#64748b")
        order_lbl.pack(side="left", padx=4)
        row_data["order_lbl"] = order_lbl

        ctk.CTkButton(
            row, text="✕", width=32, height=32,
            fg_color="#ef4444", hover_color="#dc2626",
            command=lambda rd=row_data: self._delete_troop_row(rd),
        ).pack(side="right", padx=8)

        self.troop_rows.append(row_data)
        self._refresh_order_labels()

    def _delete_troop_row(self, rd: dict):
        rd["frame"].destroy()
        self.troop_rows.remove(rd)
        self._refresh_order_labels()
        self._save_troops()

    def _move_troop(self, rd: dict, direction: int):
        """Move troop row up (-1) or down (+1) in deploy order."""
        idx = self.troop_rows.index(rd)
        new_idx = idx + direction
        if new_idx < 0 or new_idx >= len(self.troop_rows):
            return

        # Swap in list
        self.troop_rows[idx], self.troop_rows[new_idx] = \
            self.troop_rows[new_idx], self.troop_rows[idx]

        # Re-pack all frames in new order
        for r in self.troop_rows:
            r["frame"].pack_forget()
        for r in self.troop_rows:
            r["frame"].pack(fill="x", pady=3, padx=4)

        self._refresh_order_labels()
        self._save_troops()

    def _refresh_order_labels(self):
        """Update the order number shown on each troop row."""
        for i, rd in enumerate(self.troop_rows):
            if "order_lbl" in rd:
                rd["order_lbl"].configure(text=f"#{i+1}")

    # ── Save handlers ────────────────────────────────────────────────────────

    def _save_loot(self):
        try:
            def _parse(entry: ctk.CTkEntry) -> list[int]:
                vals = [int(x.strip()) for x in entry.get().split(",") if x.strip()]
                return sorted(vals) if vals else [0]

            loot = self.config.setdefault("loot", {})
            loot["gold_thresholds"]        = _parse(self._gold_entry)
            loot["elixir_thresholds"]      = _parse(self._elixir_entry)
            loot["dark_elixir_thresholds"] = _parse(self._dark_entry)
            loot["min_gold"]               = loot["gold_thresholds"][0]
            loot["min_elixir"]             = loot["elixir_thresholds"][0]
            loot["gold_priority"]          = self._gold_pri_var.get()
            loot["elixir_priority"]        = self._elixir_pri_var.get()
            loot["dark_elixir_priority"]   = self._dark_pri_var.get()
            save_config(self.config, CONFIG_FILE)

            if self.engine and self.running:
                self.engine.update_loot_config(loot)

            mode = "PRIORITY" if any([loot["gold_priority"], loot["elixir_priority"],
                                       loot["dark_elixir_priority"]]) else "OR"
            self._log(f"Loot saved [{mode}]: G={loot['gold_thresholds']} "
                      f"E={loot['elixir_thresholds']} DE={loot['dark_elixir_thresholds']}")
        except ValueError as e:
            self._log(f"Invalid loot input: {e}", "error")

    def _save_troops(self):
        speed_map = {"INSTANT (0.02s)": 0.02, "ULTRA FAST (0.05s)": 0.05,
                     "FAST (0.08s)": 0.08, "NORMAL (0.12s)": 0.12}
        troops_cfg = self.config.setdefault("troops", {})
        troops_cfg["deploy_speed"] = speed_map.get(self._speed_var.get(), 0.08)

        custom = []
        for rd in self.troop_rows:
            name = rd["name_var"].get().strip()
            if not name:
                continue
            custom.append({"name": name, "image": rd["image_path"]})

        troops_cfg["custom_troops"] = custom
        save_config(self.config, CONFIG_FILE)
        self._log(f"Troops saved: {len(custom)} configured")

    def _sync_config_from_ui(self):
        """Pull current UI values into self.config without writing to disk."""
        try:
            def _parse(entry):
                vals = [int(x.strip()) for x in entry.get().split(",") if x.strip()]
                return sorted(vals) if vals else [0]
            loot = self.config.setdefault("loot", {})
            loot["gold_thresholds"]        = _parse(self._gold_entry)
            loot["elixir_thresholds"]      = _parse(self._elixir_entry)
            loot["dark_elixir_thresholds"] = _parse(self._dark_entry)
            loot["gold_priority"]          = self._gold_pri_var.get()
            loot["elixir_priority"]        = self._elixir_pri_var.get()
            loot["dark_elixir_priority"]   = self._dark_pri_var.get()
        except Exception:
            pass

        speed_map = {"INSTANT (0.02s)": 0.02, "ULTRA FAST (0.05s)": 0.05,
                     "FAST (0.08s)": 0.08, "NORMAL (0.12s)": 0.12}
        troops = self.config.setdefault("troops", {})
        troops["deploy_speed"] = speed_map.get(self._speed_var.get(), 0.08)
        custom = []
        for rd in self.troop_rows:
            name = rd["name_var"].get().strip()
            if not name:
                continue
            custom.append({"name": name, "image": rd["image_path"]})
        troops["custom_troops"] = custom

    # ── Bot control ───────────────────────────────────────────────────────────

    def _toggle_bot(self):
        if self.running:
            self._stop_bot()
        else:
            self._start_bot()

    def _start_bot(self):
        if self.running:
            return
        self._sync_config_from_ui()

        try:
            adb_cfg = self.config.get("adb", {})
            self.adb = ADBController(
                device_id=adb_cfg.get("device_id", "127.0.0.1:5555"),
                adb_port=adb_cfg.get("port", 5555),
                adb_path=adb_cfg.get("adb_path"),
            )
            self.vision = TemplateMatcher(self.config)
            self.engine = CoCBot(
                adb=self.adb,
                vision=self.vision,
                config=self.config,
                status_callback=self._on_bot_status,
            )
        except Exception as e:
            self._log(f"Init error: {e}", "error")
            return

        self.running = True
        self.start_btn.configure(text="STOP BOT", fg_color="#ef4444", hover_color="#dc2626")
        self.status_dot.configure(text="● Running", text_color="#22c55e")
        self.status_msg.configure(text="Bot is farming…")

        self.bot_thread = threading.Thread(target=self.engine.run, daemon=True)
        self.bot_thread.start()
        self._log("Bot started")

    def _stop_bot(self):
        if not self.running:
            return
        self.running = False
        if self.engine:
            self.engine._cb = None   # detach callback first so no GUI updates after this
            self.engine.stop()       # sets _stop_event → wakes all sleeping/waiting code
        # Wait briefly for the thread to finish (non-blocking — just give it a moment)
        if self.bot_thread and self.bot_thread.is_alive():
            self.bot_thread.join(timeout=3)
        self.engine = None
        self.bot_thread = None
        self.start_btn.configure(text="START BOT", fg_color="#22c55e", hover_color="#16a34a")
        self.status_dot.configure(text="● Stopped", text_color="#94a3b8")
        self.status_msg.configure(text="Press START to begin farming")
        self._log("Bot stopped")

    # ── Stats ─────────────────────────────────────────────────────────────────

    def _reset_stats(self):
        if self.engine:
            self.engine.stats = {"cycles": 0, "attacks": 0, "skipped": 0,
                                  "gold": 0, "elixir": 0, "dark_elixir": 0}
        for lbl in self._stat_labels.values():
            lbl.configure(text="0")
        self._log("Stats reset")

    def _update_stats(self):
        if not self.engine:
            return
        s = self.engine.get_stats()
        for key, lbl in self._stat_labels.items():
            val = s.get(key, 0)
            lbl.configure(text=f"{val:,}")

    # ── Logging ───────────────────────────────────────────────────────────────

    def _on_bot_status(self, msg: str, level: str = "info"):
        self._status_q.put({"msg": msg, "level": level})

    def _log(self, msg: str, level: str = "info"):
        ts = time.strftime("%H:%M:%S")
        icon = {"error": "✕", "warning": "!", "success": "✓"}.get(level, "›")
        line = f"[{ts}] {icon} {msg}"
        self._log_lines.append(line)
        if len(self._log_lines) > self._max_log:
            self._log_lines.pop(0)
        self._refresh_log()

    def _refresh_log(self):
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.insert("end", "\n".join(self._log_lines))
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    # ── Poll loop ─────────────────────────────────────────────────────────────

    def _poll(self):
        try:
            while True:
                item = self._status_q.get_nowait()
                self._log(item["msg"], item.get("level", "info"))
                self.status_msg.configure(text=item["msg"][:90])
        except Empty:
            pass
        self._update_stats()
        self.root.after(400, self._poll)

    # ── Entry point ───────────────────────────────────────────────────────────

    def run(self):
        self.root.mainloop()
