###################
# Made by Eclip5e #
###################
import sys
sys.dont_write_bytecode = True

import os
import json
import keyboard
from bot import PGBot, BASE_DIR
from gui import App

SETTINGS_PATH = os.path.join(BASE_DIR, 'settings.json')


def main():
    # Load Settings
    try:
        with open(SETTINGS_PATH) as f:
            settings = json.load(f)
    except FileNotFoundError:
        print("settings.json not found! Please create it.")
        return
    except ValueError as e:
        print(f"settings.json is not valid JSON: {e}")
        return

    # Vars
    version = '0.5.0'
    appName = 'Pirate Galaxy Bot'

    # Initialize Bot
    bot = PGBot(settings, appName, version)

    # Initialize GUI
    app = App(bot, SETTINGS_PATH)

    # Global hotkeys. Callbacks run on the keyboard thread, so they never touch Tk directly
    def on_quit():
        bot.stop()
        os._exit(0)

    def on_pause():
        app.command_queue.put("pause")

    hotkeys = bot.settings.get("hotkeys", {})
    try:
        keyboard.add_hotkey(hotkeys.get("quit", "ctrl+shift+q"), on_quit)
        keyboard.add_hotkey(hotkeys.get("pause", "ctrl+shift+p"), on_pause)
    except ValueError as e:
        print(f"Invalid hotkey in settings.json: {e}")
        return

    # Start the App
    app.mainloop()

    bot.stop()
    keyboard.unhook_all()
    os._exit(0)


if __name__ == "__main__":
    main()
