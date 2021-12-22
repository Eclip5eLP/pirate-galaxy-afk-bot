###################
# Made by Eclip5e #
###################

#Check installed Modules
from importer import Importer

Importer.verifyLibs({'pyautogui', 'keyboard', 'colorama', 'datetime', 'requests', 'pytesseract', 'opencv-python'})

#Import Modules
import pyautogui
from colorama import Fore, Back, Style
import colorama
from time import sleep, time
import json
import keyboard
import cv2 as cv
import numpy as np
from bot import PGBot, BotState
from windowcapture import WindowCapture

#Load Settings
with open('settings.json') as f:
	settings = json.load(f)

#Vars
version = "0.2"
appName = "Pirate Galaxy Bot"

colorama.init()
wincap = WindowCapture()
bot = PGBot(settings, appName, version)

#Start Bot
bot.terminal(appName + " v" + version + "\n")
bot.terminal("Made by Eclip5e\n")
bot.terminal("Initializing...")

sleep(1)
bot.start()

#Main Loop
loop_time = time()
while(True):
	if bot.objectCount >= 5:
		bot.terminal("Many Objects detected (" + str(bot.objectCount) + ")")

	bot.update_targets()

	#Show FPS
	#print('FPS {}'.format(1 / (time() - loop_time)))
	loop_time = time()

	#Hotkeys
	if keyboard.is_pressed('q'):
		bot.stop()
		cv.destroyAllWindows()
		break

#Quit Application
bot.terminal(Fore.LIGHTRED_EX + "Quit" + Fore.WHITE)