"""Pikipelago launcher window: pick a seed and your game disc or assets, then play.

Only tkinter and the launcher library are used. Runs the same `python -m randomizer run`
command as the console launcher; when tkinter is unavailable it falls back to that launcher.
Usage: gui.py [seed.json] [--server host:port]
"""
import os
import queue
import subprocess
import sys
import threading
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import launcher  # noqa: E402
import discimage  # noqa: E402

# Pikmin-inspired palette: forest floor, leaf, and the three Onion colors.
SOIL = "#17301f"
PANEL = "#22422d"
PANEL_EDGE = "#2f5a3c"
LEAF = "#9be15d"
LEAF_DARK = "#4f9a3a"
CREAM = "#f4f1e6"
MUTED = "#b9c6b0"
RED, YELLOW, BLUE = "#ff5f5f", "#ffd75a", "#5aa9ff"
FONT = "Segoe UI"
COLOR_OF = {"red": RED, "yellow": YELLOW, "blue": BLUE}
AREA_NAMES = {"impact-day2": "Impact Site", "foh-day2": "Forest of Hope", "navel-day2": "Forest Navel",
              "spring-day2": "Distant Spring", "trial-day2": "Final Trial"}


def describe_start(manifest):
    return AREA_NAMES.get(manifest.get("profile", ""), manifest.get("profile", "?"))


def starting_stats_hint(manifest):
    if not manifest:
        return ""
    color = manifest.get("starting_color", "red")
    stats = manifest.get("color_stats", {}).get(color)
    if not stats:
        return "Starting Pikmin stats: standard."
    unusual = any(stats.get(key, default) != default for key, default in
                  (("movement", 100), ("damage", 100), ("attack_rate", 100), ("carry", 1)))
    if not unusual:
        return "Starting Pikmin stats: standard."
    return (f"Seed starting stats — {color.title()} Pikmin: movement {stats['movement']}%, "
            f"damage {stats['damage']}%, attack rate {stats['attack_rate']}%, carry strength {stats['carry']}. "
            "These are seed rules, not the game's playback speed.")


