#!python3
###################
# Made by Eclip5e #
###################

import sys, os
from time import sleep, time
from threading import Thread, Lock
from pathlib import Path
import datetime
import cv2 as cv
import numpy as np
import math
import mss
import keyboard
import win32api, win32con
import easyocr
import random

sys.dont_write_bytecode = True

class BotState:
    INIT = 0
    FARMING = 1
    FLEEING = 2

class PGBot:
    INIT_TIME = 2

    def __init__(self, settings, appName, version):
        self.lock = Lock()

        self.state = BotState.INIT
        self.timestamp = time()
        self.updated = True
        self.version = version
        self.appName = appName
        
        self.stopped = True
        self.paused = False

        self.minimapLoc = [0,0]
        self.presets = settings.get('presets', {"custom": ["blaster","collector","repair","afterburner","","","",""]})
        self.skillset_name = settings.get('skillset', 'custom')
        
        # Fallback to custom if the skillset doesn't exist
        if self.skillset_name not in self.presets:
            self.skillset_name = 'custom'
            
        self.skills = self.presets[self.skillset_name]

        self.plr_energy = 0
        self.plr_hp = 100
        self.dtime = [0,0,0,0,0] # Energy, HP, Map, Collector, NavMenu
        self.outliers = [0,0,0,0]
        self.objectCount = 0
        self.objectPrio = settings.get('priority', ["enemy","loot","enemyIdle"])
        self.objectPixel = settings.get('search', {"enemy": [135,27,11],"enemyIdle": [162,151,15],"loot": [19,193,217]})
        self.healOnHp = settings.get('healOnHp', 25)
        self.defendOnHp = settings.get('defendOnHp', 45)
        self.runOnHp = settings.get('runOnHp', 10)
        self.lowEnergy = settings.get('lowEnergy', 1000)
        self.occasionalSkill = settings.get('occasionalSkill', 150)

        self.targets = False
        self.lastPrint = ''
        self.ui_cache = {}
        
        self.last_used = {}
        self.cooldowns = {
            "rocket": 15, "orbitalstrike": 38, "stun": 75, "thermoblast": 90, 
            "taunt": 90, "sniper": 6, "attackdroid": 290, "speedactuator": 140, 
            "aimcomp": 105, "perforator": 92, "dmgbuff": 142, "shield": 100, 
            "protector": 60, "scramble": 83, "aggrobomb": 95, "mine": 35, 
            "stundome": 110, "stickybomb": 80, "magnettrap": 180, "aggrobeacon": 165,
            "afterburner": 15, "repair": 10, "collector": 5
        }
        self.global_cooldown = 0
        
        self.gui_callback = None
        
        self.techTree = {"aoe": ["rocket", "orbitalstrike", "aggrobomb", "mine", "stundome", "stickybomb", "magnettrap", "aggrobeacon"], "defend": ["shield", "protector", "scramble"], "single": ["rocket", "orbitalstrike", "stun", "thermoblast", "taunt", "sniper", "attackdroid"], "buff": ["speedactuator", "aimcomp", "perforator", "dmgbuff"]}

        # Initialize MSS for screen capture
        self.sct = mss.mss()
        
        # Initialize EasyOCR for numbers in a background thread
        self.ocr_ready = False
        self.reader = None
        Thread(target=self._init_ocr, daemon=True).start()

    def _init_ocr(self):
        self.terminal("Initializing EasyOCR... (This may take a moment)", "info")
        self.reader = easyocr.Reader(['en'], gpu=True)
        self.ocr_ready = True
        self.terminal("EasyOCR Ready!", "info")

    def set_gui_callback(self, callback):
        self.gui_callback = callback

    def update_targets(self):
        if not self.checkTimePassed(2, 1):
            return

        targets = self.findObject(True)
        with self.lock:
            self.targets = targets
            self.updated = True

        if (self.plr_hp <= self.healOnHp):
            self.skill(self.checkSkill("repair"))

    def start(self):
        self.stopped = False
        t = Thread(target=self.run)
        t.daemon = True
        t.start()
        self.terminal('Bot started', 'info')

    def stop(self):
        self.stopped = True

    def run(self):
        while not self.stopped:
            if self.paused:
                sleep(0.2)
                continue

            if self.state == BotState.INIT:
                if time() > self.timestamp + self.INIT_TIME:
                    with self.lock:
                        self.state = BotState.FARMING

            elif self.state == BotState.FARMING:
                if self.checkTimePassed(0, 15):
                    if self.checkEnergy():
                        self.terminal(f'Low Energy! ({self.plr_energy})', 'danger')

                self.checkHP()

                # Check if Nav Menu is open
                if self.checkTimePassed(4, 45):
                    if self.search('orbit') is not None:
                        navmenu = self.search('navmenu')
                        if navmenu is not None:
                            self.click(navmenu[0] + 5, navmenu[1] + 5)

                # Battle and Collect
                if self.targets is not False:
                    # Ignore idle targets if energy is low or if below low hp threshold
                    if self.targets[2] == 'enemyIdle' and (self.plr_energy <= self.lowEnergy or self.plr_hp <= self.healOnHp):
                        continue

					# Use Collector to prevent softlock
                    if self.checkTimePassed(3, 4):
                        self.skill(self.checkSkill("collector"))

                    try:
                        if self.updated:
                            self.moveTo(self.targets)
                            with self.lock:
                                self.updated = False
                        self.interact(self.targets[2])
                    except Exception:
                        pass 

            elif self.state == BotState.FLEEING:
                self.checkHP()
                self.useTech("afterburner")
                self.useTech("repair")

                if self.plr_hp >= math.ceil(self.healOnHp / 2):
                    with self.lock:
                        self.state = BotState.FARMING

    #---# Helper Scripts #---#
    def click(self, x, y):
        win32api.SetCursorPos((int(x), int(y)))
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN,0,0)
        sleep(0.1)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP,0,0)

    def doubleclick(self, x, y):
        self.click(x,y)
        self.click(x,y)

    def getNum(self, image_np):
        if not self.ocr_ready or self.reader is None:
            return ""
        # image_np is expected to be a numpy array (RGB or Grayscale)
        result = self.reader.readtext(image_np, allowlist='0123456789,')
        if len(result) > 0:
            text = result[0][1]
            return text
        return ""

    def mss_screenshot(self, region=None):
        # region format: (left, top, width, height)
        if region:
            monitor = {"top": int(region[1]), "left": int(region[0]), "width": int(region[2]), "height": int(region[3])}
        else:
            monitor = self.sct.monitors[1] # Primary monitor
            
        sct_img = self.sct.grab(monitor)
        # Convert to numpy array
        img = np.array(sct_img)
        # Convert BGRA to RGB
        img = cv.cvtColor(img, cv.COLOR_BGRA2RGB)
        return img

    def imgFindPixel(self, img, c, findAll = False):
        # img is RGB numpy array
        mask = np.all(img[:, :, :3] == c, axis=-1)
        coords = np.argwhere(mask)
        if coords.size > 0:
            results = coords[:, [1, 0]].tolist()
            return results if findAll else results[0]
        return False

	# Find Object on Minimap
    def minimapFind(self, find, nearest = False):
        minimap = self.search('minimap')
        if minimap is not None:
            self.minimapLoc = [minimap[0] + 25, minimap[1] - 100]
            minimap_img = self.mss_screenshot(region=(self.minimapLoc[0], self.minimapLoc[1], 115, 115))
            found = self.imgFindPixel(minimap_img, find, nearest)
            if found is not False:
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
    def search(self, img_name, conf=0.8):
        template_path = f'./data/images/{img_name}.png'
        if not os.path.exists(template_path):
            return None
        
        template = cv.imread(template_path, cv.IMREAD_COLOR)
        if template is None:
            return None
            
        template = cv.cvtColor(template, cv.COLOR_BGR2RGB)
        
        # Check cache first
        if img_name in self.ui_cache:
            loc = self.ui_cache[img_name]
            h, w, _ = template.shape
            verify_region = (max(0, loc[0] - 10), max(0, loc[1] - 10), w + 20, h + 20)
            screen_small = self.mss_screenshot(region=verify_region)
            result = cv.matchTemplate(screen_small, template, cv.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv.minMaxLoc(result)
            if max_val >= conf:
                new_loc = (verify_region[0] + max_loc[0], verify_region[1] + max_loc[1])
                self.ui_cache[img_name] = new_loc
                return new_loc

        # If not in cache or verification failed, do full screen search
        screen = self.mss_screenshot()
        result = cv.matchTemplate(screen, template, cv.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv.minMaxLoc(result)
        
        if max_val >= conf:
            self.ui_cache[img_name] = max_loc
            return max_loc
        return None

    def checkEnergy(self, num = None):
        if num is None:
            num = self.lowEnergy

        find = self.search('energy', 0.72)
        if find is not None:
            cenergy_img = self.mss_screenshot(region=(find[0] - 100, find[1], 100, 20))
            cenergy_img = cv.resize(cenergy_img, (0,0), fx=2, fy=2, interpolation=cv.INTER_CUBIC)
            cenergy_str = self.getNum(cenergy_img).replace(' ', '').replace(',', '')
            
            try:
                cenergy = int(cenergy_str)
            except Exception:
                cenergy = 0

			# Statistical outliers
            if self.outliers[2] - cenergy >= 1000 and self.outliers[3] <= 2:
                cenergy = self.outliers[2]
                nout = self.outliers[3] + 1
            else:
                nout = 0

            with self.lock:
                self.outliers[3] = nout
                self.plr_energy = cenergy
                self.outliers[2] = cenergy

            if (cenergy <= num):
                return True
            return False
        else:
            self.plr_energy = 10000
            return False

    # Find Energy
    def findEnergy(self):
        return False

    # Find Objects
    def findObject(self, nearest = False):
        for obj in self.objectPrio:
            find = self.minimapFind(self.objectPixel[obj], nearest)
            if find is not False:
                if isinstance(find, list):
                    if len(find) > 0 and isinstance(find[0], list):
                        find = find[0] # Take first if multiple
                    find.append(obj)
                    return find
        self.objectCount = 0
        return False

	# Move to Position and avoid obstacles
    def moveTo(self, pos = False):
        if pos == False:
            return False
        self.click(self.minimapLoc[0] + pos[0] - 1, self.minimapLoc[1] + pos[1])

	# Check HP and heal if needed
    def checkHP(self):
        if not self.checkTimePassed(1, 2):
            if (self.plr_hp <= self.healOnHp):
                self.skill(self.checkSkill("repair"))
                return True
            return False

        find = self.search('minimap')
        if find is not None:
            chp_img = self.mss_screenshot(region=(find[0] - 25, find[1] + 5, 20, 15))
            
            # Upscale the image slightly to help OCR accuracy
            chp_img = cv.resize(chp_img, (0,0), fx=2, fy=2, interpolation=cv.INTER_CUBIC)
            chp_str = self.getNum(chp_img).replace(' ', '').replace(',', '')
            
            if chp_str != '':
                try:
                    chp = int(chp_str)
                except:
                    chp = 100

                with self.lock:
                    self.plr_hp = chp

                if (chp <= self.healOnHp):
                    self.skill(self.checkSkill("repair"))
                    return True
            else:
                with self.lock:
                    self.plr_hp = 100
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
                with self.lock:
                    self.state = BotState.FLEEING

			# Always Attack fallback
            #self.skill_force(1)
            self.skill(self.checkSkill("blaster"))

    # Interaction types
    def interactType(self, itype):
        cond_aoe = self.objectCount >= 2
        cond_defend = self.plr_hp <= self.defendOnHp
        
        should_use = False
        if itype == 'aoe' and cond_aoe:
            should_use = True
        elif itype == 'defend' and cond_defend:
            should_use = True
        elif itype == 'single' or itype == 'buff':
            should_use = True
            
        if not should_use:
            return
            
        for tech in self.techTree[itype]:
            if self.checkSkill(tech):
                if self.useTech(tech):
                    return

    # Use a skill with internal cooldowns
    def useTech(self, tech_name):
        current_time = time()
        cd = self.cooldowns.get(tech_name, 10)
        
        if current_time - self.last_used.get(tech_name, 0) >= cd:
            if self.skill(self.checkSkill(tech_name)):
                self.last_used[tech_name] = current_time
                return True
        return False

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
            self.terminal(f"Skill {num} invalid", "error")
            return False

        # Enforce 1s Global Cooldown
        if time() - self.global_cooldown < 0.9:
            return False

        self.skill_force(num)

        self.global_cooldown = time()
        return True
    
    # Force to use a Skill
    def skill_force(self, num):
        keyboard.press(str(num))
        sleep(0.1)
        keyboard.release(str(num))

    def terminal(self, text, type='info'):
        if text != self.lastPrint:
            text_final = f"[{type.upper()}] {text}"
            if self.gui_callback:
                self.gui_callback(text_final, type)
            else:
                print(text_final)

            with self.lock:
                self.lastPrint = text
        return True

	# Check time passed since last check
    def checkTimePassed(self, delta, secs):
        if self.dtime[delta] == 0:
            self.dtime[delta] = datetime.datetime.now() - datetime.timedelta(seconds=secs)
        if datetime.timedelta.total_seconds(datetime.datetime.now()-self.dtime[delta]) >= secs:
            self.dtime[delta] = datetime.datetime.now()
            return True
        return False