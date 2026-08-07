# Installation
- Edit your ships weapon configuration in the settings.json<br>
- Install the following modules using pip:<br>
``pip install pyautogui keyboard colorama datetime requests opencv-python pypiwin32 mss easyocr customtkinter``<br>

# How to use

Run ``python PGBot.py`` (Or on windows just start run.bat to start the bot)<br>
Make sure to have Pirate Galaxy open on your main monitor.<br>

# Settings

You can also adjust the settings inside the GUI after starting the bot.

```
{
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
        "sniper": [
            "blaster",
            "collector",
            "repair",
            "afterburner",
            "sniper",
            "attackdroid",
            "orbitalstrike",
            "dmgbuff"
        ],
        "custom": [
            "blaster",
            "collector",
            "repair",
            "afterburner",
            "sniper",
            "",
            "orbitalstrike",
            ""
        ]
    }
}
```

- Change "skillset" to any of the presets in list.<br>
Possible Skills:<br>
``blaster, collector, repair, afterburner, rocket, orbitalstrike, aggrobomb, mine, stundome, stickybomb, magnettrap, shield, protector, scramble, aggrobeacon, stun, thermoblast, taunt, sniper, attackdroid, speedactuator, aimcomp, perforator, dmgbuff, lightningchain``
