# Installation
- Edit your ships weapon configuration in the settings.json<br>
- Install the following modules using pip:<br>
``pip install keyboard opencv-python numpy pywin32 mss easyocr customtkinter``<br>
- For GPU OCR (recommended, much faster) install the CUDA build of PyTorch from https://pytorch.org/get-started/locally/ before EasyOCR. The bot falls back to the CPU automatically if CUDA is not available; the log and the sidebar show which one is used.<br>

# How to use

Run ``python PGBot.py`` (Or on windows just start run.bat to start the bot)<br>
Make sure to have Pirate Galaxy open on your main monitor.<br>

Hotkeys (configurable in settings.json):
- ``ctrl+shift+p`` pause / resume
- ``ctrl+shift+q`` quit immediately

While the bot is running it controls the mouse, pause it to use your PC.

# Settings

You can also adjust the most common settings inside the GUI after starting the bot.

| Setting | Description |
| --- | --- |
| ``priority`` | Order in which minimap objects are targeted |
| ``search`` | RGB color of each object type on the minimap |
| ``colorTolerance`` | Allowed difference per color channel when matching minimap colors |
| ``healOnHp`` | Use repair at or below this HP |
| ``defendOnHp`` | Use defensive skills at or below this HP |
| ``runOnHp`` | Flee (move away from enemies, afterburner + repair) at or below this HP |
| ``fleeUntilHp`` | Return to farming once HP is back at this value |
| ``lowEnergy`` | Below this energy idle enemies are ignored and a warning is logged |
| ``skillInterval`` | Seconds between skill ticks. Each tick uses at most one skill, then always the blaster |
| ``moveInterval`` | Seconds between re-clicking the same target on the minimap |
| ``moveDeadzone`` | Don't click a target closer than this many minimap pixels to the center |
| ``fleeDistance`` | How far (minimap pixels) to click away from the nearest enemy when fleeing |
| ``aoeRadius`` | Only count enemies within this minimap radius for AoE skills (0 = whole minimap) |
| ``clickOffset`` | ``[x, y]`` pixel correction for minimap clicks |
| ``hotkeys`` | ``pause`` and ``quit`` hotkeys |
| ``cooldowns`` | Override skill cooldowns in seconds, e.g. ``{"rocket": 14}`` |
| ``skillset`` | Active preset from ``presets`` |
| ``presets`` | Skill slots 1-8 per ship, use ``""`` for unused slots |

Possible Skills:<br>
``blaster, collector, repair, afterburner, rocket, orbitalstrike, aggrobomb, mine, stundome, stickybomb, magnettrap, shield, protector, scramble, aggrobeacon, stun, thermoblast, taunt, sniper, attackdroid, speedactuator, aimcomp, perforator, dmgbuff, lightningchain``<br>
Ally skills (``repairtarget, repairfield, resurrect``) can be in a preset but are not used by the bot.
