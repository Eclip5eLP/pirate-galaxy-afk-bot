###################
# Made by Eclip5e #
###################

# Check installed Modules
import re, sys, os
import subprocess
import pkg_resources

sys.dont_write_bytecode = True

from importer import Importer
Importer.verifyLibs({'pyautogui', 'keyboard', 'colorama', 'datetime', 'requests', 'pytesseract', 'opencv-python', 'pypiwin32'})

# Import Modules
from colorama import Fore, Back, Style
from bot import PGBot, BotState
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
version = '0.3.1'
appName = 'Pirate Galaxy Bot'

colorama.init()
bot = PGBot(settings, appName, version)

# Start Bot
bot.terminal(f'{appName} v{version}', 'info')
bot.terminal('Made by Eclip5e\n', 'info')
bot.terminal('Initializing...')

sleep(1)
bot.start()

# Main Loop
loop_time = time()
while(True):
	if not bot.paused:
		# Update bots targets
		bot.update_targets()

		# Show FPS
		#print('FPS {}'.format(1 / (time() - loop_time)))
		loop_time = time()

		# Print HP and Energy
		print(f'{Fore.GREEN}HP: {bot.plr_hp} | {Fore.LIGHTCYAN_EX}Energy: {bot.plr_energy}{Fore.WHITE}{bot.ws}', end='\r')
	else:
		sleep(0.2)

	# Hotkeys
	if keyboard.is_pressed('q'): # Quit
		bot.stop()
		cv.destroyAllWindows()
		break
	if keyboard.is_pressed('p'): # Pause
		if bot.paused:
			bot.paused = False
			print(f'{Fore.LIGHTCYAN_EX}Unpaused{Fore.WHITE}{bot.ws}', end='\r')
			sleep(1)
		else:
			bot.paused = True
			print(f'{Fore.LIGHTCYAN_EX}Paused{Fore.WHITE}{bot.ws}', end='\r')
			sleep(1)

# Quit Application
bot.terminal(f'\nQuit', 'danger')