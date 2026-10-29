#!python3
###################
# Made by Eclip5e #
###################

import os
import math
import queue
import traceback
from time import sleep, time
from threading import Thread, Lock, Event, local

import cv2 as cv
import numpy as np
import mss
import keyboard
import win32api, win32con

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMAGE_DIR = os.path.join(BASE_DIR, 'data', 'images')


class BotState:
    INIT = 0
    FARMING = 1
    FLEEING = 2
    NAMES = {0: 'INIT', 1: 'FARMING', 2: 'FLEEING'}


# UI layout, relative to the top-left corner of the 'minimap' template
MINIMAP_OFFSET = (25, -100)
MINIMAP_SIZE = 115
HP_OFFSET = (-25, 5)
HP_SIZE = (20, 15)
# Relative to the top-left corner of the 'energy' template
ENERGY_OFFSET = (-100, 0)
ENERGY_SIZE = (100, 20)
# Extra pixels grabbed around the minimap template so it can be re-located without a full screen search
ANCHOR_MARGIN = 10

ENEMY_TYPES = ('enemy', 'enemyIdle')
BASE_SKILLS = {'blaster', 'collector', 'repair', 'afterburner'}
# Ally skills are intentionally unused (solo farming bot)
ALLY_SKILLS = {'repairtarget', 'repairfield', 'resurrect'}

DEFAULT_SETTINGS = {
    "priority": ["enemy", "loot", "enemyIdle"],
    "search": {"enemy": [135, 27, 11], "enemyIdle": [162, 151, 15], "loot": [19, 193, 217]},
    "colorTolerance": 12,
    "healOnHp": 25,
    "defendOnHp": 45,
    "runOnHp": 10,
    "fleeUntilHp": 50,
    "lowEnergy": 1000,
    "skillInterval": 0.9,
    "moveInterval": 0.25,
    "moveDeadzone": 2,
    "fleeDistance": 45,
    "aoeRadius": 0,
    "clickOffset": [0, 0],
    "hotkeys": {"pause": "ctrl+shift+p", "quit": "ctrl+shift+q"},
    "cooldowns": {},
    "skillset": "custom",
    "presets": {"custom": ["blaster", "collector", "repair", "afterburner", "", "", "", ""]},
}


