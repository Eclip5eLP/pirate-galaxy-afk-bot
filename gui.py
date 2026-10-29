import os
import json
import queue
import customtkinter as ctk

# Set appearance mode and color theme
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

DEFAULT_BTN = dict(fg_color=["#3B8ED0", "#1F6AA5"], hover_color=["#36719F", "#144870"])
MAX_LOG_LINES = 500
LOG_COLORS = {"danger": "#ff5555", "error": "#ff5555", "warn": "#ffaa33", "system": "#55aaff"}


class App(ctk.CTk):
    def __init__(self, bot_instance, settings_path):
        super().__init__()

        self.bot = bot_instance
        self.settings_path = settings_path
        # Commands from other threads (hotkeys), processed in update_gui
        self.command_queue = queue.Queue()

        self.title(f"{self.bot.appName} {self.bot.version}")
        self.geometry("900x600")
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Configure grid layout
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Sidebar for controls
        self.sidebar_frame = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(8, weight=1)

        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="PGBot Dashboard", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        self.start_btn = ctk.CTkButton(self.sidebar_frame, text="Loading OCR...", command=self.toggle_start, state="disabled")
        self.start_btn.grid(row=1, column=0, padx=20, pady=10)

        self.pause_btn = ctk.CTkButton(self.sidebar_frame, text="Pause Bot", command=self.toggle_pause, state="disabled")
        self.pause_btn.grid(row=2, column=0, padx=20, pady=10)

        self.state_label = ctk.CTkLabel(self.sidebar_frame, text="State: STOPPED")
        self.state_label.grid(row=3, column=0, padx=20, pady=5)

        self.hp_label = ctk.CTkLabel(self.sidebar_frame, text="HP: ?", text_color="green")
        self.hp_label.grid(row=4, column=0, padx=20, pady=5)

        self.energy_label = ctk.CTkLabel(self.sidebar_frame, text="Energy: ?", text_color="cyan")
        self.energy_label.grid(row=5, column=0, padx=20, pady=5)

        self.target_label = ctk.CTkLabel(self.sidebar_frame, text="Target: -")
        self.target_label.grid(row=6, column=0, padx=20, pady=5)

        self.ocr_label = ctk.CTkLabel(self.sidebar_frame, text="OCR: loading", text_color="gray")
        self.ocr_label.grid(row=7, column=0, padx=20, pady=5)

        hotkeys = self.bot.settings.get("hotkeys", {})
        self.hotkey_label = ctk.CTkLabel(self.sidebar_frame, justify="left", text_color="gray",
                                         text=f"Pause: {hotkeys.get('pause', '-')}\nQuit: {hotkeys.get('quit', '-')}")
        self.hotkey_label.grid(row=9, column=0, padx=20, pady=(5, 20), sticky="s")

        # Main area (Log and Settings)
        self.main_tabview = ctk.CTkTabview(self)
        self.main_tabview.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")

        self.tab_logs = self.main_tabview.add("Logs")
        self.tab_settings = self.main_tabview.add("Settings")

        # Logs tab
        self.tab_logs.grid_columnconfigure(0, weight=1)
        self.tab_logs.grid_rowconfigure(0, weight=1)

        self.log_textbox = ctk.CTkTextbox(self.tab_logs, state="disabled", wrap="word")
        self.log_textbox.grid(row=0, column=0, sticky="nsew")
        for tag, color in LOG_COLORS.items():
            self.log_textbox.tag_config(tag, foreground=color)

        # Settings tab
        self.setup_settings_tab()

        # Start GUI update loop
        self.update_gui()

    def setup_settings_tab(self):
        # Settings don't change often, a plain frame is much lighter than a scrollable one
        self.settings_frame = ctk.CTkFrame(self.tab_settings, fg_color="transparent")
        self.settings_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Priority list
        self.priority_label = ctk.CTkLabel(self.settings_frame, text="Priority List (Top = Highest):", font=ctk.CTkFont(weight="bold"))
        self.priority_label.pack(anchor="w", pady=(0, 5))

        self.priority_list = list(self.bot.objectPrio)
        self.prio_frame = ctk.CTkFrame(self.settings_frame)
        self.prio_frame.pack(fill="x", pady=5)
        self.render_priority_list()

        # Simple inputs
        self.inputs_frame = ctk.CTkFrame(self.settings_frame, fg_color="transparent")
        self.inputs_frame.pack(fill="x", pady=10)
        self.inputs_frame.grid_columnconfigure(1, weight=1)

        self.vars = {}
        fields = [
            ("healOnHp", "Heal on HP <= %:"),
            ("defendOnHp", "Defend on HP <= %:"),
            ("runOnHp", "Run on HP <= %:"),
            ("fleeUntilHp", "Stop running at HP >= %:"),
            ("lowEnergy", "Low Energy Alert:"),
            ("colorTolerance", "Minimap Color Tolerance:"),
        ]
        for row, (key, text) in enumerate(fields):
            var = ctk.StringVar(value=str(getattr(self.bot, key)))
            self.vars[key] = var
            ctk.CTkLabel(self.inputs_frame, text=text).grid(row=row, column=0, padx=5, pady=4, sticky="w")
            ctk.CTkEntry(self.inputs_frame, textvariable=var).grid(row=row, column=1, padx=5, pady=4, sticky="ew")

        # skillset (dropdown)
        preset_names = list(self.bot.presets.keys())
        self.skillset_var = ctk.StringVar(value=self.bot.skillset_name)
        row = len(fields)
        ctk.CTkLabel(self.inputs_frame, text="Skillset Preset:").grid(row=row, column=0, padx=5, pady=4, sticky="w")
        self.skillset_menu = ctk.CTkOptionMenu(self.inputs_frame, values=preset_names, variable=self.skillset_var)
        self.skillset_menu.grid(row=row, column=1, padx=5, pady=4, sticky="ew")

        # Save button
        self.save_btn = ctk.CTkButton(self.settings_frame, text="Save Settings", command=self.save_settings)
        self.save_btn.pack(pady=10)

    def render_priority_list(self):
        # Clear frame
        for widget in self.prio_frame.winfo_children():
            widget.destroy()

        for i, item in enumerate(self.priority_list):
            row_frame = ctk.CTkFrame(self.prio_frame, fg_color="transparent")
            row_frame.pack(fill="x", pady=2)

            lbl = ctk.CTkLabel(row_frame, text=f"{i+1}. {item}")
            lbl.pack(side="left", padx=10)

            # Down button
            if i < len(self.priority_list) - 1:
                btn_down = ctk.CTkButton(row_frame, text="v", width=30, command=lambda idx=i: self.move_prio(idx, 1))
                btn_down.pack(side="right", padx=2)
            else:
                # Placeholder for alignment
                ctk.CTkFrame(row_frame, width=34, height=28, fg_color="transparent").pack(side="right", padx=2)

            # Up button
            if i > 0:
                btn_up = ctk.CTkButton(row_frame, text="^", width=30, command=lambda idx=i: self.move_prio(idx, -1))
                btn_up.pack(side="right", padx=2)
            else:
                ctk.CTkFrame(row_frame, width=34, height=28, fg_color="transparent").pack(side="right", padx=2)

    def move_prio(self, index, direction):
        new_index = index + direction
        # Swap
        self.priority_list[index], self.priority_list[new_index] = self.priority_list[new_index], self.priority_list[index]
        self.render_priority_list()

    def toggle_start(self):
        if not self.bot.ocr_ready:
            return

        if self.bot.stopped:
            self.bot.start()
            self.start_btn.configure(text="Stop Bot", fg_color="red", hover_color="darkred")
            self.pause_btn.configure(state="normal", text="Pause Bot", **DEFAULT_BTN)
        else:
            self.bot.stop()
            self.start_btn.configure(text="Start Bot", **DEFAULT_BTN)
            self.pause_btn.configure(state="disabled", text="Pause Bot", **DEFAULT_BTN)
            self.log_message("Bot stopped.", "system")

    def toggle_pause(self):
        if self.bot.stopped:
            return
        if not self.bot.paused:
            self.bot.set_paused(True)
            self.pause_btn.configure(text="Resume Bot", fg_color="orange", hover_color="darkorange")
            self.log_message("Bot paused.", "system")
        else:
            self.bot.set_paused(False)
            self.pause_btn.configure(text="Pause Bot", **DEFAULT_BTN)
            self.log_message("Bot resumed.", "system")

    def save_settings(self):
        try:
            values = {key: int(var.get()) for key, var in self.vars.items()}
        except ValueError:
            self.log_message("[System] Error saving settings: Make sure all text fields contain valid numbers.", "danger")
            return

        if not (0 <= values["runOnHp"] < values["healOnHp"] <= 100 and values["runOnHp"] < values["fleeUntilHp"] <= 100
                and 0 <= values["defendOnHp"] <= 100):
            self.log_message("[System] Error saving settings: Use 0 <= Run < Heal <= 100, Run < Stop running <= 100 and Defend <= 100.", "danger")
            return
        if not 0 <= values["colorTolerance"] <= 60:
            self.log_message("[System] Error saving settings: Color tolerance must be between 0 and 60.", "danger")
            return

        try:
            with open(self.settings_path, 'r') as f:
                settings = json.load(f)
        except (OSError, ValueError):
            settings = dict(self.bot.settings)

        settings.update(values)
        settings["priority"] = list(self.priority_list)
        settings["skillset"] = self.skillset_var.get()
        settings.pop("occasionalSkill", None)

        # Update bot instance
        self.bot.apply_settings(settings)

        try:
            with open(self.settings_path, 'w') as f:
                json.dump(settings, f, indent=4)
        except OSError as e:
            self.log_message(f"[System] Error writing settings.json: {e}", "danger")
            return
        self.log_message("[System] Settings saved successfully.", "info")

    def log_message(self, message, msg_type="text"):
        self.log_textbox.configure(state="normal")
        self.log_textbox.insert("end", message + "\n", msg_type if msg_type in LOG_COLORS else ())
        # Keep the log short, a huge textbox slows the whole GUI down over time
        lines = int(self.log_textbox.index("end-1c").split(".")[0])
        if lines > MAX_LOG_LINES:
            self.log_textbox.delete("1.0", f"{lines - MAX_LOG_LINES}.0")
        self.log_textbox.see("end")
        self.log_textbox.configure(state="disabled")

    def update_gui(self):
        """Constantly update GUI from bot's state without freezing"""
        try:
            # Hotkey commands
            while True:
                try:
                    cmd = self.command_queue.get_nowait()
                except queue.Empty:
                    break
                if cmd == "pause":
                    self.toggle_pause()

            # Log messages from bot threads
            for _ in range(100):
                try:
                    message, msg_type = self.bot.log_queue.get_nowait()
                except queue.Empty:
                    break
                self.log_message(message, msg_type)

            # Update OCR Loading state
            if self.bot.ocr_ready and self.start_btn.cget("text") == "Loading OCR...":
                self.start_btn.configure(text="Start Bot", state="normal")
            self.set_text(self.ocr_label, f"OCR: {self.bot.ocr_device}")

            # Update State/HP/Energy
            if self.bot.stopped:
                state_str = "STOPPED"
            elif self.bot.paused:
                state_str = "PAUSED"
            else:
                state_str = self.bot.state_name
            self.set_text(self.state_label, f"State: {state_str}")

            hp = self.bot.plr_hp
            hp_color = "green"
            if hp is not None and hp <= self.bot.healOnHp:
                hp_color = "red"
            elif hp is not None and hp <= self.bot.defendOnHp:
                hp_color = "orange"
            self.set_text(self.hp_label, f"HP: {'?' if hp is None else hp}", hp_color)

            energy = self.bot.plr_energy
            self.set_text(self.energy_label, f"Energy: {'?' if energy is None else energy}")

            targets = self.bot.targets
            self.set_text(self.target_label, f"Target: {targets[2]} ({self.bot.objectCount})" if targets else "Target: -")
        except Exception:
            pass
        self.after(100, self.update_gui)

    def set_text(self, label, text, color=None):
        # Only reconfigure when something changed, CTk redraws are expensive
        if label.cget("text") != text or (color and label.cget("text_color") != color):
            if color:
                label.configure(text=text, text_color=color)
            else:
                label.configure(text=text)

    def on_closing(self):
        self.bot.stop()
        self.destroy()
