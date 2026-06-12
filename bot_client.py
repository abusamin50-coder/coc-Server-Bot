"""
CoC Bot Client — User এর PC তে চলবে।
Login করে server থেকে config নিয়ে bot চালাবে।
প্রতিবার open করলে password চাইবে।
"""

import sys
import json
import time
import threading
import tkinter as tk
from tkinter import ttk, messagebox
import requests
from loguru import logger

# ─── Server URL — deploy করার পর এখানে দাও ───
SERVER_URL = "https://your-app.railway.app"  # <-- পরে update করতে হবে
# ──────────────────────────────────────────────

logger.remove()
logger.add("logs/client.log", rotation="5 MB", retention="7 days", level="INFO")


class BotClient:
    def __init__(self):
        self.user_id         = None
        self.username        = None
        self.session_version = None
        self.devices         = []
        self.selected_device = None
        self.bot_running     = False
        self._bot_thread     = None
        self._stop_event     = threading.Event()

        self.root = tk.Tk()
        self.root.title("CoC Bot")
        self.root.geometry("480x560")
        self.root.resizable(False, False)
        self.root.configure(bg="#0f0f1a")
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self._show_login()

    # ─────────────────────────── Login UI ─────────────────────────────────────

    def _show_login(self):
        self._clear_root()
        self.root.title("CoC Bot — Login")

        frame = tk.Frame(self.root, bg="#1a1a2e", bd=0)
        frame.place(relx=0.5, rely=0.5, anchor="center", width=360, height=380)

        tk.Label(frame, text="CoC Bot", font=("Segoe UI", 20, "bold"),
                 fg="#f0a500", bg="#1a1a2e").pack(pady=(30, 5))
        tk.Label(frame, text="Login করো", font=("Segoe UI", 10),
                 fg="#aaaaaa", bg="#1a1a2e").pack(pady=(0, 20))

        # Notice label
        self.notice_label = tk.Label(frame, text="", font=("Segoe UI", 9),
                                     fg="#e74c3c", bg="#1a1a2e", wraplength=320)
        self.notice_label.pack(pady=(0, 10))

        tk.Label(frame, text="Username", font=("Segoe UI", 9),
                 fg="#aaaaaa", bg="#1a1a2e", anchor="w").pack(fill="x", padx=30)
        self.entry_user = tk.Entry(frame, font=("Segoe UI", 11),
                                   bg="#0f0f1a", fg="#e0e0e0",
                                   insertbackground="#f0a500",
                                   relief="flat", bd=5)
        self.entry_user.pack(fill="x", padx=30, pady=(2, 10))

        tk.Label(frame, text="Password", font=("Segoe UI", 9),
                 fg="#aaaaaa", bg="#1a1a2e", anchor="w").pack(fill="x", padx=30)
        self.entry_pass = tk.Entry(frame, show="*", font=("Segoe UI", 11),
                                   bg="#0f0f1a", fg="#e0e0e0",
                                   insertbackground="#f0a500",
                                   relief="flat", bd=5)
        self.entry_pass.pack(fill="x", padx=30, pady=(2, 20))
        self.entry_pass.bind("<Return>", lambda e: self._do_login())

        self.login_btn = tk.Button(frame, text="Login", font=("Segoe UI", 11, "bold"),
                                   bg="#f0a500", fg="#000000",
                                   relief="flat", cursor="hand2",
                                   command=self._do_login)
        self.login_btn.pack(fill="x", padx=30, ipady=8)

        self.status_label = tk.Label(frame, text="", font=("Segoe UI", 9),
                                     fg="#e74c3c", bg="#1a1a2e")
        self.status_label.pack(pady=10)

        self.entry_user.focus()

    def _do_login(self):
        username = self.entry_user.get().strip()
        password = self.entry_pass.get()

        if not username or not password:
            self.status_label.config(text="Username এবং Password দাও।")
            return

        self.login_btn.config(state="disabled", text="যাচাই করছি...")
        self.status_label.config(text="")
        self.root.update()

        try:
            res = requests.post(
                f"{SERVER_URL}/api/auth",
                json={"username": username, "password": password},
                timeout=10,
            )
            data = res.json()

            if data.get("ok"):
                self.user_id         = data["user_id"]
                self.username        = data["username"]
                self.session_version = data["session_version"]
                self.devices         = data["devices"]

                # Show notices
                notices = data.get("notices", [])
                if notices:
                    msg = "\n".join(f"[{n['level'].upper()}] {n['message']}" for n in notices)
                    messagebox.showinfo("Notice", msg)

                self._show_dashboard()
            else:
                reason = data.get("reason", "")
                if reason == "banned":
                    msg = data.get("message", "Account ban করা হয়েছে।")
                    self.status_label.config(text=f"Ban: {msg}\nAdmin এর সাথে যোগাযোগ করো।")
                elif reason == "ip_banned":
                    self.status_label.config(text="এই device থেকে access নেই।\nAdmin এর সাথে যোগাযোগ করো।")
                else:
                    self.status_label.config(text="Username বা Password ভুল।")

                self.login_btn.config(state="normal", text="Login")

        except requests.exceptions.ConnectionError:
            self.status_label.config(text="Server এর সাথে connection নেই।\nInternet check করো।")
            self.login_btn.config(state="normal", text="Login")
        except Exception as e:
            self.status_label.config(text=f"Error: {e}")
            self.login_btn.config(state="normal", text="Login")

    # ─────────────────────────── Dashboard UI ─────────────────────────────────

    def _show_dashboard(self):
        self._clear_root()
        self.root.title(f"CoC Bot — {self.username}")

        # Top bar
        top = tk.Frame(self.root, bg="#1a1a2e", pady=8)
        top.pack(fill="x")
        tk.Label(top, text=f"  CoC Bot  |  {self.username}",
                 font=("Segoe UI", 11, "bold"), fg="#f0a500", bg="#1a1a2e").pack(side="left")
        tk.Button(top, text="Logout", font=("Segoe UI", 9),
                  bg="#c0392b", fg="white", relief="flat", cursor="hand2",
                  command=self._logout).pack(side="right", padx=10)

        # Device selector
        dev_frame = tk.Frame(self.root, bg="#0f0f1a", pady=5)
        dev_frame.pack(fill="x", padx=15)
        tk.Label(dev_frame, text="Device:", font=("Segoe UI", 9),
                 fg="#aaaaaa", bg="#0f0f1a").pack(side="left")

        self.device_var = tk.StringVar()
        dev_names = [f"{d['device_name']} ({d['adb_host']}:{d['adb_port']})" for d in self.devices]
        self.device_combo = ttk.Combobox(dev_frame, textvariable=self.device_var,
                                          values=dev_names, state="readonly",
                                          font=("Segoe UI", 9), width=35)
        self.device_combo.pack(side="left", padx=8)
        if dev_names:
            self.device_combo.current(0)
            self.selected_device = self.devices[0]
        self.device_combo.bind("<<ComboboxSelected>>", self._on_device_select)

        # Status
        self.status_frame = tk.Frame(self.root, bg="#0f0f1a")
        self.status_frame.pack(fill="x", padx=15, pady=5)
        self.status_dot = tk.Label(self.status_frame, text="⬤", font=("Segoe UI", 12),
                                    fg="#7f8c8d", bg="#0f0f1a")
        self.status_dot.pack(side="left")
        self.status_text = tk.Label(self.status_frame, text="Bot বন্ধ আছে",
                                     font=("Segoe UI", 9), fg="#aaaaaa", bg="#0f0f1a")
        self.status_text.pack(side="left", padx=5)

        # Attack counter
        counter_frame = tk.Frame(self.root, bg="#1a1a2e", bd=1, relief="flat")
        counter_frame.pack(fill="x", padx=15, pady=5)
        self.attack_label = tk.Label(counter_frame,
                                      text=self._attack_text(),
                                      font=("Segoe UI", 9), fg="#aaaaaa", bg="#1a1a2e",
                                      pady=6, padx=10)
        self.attack_label.pack(side="left")

        # Buttons
        btn_frame = tk.Frame(self.root, bg="#0f0f1a")
        btn_frame.pack(pady=10)
        self.start_btn = tk.Button(btn_frame, text="▶  Start Bot",
                                    font=("Segoe UI", 11, "bold"),
                                    bg="#27ae60", fg="white", relief="flat",
                                    cursor="hand2", width=14, pady=8,
                                    command=self._start_bot)
        self.start_btn.pack(side="left", padx=5)
        self.stop_btn = tk.Button(btn_frame, text="■  Stop Bot",
                                   font=("Segoe UI", 11, "bold"),
                                   bg="#c0392b", fg="white", relief="flat",
                                   cursor="hand2", width=14, pady=8,
                                   state="disabled", command=self._stop_bot)
        self.stop_btn.pack(side="left", padx=5)

        # Log area
        log_frame = tk.Frame(self.root, bg="#0f0f1a")
        log_frame.pack(fill="both", expand=True, padx=15, pady=(5, 15))
        tk.Label(log_frame, text="Log", font=("Segoe UI", 9),
                 fg="#aaaaaa", bg="#0f0f1a").pack(anchor="w")

        self.log_text = tk.Text(log_frame, font=("Consolas", 9),
                                 bg="#0a0a14", fg="#00ff88",
                                 relief="flat", state="disabled",
                                 wrap="word", height=14)
        scroll = tk.Scrollbar(log_frame, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scroll.set)
        self.log_text.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        self._log("System ready. Bot start করতে Start Bot চাপো।")

    def _attack_text(self):
        if self.selected_device:
            d = self.selected_device
            return f"আজকের attack: {d.get('attacks_today', 0)} / {d.get('attack_limit', 50)}"
        return ""

    def _on_device_select(self, event=None):
        idx = self.device_combo.current()
        if 0 <= idx < len(self.devices):
            self.selected_device = self.devices[idx]
            self.attack_label.config(text=self._attack_text())

    # ─────────────────────────── Bot control ──────────────────────────────────

    def _start_bot(self):
        if not self.selected_device:
            messagebox.showwarning("Device নেই", "Device select করো।")
            return

        if not self._verify_session():
            return

        self._stop_event.clear()
        self.bot_running = True
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.status_dot.config(fg="#27ae60")
        self.status_text.config(text="Bot চলছে...")

        self._bot_thread = threading.Thread(target=self._bot_loop, daemon=True)
        self._bot_thread.start()
        self._log("Bot শুরু হয়েছে।")

    def _stop_bot(self):
        self._stop_event.set()
        self.bot_running = False
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self.status_dot.config(fg="#7f8c8d")
        self.status_text.config(text="Bot বন্ধ আছে")
        self._log("Bot বন্ধ করা হয়েছে।")

    def _bot_loop(self):
        from adb_controller import ADBController
        from bot_engine import BotEngine
        from config import load_config

        dev = self.selected_device

        try:
            self._log(f"LDPlayer এ connect করছি ({dev['adb_host']}:{dev['adb_port']})...")
            adb = ADBController(
                device_id=f"{dev['adb_host']}:{dev['adb_port']}",
                adb_port=dev['adb_port'],
            )
            if not adb.connect_device():
                self._log("ERROR: LDPlayer এ connect করা যায়নি। LDPlayer চালু আছে কিনা দেখো।")
                self.root.after(0, self._stop_bot)
                return

            self._log("Connected! Bot চালু হচ্ছে...")

            # Server থেকে config নাও
            cfg = load_config()
            cfg["loot"]["min_gold"]    = dev.get("min_gold", 0)
            cfg["loot"]["min_elixir"]  = dev.get("min_elixir", 6000)
            cfg["troops"]["custom_troops"] = dev.get("troops", [])
            cfg["troops"]["deploy_speed"]  = dev.get("deploy_speed", 0.08)

            engine = BotEngine(adb=adb, config=cfg)
            attack_limit = dev.get("attack_limit", 50)

            while not self._stop_event.is_set():
                # Session verify প্রতি 5 মিনিটে
                if not self._verify_session(silent=True):
                    self._log("Session invalid — bot বন্ধ হচ্ছে।")
                    break

                attacks_today = dev.get("attacks_today", 0)
                if attacks_today >= attack_limit:
                    self._log(f"Daily limit ({attack_limit}) পূরণ হয়েছে। Bot বন্ধ।")
                    break

                self._log("Attack cycle শুরু...")
                try:
                    result = engine.run_attack_cycle()
                    if result:
                        dev["attacks_today"] = attacks_today + 1
                        self._report_attack(dev["device_id"])
                        self.root.after(0, lambda: self.attack_label.config(text=self._attack_text()))
                        self._log(f"Attack সফল! ({dev['attacks_today']}/{attack_limit})")
                except Exception as e:
                    self._log(f"Attack error: {e}")

                if not self._stop_event.wait(2):
                    continue

        except Exception as e:
            self._log(f"Bot error: {e}")
            logger.exception(e)
        finally:
            self.root.after(0, self._stop_bot)

    def _verify_session(self, silent=False) -> bool:
        try:
            res = requests.post(
                f"{SERVER_URL}/api/verify_session",
                json={"user_id": self.user_id, "session_version": self.session_version},
                timeout=8,
            )
            data = res.json()
            if data.get("ok"):
                return True

            reason = data.get("reason", "")
            if not silent:
                if reason == "banned":
                    messagebox.showerror("Banned", "তোমার account ban করা হয়েছে।")
                elif reason == "session_expired":
                    messagebox.showwarning("Session Expired", "Password পরিবর্তন হয়েছে। আবার login করো।")
                else:
                    messagebox.showerror("Error", "Session invalid। আবার login করো।")
            self.root.after(0, self._logout)
            return False

        except Exception:
            return True  # Network error হলে bot বন্ধ করব না

    def _report_attack(self, device_id):
        try:
            requests.post(
                f"{SERVER_URL}/user/api/attack_count/{device_id}",
                json={"user_id": self.user_id, "session_version": self.session_version},
                timeout=5,
            )
        except Exception:
            pass

    # ─────────────────────────── Helpers ──────────────────────────────────────

    def _log(self, msg: str):
        def _append():
            self.log_text.config(state="normal")
            self.log_text.insert("end", f"[{time.strftime('%H:%M:%S')}] {msg}\n")
            self.log_text.see("end")
            self.log_text.config(state="disabled")
        try:
            self.root.after(0, _append)
        except Exception:
            pass

    def _logout(self):
        self._stop_bot() if self.bot_running else None
        self.user_id = self.username = self.session_version = None
        self.devices = []
        self._show_login()

    def _clear_root(self):
        for widget in self.root.winfo_children():
            widget.destroy()

    def _on_close(self):
        if self.bot_running:
            if messagebox.askyesno("Bot চলছে", "Bot এখনো চলছে। বন্ধ করে exit করবে?"):
                self._stop_event.set()
                self.root.destroy()
        else:
            self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = BotClient()
    app.run()