class LauncherApp:
    def __init__(self, root, seed_arg=None, server_arg=None):
        import tkinter as tk
        from tkinter import ttk
        self.tk, self.ttk = tk, ttk
        self.root = root
        self.config = launcher.load_config()
        self.manifest = None
        self.process = None
        self.worker = None
        self.lines = queue.Queue()
        self.show_setup = False
        self.exe = launcher.ROOT / "bin" / "nectar.exe"
        root.title("Pikipelago")
        root.configure(bg=SOIL)
        root.minsize(760, 600)
        root.geometry("900x760")
        self.style()
        self.build()
        seed = seed_arg or self.config.get("seed")
        if not seed and (launcher.ROOT / "seeds" / "seed.json").is_file():
            seed = str(launcher.ROOT / "seeds" / "seed.json")
        if seed and Path(seed).is_file():
            self.set_seed(seed)
        installed = self.config.get("assets")
        source = installed if installed and launcher.assets_problem(installed) is None else self.config.get("image") or installed
        if source:
            self.source_var.set(source)
        if server_arg:
            self.server_var.set(server_arg)
        elif self.config.get("server"):
            self.server_var.set(self.config["server"])
        self.refresh_source_status()
        root.after(100, self.pump)

    # --- Layout -----------------------------------------------------------

    def style(self):
        s = self.ttk.Style(self.root)
        s.theme_use("clam")
        s.configure("TFrame", background=SOIL)
        s.configure("Panel.TFrame", background=PANEL)
        s.configure("TLabel", background=SOIL, foreground=CREAM, font=(FONT, 10))
        s.configure("Panel.TLabel", background=PANEL, foreground=CREAM, font=(FONT, 10))
        s.configure("Muted.TLabel", background=PANEL, foreground=MUTED, font=(FONT, 9))
        s.configure("Heading.TLabel", background=PANEL, foreground=LEAF, font=(FONT, 11, "bold"))
        s.configure("TEntry", fieldbackground="#0f1f15", foreground=CREAM, insertcolor=CREAM, bordercolor=PANEL_EDGE)
        s.configure("TButton", background=PANEL_EDGE, foreground=CREAM, font=(FONT, 10), borderwidth=0, padding=(10, 5))
        s.map("TButton", background=[("active", "#3d7450"), ("disabled", "#2a3d30")], foreground=[("disabled", MUTED)])
        s.configure("Play.TButton", background=LEAF_DARK, foreground=CREAM, font=(FONT, 13, "bold"), padding=(26, 10))
        s.map("Play.TButton", background=[("active", LEAF), ("disabled", "#2a3d30")], foreground=[("active", SOIL), ("disabled", MUTED)])
        s.configure("Leaf.Horizontal.TProgressbar", troughcolor="#0f1f15", background=LEAF, bordercolor=PANEL, lightcolor=LEAF, darkcolor=LEAF_DARK)

    def panel(self, parent, title):
        frame = self.ttk.Frame(parent, style="Panel.TFrame", padding=(14, 10))
        frame.pack(fill="x", padx=16, pady=(0, 10))
        self.ttk.Label(frame, text=title, style="Heading.TLabel").grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 6))
        frame.columnconfigure(1, weight=1)
        return frame

    def build(self):
        tk, ttk = self.tk, self.ttk
        header = tk.Canvas(self.root, height=92, bg=SOIL, highlightthickness=0)
        header.pack(fill="x")
        header.bind("<Configure>", lambda e: self.draw_header(header))

        seed = self.panel(self.root, "1. CHOOSE A RUN")
        choices = ttk.Frame(seed, style="Panel.TFrame")
        choices.grid(row=1, column=0, columnspan=3, sticky="w", pady=(0, 8))
        self.new_solo_button = ttk.Button(choices, text="New solo run…", command=self.new_solo)
        self.new_solo_button.pack(side="left")
        ttk.Button(choices, text="Open seed…", command=self.browse_seed).pack(side="left", padx=(8, 0))
        ttk.Label(choices, text="Solo: create here. AP: open your slot's .pikmin.json file.",
                  style="Muted.TLabel").pack(side="left", padx=(12, 0))
        self.seed_var = tk.StringVar()
        ttk.Label(seed, text="Seed file", style="Panel.TLabel").grid(row=2, column=0, sticky="w", padx=(0, 8))
        self.seed_entry = ttk.Entry(seed, textvariable=self.seed_var)
        self.seed_entry.grid(row=2, column=1, sticky="ew")
        ttk.Button(seed, text="Browse…", command=self.browse_seed).grid(row=2, column=2, padx=(8, 0))
        self.card = tk.Canvas(seed, height=64, bg=PANEL, highlightthickness=0)
        self.card.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(8, 0))
        self.resume_var = tk.StringVar()
        ttk.Label(seed, textvariable=self.resume_var, style="Muted.TLabel", wraplength=700).grid(
            row=4, column=0, columnspan=3, sticky="w", pady=(4, 0))
        self.stats_hint_var = tk.StringVar()
        ttk.Label(seed, textvariable=self.stats_hint_var, style="Panel.TLabel", wraplength=760).grid(
            row=5, column=0, columnspan=3, sticky="w", pady=(6, 0))
        ttk.Label(seed, text="While playing: F1 opens game settings (graphics, audio and controls). F8 opens the tracker.",
                  style="Muted.TLabel", wraplength=760).grid(row=6, column=0, columnspan=3, sticky="w", pady=(6, 0))
        self.seed_var.trace_add("write", lambda *a: self.on_seed_changed())

        data = self.panel(self.root, "2. SET UP GAME DATA — ONCE")
        self.data_panel = data
        self.installed_row = ttk.Frame(data, style="Panel.TFrame")
        ttk.Label(self.installed_row, text="Pikmin installed ✓", style="Panel.TLabel").pack(side="left")
        ttk.Button(self.installed_row, text="Change…", command=self.change_setup).pack(side="left", padx=(12, 0))
        self.source_var = tk.StringVar()
        ttk.Label(data, text="Disc image or assets folder", style="Panel.TLabel").grid(row=1, column=0, sticky="w", padx=(0, 8))
        ttk.Entry(data, textvariable=self.source_var).grid(row=1, column=1, sticky="ew")
        ttk.Button(data, text="Disc image…", command=self.browse_image).grid(row=1, column=2, padx=(8, 0))
        ttk.Button(data, text="Folder…", command=self.browse_folder).grid(row=1, column=3, padx=(6, 0))
        self.source_status = ttk.Label(data, text="", style="Muted.TLabel", wraplength=700)
        self.source_status.grid(row=2, column=0, columnspan=4, sticky="w", pady=(6, 0))
        self.source_var.trace_add("write", lambda *a: self.refresh_source_status())
        self.setup_widgets = list(data.grid_slaves())

        self.ap = self.panel(self.root, "3. CONNECT TO ARCHIPELAGO")
        self.server_var = tk.StringVar()
        self.password_var = tk.StringVar()
        ttk.Label(self.ap, text="Server host:port", style="Panel.TLabel").grid(row=1, column=0, sticky="w", padx=(0, 8))
        ttk.Entry(self.ap, textvariable=self.server_var).grid(row=1, column=1, sticky="ew")
        ttk.Label(self.ap, text="Room password", style="Panel.TLabel").grid(row=2, column=0, sticky="w", padx=(0, 8), pady=(6, 0))
        ttk.Entry(self.ap, textvariable=self.password_var, show="•").grid(row=2, column=1, sticky="ew", pady=(6, 0))
        ttk.Label(self.ap, text="Use the server address and port from your room page, not the browser URL. Password is optional and never saved.", wraplength=700,
                  style="Muted.TLabel").grid(row=3, column=0, columnspan=4, sticky="w", pady=(6, 0))
        self.reconnect_button = ttk.Button(self.ap, text="Reconnect", command=self.reconnect, state="disabled")
        self.reconnect_button.grid(row=2, column=2, padx=(8, 0))
        self.ap.pack_forget()

        actions = ttk.Frame(self.root)
        actions.pack(fill="x", padx=16, pady=(4, 6))
        self.play_button = ttk.Button(actions, text="PLAY", style="Play.TButton", command=self.play)
        self.play_button.pack(side="left")
        self.stop_button = ttk.Button(actions, text="Stop", command=self.stop, state="disabled")
        self.stop_button.pack(side="left", padx=(10, 0))
        ttk.Button(actions, text="Copy diagnostics", command=self.copy_diagnostics).pack(side="left", padx=(0, 8))
        self.status_var = tk.StringVar(value=f"Ready. Version {launcher.runtime_version()}.")
        ttk.Label(actions, textvariable=self.status_var, wraplength=220).pack(side="left", padx=(16, 0))
        self.progress = ttk.Progressbar(actions, style="Leaf.Horizontal.TProgressbar", length=180, mode="determinate")
        self.progress.pack(side="right")

        log_frame = ttk.Frame(self.root)
        log_frame.pack(fill="both", expand=True, padx=16, pady=(0, 14))
        self.log = tk.Text(log_frame, bg="#0f1f15", fg=MUTED, insertbackground=CREAM, font=("Consolas", 9),
                           relief="flat", wrap="word", state="disabled", height=10)
        scroll = ttk.Scrollbar(log_frame, command=self.log.yview)
        self.log.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.log.pack(fill="both", expand=True)
        self.log.tag_configure("error", foreground=RED)
        self.log.tag_configure("good", foreground=LEAF)

    def draw_header(self, canvas):
        canvas.delete("all")
        width = max(canvas.winfo_width(), 400)
        canvas.create_rectangle(0, 84, width, 92, fill=LEAF_DARK, outline="")
        title = canvas.create_text(24, 46, anchor="w", text="Pikipelago", fill=CREAM, font=(FONT, 26, "bold"))
        canvas.create_text(canvas.bbox(title)[2] + 18, 52, anchor="w", text="Pikmin 1 randomizer · Archipelago", fill=MUTED, font=(FONT, 10))
        for index, color in enumerate((RED, YELLOW, BLUE)):
            x = width - 120 + index * 40
            canvas.create_line(x, 30, x, 16, fill=LEAF_DARK, width=2)
            canvas.create_polygon(x, 16, x + 9, 8, x + 3, 20, fill=LEAF, outline="")
            canvas.create_oval(x - 11, 30, x + 11, 52, fill=color, outline="")
            canvas.create_oval(x - 6, 37, x - 2, 41, fill="#111", outline="")
            canvas.create_oval(x + 2, 37, x + 6, 41, fill="#111", outline="")

    # --- Seed and source -----------------------------------------------------

    def new_solo(self):
        if self.worker and self.worker.is_alive():
            return
        from tkinter import simpledialog
        name = simpledialog.askstring("New solo run",
            "Create a solo run with a random starting area and color, standard stats, "
            "and no traps. Goal: defeat Emperor Bulblax.\n\n"
            "Seed name (blank makes a fresh run; repeating a name resumes that seed):", parent=self.root)
        if name is None:
            return
        try:
            path = launcher.create_solo_seed(name)
            self.config["seed"] = str(path)
            launcher.save_config(self.config)
            self.set_seed(path)
            self.status_var.set("Solo run created. Choose game data, then Play solo.")
        except (OSError, ValueError) as exc:
            self.append(f"Could not create the solo run: {exc}", "error")

    def browse_seed(self):
        if self.worker and self.worker.is_alive():
            return
        from tkinter import filedialog
        chosen = filedialog.askopenfilename(title="Choose a seed", filetypes=[("Pikipelago seed", "*.json"), ("All files", "*.*")])
        if chosen:
            self.set_seed(chosen)

    def set_seed(self, path):
        self.seed_var.set(str(Path(path)))

    def on_seed_changed(self):
        path = self.seed_var.get().strip()
        self.manifest = None
        self.stats_hint_var.set("")
        if path and Path(path).is_file():
            try:
                self.manifest = launcher.load_manifest(path)
            except launcher.LaunchError as exc:
                self.ap.pack_forget()
                self.play_button.configure(text="PLAY")
                self.render_card(error=str(exc))
                return
        self.stats_hint_var.set(starting_stats_hint(self.manifest))
        self.render_card()
        self.resume_var.set(launcher.run_summary(self.manifest, path) if self.manifest else "")
        if self.manifest and self.manifest.get("mode") == "ap":
            self.play_button.configure(text="Connect & play")
            self.ap.pack(fill="x", padx=16, pady=(0, 10), before=self.play_button.master)
        else:
            self.play_button.configure(text=("Continue solo" if self.resume_var.get().startswith("Continue") else "Play solo") if self.manifest else "PLAY")
            self.ap.pack_forget()

    def render_card(self, error=None):
        card = self.card
        card.delete("all")
        if error:
            card.create_text(8, 12, anchor="nw", text=error, fill=RED, font=(FONT, 9), width=680)
            return
        if not self.manifest:
            card.create_text(8, 22, anchor="w", text="Create a solo run, or open the .pikmin.json file supplied by your AP host.", fill=MUTED, font=(FONT, 10))
            return
        m = self.manifest
        color = m.get("starting_color", "red")
        card.create_oval(8, 12, 40, 44, fill=COLOR_OF.get(color, MUTED), outline="")
        card.create_text(52, 16, anchor="nw", text=f"{m.get('slot', '?')}  ·  {m.get('mode', '?').upper()}  ·  seed “{m.get('seed', '?')}”  ·  id {launcher.short_fingerprint(m)}",
                         fill=CREAM, font=(FONT, 11, "bold"))
        goal = "Emperor Bulblax after 25 repairs" if m.get("goal_mode") == "emperor_bulblax" else "25 Ship Repairs"
        extras = []
        if m.get("death_link"):
            extras.append(f"DeathLink ×{m['death_link_pikmin']}")
        if m.get("campaign_layout"):
            extras.append("campaign enemies")
        if m.get("color_stats"):
            extras.append("rolled stats")
        card.create_text(52, 38, anchor="nw", fill=MUTED, font=(FONT, 9),
                         text=f"Start: {describe_start(m)} with {color} Pikmin  ·  Goal: {goal}  ·  {len(m.get('locations', {}))} checks"
                              + (f"  ·  {', '.join(extras)}" if extras else ""))

    def browse_image(self):
        from tkinter import filedialog
        chosen = filedialog.askopenfilename(title="Choose your Pikmin disc image",
                                            filetypes=[("GameCube image", "*.iso *.gcm *.rvz *.wia"), ("All files", "*.*")])
        if chosen:
            self.source_var.set(str(Path(chosen)))

    def browse_folder(self):
        from tkinter import filedialog
        chosen = filedialog.askdirectory(title="Choose the extracted assets folder (contains dataDir)")
        if chosen:
            self.source_var.set(str(Path(chosen)))

    def change_setup(self):
        self.show_setup = True
        self.refresh_source_status()

    def copy_diagnostics(self):
        report = launcher.diagnostic_report(self.manifest, self.source_var.get().strip(), self.log.get("1.0", "end"))
        self.root.clipboard_clear()
        self.root.clipboard_append(report)
        self.status_var.set("Diagnostics copied. No passwords, addresses, paths or raw logs included.")

    def refresh_source_status(self):
        source = self.source_var.get().strip().strip('"')
        if not source:
            text = "Choose your own Pikmin (USA Rev 1 or Europe) disc image (.iso, .gcm, .rvz or .wia), or a folder that already contains dataDir."
        elif discimage.is_disc_image(source):
            if not Path(source).is_file():
                text = "That disc image does not exist."
            elif discimage.assets_ready(launcher.game_data_dir(), launcher.assets_problem):
                text = f"Disc image; assets already extracted to {launcher.game_data_dir() / 'assets'}."
            else:
                text = "Disc image; the first Play extracts about 650 MB of game data (a few minutes; RVZ is decoded first). The image is never modified."
        else:
            problem = launcher.assets_problem(source)
            text = "Extracted assets folder looks good." if problem is None else problem
        self.source_status.configure(text=text)
        installed = bool(source and not discimage.is_disc_image(source) and launcher.assets_problem(source) is None)
        if hasattr(self, "setup_widgets"):
            for widget in self.setup_widgets:
                if widget.grid_info().get("row") == 0:
                    continue
                if installed and not self.show_setup:
                    widget.grid_remove()
                else:
                    widget.grid()
            if installed and not self.show_setup:
                self.installed_row.grid(row=1, column=0, columnspan=4, sticky="w")
            else:
                self.installed_row.grid_remove()

    # --- Running ----------------------------------------------------------

    def append(self, text, tag=None):
        self.log.configure(state="normal")
        self.log.insert("end", text + "\n", tag)
        self.log.see("end")
        self.log.configure(state="disabled")

    def set_running(self, running):
        self.play_button.configure(state="disabled" if running else "normal")
        self.new_solo_button.configure(state="disabled" if running else "normal")
        self.seed_entry.configure(state="disabled" if running else "normal")
        self.stop_button.configure(state="normal" if running else "disabled")

    def play(self):
        if self.worker and self.worker.is_alive():
            return
        seed = self.seed_var.get().strip()
        source = self.source_var.get().strip().strip('"')
        try:
            if not seed or not Path(seed).is_file():
                raise launcher.LaunchError("Choose a seed file first.")
            if not self.exe.is_file():
                raise launcher.LaunchError(f"The game executable is missing: {self.exe}. Re-extract the release zip.")
            manifest = launcher.load_manifest(seed)
            if not source:
                raise launcher.LaunchError("Choose your disc image or extracted assets folder first.")
            if discimage.is_disc_image(source) and not Path(source).is_file():
                raise launcher.LaunchError("That disc image does not exist. Choose it again.")
            if not discimage.is_disc_image(source) and launcher.assets_problem(source):
                raise launcher.LaunchError(launcher.assets_problem(source))
            server = None
            if manifest["mode"] == "ap":
                launcher.check_ap_dependencies()
                server = launcher.validate_server(self.server_var.get())
        except launcher.LaunchError as exc:
            self.append(str(exc), "error")
            self.status_var.set("Fix the highlighted problem and try again.")
            return
        self.config.update(seed=str(Path(seed).resolve()))
        if server:
            self.config["server"] = server
        launcher.save_config(self.config)
        password = self.password_var.get() or None
        self.log.configure(state="normal"); self.log.delete("1.0", "end"); self.log.configure(state="disabled")
        self.set_running(True)
        self.progress.configure(value=0)
        self.worker = threading.Thread(target=self.run, args=(seed, manifest, source, server, password), daemon=True)
        self.worker.start()

    def run(self, seed, manifest, source, server, password):
        try:
            if discimage.is_disc_image(source):
                self.lines.put(("status", "Extracting game data from the disc image…"))
                assets = launcher.extract_image(source, on_line=lambda line: self.lines.put(("extract", line)))
                self.config["image"] = str(Path(source).resolve())
            else:
                assets = str(Path(source).resolve())
                self.config.pop("image", None)
            self.config["assets"] = assets
            self.lines.put(("installed", assets))
            launcher.save_config(self.config)
            session = launcher.session_dir(manifest, seed)
            self.lines.put(("line", launcher.seed_card(manifest, seed)))
            self.lines.put(("line", f"Assets:  {assets}\nSession: {session}"))
            env = dict(os.environ)
            env.pop("PIKMIN_AP_PASSWORD", None)
            env["PYTHONUNBUFFERED"] = "1"
            env["PIKMIN_AP_CONTROL"] = "1" if server else "0"
            if password:
                env["PIKMIN_AP_PASSWORD"] = password
            command = launcher.build_command(seed, session, self.exe, assets, server)
            self.lines.put(("status", "Connecting to Archipelago…" if server else "Starting solo game…"))
            self.lines.put(("progress", 100))
            self.process = subprocess.Popen(command, cwd=str(launcher.ROOT), env=env, stdout=subprocess.PIPE,
                                            stderr=subprocess.STDOUT, stdin=subprocess.PIPE if server else subprocess.DEVNULL, text=True, encoding="utf-8", errors="replace",
                                            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            self.lines.put(("connection_controls", bool(server)))
            captured = []
            for line in self.process.stdout:
                captured.append(line)
                self.lines.put(("line", line.rstrip("\n")))
                if line.startswith("PIKMIN_AP_STATUS: connected"):
                    self.lines.put(("status", "Connected to Archipelago. Game ready."))
                elif line.startswith("PIKMIN_AP_STATUS: refused"):
                    self.lines.put(("status", "Connection refused. Correct the room address/password, then Reconnect."))
                elif line.startswith("PIKMIN_AP_STATUS: connecting"):
                    self.lines.put(("status", "Connecting to Archipelago…"))
                elif line.startswith(("AP disconnected:", "AP connection handshake failed.")):
                    self.lines.put(("status", "Connection failed — retrying. Check the room address, port and availability."))
            code = self.process.wait()
            if code:
                self.lines.put(("error", launcher.explain_failure(code, "".join(captured), session)))
                self.lines.put(("status", "The game closed with an error; see the log above."))
            else:
                self.lines.put(("good", "Game closed normally. Your day-end save and checks are kept for next time."))
                self.lines.put(("status", "Ready."))
        except launcher.LaunchError as exc:
            self.lines.put(("error", str(exc)))
            self.lines.put(("status", "Could not start; see the log above."))
        except OSError as exc:
            self.lines.put(("error", f"Could not start the game runner: {exc}"))
            self.lines.put(("status", "Could not start."))
        finally:
            self.process = None
            self.lines.put(("connection_controls", False))
            self.lines.put(("done", None))

    def reconnect(self):
        import json
        process = self.process
        if not process or process.poll() is not None or process.stdin is None:
            return
        try:
            server = launcher.validate_server(self.server_var.get())
            process.stdin.write(json.dumps({"server": server, "password": self.password_var.get() or None}) + "\n")
            process.stdin.flush()
            self.config["server"] = server
            launcher.save_config(self.config)
            self.status_var.set("Reconnecting to Archipelago…")
        except (launcher.LaunchError, OSError) as exc:
            self.append(f"Could not reconnect: {exc}", "error")

    def stop(self):
        process = self.process
        if process and process.poll() is None:
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(process.pid)], capture_output=True)
            self.append("Stopped. Anything not saved at a day end is lost.", "error")

    def pump(self):
        try:
            while True:
                kind, payload = self.lines.get_nowait()
                if kind == "line":
                    self.append(payload)
                elif kind == "error":
                    self.append(payload, "error")
                elif kind == "good":
                    self.append(payload, "good")
                elif kind == "status":
                    self.status_var.set(payload)
                elif kind == "connection_controls":
                    self.reconnect_button.configure(state="normal" if payload else "disabled")
                elif kind == "progress":
                    self.progress.configure(value=payload)
                elif kind == "installed":
                    self.show_setup = False
                    self.source_var.set(payload)
                elif kind == "extract":
                    percent = discimage.progress_percent(payload)
                    if "decoding disc image" in payload or payload.startswith("Decoding "):
                        self.status_var.set("Decoding disc image…")
                    elif payload.startswith("[100%]"):
                        self.status_var.set("Finishing installation…")
                    elif percent is not None:
                        self.status_var.set("Extracting game files…")
                    if percent is not None:
                        self.progress.configure(value=percent)
                        self.status_var.set(f"Extracting game data… {percent}%")
                    else:
                        self.append(payload)
                elif kind == "done":
                    self.set_running(False)
                    self.refresh_source_status()
        except queue.Empty:
            pass
        self.root.after(100, self.pump)


def main(argv=None):
    if sys.platform == "win32":
        # Give the launcher its own taskbar identity instead of Python/IDLE.
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Pikipelago.Launcher")
    argv = list(sys.argv[1:] if argv is None else argv)
    server = None
    if "--server" in argv:
        index = argv.index("--server")
        server = argv[index + 1] if index + 1 < len(argv) else None
        del argv[index:index + 2]
    seed = next((a for a in argv if not a.startswith("--")), None)
    try:
        import tkinter
        root = tkinter.Tk()
    except Exception as exc:  # No tkinter or no display: use the console launcher.
        print(f"Window unavailable ({exc}); using the console launcher.")
        return launcher.main([a for a in sys.argv[1:]])
    LauncherApp(root, seed, server)
    root.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
