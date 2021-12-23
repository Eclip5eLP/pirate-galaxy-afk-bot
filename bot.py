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
from colorama import Fore, Back, Style
from PIL import Image
from win32api import GetSystemMetrics
import cv2 as cv
import pyautogui
import colorama
import keyboard
import random
import win32api, win32ui, win32con
import requests
import json
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

	appName = "Unknown"
	version = "0"
	pytesseract.pytesseract.tesseract_cmd = ""
	conApi = ""
	minimapLoc = [0,0]
	skills = []
	updated = False

	plr_name = ""
	plr_energy = 0
	plr_hp = 0
	outliers = [0,0,0,0]
	lastChat = []
	objectCount = 0
	objectPrio = []
	objectPixel = []
	healOnHp = 0
	defendOnHp = 0
	runOnHp = 0
	lowEnergy = 0
	showTechUsage = False

	targets = False
	lastPrint = "";

	techTree = {"aoe": ["rocket", "orbitalstrike", "aggrobomb", "mine", "stundome", "stickybomb", "magnettrap"], "defend": ["shield", "protector", "scramble", "aggrobeacon"], "single": ["rocket", "orbitalstrike", "stun", "thermoblast", "taunt", "sniper", "attackdroid"], "buff": ["speedactuator", "aimcomp", "perforator", "dmgbuff"]}

	# Init
	def __init__(self, settings, appName, version):
		self.lock = Lock()

		self.state = BotState.INIT
		self.timestamp = time()
		self.updated = True
		self.ws = "                     "

		self.version = version
		pytesseract.pytesseract.tesseract_cmd = settings['tesseract']

		self.appName = appName
		self.conApi = settings['conApi']
		self.minimapLoc = [0,0]
		presets = settings['skills']
		self.skills = presets[settings['skillset']]

		self.plr_name = settings['username']
		self.plr_energy = 0
		self.plr_hp = 0
		self.outliers = [0,0,0,0]
		self.lastChat = []
		self.objectCount = 0
		self.objectPrio = settings['priority']
		self.objectPixel = settings['search']
		self.healOnHp = settings['healOnHp']
		self.defendOnHp = settings['defendOnHp']
		self.runOnHp = settings['runOnHp']
		self.lowEnergy = settings['lowEnergy']
		self.showTechUsage = settings['showTechUsage']

	# Find targets on minimap
	def update_targets(self):
		targets = self.findObject(True)
		self.lock.acquire()
		self.targets = targets
		self.updated = True
		self.lock.release()

		if self.state == BotState.FARMING:
			if self.targets != False:
				self.moveTo(self.targets)
				self.interact(self.targets[2])

	# Start the bot
	def start(self):
		self.stopped = False
		t = Thread(target=self.run)
		t.start()
		print(Fore.GREEN + "Bot started" + Fore.WHITE)

	# Stop the bot
	def stop(self):
		self.stopped = True

	# Main Bot Logic
	def run(self):
		while not self.stopped:
			if self.state == BotState.INIT: # Initializing
				if time() > self.timestamp + self.INIT_TIME:
					self.lock.acquire()
					self.state = BotState.FARMING
					self.lock.release()

			elif self.state == BotState.FARMING: # Farming
				# Chat Decoy
				#self.checkChat()

				# Check Energy
				if self.checkEnergy(self.lowEnergy):
					#self.findEnergy()
					self.terminal(Fore.LIGHTRED_EX + 'Low Energy! (' + str(self.plr_energy) + ')' + Fore.WHITE + self.ws)

				self.checkHP()

				#self.update_targets()

				# Battle and Collect
				if self.targets != False:
					if self.updated:
						self.moveTo(self.targets)
						self.lock.acquire()
						self.updated = False
						self.lock.release()
					self.interact(self.targets[2])

			elif self.state == BotState.FLEEING: # Fleeing
				self.checkHP()

				if self.checkSkill("afterburner"):
					self.skill(self.checkSkill("afterburner"))

				if self.plr_hp >= math.ceil(self.healOnHp / 2):
					self.lock.acquire()
					self.state = BotState.FARMING
					self.lock.release()

	# Scripts #

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
			if listAll != []:
				return listAll
			else:
				return False
		return False

	# Find Object on Minimap
	def minimapFind(self, find, nearest = False):
		elist = []
		minimap = self.search('minimap')
		if minimap != False:
			self.minimapLoc = [minimap.left + 25, minimap.top - 100]
			minimap = pyautogui.screenshot('./data/search/minimap.png', region=(minimap.left + 25, minimap.top - 100, 115, 115))
			found = self.imgFindPixel(minimap, find, nearest)
			if found != False:
				if nearest == False:
					return found
				else:
					elist = found
			else:
				return False
		else:
			return False

		# Return nearest
		self.objectCount = len(elist)
		center = [115 / 2, 115 / 2]
		near = []
		for loc in elist:
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

	# Check Energy and notify User
	def checkEnergy(self, num):
		find = self.search('energy', 0.7)
		if find != False:
			cenergy = pyautogui.screenshot('./data/search/energy.png', region=(find.left - 100, find.top, 100, 20))
			cenergy = self.getNum(Image.open('./data/search/energy.png')).replace('\x0c', '').replace('\n', '').replace(',','')
			if cenergy == '':
				cenergy = 10000
			else:
				cenergy = int(cenergy)

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
			self.terminal(Fore.LIGHTRED_EX + "Cant find Interface" + Fore.WHITE + self.ws)
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
		find = self.search('minimap')
		if find != False:
			chp = pyautogui.screenshot('./data/search/hp.png', region=(find.left - 25, find.top + 5, 20, 15))
			newImg = Image.new('RGB', (2*chp.size[0], chp.size[1]), (250,250,250))
			newImg.paste(chp,(0,0))
			newImg.paste(chp,(chp.size[0],0))
			newImg.save("./data/search/hp.png", "PNG")

			chp = self.getNum(Image.open('./data/search/hp.png')).replace('\n', '').replace('\x0c', '').replace('|', '')
			chp = chp[0:int(len(chp)/2)]
			if chp != '':
				chp = int(chp)

				if chp == 1 or chp == 2:
					return False

				self.lock.acquire()
				self.plr_hp = chp
				self.lock.release()

				if (chp <= self.healOnHp):
					self.skill(3)
					if self.showTechUsage:
						print(Fore.LIGHTCYAN_EX + "Used Repair droid" + Fore.WHITE + self.ws)
					self.terminal(Fore.LIGHTRED_EX + "Low HP (" + str(self.plr_hp) + ")" + Fore.WHITE + self.ws)
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
			if self.checkSkill("collector"): #Collector
				self.skill(self.checkSkill("collector"))

		# Attack Enemy
		if act == "enemy" or act == "enemyIdle":

			# AOE Attacks
			techs = []
			for tech in self.techTree["aoe"]:
				if self.checkSkill(tech):
					techs.append(tech)
			if self.objectCount >= 5 and len(techs) > 0:
				use = techs[random.randint(0, len(techs) - 1)]
				self.skill(self.checkSkill(use))
				if self.showTechUsage:
					print(Fore.LIGHTCYAN_EX + "Used " + use + Fore.WHITE + self.ws)

			# Defend
			techs = []
			for tech in self.techTree["defend"]:
				if self.checkSkill(tech):
					techs.append(tech)
			if self.plr_hp <= self.defendOnHp and len(techs) > 0:
				use = techs[random.randint(0, len(techs) - 1)]
				self.skill(self.checkSkill(use))
				if self.showTechUsage:
					print(Fore.LIGHTCYAN_EX + "Used " + use + Fore.WHITE + self.ws)

			# Occasional Attacks
			techs = []
			for tech in self.techTree["single"]:
				if self.checkSkill(tech):
					techs.append(tech)
			if random.randint(1, 250) == 1 and len(techs) > 0:
				use = techs[random.randint(0, len(techs) - 1)]
				self.skill(self.checkSkill(use))
				if self.showTechUsage:
					print(Fore.LIGHTCYAN_EX + "Used " + use + Fore.WHITE + self.ws)

			# Occasional Buffs
			techs = []
			for tech in self.techTree["buff"]:
				if self.checkSkill(tech):
					techs.append(tech)
			if random.randint(1, 250) == 1 and len(techs) > 0:
				use = techs[random.randint(0, len(techs) - 1)]
				self.skill(self.checkSkill(use))
				if self.showTechUsage:
					print(Fore.LIGHTCYAN_EX + "Used " + use + Fore.WHITE + self.ws)

			# Run
			if self.plr_hp <= self.runOnHp:
				#self.terminal(Fore.LIGHTRED_EX + "Running away..." + Fore.WHITE + self.ws)
				self.lock.acquire()
				self.state = BotState.FLEEING
				self.lock.release()

			# Always Attack fallback
			self.skill(1)

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
		find = self.search('chatWindow')
		if find != False:
			_screenImg = pyautogui.screenshot('./data/search/skills.png', region=(find.left, find.top + 25, 380, 50))
			keyboard.press(str(num))
			sleep(0.1)
			keyboard.release(str(num))
		else:
			return False

	# Check Chat for Username
	def checkChat(self):
		find = self.search('mail')
		if find != False:
			chat = pyautogui.screenshot('./data/search/chat.png', region=(find.left, find.top + 50, 300, GetSystemMetrics(1) * 0.75))
			chat = self.getText(Image.open('./data/search/chat.png')).replace('\x0c', '').replace('|', '')
			for msg in self.lastChat:
				if len(msg) >= 4:
					chat = chat.replace(msg, '')
			if self.plr_name in chat:
				self.chatSend("hey")

			self.lock.acquire()
			self.lastChat.append(chat)
			self.lock.release()

			return True
		else:
			return False

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
	def terminal(self, text):
		if text != self.lastPrint:
			print(text)

			self.lock.acquire()
			self.lastPrint = text
			self.lock.release()

			if self.conApi != "":
				apiCall = self.conApi + "?app=" + self.appName + "&log=" + text
				response = requests.get(apiCall)
				return response
		return None