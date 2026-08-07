import customtkinter as ctk
import threading
import json
from time import sleep

# Set appearance mode and color theme
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

class App(ctk.CTk):
    def __init__(self, bot_instance):
        super().__init__()
        
        self.bot = bot_instance
        
        self.title("Pirate Galaxy Bot")
        self.geometry("900x600")
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Configure grid layout
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # Sidebar for controls
        self.sidebar_frame = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(5, weight=1)
        
        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="PGBot Dashboard", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))
        
        self.start_btn = ctk.CTkButton(self.sidebar_frame, text="Loading OCR...", command=self.toggle_start, state="disabled")
        self.start_btn.grid(row=1, column=0, padx=20, pady=10)
        
        self.pause_btn = ctk.CTkButton(self.sidebar_frame, text="Pause Bot", command=self.toggle_pause, state="disabled")
        self.pause_btn.grid(row=2, column=0, padx=20, pady=10)
        
        self.state_label = ctk.CTkLabel(self.sidebar_frame, text="State: INIT")
        self.state_label.grid(row=3, column=0, padx=20, pady=10)
        
        self.hp_label = ctk.CTkLabel(self.sidebar_frame, text="HP: 100", text_color="green")
        self.hp_label.grid(row=4, column=0, padx=20, pady=10)
        
        self.energy_label = ctk.CTkLabel(self.sidebar_frame, text="Energy: 10000", text_color="cyan")
        self.energy_label.grid(row=5, column=0, padx=20, pady=10, sticky="n")
        
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
        
        # Settings tab
        self.setup_settings_tab()
        
        # Start GUI update loop
        self.update_gui()
        
    def setup_settings_tab(self):
        # We will use a scrollable frame for settings
        self.settings_scroll = ctk.CTkScrollableFrame(self.tab_settings)
        self.settings_scroll.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Priority list
        self.priority_label = ctk.CTkLabel(self.settings_scroll, text="Priority List (Top = Highest):", font=ctk.CTkFont(weight="bold"))
        self.priority_label.pack(anchor="w", pady=(10, 5))
        
        self.priority_list = list(self.bot.objectPrio)
        self.prio_frame = ctk.CTkFrame(self.settings_scroll)
        self.prio_frame.pack(fill="x", pady=5)
        self.render_priority_list()
        
        # Simple inputs
        self.inputs_frame = ctk.CTkFrame(self.settings_scroll, fg_color="transparent")
        self.inputs_frame.pack(fill="x", pady=15)
        self.inputs_frame.grid_columnconfigure(1, weight=1)
        
        # healOnHp
        self.heal_var = ctk.StringVar(value=str(self.bot.healOnHp))
        ctk.CTkLabel(self.inputs_frame, text="Heal on HP <= %:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        ctk.CTkEntry(self.inputs_frame, textvariable=self.heal_var).grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        
        # defendOnHp
        self.defend_var = ctk.StringVar(value=str(self.bot.defendOnHp))
        ctk.CTkLabel(self.inputs_frame, text="Defend on HP <= %:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        ctk.CTkEntry(self.inputs_frame, textvariable=self.defend_var).grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        
        # runOnHp
        self.run_var = ctk.StringVar(value=str(self.bot.runOnHp))
        ctk.CTkLabel(self.inputs_frame, text="Run on HP <= %:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        ctk.CTkEntry(self.inputs_frame, textvariable=self.run_var).grid(row=2, column=1, padx=5, pady=5, sticky="ew")
        
        # lowEnergy
        self.energy_var = ctk.StringVar(value=str(self.bot.lowEnergy))
        ctk.CTkLabel(self.inputs_frame, text="Low Energy Alert:").grid(row=3, column=0, padx=5, pady=5, sticky="w")
        ctk.CTkEntry(self.inputs_frame, textvariable=self.energy_var).grid(row=3, column=1, padx=5, pady=5, sticky="ew")
        
        # occasionalSkill
        self.occasional_var = ctk.StringVar(value=str(self.bot.occasionalSkill))
        ctk.CTkLabel(self.inputs_frame, text="Occasional Skill Rate (1 in X):").grid(row=4, column=0, padx=5, pady=5, sticky="w")
        ctk.CTkEntry(self.inputs_frame, textvariable=self.occasional_var).grid(row=4, column=1, padx=5, pady=5, sticky="ew")
        
        # skillset (dropdown)
        preset_names = list(self.bot.presets.keys())
        self.skillset_var = ctk.StringVar(value=self.bot.skillset_name)
        ctk.CTkLabel(self.inputs_frame, text="Skillset Preset:").grid(row=5, column=0, padx=5, pady=5, sticky="w")
        self.skillset_menu = ctk.CTkOptionMenu(self.inputs_frame, values=preset_names, variable=self.skillset_var)
        self.skillset_menu.grid(row=5, column=1, padx=5, pady=5, sticky="ew")
        
        # Save button
        self.save_btn = ctk.CTkButton(self.settings_scroll, text="Save Settings", command=self.save_settings)
        self.save_btn.pack(pady=20)
        
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
            self.pause_btn.configure(state="normal")
            self.log_message("Bot started.", "system")
        else:
            self.bot.stop()
            self.start_btn.configure(text="Start Bot", fg_color=["#3B8ED0", "#1F6AA5"], hover_color=["#36719F", "#144870"])
            self.pause_btn.configure(state="disabled", text="Pause Bot")
            self.log_message("Bot stopped.", "system")
            
    def toggle_pause(self):
        if not self.bot.paused:
            self.bot.paused = True
            self.pause_btn.configure(text="Resume Bot", fg_color="orange", hover_color="darkorange")
            self.log_message("Bot paused.", "system")
        else:
            self.bot.paused = False
            self.pause_btn.configure(text="Pause Bot", fg_color=["#3B8ED0", "#1F6AA5"], hover_color=["#36719F", "#144870"])
            self.log_message("Bot resumed.", "system")
            
    def save_settings(self):
        try:
            heal = int(self.heal_var.get())
            defend = int(self.defend_var.get())
            run = int(self.run_var.get())
            energy = int(self.energy_var.get())
            occasional = int(self.occasional_var.get())
            skillset = self.skillset_var.get()
            
            # Update bot instance
            self.bot.healOnHp = heal
            self.bot.defendOnHp = defend
            self.bot.runOnHp = run
            self.bot.lowEnergy = energy
            self.bot.occasionalSkill = occasional
            self.bot.skillset_name = skillset
            self.bot.skills = self.bot.presets[skillset]
            self.bot.objectPrio = list(self.priority_list)
            
            # Save to JSON
            with open('settings.json', 'r') as f:
                settings = json.load(f)
                
            settings["priority"] = self.priority_list
            settings["healOnHp"] = heal
            settings["defendOnHp"] = defend
            settings["runOnHp"] = run
            settings["lowEnergy"] = energy
            settings["occasionalSkill"] = occasional
            settings["skillset"] = skillset
            
            with open('settings.json', 'w') as f:
                json.dump(settings, f, indent=4)
                
            self.log_message("[System] Settings saved successfully.", "info")
        except ValueError:
            self.log_message("[System] Error saving settings: Make sure all text fields contain valid numbers.", "danger")
            
    def log_message(self, message, msg_type="text"):
        self.log_textbox.configure(state="normal")
        self.log_textbox.insert("end", message + "\n")
        self.log_textbox.see("end")
        self.log_textbox.configure(state="disabled")

    def update_gui(self):
        """Constantly update GUI from bot's state without freezing"""
        try:
            if hasattr(self, 'bot'):
                # Update OCR Loading state
                if not self.bot.ocr_ready:
                    pass # Button already says Loading OCR...
                elif self.start_btn.cget("text") == "Loading OCR...":
                    self.start_btn.configure(text="Start Bot", state="normal")
                
                # Update HP/Energy
                state_str = "INIT"
                if self.bot.state == 1: state_str = "FARMING"
                elif self.bot.state == 2: state_str = "FLEEING"
                
                self.state_label.configure(text=f"State: {state_str}")
                self.hp_label.configure(text=f"HP: {self.bot.plr_hp}")
                self.energy_label.configure(text=f"Energy: {self.bot.plr_energy}")
        except Exception:
            pass
        self.after(500, self.update_gui)
            
    def on_closing(self):
        self.bot.stop()
        self.destroy()
