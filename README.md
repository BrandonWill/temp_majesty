# Majesty Gold HD Modding Toolkit

A complete toolset for modding Majesty Gold HD — sprite extraction/injection, quest generation,
custom spells, and AI overhaul. Fully reverse-engineered binary formats with in-game verified results.

**Repo:** https://github.com/BrandonWill/temp_majesty

## Project Overview

This repo contains:
1. **Python modding tools** — CAM reader/writer, sprite extractor/injector
2. **Quest Map Generator** — Programmatic .q file generation without RGSEditor
3. **IceSpell mod** — Custom freeze spell (standalone mod format, `.mmxml`)
4. **IceSpell_Quest** — Test quest with Ice Spell + AI opponent (self-contained `.mqxml`)
5. **Game data files** — Original Data/, DataMX/, Quests/, SDK/ for reference and modding

## Repository Structure

```
├── cam_reader.py              # Parse CAM archive files
├── cam_writer.py              # Repack CAM archives with modifications
├── sprite_extractor.py        # Extract sprites as PNGs with correct colors
├── sprite_injector.py         # Encode PNGs back into TILE RLE format
├── RESEARCH_NOTES.md          # Detailed binary format reverse-engineering notes
├── README.md                  # This file
│
├── IceSpell/                  # Ice Freeze spell — standalone mod (.mmxml)
│   ├── IceSpell.mmxml         # Mod definition (game loads this)
│   ├── Data/                  # Compiled BCD, XMLs, Quest_maindata.cam
│   ├── GPL/                   # GPL source, globals, compiler project
│   ├── sprites/               # Raw TILE frame data
│   ├── preview/               # PNG previews of overlay sprites
│   ├── utility/               # Sprite generation scripts
│   ├── TODO.md                # Current status + next steps
│   └── deploy.bat             # Deploy to Mods folder
│
├── IceSpell_Quest/            # Test quest — Ice Spell + AI + map
│   ├── Quest.mqxml            # Quest definition with DataConfiguration
│   ├── Quest.q                # Binary map template (RGSEditor-generated)
│   ├── Quest.rgs              # Terrain data
│   ├── Data/                  # Quest-specific data (BCD, XMLs, CAM)
│   ├── GPL/                   # Quest GPL source
│   ├── MyAI/                  # AI opponent (Dwarfeh AI fork)
│   ├── VISUAL_VERIFICATION.md # Test results and screenshot analysis
│   └── crash_troubleshooting.md # Crash analysis notes
│
├── QuestMapGenerator/         # Programmatic .q file generator
│   ├── quest_map_generator.py # Parser + writer + CLI
│   ├── test_all_quests.py     # Validation suite (37/37 pass)
│   └── *.md                   # Reference docs for terrain/buildings
│
├── Data/                      # Original game data files
├── DataMX/                    # Expansion data files
├── Quests/                    # Original quest .q files (22)
├── QuestsMX/                  # Expansion quest .q files (14)
├── MyQuest/                   # Minimal test quest (RGSEditor template)
├── SDK/                       # Game SDK (gplbcc.exe, docs, examples)
├── Music/                     # Game music tracks
└── utility/                   # Scratch scripts (gitignored)
```

## Tools

| File | Purpose |
|------|---------|
| `cam_reader.py` | Parse CAM archive files (sections, file entries, offsets) |
| `sprite_extractor.py` | Extract sprites as PNGs with correct palette colors |
| `sprite_injector.py` | Encode PNGs back into TILE RLE format |
| `cam_writer.py` | Repack CAM archives with modified/replaced entries |
| `QuestMapGenerator/quest_map_generator.py` | Parse/validate/generate .q quest templates |

## Quick Start

```bash
# List all sprite records
python sprite_extractor.py --cam Data/maindata.cam --list

# Extract a unit's walk frames
python sprite_extractor.py --cam Data/maindata.cam --extract AVA1 Walk

# Round-trip test a tile
python sprite_injector.py --cam Data/maindata.cam --roundtrip --tile-idx 3547

# Repack CAM with a modified tile
python cam_writer.py --cam Data/maindata.cam --replace-tile 3547 --tile-data new.bin --output modded.cam

# Generate a test quest
python QuestMapGenerator/quest_map_generator.py generate --name IceTest --output output/IceTest --lairs "BBw1:Ice Cave:N"

# Validate all quest files
python QuestMapGenerator/test_all_quests.py
```

## IceSpell Mod — Current Status

A custom Ice Freeze spell that Ice Elementals cast on nearby units.

