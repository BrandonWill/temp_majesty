# Majesty Gold HD Modding - Project Context

## Detailed Steering Files (manual inclusion)

When working on specific subsystems, include the relevant detailed steering file for full context:
- **Quest/mod creation** → `#quest-and-mod-creation` (MQXML format, RGS workflow, file structure, XML schema)
- **CAM/sprite work** → `#cam-and-sprites` (TILE format, palettes, sprite encoding/decoding)
- **GPL scripting** → `#gpl-reference` (undocumented primitives, engine gotchas, patterns, debugging)

## TODO Structure

Work is tracked across multiple TODO files:
- **`TODO.md`** — Master TODO. High-level summary of all active work. Cross-references subfolder TODOs.
- **`TODO-Ghidra.md`** — EXE patching / Ghidra disassembly work. Delegate to the Ghidra machine session.
- **`IceSpell/TODO.md`** — IceSpell mod-specific tasks (sprites, GPL, in-game testing).
- **`SMNUResearch/FUTURE_TODO.md`** — Panel system research, SMNU compiler, navigation patches.

**Rules:**
- When adding Ghidra/exe-patch tasks, put them in `TODO-Ghidra.md`, not the root TODO.
- When editing any subfolder TODO, keep the root TODO.md summary in sync (a hook reminds you).
- Subfolder TODOs contain detailed implementation steps; root TODO has one-liner summaries.

## Workspace Layout

