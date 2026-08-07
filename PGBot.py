###################
# Made by Eclip5e #
###################
import sys
import json
import threading
import time
import keyboard
import cv2 as cv
from bot import PGBot
from gui import App

sys.dont_write_bytecode = True

def main():
    # Load Settings
    try:
        with open('settings.json') as f:
            settings = json.load(f)
    except FileNotFoundError:
        print("settings.json not found! Please create it.")
        return

    # Vars
    version = '0.4.1'
    appName = 'Pirate Galaxy Bot'

    # Initialize Bot
    bot = PGBot(settings, appName, version)

    # Initialize GUI
    app = App(bot)
    
    # Set the callback so the bot can log to the GUI
    bot.set_gui_callback(app.log_message)

    def background_loop():
        while True:
            # Check if app is destroyed
            if not hasattr(app, 'winfo_exists') or not app.winfo_exists():
                break

            if not bot.paused and not bot.stopped:
                # Update bots targets
                bot.update_targets()

            time.sleep(0.1)

    # Use keyboard hooks for instant response
    def on_quit():
        import os
        os._exit(0)

    def on_pause():
        app.after(0, app.toggle_pause)

    keyboard.add_hotkey('q', on_quit)
    keyboard.add_hotkey('p', on_pause)

    t = threading.Thread(target=background_loop, daemon=True)
    t.start()
    
    # Start the App
    app.mainloop()

if __name__ == "__main__":
    main()