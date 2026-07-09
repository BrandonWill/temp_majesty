# Majesty Gold HD Modding - Project Context

## Workspace Layout

This workspace IS the git repo (https://github.com/BrandonWill/temp_majesty). Push directly from here.

### Modding Tools (workspace root)
- `cam_reader.py` — Parses CAM archive files (the game's binary container format)
- `sprite_extractor.py` — Extracts sprites as PNGs from maindata.cam with correct colors
- `sprite_injector.py` — Encodes PNGs back into the game's TILE RLE format
- `cam_writer.py` — Repacks CAM archives with modified/replaced entries
- `RESEARCH_NOTES.md` — Detailed reverse-engineering notes on the binary formats
- `README.md` — High-level documentation of the modding toolkit
- `utility/` — Scratch/investigation scripts (gitignored)

### Game Data (tracked in git)
- `Data/` — Original game mode data files (maindata.cam, unittype.cam, action.cam, etc.)
- `Data/maindata.cam` — The main game sprite archive (91.6 MB, tracked in git via LFS-like history)
- `DataMX/` — Expansion mode data files (overlays on top of base Data/)
- `SDK/` — Quest SDK with GPL source, examples, documentation, and Gplbcc.exe compiler
- `MyQuest/` — The user's custom quest project
- `Quests/` — Original game quest files
- `QuestsMX/` — Expansion quest files
- `Music/` — Game music tracks

## Key Technical Facts

### CAM File Format
- Container with sections (IMAG, TILE, SPLT, CUT, DUNT, DACT, DMOV, etc.)
- Parsed by `cam_reader.py`, repacked by `cam_writer.py`
- Each section has named file entries with offset + size

### TILE Sprite Format (Version 3)
- Header: 16 bytes + 6 zeros + u32 palette_id + height×u32 offset table
- Row RLE: repeated `[u16 x_position][u8 count][u8 flags][count pixel bytes]`
- x_position is ABSOLUTE column (not relative skip)
- flags 0x80 = last segment in row
- Pixel bytes are palette indices into SPLT section
- Palette index 0 = transparent; indices 248-255 = shadow/blend (magic pink)

### Critical Constraints
- **SPLT palettes are READ-ONLY** — modifying them crashes the game
- **Sprites must use existing palette colors** — quantize new art to the target palette
- **Original game mode** reads from `Data/maindata.cam` and `Data/unittype.cam`
- **Expansion mode** first loads base Data/, then overlays `DataMX/mx_maindata.cam` and `DataMX/mx_Unittype.cam`
- **In-game pixel modification confirmed working** in original mode (tested: all walk frames to solid color → visible change)

### Game Data Architecture
```
unittype.cam → defines units (ImageIDBase, stats, spells)
maindata.cam → IMAG section (animation metadata) + TILE section (pixel data) + SPLT (palettes)
action.cam → spell/action definitions (DACT section)
M_Overlays.xml → visual effect overlay definitions
M_ParticleSystems.xml → particle effect definitions  
M_Characters.xml → unit type definitions (XML source for unittype.cam)
M_Actions.xml → action definitions (XML source for action.cam)
```

### GPL Scripting
- GPL is the game's scripting language for quest/gameplay logic
- Source files in `SDK/OriginalQuests/Gpl/` (base) and `GplMx/` (expansion)
- Compiled to `.bcd` bytecode by `Gplbcc.exe`
- Key GPL capabilities:
  - `$createeffector(agent, "name", duration)` — attach visual effect + timer
  - `$adjustattribute(agent, #ATTRIB_HP, amount)` — modify HP/stats
  - `$SetAttribute(agent, #attribute, value)` — set status flags
  - `$GetAttribute(agent, #attribute)` — read status
  - `$SpecifyIntent(agent, #intent)` — force behavior (flee, petrified, etc.)
  - `$CheckEffector(agent, "name")` — check if effect is active
  - `$randomnumber(N)` — random 0 to N
  - `$IsDead(agent)` — death check
- Duration values in GPL are in **game ticks/milliseconds** (need verification — the user noted 19000 may not equal 19 real seconds; likely tied to game speed/frame timing)
- Status effects use the effector system: a visible overlay + an invisible timer effector

### Petrification System (Template for New Status Effects)
The existing petrify system uses:
1. **Action XML** — defines the spell (ID, GPLFunction, timeout, spell type)
2. **Two overlays** — `petrify_effector` (visible grey stone overlay) + `petrify_icon` (invisible timer that calls end function)
3. **GPL functions** — `Petrify_Begin` (applies effect) and `Petrify_End` (removes it)
4. **Attributes** — `#ATTRIB_HasEffectPetrify` flag, `#ATTRIB_IsFrozen` flag
5. **Intent** — `#intent_petrified` forces unit to stop acting
6. **IsFrozen check** — AI uses this to skip petrified units in decision trees

### Creating New Visual Effects (Overlays)
To create a new visual overlay (like an ice/frozen effect):
1. Need sprite frames in TILE format inside a CAM file
2. Need an IMAG record pointing to those TILE frames
3. The overlay is non-directional (no 8-way facing needed)
4. Referenced by `ImageIDBase` in the overlay XML definition
5. Sprite art must use colors from an existing SPLT palette

The sprite frames for an overlay are typically:
- A short animation loop (shimmer, pulse, sparkle)
- Rendered ON TOP of the affected unit
- Transparent background with the effect drawn in the character's area
- The existing `petrify_effector` (MRB1) sprite shows how these look

### Quest Mod Structure (WrathOfKrolm Example)
```
Quest.mqxml — quest metadata + DataConfiguration (what files to load)
Data/Quest_maindata.cam — custom sprites (IMAG + TILE + SPLT)
Data/Quest_Characters.xml — unit definitions
Data/Quest_Actions.xml — spell/action definitions
Data/Quest_Overlays.xml — visual effect definitions
GPL/Quest.gpl — gameplay logic
```

## Working With This Project

### Running Commands
- All Python scripts run from the workspace root
- `Data/maindata.cam` is the canonical sprite archive (tracked in git, scripts default to it)
- Use `python utility/test_decoder.py` as the scratch/investigation script (trusted command)
- The `utility/` folder is gitignored — use it for throwaway scripts and experiments
- This workspace is the git repo — commit and push directly (no more copying to a separate folder)

### Testing In-Game
- Test sprite changes in **original game mode** (not expansion)
- For expansion mode, modify files in `DataMX/` folder
- Always backup original game files before replacing
- The game needs `maindata.cam` to exist but may cache some data from it

### Pre-Flight Validation (run before loading game)
The game crashes silently with no useful error messages. These checks catch most crash causes offline:

1. **TILE round-trip** — Every generated TILE must decode back to identical pixels:
   `python sprite_injector.py --cam Data/maindata.cam --roundtrip --tile-idx <idx>`
2. **CAM structural integrity** — After any repack, re-read with `cam_reader.py` and verify:
   - All section file counts match expected values
   - All file offsets are within the file bounds
   - No palette modifications in SPLT entries (crashes the game)
3. **XML cross-references** — Every `ImageIDBase` in overlay/character/action XMLs must
   have a matching IMAG record in the CAM file being loaded
4. **GPL compilation** — Always compile GPL with `Gplbcc.exe` before loading. Syntax errors,
   undefined functions, and type mismatches are caught here without needing the game.
5. **Effector name consistency** — Every `$createeffector(agent, "name", ...)` in GPL must
   have a matching overlay definition with that exact ID/Name in the XML
6. **Palette index bounds** — Every pixel byte in generated TILE data must be 0-255,
   and palette_id must reference a valid SPLT entry index

### Defensive GPL Coding Patterns
GPL has no try/catch. Guard every function entry:
```gpl
function Freeze_Begin(agent ThisAgent, agent target)
begin
    If ($IsDead(target)) return;
    If (target's "Type" == "Building") return;
    If (target's "Type" == "Lair") return;
    If ($GetAttribute(target, #ATTRIB_HasEffectFreeze) == 1) return;
    // ... rest of logic
end
```

Use `$DebugOut` for logging (check SDK/Documentation/GPL Debugger.pdf for how to view output):
```gpl
$DebugOut(911, "Freeze_Begin called on: ", target);
```

### constants.rgs
Binary terrain/map definition file edited by RGSeditor. Defines terrain tile combinations,
height/slope data for the map. NOT a code constants file despite the name. Not relevant
to spell/sprite modding.

### Q File Format (Reverse-Engineered)

The `.q` file is the binary quest map produced by RGSEditor. Key findings:

**Header (16 bytes):**
- Bytes 0-3: Magic "RGMa" (editor version) or "RGM6" (base game version)
- Bytes 4-7: zeros
- Bytes 8-11: Same magic repeated
- Bytes 12-15: zeros

**Strings (starting at offset 0x10):**
- Null-terminated quest name (e.g., "basicAI", "WrathOfKrolm", "BARREN_WASTE")
- Null-terminated pattern/module name (e.g., "pattMyAI", references the GPL entry function)

**Map parameters (after strings):**
- Several u32 values encoding map dimensions, seed/checksum, etc.
- MyQuest uses dimensions ~256x256 (value 0x00000100)
- WrathOfKrolm and base quests use 32768x32768 (0x00008000)
- Followed by "NONE"/"none" section markers

**Object entries (bulk of file):**

Two types identified:

1. **Short entries (24 bytes each)** — Spawner definitions:
   - 4-byte Object_ID (e.g., "BVr1" = Ratman Champion)
   - u32 value (spawn count or index, values like 9-17 seen)
   - 16 bytes zeros/flags (includes a u32 = 1 at offset +16)
   - These come in groups of 4 (spacing: 24,24,24,73) representing lair spawn lists
   - A u32 count precedes each group (e.g., "04 00 00 00" = 4 entries)

2. **Long entries (29+ bytes each)** — Placed buildings/lairs:
   - 4-byte Object_ID (e.g., "BBw1" = Ice Cave, "ABJ1" = Palace)
   - u32 = 0
   - Null-terminated description string (e.g., "Ice Cave", "Goblin Fortress", "Palace")
   - Position data follows (encoding not fully cracked — appears to be in the u32 before/after)

**Object ID conventions:**
- `BV**` = monsters/characters (BVm1=Ice Dragon, BVx1=Yeti, BVN1=Daemon, BVr1=Ratman Champion)
- `BB**` = monster lairs (BBw1=Ice Cave, BBz1=Goblin Fortress, BBH1=Goblin Camp, BBx1=Rat's Nest)
- `AB**` = player buildings (ABJ1=Palace)

**Coordinate encoding (PARTIALLY UNDERSTOOD):**
- The u32 value immediately before each Long_Entry lair appears to encode position
- Values seen: 1476395008 (Ice Cave), 1258291200, 1157627904 (Snake Pits)
- These could be fixed-point coordinates or packed x,y pairs — needs more analysis
- Comparing multiple quests with known map layouts against these values would crack it

**File sizes:**
- Minimal (MyQuest, ~20 objects): 2469 bytes
- Medium (WrathOfKrolm): 3198 bytes  
- Large (Brashnard, many lairs): 4870 bytes

**RGS terrain file:**
- Magic "RGCB" (newer) or "RGCA" (older)
- Quest.rgs: 49833 bytes, Data/constants.rgs: 28012 bytes
- Contains terrain heightmap/type data
- For test quests, reusing an existing .rgs is the simplest approach

**Exploration script:** `utility/test_decoder.py` was used for this research.
The Quests/ folder has 38 .q files available for comparison analysis.

### RGSEditor
- Located at `SDK/RGSeditor.exe` (also decompiled sections in `SDK/RGSeditor/`)
- Creates `.q` map files and `.rgs` terrain files
- Also used to configure mods (`.mmxml`) — sets GPL Bytecode and Game Object Definitions fields
- For quest creation: saves Quest.q + Quest.mqxml, then you hand-edit the mqxml to add mod references

### What's Proven Working
- Extract any sprite: `python sprite_extractor.py --cam Data/maindata.cam --extract AVA1 Walk`
- Encode sprites back: `python sprite_injector.py --cam Data/maindata.cam --roundtrip --tile-idx 3547`
- Repack CAM: `python cam_writer.py --cam Data/maindata.cam --replace-tile 3547 --tile-data new.bin --output modded.cam`
- Swap unit appearance via unittype.cam: change ImageIDBase field in DUNT entry

### Future Scope: Automated Test Quest Generator
To speed up in-game testing, explore auto-generating a minimal "test harness" quest:
- Use a pre-made flat terrain `.q` file (binary map — RGSeditor format, needs understanding)
- Auto-generate `.mqxml` with DataConfiguration loading the mod's CAM/XML/BCD files
- GPL script that immediately on quest start: spawns the test unit, gives resources, triggers the spell
- Goal: compile → launch game → select test quest → see feature in under 10 seconds
- The `.q` binary map format is unexplored — understanding it would unlock full automation
- Alternatively: keep one hand-made minimal test map and just swap the GPL/XML/CAM references
