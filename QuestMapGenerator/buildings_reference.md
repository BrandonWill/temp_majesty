# Building & Lair Reference

Complete catalog of all buildings and lairs from the base game and expansion.
Extracted from `SDK/OriginalQuests/Data/M_Buildings.xml` and `SDK/OriginalQuests/DataMX/MX_Buildings.xml`.

**Total:** 117 buildings (91 base + 26 expansion)

## Player Buildings (AB* prefix)

Buildings the human player can construct or that appear as player structures.

### Hero Guilds

| ID | Name | Cost | HP | Produces | Max Members | Upgrades |
|---|---|---|---|---|---|---|
| `ABV1` | Warriors Guild | 800 | 700 | Paladin, Warrior, Warrior_of_Discord | 4 |  |
| `ABW1` | Rangers Guild | 700 | 250 | Ranger | 4 |  |
| `ABW1` | Rangers Guild | 700 | 250 | Ranger | 4 |  |
| `ABX1` | Rogues Guild | 600 | 250 | Rogue | 4 | Rogues_Guild2 |
| `ABX2` | Rogues Guild Level 2 | 850 | 350 | Rogue | 4 |  |
| `ABY1` | Wizards Guild | 1500 | 350 | Wizard | 4 | Wizards_Guild2 |
| `ABY2` | Wizards Guild Level 2 | 2500 | 500 | Wizard | 4 | Wizards_Guild3 |
| `ABY3` | Wizards Guild Level 3 | 3500 | 700 | Wizard | 4 |  |
| `ABb1` | Dwarven Settlement | 1250 | 600 | Dwarf | 3 |  |
| `ABc1` | Elven Bungalow | 750 | 300 | Elf | 2 |  |
| `ABf1` | Gnome Hovel | 100 | 75 | Gnome | 3 |  |
| `ABm1` | Outpost | 3000 | 400 |  | 6 |  |
| `ABr1` | Embassy | 3000 | 300 | Adept, Barbarian, Cultist, Healer, Monk, Paladin, Priestess, Ranger, Rogue, Solarus, Warrior, Warrior_of_Discord, Wizard, Dwarf, Elf, Gnome | 2 |  |

### Temples

| ID | Name | Cost | HP | Produces | Max Members | Upgrades |
|---|---|---|---|---|---|---|
| `ABO1` | Temple to Agrela | 1000 | 250 | Healer | 4 | Temple_Agrela2 |
| `ABO2` | Temple to Agrela Level 2 | 1500 | 300 | Healer | 4 | Temple_Agrela3 |
| `ABO3` | Temple to Agrela Level 3 | 2600 | 400 | Healer | 4 |  |
| `ABP1` | Temple to Dauros | 1600 | 400 | Monk | 4 | Temple_Dauros2 |
| `ABP2` | Temple to Dauros Level 2 | 2200 | 500 | Monk | 4 | Temple_Dauros3 |
| `ABP3` | Temple to Dauros Level 3 | 3400 | 700 | Monk | 4 |  |
| `ABQ1` | Temple to Fervus | 900 | 235 | Cultist | 4 | Temple_Fervus2 |
| `ABQ2` | Temple to Fervus Level 2 | 1300 | 336 | Cultist | 4 | Temple_Fervus3 |
| `ABQ3` | Temple to Fervus Level 3 | 2500 | 444 | Cultist | 4 |  |
| `ABR1` | Temple to Helia | 1000 | 400 | Solarus | 4 | Temple_Helia2 |
| `ABR2` | Temple to Helia Level 2 | 2000 | 600 | Solarus | 4 |  |
| `ABS1` | Temple to Krolm | 900 | 800 | Barbarian | 4 |  |
| `ABS1` | Temple to Krolm | 900 | 800 | Barbarian | 6 |  |
| `ABT1` | Temple to Krypta | 1400 | 350 | Priestess | 4 | Temple_Krypta2 |
| `ABT2` | Temple to Krypta Level 2 | 1800 | 425 | Priestess | 4 | Temple_Krypta3 |
| `ABT3` | Temple to Krypta Level 3 | 2200 | 475 | Priestess | 4 |  |
| `ABU1` | Temple to Lunord | 1000 | 350 | Adept | 4 | Temple_Lunord2 |
| `ABU2` | Temple to Lunord Level 2 | 2000 | 500 | Adept | 4 |  |

### Economic & Service Buildings