class PGBot:
    INIT_TIME = 2           # Seconds to wait after start before acting
    FRAME_DELAY = 0.02      # Delay between minimap captures (~40-50 fps)
    KEY_HOLD = 0.04         # How long keys / mouse buttons are held down
    BLASTER_DELAY = 0.05    # Pause between a skill and the blaster in the same tick
    HP_INTERVAL = 0.5
    ENERGY_INTERVAL = 15
    NAVMENU_INTERVAL = 45
    FULL_SEARCH_INTERVAL = 1

    def __init__(self, settings, appName, version):
        self.version = version
        self.appName = appName

        self.input_lock = Lock()
        self.ocr_lock = Lock()
        self.log_queue = queue.Queue()
        self._tls = local()
        self._stop_event = Event()
        self._threads = []

        self.state = BotState.INIT
        self.timestamp = time()
        self.stopped = True
        self.paused = False

        self.plr_hp = None      # None = not read yet
        self.plr_energy = None
        self.targets = False    # [x, y, type] on the minimap or False
        self.objectCount = 0
        self.anchor = None      # Screen position of the minimap template
        self.minimapLoc = [0, 0]
        self.ui_cache = {}
        self.last_used = {}
        self.lastPrint = ''

        self._hp_pending = None
        self._energy_outliers = 0
        self._last_full_search = 0
        self._last_tick = 0
        self._last_move = 0
        self._last_move_target = None
        self._warned = set()

        self.base_cooldowns = {
            "rocket": 15, "orbitalstrike": 38, "stun": 75, "thermoblast": 90,
            "taunt": 90, "sniper": 6, "attackdroid": 290, "speedactuator": 140,
            "aimcomp": 105, "perforator": 92, "dmgbuff": 142, "shield": 100,
            "protector": 60, "scramble": 83, "aggrobomb": 95, "mine": 35,
            "stundome": 110, "stickybomb": 80, "magnettrap": 180, "aggrobeacon": 165,
            "lightningchain": 10,  # Unknown, override in settings.json "cooldowns"
            "afterburner": 15, "repair": 10, "collector": 5
        }
        self.techTree = {
            "aoe": ["rocket", "orbitalstrike", "lightningchain", "aggrobomb", "mine", "stundome", "stickybomb", "magnettrap", "aggrobeacon"],
            "defend": ["shield", "protector", "scramble"],
            "single": ["rocket", "orbitalstrike", "lightningchain", "stun", "thermoblast", "taunt", "sniper", "attackdroid"],
            "buff": ["speedactuator", "aimcomp", "perforator", "dmgbuff"]
        }

        self.settings = {}
        self.apply_settings(settings)

        # Templates are loaded once instead of on every search
        self.templates = {}
        for name in ('minimap', 'energy', 'navmenu', 'orbit'):
            img = cv.imread(os.path.join(IMAGE_DIR, f'{name}.png'), cv.IMREAD_COLOR)
            if img is None:
                self.terminal(f"Template {name}.png missing", "error")
                continue
            self.templates[name] = cv.cvtColor(img, cv.COLOR_BGR2RGB)

        # EasyOCR (and torch) are imported in the background so the GUI opens instantly
        self.ocr_ready = False
        self.ocr_device = 'loading'
        self.reader = None
        Thread(target=self._init_ocr, daemon=True).start()

    #---# Settings #---#
    def apply_settings(self, settings):
        merged = dict(DEFAULT_SETTINGS)
        merged.update(settings)
        self.settings = merged

        self.presets = merged['presets']
        self.skillset_name = merged['skillset'] if merged['skillset'] in self.presets else next(iter(self.presets))
        self.skills = self.presets[self.skillset_name]
        self.objectPrio = list(merged['priority'])
        self.objectPixel = merged['search']
        self.colorTolerance = int(merged['colorTolerance'])
        self.healOnHp = merged['healOnHp']
        self.defendOnHp = merged['defendOnHp']
        self.runOnHp = merged['runOnHp']
        self.fleeUntilHp = merged['fleeUntilHp']
        self.lowEnergy = merged['lowEnergy']
        self.skillInterval = float(merged['skillInterval'])
        self.moveInterval = float(merged['moveInterval'])
        self.moveDeadzone = float(merged['moveDeadzone'])
        self.fleeDistance = float(merged['fleeDistance'])
        self.aoeRadius = float(merged['aoeRadius'])
        self.clickOffset = list(merged['clickOffset'])
        self.cooldowns = dict(getattr(self, 'base_cooldowns', {}))
        self.cooldowns.update(merged['cooldowns'])

        self._color_ranges = {}
        for name, c in self.objectPixel.items():
            c = np.array(c, dtype=int)
            lo = np.clip(c - self.colorTolerance, 0, 255).astype(np.uint8)
            hi = np.clip(c + self.colorTolerance, 0, 255).astype(np.uint8)
            self._color_ranges[name] = (lo, hi)

        self._check_skillset()

    def _check_skillset(self):
        known = BASE_SKILLS | ALLY_SKILLS | set(self.cooldowns)
        for s in self.skills:
            if s and s not in known:
                self.terminal(f"Unknown skill '{s}' in preset '{self.skillset_name}' - it will never be used", "warn")
        if 'blaster' not in self.skills:
            self.terminal(f"Preset '{self.skillset_name}' has no blaster!", "warn")

    #---# OCR #---#
    def _init_ocr(self):
        self.terminal("Initializing EasyOCR... (This may take a moment)", "info")
        try:
            import easyocr
            import torch
        except Exception as e:
            self.ocr_device = 'failed'
            self.ocr_ready = True
            self.terminal(f"EasyOCR could not be imported ({e}). HP/Energy will not be read.", "error")
            return

        reader = None
        if torch.cuda.is_available():
            try:
                reader = easyocr.Reader(['en'], gpu=True, verbose=False)
                self._ocr_warmup(reader)
                self.ocr_device = f"GPU ({torch.cuda.get_device_name(0)})"
            except Exception as e:
                reader = None
                self.terminal(f"CUDA OCR failed ({e}), falling back to CPU", "warn")
        else:
            cuda_build = getattr(torch.version, 'cuda', None)
            hint = "PyTorch build has no CUDA support (install the CUDA build from pytorch.org)" if not cuda_build else "no usable CUDA device/driver found"
            self.terminal(f"CUDA not available: {hint}. Using CPU.", "warn")

        if reader is None:
            try:
                reader = easyocr.Reader(['en'], gpu=False, verbose=False)
                self._ocr_warmup(reader)
                self.ocr_device = 'CPU'
            except Exception as e:
                self.ocr_device = 'failed'
                self.ocr_ready = True
                self.terminal(f"EasyOCR failed to start ({e}). HP/Energy will not be read.", "error")
                return

        self.reader = reader
        self.ocr_ready = True
        self.terminal(f"EasyOCR Ready! ({self.ocr_device})", "info")

    def _ocr_warmup(self, reader):
        reader.readtext(np.zeros((30, 60, 3), dtype=np.uint8), allowlist='0123456789,')

    def getNum(self, image_np):
        """Read a number from an RGB image. Returns None if nothing usable was read."""
        if self.reader is None:
            return None
        # readtext is slower than recognize() but recognize misreads these small crops (100 -> 102)
        with self.ocr_lock:
            result = self.reader.readtext(image_np, allowlist='0123456789,')
        digits = ''.join(ch for ch in ''.join(r[1] for r in result) if ch.isdigit())
        return int(digits) if digits else None

    #---# Control #---#
    def start(self):
        # Make sure old threads are gone so a quick stop/start never runs two loops
        self._stop_event.set()
        for t in self._threads:
            t.join(timeout=3)

        self._stop_event = Event()
        self.stopped = False
        self.paused = False
        self.state = BotState.INIT
        self.timestamp = time()
        self.targets = False
        self._last_tick = 0
        self._last_move = 0
        self._last_move_target = None

        self._threads = [
            Thread(target=self._action_loop, daemon=True, name='PGBot-action'),
            Thread(target=self._monitor_loop, daemon=True, name='PGBot-monitor'),
        ]
        for t in self._threads:
            t.start()
        self.terminal('Bot started', 'info')

    def stop(self):
        self.stopped = True
        self.paused = False
        self._stop_event.set()
        self.release_inputs()

    def set_paused(self, paused):
        self.paused = paused
        if paused:
            self.release_inputs()

    #---# Main loops #---#
    def _action_loop(self):
        """Fast loop: capture minimap -> detect -> click/skill immediately, all on fresh data."""
        stop = self._stop_event
        last_error = 0
        while not stop.is_set():
            try:
                if self.paused:
                    sleep(0.1)
                    continue

                now = time()
                if self.state == BotState.INIT:
                    if now >= self.timestamp + self.INIT_TIME:
                        self.state = BotState.FARMING
                    sleep(0.1)
                    continue

                minimap = self.read_minimap()
                if minimap is None:
                    self.targets = False
                    self.objectCount = 0
                    self._combat_tick(None)
                    sleep(0.1)
                    continue

                blobs = self.detect(minimap)
                self._update_state()

                if self.state == BotState.FLEEING:
                    self._flee(blobs)
                else:
                    self._farm(blobs)
            except Exception:
                if time() - last_error > 5:
                    self.terminal(f"Action loop error: {traceback.format_exc(limit=3)}", "error")
                last_error = time()
                sleep(0.5)
            stop.wait(self.FRAME_DELAY)

    def _monitor_loop(self):
        """Slow loop: OCR for HP / energy and UI checks, so they never delay reactions."""
        stop = self._stop_event
        last_hp = last_energy = 0
        last_nav = time()
        last_error = 0
        while not stop.is_set():
            try:
                if self.paused:
                    sleep(0.2)
                    continue

                now = time()
                if self.reader is not None:
                    if now - last_hp >= self.HP_INTERVAL:
                        last_hp = now
                        self.checkHP()
                    if now - last_energy >= self.ENERGY_INTERVAL:
                        last_energy = now
                        if self.checkEnergy():
                            self.terminal(f'Low Energy! ({self.plr_energy})', 'danger')

                if now - last_nav >= self.NAVMENU_INTERVAL:
                    last_nav = now
                    self.checkNavMenu()
            except Exception:
                if time() - last_error > 5:
                    self.terminal(f"Monitor loop error: {traceback.format_exc(limit=3)}", "error")
                last_error = time()
                sleep(0.5)
            stop.wait(0.05)

    #---# Decisions #---#
    def _update_state(self):
        hp = self.plr_hp
        if hp is None:
            return
        if self.state == BotState.FARMING and hp <= self.runOnHp:
            self.state = BotState.FLEEING
            self.terminal(f'HP {hp} - fleeing!', 'danger')
        elif self.state == BotState.FLEEING and hp >= self.fleeUntilHp:
            self.state = BotState.FARMING
            self.terminal(f'HP {hp} - back to farming', 'info')

    def _farm(self, blobs):
        target = self.choose_target(blobs)
        if target is None:
            self.targets = False
            self.objectCount = 0
            self._last_move_target = None
        else:
            self.targets = [target[0], target[1], target[2]]
            self.objectCount = self._count_enemies(blobs)
            self.moveTo(target)
        self._combat_tick(target)

    def _flee(self, blobs):
        self.targets = False
        enemies = [p for t in ENEMY_TYPES for p in blobs.get(t, [])]
        self.objectCount = len(enemies)
        if enemies:
            c = (MINIMAP_SIZE - 1) / 2
            nx, ny = min(enemies, key=lambda p: (p[0] - c) ** 2 + (p[1] - c) ** 2)
            vx, vy = c - nx, c - ny
            norm = math.hypot(vx, vy)
            if norm < 1:
                vx, vy, norm = 0, -1, 1
            px = min(max(c + vx / norm * self.fleeDistance, 3), MINIMAP_SIZE - 4)
            py = min(max(c + vy / norm * self.fleeDistance, 3), MINIMAP_SIZE - 4)
            if time() - self._last_move >= self.moveInterval:
                self._click_minimap(px, py)
                self._last_move = time()
        self._combat_tick(None)

    def choose_target(self, blobs):
        low_energy = self.plr_energy is not None and self.plr_energy <= self.lowEnergy
        low_hp = self.plr_hp is not None and self.plr_hp <= self.healOnHp
        c = (MINIMAP_SIZE - 1) / 2
        for obj in self.objectPrio:
            # Ignore idle targets if energy is low or if below heal threshold
            if obj == 'enemyIdle' and (low_energy or low_hp):
                continue
            points = blobs.get(obj)
            if points:
                x, y = min(points, key=lambda p: (p[0] - c) ** 2 + (p[1] - c) ** 2)
                return (x, y, obj)
        return None

    def _count_enemies(self, blobs):
        c = (MINIMAP_SIZE - 1) / 2
        count = 0
        for t in ENEMY_TYPES:
            for x, y in blobs.get(t, []):
                if self.aoeRadius <= 0 or math.hypot(x - c, y - c) <= self.aoeRadius:
                    count += 1
        return count

    def _combat_tick(self, target):
        """Once per skillInterval: use at most one skill, then always the blaster."""
        now = time()
        if now - self._last_tick < self.skillInterval:
            return
        self._last_tick = now

        tech = self._pick_skill(target, now)
        if tech is not None and self.skill(self.checkSkill(tech)):
            self.last_used[tech] = now
            sleep(self.BLASTER_DELAY)

        # Blaster is always pressed last, it briefly blocks the other skills in game
        self.skill(self.checkSkill('blaster'))

    def _pick_skill(self, target, now):
        hp = self.plr_hp
        hp_low = hp is not None and hp <= self.healOnHp
        hp_defend = hp is not None and hp <= self.defendOnHp
        target_type = target[2] if target else None

        candidates = []
        if hp_low:
            candidates.append('repair')
        if self.state == BotState.FLEEING:
            candidates += ['afterburner', 'repair'] + self.techTree['defend']
        elif target_type == 'loot':
            candidates.append('collector')
        elif target_type in ENEMY_TYPES:
            if self.objectCount >= 2:
                candidates += self.techTree['aoe']
            if hp_defend:
                candidates += self.techTree['defend']
            # Use Collector regularly to prevent softlock
            candidates.append('collector')
            candidates += self.techTree['single'] + self.techTree['buff']

        for tech in candidates:
            if self.checkSkill(tech) and now - self.last_used.get(tech, 0) >= self.cooldowns.get(tech, 10):
                return tech
        return None

    #---# Vision #---#
    def _sct(self):
        # mss keeps its Windows handles per thread, so every thread needs its own instance
        sct = getattr(self._tls, 'sct', None)
        if sct is None:
            sct = getattr(mss, 'MSS', mss.mss)()  # mss.mss is deprecated in newer versions
            self._tls.sct = sct
        return sct

    def grab(self, left, top, width, height):
        """Grab a screen region (clamped to the screen). Returns (RGB image, (left, top))."""
        sct = self._sct()
        vs = sct.monitors[0]
        l = max(int(left), vs['left'])
        t = max(int(top), vs['top'])
        r = min(int(left + width), vs['left'] + vs['width'])
        b = min(int(top + height), vs['top'] + vs['height'])
        if r <= l or b <= t:
            return None, (l, t)
        img = np.asarray(sct.grab({"left": l, "top": t, "width": r - l, "height": b - t}))
        return cv.cvtColor(img, cv.COLOR_BGRA2RGB), (l, t)

    def screenshot_full(self):
        mon = self._sct().monitors[1]  # Primary monitor
        return self.grab(mon['left'], mon['top'], mon['width'], mon['height'])

    def search(self, img_name, conf=0.8):
        """Template search with a cached position. Returns the screen position or None."""
        template = self.templates.get(img_name)
        if template is None:
            return None
        h, w = template.shape[:2]

        loc = self.ui_cache.get(img_name)
        if loc is not None:
            img, origin = self.grab(loc[0] - 10, loc[1] - 10, w + 20, h + 20)
            if img is not None and img.shape[0] >= h and img.shape[1] >= w:
                result = cv.matchTemplate(img, template, cv.TM_CCOEFF_NORMED)
                _, max_val, _, max_loc = cv.minMaxLoc(result)
                if max_val >= conf:
                    new_loc = (origin[0] + max_loc[0], origin[1] + max_loc[1])
                    self.ui_cache[img_name] = new_loc
                    return new_loc

        screen, origin = self.screenshot_full()
        if screen is None:
            return None
        result = cv.matchTemplate(screen, template, cv.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv.minMaxLoc(result)
        if max_val >= conf:
            new_loc = (origin[0] + max_loc[0], origin[1] + max_loc[1])
            self.ui_cache[img_name] = new_loc
            return new_loc
        return None

    def read_minimap(self):
        """One grab that verifies the minimap anchor and returns the minimap image (RGB) or None."""
        template = self.templates.get('minimap')
        if template is None:
            return None
        th, tw = template.shape[:2]

        anchor = self.anchor
        if anchor is None:
            if time() - self._last_full_search < self.FULL_SEARCH_INTERVAL:
                return None
            self._last_full_search = time()
            anchor = self.search('minimap')
            if anchor is None:
                self.terminal('Minimap not found', 'warn')
                return None
            self.anchor = anchor

        m = ANCHOR_MARGIN
        left = anchor[0] + min(0, MINIMAP_OFFSET[0], HP_OFFSET[0]) - m
        top = anchor[1] + min(0, MINIMAP_OFFSET[1], HP_OFFSET[1]) - m
        right = anchor[0] + max(tw, MINIMAP_OFFSET[0] + MINIMAP_SIZE, HP_OFFSET[0] + HP_SIZE[0]) + m
        bottom = anchor[1] + max(th, MINIMAP_OFFSET[1] + MINIMAP_SIZE, HP_OFFSET[1] + HP_SIZE[1]) + m
        img, origin = self.grab(left, top, right - left, bottom - top)
        if img is None:
            self.anchor = None
            return None

        # Verify the anchor in a small window around its last position
        wx, wy = anchor[0] - m - origin[0], anchor[1] - m - origin[1]
        window = img[max(wy, 0):wy + th + 2 * m, max(wx, 0):wx + tw + 2 * m]
        if window.shape[0] < th or window.shape[1] < tw:
            self.anchor = None
            return None
        result = cv.matchTemplate(window, template, cv.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv.minMaxLoc(result)
        if max_val < 0.8:
            self.anchor = None
            return None
        anchor = (origin[0] + max(wx, 0) + max_loc[0], origin[1] + max(wy, 0) + max_loc[1])
        self.anchor = anchor
        self.ui_cache['minimap'] = anchor

        mx, my = anchor[0] + MINIMAP_OFFSET[0], anchor[1] + MINIMAP_OFFSET[1]
        self.minimapLoc = [mx, my]
        x0, y0 = mx - origin[0], my - origin[1]
        minimap = img[y0:y0 + MINIMAP_SIZE, x0:x0 + MINIMAP_SIZE]
        if x0 < 0 or y0 < 0 or minimap.shape[:2] != (MINIMAP_SIZE, MINIMAP_SIZE):
            return None
        return minimap

    def detect(self, minimap):
        """Find colored blobs on the minimap. Returns {type: [(x, y) centroid, ...]}."""
        blobs = {}
        for name, (lo, hi) in self._color_ranges.items():
            mask = cv.inRange(minimap, lo, hi)
            if not mask.any():
                blobs[name] = []
                continue
            n, _, _, centroids = cv.connectedComponentsWithStats(mask, connectivity=8)
            blobs[name] = [(float(cx), float(cy)) for cx, cy in centroids[1:n]]
        return blobs

    #---# UI readings #---#
    def checkHP(self):
        anchor = self.anchor
        if anchor is None:
            return False
        img, _ = self.grab(anchor[0] + HP_OFFSET[0], anchor[1] + HP_OFFSET[1], *HP_SIZE)
        if img is None:
            return False

        # The game hides the HP number at full HP, so no white text pixels means 100
        hsv = cv.cvtColor(img, cv.COLOR_RGB2HSV)
        if np.count_nonzero((hsv[..., 1] < 90) & (hsv[..., 2] > 160)) < 10:
            self._hp_pending = None
            self.plr_hp = 100
            return False

        # Upscale the image slightly to help OCR accuracy
        img = cv.resize(img, (0, 0), fx=2, fy=2, interpolation=cv.INTER_CUBIC)
        chp = self.getNum(img)
        if chp is None or chp > 100:
            return False  # Unreadable: keep the last known value

        last = self.plr_hp
        if last is not None and abs(chp - last) >= 50:
            # Big jumps are often misreads (e.g. "100" read as "10"), accept once confirmed
            if self._hp_pending is None or abs(self._hp_pending - chp) > 10:
                self._hp_pending = chp
                return False
        self._hp_pending = None
        self.plr_hp = chp
        return chp <= self.healOnHp

    def checkEnergy(self, num=None):
        if num is None:
            num = self.lowEnergy

        find = self.search('energy', 0.72)
        if find is None:
            self.terminal('Energy display not found', 'warn')
            return False

        img, _ = self.grab(find[0] + ENERGY_OFFSET[0], find[1] + ENERGY_OFFSET[1], *ENERGY_SIZE)
        if img is None:
            return False
        img = cv.resize(img, (0, 0), fx=2, fy=2, interpolation=cv.INTER_CUBIC)
        cenergy = self.getNum(img)
        if cenergy is None:
            return False

        # Statistical outliers, accepted after 3 consecutive reads
        last = self.plr_energy
        if last is not None and abs(last - cenergy) >= 1000 and self._energy_outliers < 2:
            self._energy_outliers += 1
            return False
        self._energy_outliers = 0
        self.plr_energy = cenergy
        return cenergy <= num

    def checkNavMenu(self):
        if self.search('orbit') is not None:
            navmenu = self.search('navmenu')
            if navmenu is not None:
                self.click(navmenu[0] + 5, navmenu[1] + 5)

    #---# Input #---#
    def moveTo(self, target):
        c = (MINIMAP_SIZE - 1) / 2
        x, y = target[0], target[1]
        if math.hypot(x - c, y - c) <= self.moveDeadzone:
            return False

        now = time()
        prev = self._last_move_target
        new_target = prev is None or prev[2] != target[2] or math.hypot(prev[0] - x, prev[1] - y) > 8
        if (new_target and now - self._last_move >= 0.08) or now - self._last_move >= self.moveInterval:
            self._click_minimap(x, y)
            self._last_move = time()
            self._last_move_target = target
            return True
        return False

    def _click_minimap(self, x, y):
        self.click(self.minimapLoc[0] + x + self.clickOffset[0], self.minimapLoc[1] + y + self.clickOffset[1])

    def click(self, x, y):
        with self.input_lock:
            win32api.SetCursorPos((int(round(x)), int(round(y))))
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0)
            sleep(self.KEY_HOLD)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0)

    def release_inputs(self):
        try:
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0)
            for i in range(1, 9):
                keyboard.release(str(i))
        except Exception:
            pass

    # Check if User has Skill, returns the slot (1-8) or False
    def checkSkill(self, check):
        if not check:
            return False
        for index, a in enumerate(self.skills, start=1):
            if check == a:
                return index
        return False

    # Use a Skill
    def skill(self, num):
        if num is False or num is None or not 1 <= num <= 8:
            return False
        self.skill_force(num)
        return True

    # Force to use a Skill
    def skill_force(self, num):
        with self.input_lock:
            keyboard.press(str(num))
            sleep(self.KEY_HOLD)
            keyboard.release(str(num))

    #---# Logging #---#
    def terminal(self, text, type='info'):
        """Thread-safe log. The GUI drains log_queue, worker threads never touch Tk."""
        if text != self.lastPrint:
            self.lastPrint = text
            self.log_queue.put((f"[{type.upper()}] {text}", type))
        return True

    @property
    def state_name(self):
        return BotState.NAMES.get(self.state, '?')
