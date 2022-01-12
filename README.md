# Installation
-Install Tesserract OCR and edit its path in the settings.json<br>
Possible solution to install Tesseract: <a href="https://stackoverflow.com/questions/46140485/tesseract-installation-in-windows">``https://stackoverflow.com/questions/46140485/tesseract-installation-in-windows``</a><br>
-Edit your ships weapon configuration in the settings.json<br>
-Install the following modules using pip:<br>
``pip install pyautogui keyboard colorama datetime requests pytesseract opencv-python pypiwin32``<br>

# How to use

Run ``python PGBot.py`` (Or on windows just start run.bat to start the bot)<br>
Make sure to have Pirate Galaxy open on your main monitor.<br>

# Settings
```
{
    "tesseract": "C:\\Program Files\\Tesseract-OCR\\tesseract.exe",
    "conApi": "",
    "username": "",
    "priority": [
        "enemy",
        "loot",
        "enemyIdle"
    ],
    "search": {
        "enemy": [135,27,11],
        "enemyIdle": [162,151,15],
        "loot": [19,193,217]
    },
    "healOnHp": 25,
    "defendOnHp": 45,
    "runOnHp": 10,
    "lowEnergy": 3000,
    "showTechUsage": false,
    "occasionalSkill": 150,
    "skillset": "custom",
    "skills": {
        "storm": [
            "blaster",
            "collector",
            "rocket",
            "repair",
            "afterburner",
            "aimcomp",
            "perforator",
            "thermo"
        ],
        "tank": [
            "blaster",
            "collector",
            "repair",
            "afterburner",
            "shield",
            "taunt",
            "scramble",
            "aggrobomb"
        ],
        "engineer": [
            "blaster",
            "collector",
            "repair",
            "afterburner",
            "repairtarget",
            "protector",
            "repairfield",
            "resurrect"
        ],
        "shock": [
            "blaster",
            "collector",
            "repair",
            "afterburner",
            "speedactuator",
            "stun",
            "beacon",
            "stundome"
        ],
        "custom": [
            "blaster",
            "collector",
            "repair",
            "afterburner",
            "scramble",
            "protector",
            "stundome",
            "orbitalstrike"
        ]
    }
}
```
-Change "tesseract" to be the location of your tesseract installation.<br>
-"conApi" and "username" can be left empty.<br>
-Change "skillset" to any of the lists.<br>
Possible Skills:<br>
``blaster, collector, repair, afterburner, rocket, orbitalstrike, aggrobomb, mine, stundome, stickybomb, magnettrap, shield, protector, scramble, aggrobeacon, stun, thermoblast, taunt, sniper, attackdroid, speedactuator, aimcomp, perforator", dmgbuff, lightningchain``