| ID | Name | Cost | HP | Upgrades | Src |
|---|---|---|---|---|---|
| `ABC1` | Blacksmith | 500 | 250 | Blacksmith2 | Base |
| `ABD1` | Fairgrounds | 3000 | 800 |  | Base |
| `ABF1` | Inn | 400 | 120 |  | Base |
| `ABG1` | Library | 600 | 100 | Library2 | Base |
| `ABH1` | Marketplace | 1500 | 200 | Marketplace2 | Base |
| `ABL1` | Trading Post | 600 | 150 |  | Base |
| `ABh1` | Royal Gardens | 1200 | 250 |  | Base |
| `ABk1` | Statue | 600 | 60 |  | Base |
| `ABl1` | Magic Bazaar | 1400 | 200 | MagicBazaar2 | Expansion |
| `ABo1` | Hall Of Champions | 1000 | 300 |  | Expansion |
| `ABp1` | Mausoleum | 1500 | 300 |  | Expansion |
| `ABq1` | Sorcerers Abode | 2000 | 250 | SorcerersAbode2 | Expansion |

### Defense Buildings

| ID | Name | Cost | HP | Sight | Upgrades |
|---|---|---|---|---|---|
| `ABB1` | Ballista Tower | 1000 | 350 | 300 |  |
| `ABE1` | Guardhouse | 600 | 200 | 400 | Guardhouse2 |
| `ABE2` | Guardhouse Level 2 | 500 | 275 | 450 |  |
| `ABM1` | Wizards Tower | 500 | 250 | 300 |  |
| `ABY1` | Wizards Guild | 1500 | 350 | 150 | Wizards_Guild2 |
| `ABY2` | Wizards Guild Level 2 | 2500 | 500 | 175 | Wizards_Guild3 |
| `ABY3` | Wizards Guild Level 3 | 3500 | 700 | 200 |  |

### Special/Non-Buildable Player Structures

| ID | Name | HP | Notes |
|---|---|---|---|
| `ABA0` | Building | 0 |  |
| `ABA1` | Siege Marker | 0 | NoFlaggable, NotSpellTarget, NotInMiniMap |
| `ABC2` | Blacksmith Level 2 | 300 | HasGoldToolTip |
| `ABC3` | Blacksmith Level 3 | 400 | HasGoldToolTip |
| `ABE2` | Guardhouse Level 2 | 275 | NumberedName |
| `ABG2` | Library Level 2 | 200 | NumberedName, HasGoldToolTip |
| `ABH2` | Marketplace Level 2 | 250 | NumberedName, HasGoldToolTip |
| `ABH3` | Marketplace Level 3 | 300 | NumberedName, HasGoldToolTip |
| `ABJ1` | Palace | 550 | HasGoldToolTip |
| `ABJ2` | Palace Level 2 | 700 | HasGoldToolTip |
| `ABJ3` | Palace Level 3 | 1000 | HasGoldToolTip |
| `ABJ4` | Dark Palace | 1000 |  |
| `ABN1` | Sewer Entrance | 200 | NoFlaggable, NotSpellTarget, NumberedName |
| `ABa1` | Elven Lounge | 130 | HasGoldToolTip |
| `ABd1` | Gambling Hall | 180 | HasGoldToolTip |
| `ABe1` | House | 75 | NumberedName, HasGoldToolTip |
| `ABg1` | Gazebo | 150 | HasGoldToolTip |
| `ABj1` | Fountain | 100 | HasGoldToolTip |
| `ABl2` | Magic Bazaar Level 2 | 250 |  |
| `ABl3` | Magic Bazaar Level 3 | 300 |  |
| `ABq2` | Sorcerers Abode Level 2 | 300 |  |
| `ABq3` | Sorcerers Abode Level 3 | 350 |  |

## Monster Lairs (BB* prefix)

Structures belonging to the Monster faction. Split into actual lairs (spawn monsters),
quest objectives, and decorative markers.

### Actual Monster Lairs (spawn enemies, have significant HP)