This workspace IS the git repo (https://github.com/BrandonWill/temp_majesty). Push directly from here.

### Modding Tools (workspace root)
- `cam_reader.py` — Parses CAM archive files (the game's binary container format)
- `sprite_extractor.py` — Extracts sprites as PNGs from maindata.cam with correct colors
- `sprite_injector.py` — Encodes PNGs back into the game's TILE RLE format
- `cam_writer.py` — Repacks CAM archives with modified/replaced entries
- `CAM_MODDING_GUIDE.md` — Task-oriented modding guide (includes binary format appendix)
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

### Testing Requirements
- **Run tests before committing/pushing.** All existing tests must pass.
- **New code changes require tests.** Any new feature, bug fix, or refactor must include
  or update unit tests that cover the change.
- Test commands:
  - `python QuestMapGenerator/test_rgs_format.py` — RGS format parser/writer tests (34 tests)
  - `python -m pytest QuestMapGenerator/test_rgs_format.py -v` — same, with pytest (if installed)
  - `python tests/test_str_tool.py` — STR tool tests (if applicable)
- If a test fails after your change, fix the code or update the test before committing.
- For binary format work: always verify byte-perfect roundtrip on `MyQuest/Quest.q`.

### Compiling GPL
- Each mod/quest folder has a `MakeGPL.bat` that compiles GPL source and copies the `.bcd` to `Data/`.
- **Always use `cmd /c MakeGPL.bat`** from the mod/quest folder to compile. Do NOT invoke
  `Gplbcc.exe` manually — the bat handles paths and the copy step.
- If a mod/quest folder does NOT have a `MakeGPL.bat`, copy one from an existing mod
  (e.g., `IceSpell/MakeGPL.bat`) and update the `OUTPUTNAME` and `GPLPROJECTFILE` variables
  to match the new project. Then commit the new bat file.

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

### Q File Format (Reverse-Engineered — UPDATED)

The `.q` file is the binary quest template produced by RGSEditor. It defines the Random
Generation System (RGS) data for procedural map generation. The map is NOT pre-rendered —
it's generated at load time using these patterns + random seed.

**Key concept from SDK documentation:** The .q file encodes a HIERARCHY of placement patterns:
- **Force Pattern** — top level, places Unit Patterns on the overall map (its own grid)
- **Unit Patterns** — mid level, each has a 5×5 layout grid + resolution (tile spacing)
- **Unit Instances** — individual buildings/monsters/landmarks within a Unit Pattern

The 5×5 grid is NOT a fixed position. It's a **probability layout** — marking a unit at multiple
grid cells means the RGS will randomly choose ONE of those positions. The grid is also
randomly rotated each generation for variety.

**Header (16 bytes):**
- Bytes 0-3: Magic "RGMa" (editor) or "RGM6" (base game) or "RGM9" (expansion)
- Bytes 4-7: zeros
- Bytes 8-11: Same magic repeated
- Bytes 12-15: zeros

**Strings (starting at offset 0x10):**
- Null-terminated quest name (e.g., "basicAI", "WrathOfKrolm")
- Pattern name (12 bytes + null, format: 4+4+4 repeating pattern, references GPL entry function)

**Map parameters (after strings):**
- u32 values encoding map size, seed, faction count, starting resources
- Format varies between RGMa/RGM6/RGM9

**Spawner Sections (separated by "NONEnone\0" markers):**
- Each spawner block: [u32 count] [count × 24-byte entries]
- Entry: [4B Monster_ID] [u32 spawn_level] [8B zeros] [u32 active_flag] [4B zeros]
- After entries: [u32 0] [u32 lair_resource] [u32 0] [u32 secondary_resource] + zeros

**Team/Player Definitions (after spawners):**
- Indexed entries: "Human Player\0", "player2_ai\0", "No Name\0" × 5, "Monsters\0"
- Each with active flag and team identifier bytes
- Defines the available factions/teams for the quest

**Region Pattern Section (terrain):**
- Pattern name reference (e.g., "pattpattpattern\0")
- u32 count of Region Patches
- Each Region Patch: [4B terrain_code] [u32 value] [zeros] [u32 flags]
  - terrain_code: "gras" (grass), "snow" (snow), etc.
  - Followed by full terrain pattern names (4+4+4+full format):
    e.g., "grasgrasgrasgrass\0" + landscape ref "xBarxGraxfla\0"
- Defines terrain textures, fractal height, landscape objects (trees/rocks)

**Unit Pattern Placed Groups (the 5×5 grids):**
- Header: [4B terrain_code] [u32 5] [u32 entry_count]
- Each entry: [4B Object_ID] [u32 0] [cstr description\0] [u32 position_count] [position_count × u8]
- Position bytes: ASCII 'A'-'Y' (65-89) mapping to 5×5 grid cells
- position_count > 1 means the unit can appear at MULTIPLE candidate cells (RGS picks one randomly)
- After entries: metadata block [u32 0,3,50,50,50,1,1,0,0,0] + faction name

**Resolution (from SDK doc):** The spacing between grid cells is controlled by the
Resolution dropdown in RGSEditor. "A tile is 32 pixels wide so a resolution of 3 means
that each layout item is placed 96 pixels from its neighbor."

**Force Pattern Section (end of file):**
- Marker: [u32 2] "NONE" (standalone, not "NONEnone")
- [u32 unit_pattern_count] [u32 total_force_entries]
- Force entries: [4B faction_short] [u32 5] [cstr faction_name\0] [u32 active] [u8 map_grid_pos]
- map_grid_pos is 'A'-'Y' (same 5×5 encoding) but on the FORCE PATTERN's map layout
- This determines WHERE on the overall map each faction's Unit Pattern cluster is placed
- Terminated by final metadata block + "Rel@"

**Overlap prevention (from SDK doc):** "The placement code will not allow objects to overlap,
so a minimum spacing will be enforced if the placement would cause an overlap."
Building sizes matter at generation time — the engine adjusts positions to avoid overlap.

**Random rotation (from SDK doc):** "The placement grid is also randomly rotated to add
more variety to the placement of the pattern." So the in-game layout will NOT match the
grid positions literally — it's rotated 0°/90°/180°/270° randomly.

**Object ID conventions:**
- `BV**` = monsters/characters (BVr1=Ratman Champion, BVN1=Daemonwood, BVm1=Ice Dragon)
- `BB**` = monster lairs (BBw1=Ice Cave, BBz1=Goblin Fortress, BBH1=Goblin Camp)
- `AB**` = player buildings (ABJ1=Palace, ABe1=House, ABE1=Guardhouse)
- `AV**` = NPCs/Heroes (pre-placed)
- `BA**` = ambient terrain objects

**File sizes:**
- Minimal (MyQuest, ~35 placed entries): 2469 bytes
- Medium (Krolm, 3 entries with multi-positions): 3191 bytes
- Large (Freestyle, 162 entries): 111500 bytes

**RGS terrain file (.rgs):**
- Magic "RGCB" (newer) or "RGCA" (older)
- Contains terrain heightmap/type data used by the RGS to generate the actual map tiles
- References terrain patterns, fractal settings, and landscape patterns from constants.rgs
- For test quests, reusing an existing .rgs template is the simplest approach

**Exploration scripts:** `utility/test_mapInfo.py` (scratch), `QuestMapGenerator/quest_map_generator.py` (parser/writer).
Quests/ has 22 base .q files, QuestsMX/ has 14 expansion .q files, MyQuest/ has 1.

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

### Quest Map Generator (QuestMapGenerator/)
Complete RGSEditor replacement. Full .q file parser/writer with from-scratch quest creation.

**Key files:**
- `rgs_format.py` — Sequential parser/writer + `create_quest()` API + CLI (inspect, create, modify, presets)
- `quest_map_generator.py` — Higher-level CLI with --deploy, --terrain, --seed flags
- `test_rgs_format.py` — Unit tests (43 tests, all passing)
- `constants_rgs_reference.md` — Base game terrain/landscape pattern catalog (234 entries from Data/constants.rgs)
- `expansion_constants_reference.md` — Expansion terrain/landscape patterns (176 entries from DataMX/mx_constants.rgs)
- `buildings_reference.md` — Building/unit Object IDs (BB**, AB**, BV**, etc.)
- `FINDINGS.md` — Decompilation results, binary format details, confirmed field mappings
- `TODO.md` — Priority tracking and architecture notes

**Capabilities (all in-game validated):**
- Parse all 37 .q files (100%), byte-perfect roundtrip on MyQuest
- Create quests from scratch: unit patterns, spawners, per-lair overrides, terrain, force layout
- Multi-kingdom slot configs (up to 7 player kingdoms + monsters, like 7Kings)
- 14 terrain presets + 25 landscape zones + fully custom blend support
- Force pattern: player modes (1P-4P), difficulty ratings, off-map placement
- JSON config input, --deploy to game folder, fixed seed support
- Spawner field mapping confirmed via Ghidra decompilation

**IMPORTANT:** When working on quest generation, always check the reference .md files
in this folder FIRST — they contain the complete catalogs of terrain patterns, landscape
objects, building IDs, and sprite groups available in the game.
