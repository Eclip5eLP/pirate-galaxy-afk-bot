###################
# Made by Eclip5e #
###################

# Check installed Modules
import re, sys, os
import subprocess
import pkg_resources

sys.dont_write_bytecode = True

from importer import Importer
Importer.verifyLibs({'pyautogui', 'keyboard', 'colorama', 'datetime', 'requests', 'pytesseract', 'opencv-python'})

# Import Modules
from colorama import Fore, Back, Style
from bot import PGBot, BotState
from windowcapture import WindowCapture
from time import sleep, time
import colorama
import pyautogui
import json
import keyboard
import cv2 as cv
import numpy as np

# Load Settings
with open('settings.json') as f:
	settings = json.load(f)

# Vars
version = "0.2.1"
appName = "Pirate Galaxy Bot"

colorama.init()
wincap = WindowCapture()
bot = PGBot(settings, appName, version)
paused = False

# Start Bot
bot.terminal(appName + " v" + version + "\n")
bot.terminal("Made by Eclip5e\n")
bot.terminal("Initializing...")

sleep(1)
bot.start()

# Main Loop
loop_time = time()
while(True):
	if not paused:
		# Update bots targets
		bot.update_targets()

		# Show FPS
		#print('FPS {}'.format(1 / (time() - loop_time)))
		loop_time = time()

		# Print HP and Energy
		print(Fore.GREEN + "HP: " + str(bot.plr_hp) + " | " + Fore.LIGHTCYAN_EX + "Energy: " + str(bot.plr_energy) + Fore.WHITE + bot.ws, end="\r")

	# Hotkeys
	if keyboard.is_pressed('q'): # Quit
		bot.stop()
		cv.destroyAllWindows()
		break
	if keyboard.is_pressed('p'): # Pause
		if paused:
			paused = False
			print(Fore.LIGHTCYAN_EX + "Unpaused" + Fore.WHITE + bot.ws)
			sleep(1)
		else:
			paused = True
			print(Fore.LIGHTCYAN_EX + "Paused" + Fore.WHITE + bot.ws)
			sleep(1)

# Quit Application
bot.terminal(Fore.LIGHTRED_EX + "\nQuit" + Fore.WHITE)