| ID | Name | HP | Gold Reward | Sight | Src |
|---|---|---|---|---|---|
| `BBA1` | Creature Den | 300 | 50 | 75 | Base |
| `BBB1` | Dark Castle | 800 | 1000 | 100 | Base |
| `BBB2` | Evil Castle | 800 | 1500 | 100 | Base |
| `BBB3` | Ancient Castle | 800 | 1500 | 100 | Base |
| `BBB4` | Abandoned Castle | 800 | 1500 | 100 | Base |
| `BBH1` | Goblin Camp | 200 | 250 | 100 | Base |
| `BBI1` | Goblin Hovel | 100 | 50 | 64 | Base |
| `BBK1` | Ruined Altar | 500 | 300 | 75 | Base |
| `BBL1` | Ruined Keep | 500 | 150 | 100 | Base |
| `BBM1` | Ruined Shrine | 500 | 200 | 75 | Base |
| `BBa1` | Brashnard's Sphere | 200 | 100 | 0 | Base |
| `BBb1` | Dragon Lair | 600 | 1000 | 0 | Base |
| `BBc1` | Dragon King Tomb | 1500 | 500 | 100 | Base |
| `BBd1` | Elven Hideout | 1000 | 15000 | 250 | Base |
| `BBh1` | Liche Queen Lair | 1000 | 15000 | 0 | Base |
| `BBi1` | Slave Pits | 350 | 100 | 0 | Base |
| `BBl1` | Tower Prison | 1000 | 100 | 0 | Base |
| `BBm1` | Witch King Tower | 1000 | 15000 | 90 | Base |
| `BBO1` | Ancient Barrow | 300 | 0 | 200 | Expansion |
| `BBP1` | Archaic Tomb | 400 | 3000 | 200 | Expansion |
| `BBQ1` | Fortress of Ixmil | 1000 | 5000 | 300 | Expansion |
| `BBS1` | Snake Pit | 400 | 1300 | 200 | Expansion |
| `BBT1` | Spire Of Death | 500 | 500 | 300 | Expansion |
| `BBu1` | Ancient Graveyard | 200 | 400 | 120 | Expansion |
| `BBv1` | Broken Sewer Main | 150 | 0 | 200 | Expansion |
| `BBw1` | Ice Cave | 400 | 1000 | 100 | Expansion |
| `BBx1` | Rat's Nest | 150 | 0 | 200 | Expansion |
| `BBy1` | Goblin Watchtower | 150 | 0 | 255 | Expansion |
| `BBz1` | Goblin Fortress | 300 | 1000 | 250 | Expansion |

### Quest Objective Sites (unique loot, quest-specific)

| ID | Name | HP | Gold | Notes |
|---|---|---|---|---|
| `BBe1` | Magic Sword Site | 200 | 100 | Quest item location |
| `BBf1` | Hidden Chalice Site | 1000 | 100 | Quest item location |
| `BBg1` | Hidden Ring Site | 500 | 100 | Quest item location |
| `BBp1` | Crown Site | 1000 | 30000 | Quest item location |

### Ambient/Decorative (markers, signs, graves, chests)

| ID | Name | HP | Notes |
|---|---|---|---|
| `BBi2` | Slave Cross | 50 | Quest decoration |
| `BBs1` | Wooden Banner | 10 | Marker |
| `BBs2` | Goblin marker | 0 | Marker |
| `BBs3` | Goblin marker | 0 | Marker |
| `BBs4` | Runic Marker | 20 | Marker |
| `BBs5` | Note Stump | 5 | Marker |
| `BBs6` | Obelisk | 20 | Marker |
| `BBs7` | Fancy Iron Sign | 10 | Marker |
| `BBs8` | Wooden Sign | 10 | Marker |
| `BBs9` | Stone Tablet | 10 | Marker |
| `BBt1` | Treasure Chest | 20 | Loot |
| `BBt2` | Treasure Chest | 10 | Loot |
| `BBt3` | Treasure Chest | 20 | Loot |
| `BBt4` | Treasure Chest | 20 | Loot |

### Auto-Spawned Special Structures (do NOT place manually unless specifically needed)

These spawn automatically on the player's base area based on game events/conditions.
They won't cause issues if placed manually, but are typically not included in quest templates
since the game creates them on its own when conditions are met.

| ID | Name | HP | Notes |
|---|---|---|---|
| `BBJ1` | Graveyard | 250 | Auto-spawns near palace when heroes die. NoFlaggable, NotSpellTarget |
| `ABN1` | Sewer Entrance | 200 | Auto-spawns near palace based on city growth. NoFlaggable, NotSpellTarget |

## Quick Reference for Quest Generation

Common buildings/lairs used when generating test quests:

| Object_ID | Description | Use In Generator |
|---|---|---|
| `ABJ1` | Palace | Always placed at center (M) |
| `BBH1` | Goblin Camp | Common early-game lair |
| `BBx1` | Rat's Nest | Common early-game lair |
| `BBz1` | Goblin Fortress | Mid-game lair |
| `BBw1` | Ice Cave | Expansion lair (ice themed) |
| `BBS1` | Snake Pit | Common lair |
| `BBB1` | Dark Castle | Late-game lair |
| `BBb1` | Dragon Lair | End-game boss lair |
| `BBA1` | Creature Den | Generic monster den |