| Feature | Status |
|---------|--------|
| Mod loads in game | ✅ Working (requires valid GUID from RGSEditor) |
| IceElemental spawns from Ice Cave | ✅ Working |
| Freeze spell targets + immobilizes | ✅ Working (full cycle: freeze → hold → unfreeze) |
| Grey petrify visual on freeze | ✅ Brief start animation plays |
| Custom ice overlay sprite | ⚠️ Rendering system works (XR47 confirmed); custom ice frames may be too subtle |
| Targeting (avoids buildings/dead/already-frozen) | ✅ Guards working |
| Freeze timer + unfreeze | ✅ Working |
| Targeting spam (re-casts on frozen target) | ❌ Needs fix — wastes AI cycles |

**Deployment:** The `IceSpell/` folder is junction-linked to `Documents\My Games\MajestyHD\Mods\IceSpell`.
The `IceSpell_Quest/` folder is junction-linked to `Documents\My Games\MajestyHD\Quests\IceSpell_Quest`.
Edits in the repo are immediately live in-game — no copying needed.

**Next steps:** See `IceSpell/TODO.md` for detailed IMAG format analysis and remaining work.

## Format Status

| Component | Status |
|-----------|--------|
| CAM container format | ✅ Fully decoded |
| TILE sprite pixel format | ✅ Cracked — 8-bit paletted, per-row RLE |
| SPLT palette system | ✅ Decoded (854 palettes) — **read-only** |
| IMAG animation metadata | ✅ Decoded for reading; writing custom IMAG partially working |
| PNG extraction | ✅ Working |
| TILE encoder (PNG → game) | ✅ Round-trip verified |
| CAM repacker | ✅ Identity repack + modified tiles |
| .q quest map format | ✅ Fully decoded — parser + writer (37/37 files) |
| .mmxml mod format | ✅ Working (requires RGSEditor-generated GUID) |
| .mqxml quest format | ✅ Working |
| GPL compilation | ✅ Working via gplbcc.exe |
| Custom overlays (sprite rendering) | ✅ Confirmed working (XR47 test rendered from quest CAM) |

## Game Modes and Data Loading

**Original mode** — loads `Data/` only  
**Expansion mode** — loads `Data/` then overlays `DataMX/`  
**Mods (.mmxml)** — loaded from `Documents\My Games\MajestyHD\Mods\<name>\`  
**Quests (.mqxml)** — loaded from `Documents\My Games\MajestyHD\Quests\<name>\`

### Mod/Quest DataConfiguration

Mods and quests use XML `<DataConfiguration>` to declare what to load:
```xml
<Dataset base="MajestyExpansion">
    <Load>
        <Template>Quest.q</Template>           <!-- map template (quests only) -->
        <Constants>Quest.rgs</Constants>       <!-- terrain (quests only) -->
        <Descriptions>Data\MyFile.xml</Descriptions>  <!-- unit/spell/overlay defs -->
        <CAM>Data\Quest_maindata.cam</CAM>     <!-- custom sprites -->
        <GPL>
            <Target>Data\MyMod.bcd</Target>    <!-- compiled bytecode -->
            <Source>GPL\MySource.gpl</Source>   <!-- runtime source files -->
            <Source>GPL\MyData.dat</Source>     <!-- runtime data files -->
        </GPL>
    </Load>
</Dataset>
```

## Key Constraints

| Rule | Detail |
|------|--------|
| Don't modify SPLT palettes | Crashes the game |
| Use backslashes in mmxml/mqxml paths | Forward slashes may not work on Windows |
| GUIDs must be valid | Use RGSEditor to generate; hand-crafted GUIDs are rejected |
| CAM IMAG records must match engine format | Malformed IMAG causes crash on zone load |
| GPL has no error handling | Guard every function entry against dead/building/lair targets |

## Requirements

```
pip install Pillow numpy
```

## Architecture

```
.mmxml / .mqxml (mod/quest definition)
  └── DataConfiguration
        ├── Descriptions (XML) → unit types, spells, overlays
        ├── CAM → IMAG (animation metadata) + TILE (pixels) + SPLT (palettes)
        └── GPL → .bcd bytecode + .gpl/.dat source files
              └── Functions called by spell actions → $createeffector, $SetAttribute, etc.

unittype.cam / Characters.xml
  └── Unit: ImageIDBase = "BVi1" (links to IMAG in maindata.cam)

action.cam / Actions.xml  
  └── Spell: GPLFunction = "Ice_Freeze_Begin" (called when cast)

Overlays.xml
  └── Overlay: Name = "freeze_effector", ImageIDBase = "IR01" (IMAG in Quest_maindata.cam)
```
