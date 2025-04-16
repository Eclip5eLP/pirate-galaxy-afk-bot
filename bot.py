#!python3
###################
# Made by Eclip5e #
###################

import re, sys, os
import subprocess
import pkg_resources

sys.dont_write_bytecode = True

from time import sleep, time
from threading import Thread, Lock
from colorama import Fore
from PIL import Image
from pathlib import Path
import datetime
import cv2 as cv
import pyautogui
import colorama
import keyboard
import random
import win32api, win32ui, win32con
import pytesseract
import numpy as np
import math

class BotState:
	INIT = 0
	FARMING = 1
	FLEEING = 2

class PGBot:

	INIT_TIME = 2

	stopped = True
	lock = None

	state = None
	timestamp = None

	appName = 'UnknownAppOrigin'
	version = '0.1'
	pytesseract.pytesseract.tesseract_cmd = ''
	minimapLoc = [0,0]
	updated = False
	paused = False

	plr_energy = 0
	plr_hp = 0
	dtime = [0,0,0,0,0] # Energy, HP, Map, Collector, NavMenu
	outliers = [0,0,0,0]
	lastChat = []

	targets = False
	lastPrint = '';
	ws = "                     "

	techTree = {"aoe": ["rocket", "orbitalstrike", "aggrobomb", "mine", "stundome", "stickybomb", "magnettrap", "aggrobeacon"], "defend": ["shield", "protector", "scramble"], "single": ["rocket", "orbitalstrike", "stun", "thermoblast", "taunt", "sniper", "attackdroid"], "buff": ["speedactuator", "aimcomp", "perforator", "dmgbuff"]}

	# Init
	def __init__(self, settings, appName, version):
		self.lock = Lock()

		self.state = BotState.INIT
		self.timestamp = time()
		self.updated = True

		self.version = version
		pytesseract.pytesseract.tesseract_cmd = settings.get('tesseract', "C:/Program Files/Tesseract-OCR/tesseract.exe")

		self.appName = appName
		self.minimapLoc = [0,0]
		presets = settings.get('presets', {"custom": ["blaster","collector","repair","afterburner","","","",""]})
		self.skills = presets[settings.get('skillset', 'custom')]

		self.plr_energy = 0
		self.plr_hp = 100
		self.outliers = [0,0,0,0]
		self.lastChat = []
		self.objectCount = 0
		self.objectPrio = settings.get('priority', ["enemy","loot","enemyIdle"])
		self.objectPixel = settings.get('search', {"enemy": [135,27,11],"enemyIdle": [162,151,15],"loot": [19,193,217]})
		self.healOnHp = settings.get('healOnHp', 25)
		self.defendOnHp = settings.get('defendOnHp', 45)
		self.runOnHp = settings.get('runOnHp', 10)
		self.lowEnergy = settings.get('lowEnergy', 1000)
		self.occasionalSkill = settings.get('occasionalSkill', 150)

		if not Path(pytesseract.pytesseract.tesseract_cmd).exists():
			self.terminal(f'Cant find pytesseract!', 'danger')
			exit()

	# Find targets on minimap
	def update_targets(self):
		if not self.checkTimePassed(2, 1):
			return

		targets = self.findObject(True)
		self.lock.acquire()
		self.targets = targets
		self.updated = True
		self.lock.release()

		# Check HP with updating and using resources
		if (self.plr_hp <= self.healOnHp):
			self.skill(self.checkSkill("repair"))

	# Start the bot
	def start(self):
		self.stopped = False
		t = Thread(target=self.run)
		t.start()
		print(f'{Fore.GREEN}Bot started{Fore.WHITE}')

	# Stop the bot
	def stop(self):
		self.stopped = True

	# Main Bot Logic
	def run(self):
		while not self.stopped:
			if self.paused: # Paused
				sleep(0.2)
				continue

			if self.state == BotState.INIT: # Initializing
				if time() > self.timestamp + self.INIT_TIME:
					self.lock.acquire()
					self.state = BotState.FARMING
					self.lock.release()

			elif self.state == BotState.FARMING: # Farming
				# Check Energy
				if self.checkTimePassed(0, 30):
					if self.checkEnergy():
						self.terminal(f'Low Energy! ({self.plr_energy})', 'danger')

				self.checkHP()

				# Check if Nav Menu is open
				if self.checkTimePassed(4, 45):
					if self.search('orbit') != False:
						navmenu = self.search('navmenu')
						if navmenu != False:
							self.click(navmenu.left + 5, navmenu.top + 5)

				# Battle and Collect
				if self.targets != False:
					# Ignore idle targets if energy is low or if below low hp threshold
					if self.targets[2] == 'enemyIdle' and (self.plr_energy <= self.lowEnergy or self.plr_hp <= self.healOnHp):
						continue

					# Use Collector to prevent softlock
					if self.checkTimePassed(3, 4):
						self.skill(self.checkSkill("collector"))

					try:
						if self.updated:
							self.moveTo(self.targets)
							self.lock.acquire()
							self.updated = False
							self.lock.release()
						self.interact(self.targets[2])
					except Exception:
						pass # Ignore

			elif self.state == BotState.FLEEING: # Fleeing
				self.checkHP()

				self.skill(self.checkSkill("afterburner"))
				self.skill(self.checkSkill("repair"))

				if self.plr_hp >= math.ceil(self.healOnHp / 2):
					self.lock.acquire()
					self.state = BotState.FARMING
					self.lock.release()

	#---# Helper Scripts #---#

	# Click Function
	def click(self, x,y):
		win32api.SetCursorPos((x,y))
		win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN,0,0)
		sleep(0.1)
		win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP,0,0)

	# Double Click
	def doubleclick(self, x,y):
		self.click(x,y)
		self.click(x,y)

	# Get Text from Image
	def getText(self, image):
		return pytesseract.image_to_string(image, lang='eng', config='--psm 6')

	# Get Numbers from Image
	def getNum(self, image):
		nums = pytesseract.image_to_string(image, config='-c tessedit_char_whitelist=0123456789')
		if nums == " ":
			nums = pytesseract.image_to_string(image, config='--psm 10 --oem 3 -c tessedit_do_invert=0 -c tessedit_char_whitelist=0123456789')
		if nums == " ":
			return "0"
		return nums

	# Check a Pixel for its RGB values
	def isPixel(self, x,y,c):
		if pyautogui.pixel(x,y)[0] == c[0] and pyautogui.pixel(x,y)[1] == c[1] and pyautogui.pixel(x,y)[2] == c[2]:
			return True
		return False

	# Find Pixel in Image
	def imgFindPixel(self, img, c, findAll = False):
		width, height = img.size
		listAll = []
		for x in range(width):
			for y in range(height):
				pix = img.getpixel((x,y))
				if pix[0] == c[0] and pix[1] == c[1] and pix[2] == c[2]:
					if findAll:
						listAll.append([x,y])
					else:
						return [x,y]
		if findAll:
			if len(listAll) != 0:
				return listAll
		return False

	# Find Object on Minimap
	def minimapFind(self, find, nearest = False):
		minimap = self.search('minimap')
		if minimap != False:
			self.minimapLoc = [minimap.left + 25, minimap.top - 100]
			minimap = pyautogui.screenshot('./data/search/minimap.png', region=(minimap.left + 25, minimap.top - 100, 115, 115))
			found = self.imgFindPixel(minimap, find, nearest)
			if found != False:
				if nearest == False:
					return found
			else:
				return False
		else:
			return False

		# Return nearest
		self.objectCount = len(found)
		center = [115 / 2, 115 / 2]
		near = []
		for loc in found:
			if near == []:
				near = loc
			else:
				new_dist = abs(loc[0] - center[0]) + abs(loc[1] - center[1])
				old_dist = abs(near[0] - center[0]) + abs(near[1] - center[1])
				if new_dist < old_dist:
					near = loc
		return near

	# Image recognition
	def search(self, img, conf=0.8):
		simg = pyautogui.locateOnScreen('./data/images/' + img + '.png', confidence=conf)
		if simg != None:
			return simg
		else:
			return False

	# Check Energy and notify User; returns true if energy is low or below num
	def checkEnergy(self, num = None):
		if num is None:
			num = self.lowEnergy

		find = self.search('energy', 0.72)
		if find != False:
			cenergy = pyautogui.screenshot('./data/search/energy.png', region=(find.left - 100, find.top, 100, 20))
			cenergy = self.getNum(Image.open('./data/search/energy.png')).replace('\x0c', '').replace('\n', '').replace(',','')
			if cenergy == '' or cenergy == ' ':
				cenergy = 10000
			else:
				try:
					cenergy = int(cenergy)
				except Exception:
					cenergy = 0

			# Statistical outliers
			if self.outliers[2] - cenergy >= 1000 and self.outliers[3] <= 2:
				cenergy = self.outliers[2]
				nout = self.outliers[3] + 1
			else:
				nout = 0

			self.lock.acquire()
			self.outliers[3] = nout
			self.plr_energy = cenergy
			self.outliers[2] = cenergy
			self.lock.release()

			if (cenergy <= num):
				return True
			return False
		else:
			#self.terminal('Cant find Interface', 'danger')
			self.plr_energy = 10000
			return False

	# Find Energy
	def findEnergy(self):
		return False

	# Find Objects
	def findObject(self, nearest = False):
		for obj in self.objectPrio:
			find = self.minimapFind(self.objectPixel[obj], nearest)
			if find != False:
				find.append(obj)
				return find

		self.objectCount = 0
		return False

	# Move to Position and avoid obstacles
	def moveTo(self, pos = False):
		if pos == False:
			return False

		# Obstacle evasion

		# Move
		self.click(self.minimapLoc[0] + pos[0] - 1, self.minimapLoc[1] + pos[1])

	# Check HP and heal if needed
	def checkHP(self):
		if not self.checkTimePassed(1, 2):
			if (self.plr_hp <= self.healOnHp):
				self.skill(self.checkSkill("repair"))
				return True
			return False

		find = self.search('minimap')
		if find != False:
			chp = pyautogui.screenshot('./data/search/hp.png', region=(find.left - 25, find.top + 5, 20, 15))
			newImg = Image.new('RGB', (2*chp.size[0], chp.size[1]), (250,250,250))
			newImg.paste(chp,(0,0))
			newImg.paste(chp,(chp.size[0],0))
			newImg.save("./data/search/hp.png", "PNG")

			chp = self.getNum(Image.open('./data/search/hp.png')).replace('\n', '').replace('\x0c', '').replace('|', '')
			chp = chp[0:int(len(chp)/2)]
			if chp != '' and chp != ' ':
				chp = int(chp)

				if chp == 1 or chp == 2:
					return False

				self.lock.acquire()
				self.plr_hp = chp
				self.lock.release()

				if (chp <= self.healOnHp):
					self.skill(self.checkSkill("repair"))
					#self.terminal(f'Low HP ({self.plr_hp})', 'danger')
					return True
			else:
				self.lock.acquire()
				self.plr_hp = 100
				self.lock.release()
			return False
		else:
			return False

	# Decide action based on findings
	def interact(self, act):
		# Collect Loot
		if act == "loot":
			self.skill(self.checkSkill("collector"))

		# Attack Enemy
		if act == "enemy" or act == "enemyIdle":

			# Interaction types
			self.interactType('aoe')
			self.interactType('defend')
			self.interactType('single')
			self.interactType('buff')

			# Run
			if self.plr_hp <= self.runOnHp:
				self.lock.acquire()
				self.state = BotState.FLEEING
				self.lock.release()

			# Always Attack fallback
			self.skill(1)

	# Interaction types
	def interactType(self, itype):
		techs = []
		for tech in self.techTree[itype]:
			if self.checkSkill(tech):
				techs.append(tech)

		cond_aoe = self.objectCount >= 3 and len(techs) > 0
		cond_defend = self.plr_hp <= self.defendOnHp and len(techs) > 0
		cond_occasion = random.randint(1, self.occasionalSkill) == 1 and len(techs) > 0

		if (itype == 'aoe' and cond_aoe) or (itype == 'defend' and cond_defend) or ((itype == 'single' or itype == 'buff') and cond_occasion):
			self.skill(self.checkSkill(techs[random.randint(0, len(techs) - 1)]))

	# Check if User has Skill
	def checkSkill(self, check):
		index = 1
		for a in self.skills:
			if check == a:
				return index
			index += 1
		return False

	# Use a Skill
	def skill(self, num):
		if num == False or num < 1 or num > 8:
			return False
		keyboard.press(str(num))
		sleep(0.1)
		keyboard.release(str(num))
		# find = self.search('chatWindow')
		# if find != False:
		# 	keyboard.press(str(num))
		# 	sleep(0.1)
		# 	keyboard.release(str(num))
		# else:
		# 	return False

	# Send Decoy Message
	def chatSend(self, msg):
		find = self.search('chatWindow')
		if find != False:
			self.click(find.left + 200, find.top + 5)
			keyboard.write(msg)
			keyboard.press('enter')
			sleep(0.1)
			keyboard.release('enter')

	# Print to local and remote Terminal
	def terminal(self, text, type='text'):
		col = Fore.WHITE
		if type == 'info':
			col = Fore.LIGHTCYAN_EX
		if type == 'warn':
			col = Fore.YELLOW
		if type == 'danger':
			col = Fore.LIGHTRED_EX

		ptext = f'{col}{text}{Fore.WHITE}{self.ws}'
		if text != self.lastPrint:
			print(ptext)

			self.lock.acquire()
			self.lastPrint = ptext
			self.lock.release()
		return True

	# Check time passed since last check
	def checkTimePassed(self, delta, secs):
		if self.dtime[delta] == 0:
			self.dtime[delta] = datetime.datetime.fromtimestamp(self.dtime[delta])
		if datetime.timedelta.total_seconds(datetime.datetime.now()-self.dtime[delta]) >= secs:
			self.dtime[delta] = datetime.datetime.now()
			return True
		return False