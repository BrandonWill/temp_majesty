---
inclusion: manual
description: How to create Quests and Mods for Majesty HD — RGSEditor workflow, file formats, Steam Workshop
---

# Making A New Quest

A complete Quest definition in Majesty contains several parts:

| Component | Extension | Purpose |
|-----------|-----------|---------|
| Quest Definition file | `.mqxml` | Master file — description, display name, references to all other files |
| Quest Template | `.q` | Map layout and starting conditions (edited by RGSEditor) |
| GPL Bytecode | `.bcd` | Compiled GPL source code the Quest runs |
| Game Object Definitions | `.xml` | Optional — create or modify Buildings, Characters, Sounds |
| CAM Archives | `.cam` | Optional — custom sprites, sounds, UI panels (see #[[file:.kiro/steering/cam-and-sprites.md]]) |
| Art/Sound Binary Data | `.cam` | Images and sounds for game objects |
| RGS Constants | `.rgs` | Random Generation System data for map generation |

**Adding Game Object Definitions, Binary Data, and changing RGS Constants is optional** — a Quest can use just existing Majesty assets.

## Getting Started

1. Create the Quest Definition file and Quest Template using the **RGSEditor** (in the SDK folder).
2. Launch RGSEditor → File → New Quest...

## Create New Quest Dialog

Define the following:

- **GPL Initialization Function Name** — not case sensitive, no spaces (only underscore allowed)
- **Data Set** — Original Majesty or Northern Expansion
- **Map Size** — dimensions of the generated map
- **Random Seed** — 0 = new seed every time; fixed value = same map each time (useful for testing)

Example: Function name `InitializeMyQuest`, data set `Majesty:Original`.

## Unit Patterns

A Unit Pattern describes the placement layout of one or more units.

**Key properties:**
- 5×5 grid layout
- Variable resolution (spacing between center points of grid cells)
- Spacing adjusts based on map size
- Overlap prevention — units placed as close as possible without overlapping
- Grid is randomly rotated for placement variety

**Each unit definition is placed only once for the entire pattern.** Marking a unit at multiple grid locations randomizes WHERE it appears (the RGS picks one location).

### Adding Units to a Pattern

1. Press Add... in the Unit section
2. Select category (Buildings, Characters, etc.) and unit type
3. Click grid locations to set candidate positions

**Multiple units at one grid location:** Grid shows `*`. Only one unit is chosen for that location at generation time.

**Same unit type multiple times:** Add multiple Unit instances referencing the same type. Each gets its own grid positions and each is placed exactly once.

### Layout Grid Resolution

The Resolution dropdown controls spacing between grid cells. A tile is 32 pixels wide, so resolution of 3 = 96 pixels between neighbors.

### Randomization

- Mobile units (monsters, heroes) and terrain objects get an additional random shift of up to 100 pixels (~3 tiles)
- The entire placement grid is randomly rotated (0°/90°/180°/270°)

## Force Patterns

A Force Pattern defines how Unit Patterns are placed on the map as a whole. Most quests have one Force Pattern laying out all Unit Patterns.

1. Quest menu → Edit Force Patterns...
2. New... → name it (e.g., "Quest Layout")
3. Add... → select a Unit Pattern (e.g., "Player Start")
4. Click a Map Layout grid entry to set position

## Region Patterns

A Region Pattern defines terrain appearance and landscape objects (trees, rocks).

1. Quest menu → Edit Region Pattern...
2. New... → name it (e.g., "Quest Terrain")
3. Add Region Patches

### Region Patches

Each patch contains:
- **Terrain Pattern** — texture type (see below)
- **Fractal Settings** — terrain bumpiness
- **Landscape Pattern** — landscape objects placed on terrain

### Terrain Types

| Type | Appearance |
|------|-----------|
| Dirt | Brown dirt, occasional small rocks and grass tufts |
| Plains | Light green grass |
| Plains (child) | Dark green grass |
| Arid | Very light green grass, occasional brown grass tufts |
| Arid (child) | Yellowed grass, occasional light green tufts |
| Scorch | Gray dirt, occasional grass tufts |
| Scorch (child) | Dark gray dirt, occasional rocks |
| Swamp | Green/blue dirt, occasional dark grass tufts |
| Swamp (child) | Red/brown dirt, occasional dark grass tufts |
| Snow | Snow-covered dirt |

### Fractal Settings

Controls terrain bumpiness. Predefined options include "Rolling Hills", "Small Hills", etc.

### Landscape Patterns

Controls what landscape objects appear and how many. Example: `#BBC_Grass` (from Bell Book and Candle Quest — green leafy trees + rocks).

### Region Pattern Configuration

- **Amount Present** slider — percentage of map covered by each patch
- **Number of Seeds** slider — how many seed points the RNG uses for distribution

## The Project View

Switch via Edit menu → Project View. Shows all Quest Definition values:

- GPL Initialization Function Name
- Map Size
- Random Seed
- Difficulty
- GUID (unique identifier)
- Display Name
- Short/Long Description
- Data Set
- Load section (files)

### GUID Rules

- Auto-generated on Quest creation
- **MUST change** if using an existing Quest as a template for a new one
- Changing it invalidates previous save games
- Generate new: click current ID → press ellipses button (…)

### Description Line Breaks

Use `[newline]` tag in Short/Long descriptions for line breaks.

### Load Section

Right-click sub-sections to add/remove files. Sub-sections:
- Descriptions (XML)
- CAM (binary data)
- GPL Bytecode
- Strings
- Quest Template

**Files don't need to exist when added** — useful for bytecode files that will be compiled later.

**Paths are fully qualified when added but automatically made relative** to the Quest save location. Best practice: keep all files at or below the Quest save location.

## Compiling GPL Source to Bytecode (.bcd)

In the Project View:
1. Specify target bytecode file
2. Add source files to the GPL Bytecode entry
3. Right-click the Entry → Compile

The RGSEditor creates a temporary `.gplproj` file and calls the GPL compiler (must be in same directory as RGSEditor.exe). Output appears in the Log window.

**Compile All:** Right-click GPL Bytecode entry → Compile All, or use Quest menu → Compile GPL.

---

# Quest Definition File Format (.mqxml)

XML formatted file. Can be edited manually with a text editor (don't have it open in RGSEditor simultaneously).

## Example (Wrath Of Krolm)

```xml
<Majesty>
  <Quest id="{9757F443-4229-41dc-860B-9BD980D72733}">
    <Name>WrathOfKrolm</Name>
    <DisplayName lang="en_US">Wrath of Krolm - The Example</DisplayName>
    <Description lang="en_US">
      <Short>Destroy all Altars to Krolm, or defeat his Avatar...</Short>
      <Long>"The followers of Krolm have challenged..."</Long>
    </Description>
    <Difficulty>Hard</Difficulty>
    <DataConfiguration>
      <Dataset base="Majesty">
        <Load>
          <Descriptions>Data/WrathOfKrolm_Actions.xml</Descriptions>
          <Descriptions>Data/WrathOfKrolm_Sounds.xml</Descriptions>
          <Descriptions>Data/WrathOfKrolm_Characters.xml</Descriptions>
          <Descriptions>Data/WrathOfKrolm_Buildings.xml</Descriptions>
          <Descriptions>Data/WrathOfKrolm_Overlays.xml</Descriptions>
          <CAM>Data/WrathOfKrolm_maindata.cam</CAM>
          <CAM>Data/WrathOfKrolm_soundfx.cam</CAM>
          <CAM>Data/WrathOfKrolm_voices.cam</CAM>
          <GPL>Data/WrathOfKrolm.bcd</GPL>
          <GPLSource>GPL</GPLSource>
          <Template>Quests/WrathOfKrolm.q</Template>
          <Strings>Data/WrathOfKrolm_Text.xml</Strings>
        </Load>
        <Unload>
          <CAM/>
          <GPL/>
          <Constants/>
        </Unload>
      </Dataset>
    </DataConfiguration>
  </Quest>
</Majesty>
```

## Tag Reference

### `<Majesty>` — Top-level tag (always present)

### `<Quest id="...">` — Formal Quest Definition
- `id` attribute: Standard GUID, unique per quest
- Auto-generated by RGSEditor
- **Never reuse** for another quest
- Save games store the id to know what quest data to load

### `<Name>` — Compact Identifier
- Letters and numbers only (no spaces, no special characters)
- Primary use: name of the GPL function called when the Quest begins
- If no GPL function of that name exists, the game shows an error dialog
  (`GplDispatcherHandle error: script $Name() doesn't exist`) but the Quest still
  loads after clicking OK — just with no custom initialization or victory conditions
- **Best practice:** Either provide a matching GPL function, or use a name that already
  exists in the base GPL (e.g., `basicAI` from the template) to avoid the error popup

### `<DisplayName lang="...">` — Screen Display Name
- Shown in Quest list UI
- `lang` attribute: language/country code

**Supported language codes:**
| Code | Language |
|------|----------|
| `en_US` | English, USA |
| `fr_FR` | French, France |
| `de_DE` | German, Germany |
| `es_ES` | Spanish, Spain |
| `it_IT` | Italian, Italy |
| `en_GB` | English, Great Britain |
| `ja_JA` | Kanji, Japan |
| `ko_KR` | Korean, Korea |
| `zh_CN` | Simplified Chinese, China |
| `zh_TW` | Simplified Chinese, Taiwan |
| `pl_PL` | Polish, Poland |
| `ru_RU` | Russian, Russia |
| `pt_PT` | Portuguese, Portugal |

Multiple `<DisplayName>` entries allowed (different `lang` values). Falls back to `en_US` if requested language missing.

### `<Description lang="...">`
- Child tags: `<Short>` and `<Long>`
- Short: quest goals (available during gameplay as reminder)
- Long: displayed at quest start
- Same `lang` attribute and multiple-language support as DisplayName

### `<Difficulty>`
Values: `Easy`, `Medium`, `Hard`, `Master`

### `<DataConfiguration>` → `<Dataset base="...">`
- `base` attribute: `Majesty` or `MajestyExpansion`
- `Majesty` = original game art/sound/GPL
- `MajestyExpansion` = Northern Expansion art/sound/GPL
- **Warning:** Changing base after creation can cause crashes (Quest Template is tightly coupled to data set)

### `<Load>` — Files to load

| Tag | Purpose |
|-----|---------|
| `<Descriptions>` | XML files with asset definitions (Characters, Buildings, Sounds, Actions) — can also modify existing assets |
| `<CAM>` | Binary art/sound data |
| `<GPL>` | Compiled GPL bytecode (.bcd) |
| `<GPLSource>` | Relative path to GPL source (for debugger — optional but useful). Searches recursively through sub-folders. Multiple entries allowed. |
| `<Template>` | RGS quest template (.q) — only one entry |
| `<Strings>` | Text displayed by the Quest |

### `<Unload>` — Files to unload (rare)
Used when a Quest completely replaces base data file contents.

---

# Mod Definitions (.mmxml)

Mods are similar to Quests but loaded **alongside** a Quest, modifying the base data set.

## Key Differences from Quests

| Aspect | Quest | Mod |
|--------|-------|-----|
| Primary tag | `<Quest>` | `<Mod>` |
| File extension | `.mqxml` | `.mmxml` |
| Dataset base options | `Majesty` or `MajestyExpansion` | `Majesty`, `MajestyExpansion`, or `Any` |
| Template tag | Required | Ignored |
| Map view in RGSEditor | Yes | No (independent of quest map) |
| Loading | Standalone | Loaded with a Quest |

## Dataset Compatibility

- `base="Any"` → loaded with ANY quest (if mod only changes things common to both datasets or adds new data)
- `base="Majesty"` → only loaded with Majesty-base quests
- `base="MajestyExpansion"` → only loaded with expansion-base quests

## Multiple Mods

- Multiple mods can be active simultaneously
- Load in the order they appear in the Active Mods list
- Incompatible mods (wrong base) are silently skipped

## Example (Adjust Guardhouse)

```xml
<Majesty>
  <Mod id="{D666FCBE-9906-4582-A6A0-DC96F812441E}">
    <Name>AdjustGuardHouse</Name>
    <DisplayName lang="en_US">Adjust Guardhouse</DisplayName>
    <Description lang="en_US">
      <Short>Upgraded guard houses increase the number of guards posted
        at the guard house to two.</Short>
      <Long></Long>
    </Description>
    <DataConfiguration>
      <Dataset base="Any">
        <Load>
          <GPL>Data/AdjustGuardhouse.bcd</GPL>
        </Load>
      </Dataset>
    </DataConfiguration>
  </Mod>
</Majesty>
```

## Creating a Mod

1. RGSEditor → File → New Mod...
2. Edit values in Project View
3. Add GPL/Data files to Load section
4. Compile GPL if needed

---

# Data Descriptions (XML)

Game objects and actions are defined by data descriptions.

## Structure

- **type** — primary type (Unit, Sound)
- **subtype** — for Units: Building, Character, Projectile, Overlay, Particle System
- **name** and **ID** — identifiers
- **Engine section** — common values (not game-specific), same across all subtypes
- **Game section** — Majesty-specific values, varies by subtype

## Usage

- Majesty shipped descriptions in binary format
- SDK provides XML versions
- User-generated Quests can create/modify XML description files
- Add them to the Quest Definition's `<Descriptions>` tag
- Modifications to existing assets override the base data

---

# Steam Workshop

## Upload Process

1. RGSEditor → File → Steam Workshop Upload...
   - If grayed out: Steam Client not running — restart Steam then RGSEditor

## Workshop Project Settings

| Field | Notes |
|-------|-------|
| **Visibility** | Private, Friends Only, or Public. Keep Private/Friends until stable. |
| **Content** | Directory with your Mod/Quest files. Usually `My Games/MajestyHD/Mods/YourMod` |
| **Preview** | Screenshot or artwork (.png/.jpg, under 1MB). Do NOT put in content folder. Save near Workshop project file. |
| **Tags** | Check all relevant: Mod, Quest, Character, Building, Majesty, Northern Expansion, etc. |
| **Title** | 128 characters or less. Required. |
| **Description** | 5000 characters or less. Required. Explain what the Mod changes or Quest goals. |

## Content Best Practices

- Everything in the content directory gets uploaded (including subdirectories)
- Keep contents minimal — only what the Mod/Quest needs
- Including `.gpl` source files is encouraged (lets others see your changes)
- Build from just your changes to the SDK, not the whole SDK

## Upload Steps

1. Fill in all project values
2. File → Save (save the workshop project file)
3. File → Upload...
4. Enter optional Change Note → OK
5. **IMPORTANT:** After first upload, save the project file again (Steam assigns an ID that must be preserved)

## Recovering Lost Workshop ID

If you forget to save after first upload:
1. Go to your Workshop item page (Steam Client or browser)
2. Look at URL: `?id=yourItemNumber`
3. Edit project file with text editor → put number in `id` attribute of `SteamWorkshop` tag

## Updating

1. Reload saved Workshop project
2. Most fields will be unchecked/grayed (won't re-upload unless checked)
3. File → Upload...
4. This prevents overwriting changes made through the Workshop web pages

## Subscribing and Loading

- Users subscribe via Steam Workshop page
- Steam Client downloads to Steam install directory (NOT the My Documents location)
- If you subscribe to your own mod, it appears twice in-game (local copy + Steam copy)
- Save games look for matching Mod/Quest ID — local My Documents copy takes priority

---

---

# Programmatic Quest Generation (rgs_format.py — RGSEditor Replacement)

The `QuestMapGenerator/rgs_format.py` tool fully replaces RGSEditor for programmatic quest creation.
It was built from a complete Ghidra decompilation of RGSEditor.exe's serialization functions.

**Status: COMPLETE — all features implemented, in-game validated, 43 unit tests passing.**

## Tools

| File | Purpose |
|------|---------|
| `QuestMapGenerator/rgs_format.py` | Core parser/writer + `create_quest()` API + CLI |
| `QuestMapGenerator/quest_map_generator.py` | Higher-level CLI with --deploy |
| `QuestMapGenerator/test_rgs_format.py` | Unit test suite (43 tests) |
| `QuestMapGenerator/constants_rgs_reference.md` | Base terrain/landscape pattern catalog (234 entries) |
| `QuestMapGenerator/expansion_constants_reference.md` | Expansion patterns (176 entries) |
| `QuestMapGenerator/buildings_reference.md` | Building/unit Object IDs |
| `QuestMapGenerator/FINDINGS.md` | Decompilation results and field mappings |

## CLI Usage

```bash
# Create from JSON config
python QuestMapGenerator/rgs_format.py create --config quest.json --output Quest.q

# Inspect any .q file
python QuestMapGenerator/rgs_format.py inspect Quests/Krolm.q
python QuestMapGenerator/rgs_format.py inspect Quests/Krolm.q --section spawners

# Modify existing quest
python QuestMapGenerator/rgs_format.py modify Quests/Krolm.q --patch changes.json --output modified.q

# List available terrain presets
python QuestMapGenerator/rgs_format.py presets

# Generate + deploy in one command
python QuestMapGenerator/quest_map_generator.py generate \
  --name "MyQuest" --output out/MyQuest \
  --lairs "BBH1:Goblin Camp:N,BBw1:Ice Cave:E" \
  --terrain forest --seed 42 --deploy
```

## Python API

```python
from rgs_format import create_quest, write_quest_file

qf = create_quest(
    name="MyQuest",
    unit_patterns=[
        {"name": "Player1", "entries": [
            {"id": "ABJ1", "desc": "Palace", "cells": [77]}
        ]},
        {"name": "Monster Lairs", "entries": [
            {"id": "BBH1", "desc": "Goblin Camp", "cells": [65, 69],
             "lair_override": {
                 "monsters": [("BVL1", 60), ("BVL2", 40)],
                 "max_hp": 200,
                 "spawn_rate_ms": 15000,
                 "dispersion": 500,
                 "hit_rate_sub": 50,
             }},
            {"id": "BBw1", "desc": "Ice Cave", "cells": [85]},
        ]},
    ],
    map_size=(256, 256),
    terrain="forest",           # 14 presets or custom dict/list
    seed=42,                    # 0 = random each play
    force_layout={
        "name": "My Force",
        "players": [1, 2],      # Allowed player counts
        "difficulty": 70,
        "entries": [
            {"pattern_idx": 0, "position": "W"},
            {"pattern_idx": 1, "position": "CGHLN"},   # Multi-candidate
            {"pattern_idx": 1, "position": "off_map"},  # Edge spawning
        ],
    },
)
write_quest_file(qf, "output/Quest.q")
```

## Capabilities

| Feature | Status |
|---------|--------|
| Parse all .q versions (RGM1-RGMa) | ✅ 37/37 files |
| Byte-perfect roundtrip | ✅ MyQuest/Quest.q |
| Unit patterns with entries | ✅ |
| Per-lair spawner overrides (HP, rate, dispersion, hit reduction) | ✅ |
| Death monster lists (extra_names) | ✅ |
| Terrain: 14 presets + 25 zones + custom | ✅ In-game validated |
| Force pattern: positions, off-map, multi-candidate | ✅ |
| Player modes (1P-4P), difficulty/money/time ratings | ✅ |
| Random seed control | ✅ |
| JSON config input | ✅ |
| --deploy to game folder | ✅ |
| Warning if no enemy buildings (instant win) | ✅ |
| Inspect/modify existing .q files | ✅ |

## SpawnerBlock Field Mapping (Confirmed via Ghidra)

| Field | Meaning | Range |
|-------|---------|-------|
| `field_00` | Max HP | 0-99999 |
| `field_04` | Base Spawn Rate (ms) | 0-999999 |
| `field_08` | Dispersion (pixels) | 0-99999 |
| `field_0c` | (Not implemented) | 0-10 |
| `field_10` | Hit Rate Reduction (ms/hit) | 0-9999 |

## Terrain Presets

`grass`, `snow`, `grass_snow`, `forest`, `swamp`, `desert`, `scorched`, `mountain`,
`snow_mountain`, `dark_forest`, `barren`, `fertile`, `winter`, `bog`

Custom: pass a dict of zone blends `{"snow_ice": 60, "mountain": 40}` or a list of
raw `{"tag", "name", "fractal", "texture", "height", "weight"}` definitions.

## When to Use What

| Scenario | Tool |
|----------|------|
| Quick test quest for mod validation | `quest_map_generator.py generate --deploy` |
| Complex quest with custom spawners | `rgs_format.py create --config quest.json` |
| Inspect/debug existing quest | `rgs_format.py inspect file.q --section force` |
| Batch quest generation | Python API: `create_quest()` in a loop |
| Visual terrain/layout preview | RGSEditor (still has the GUI grid view) |
| Custom landscape objects (trees/rocks) | Edit constants.rgs (not yet automated) |

---

# Quick Reference: Minimum Viable Quest

1. **RGSEditor** → New Quest → set name, data set, map size
2. **Unit Pattern** → at least one (e.g., Palace placement)
3. **Force Pattern** → places Unit Pattern on map
4. **Region Pattern** → at least one Region Patch (terrain + fractal + landscape)
5. **GPL** → write initialization function matching the Quest name (optional but needed for win conditions)
6. **Compile** → Quest menu → Compile GPL
7. **Save** → creates `.mqxml` + `.q` files
8. Copy to `My Games/MajestyHD/Quests/YourQuest/` folder
9. Launch game → Quest appears in Quest list

# Quick Reference: Minimum Viable Quest (Programmatic)

1. Write a JSON config or use the Python API
2. `python QuestMapGenerator/quest_map_generator.py generate --name "Test" --output out --lairs "BBH1:Goblin Camp" --deploy`
3. Launch game → Quest appears in Quest list
4. No RGSEditor needed, no GUI, fully scriptable

# Quick Reference: Minimum Viable Mod

1. **RGSEditor** → New Mod → set name, data set (Any/Majesty/MajestyExpansion)
2. Write GPL source modifying desired behavior
3. Compile GPL → produces `.bcd`
4. Add `.bcd` to Mod's Load section
5. Optionally add XML descriptions (character/building/sound modifications)
6. Save `.mmxml`
7. Copy to `My Games/MajestyHD/Mods/YourMod/` folder
8. Launch game → Mod appears in Mod list → activate it


---

# XML Schema Reference

Complete reference for data description XML files. All features confirmed working via Workshop mods.

## Action/Spell Definitions

```xml
<Description type="Action" subType="Standard" ID="mySpell" Name="my_spell" Description="My Spell">
  <Engine version="1">
    <ImageSet value="Cast"/>             <!-- animation played during cast -->
    <CompletionImageSet value="Stand"/>  <!-- animation after cast -->
    <Sound value="Sound_Name"/>          <!-- optional cast sound -->
    <SoundPhase begin="Begin"/>
    <!-- EITHER a projectile OR a GPL callback (not both): -->
    <Projectile value="missile_name"/>
    <!-- OR: -->
    <Script type="0" cProc="0" GPLFunction="MySpell_Begin"/>
  </Engine>
  <Game version="1">
    <Flags value="IsSpell"/>
    <TimeoutDuration value="10000"/>     <!-- cooldown in ms -->
    <EffectorDuration value="21000"/>    <!-- effector lifetime (separate from timeout) -->
    <SpellType value="Attack"/>          <!-- Attack, CombatUtility, 4 (self-buff) -->
    <SpellRank value="6"/>              <!-- REQUIRED for AI to cast; higher = preferred -->
    <CharacterLevel value="5"/>          <!-- level required to learn/cast -->
    <ValidationScript value="check_fn"/> <!-- optional GPL gate function -->
    <Rate min="0" max="800"/>            <!-- action timing/animation rate -->
  </Game>
</Description>
```

### Key Action Attributes

| Attribute | Purpose | Notes |
|-----------|---------|-------|
| `SpellRank` | AI casting priority | **REQUIRED** — AI never casts without it |
| `SpellType` | Spell classification | Attack, CombatUtility, 4 (numeric self-buff) |
| `CharacterLevel` | Level-gate | Hero must reach this level to learn/cast |
| `ValidationScript` | Cast gating | GPL function returns true/false to allow cast |
| `EffectorDuration` | Buff duration | How long attached effector lasts (ms) |
| `TimeoutDuration` | Cooldown | Time before spell can be cast again (ms) |
| Multiple `<SpellType>` | Stack flags | Can combine Attack + CombatUtility |

## Overlay Definitions

### Visible Effector (Rendered Over Unit)

```xml
<Description type="Unit" subType="Overlay" ID="xxx" Name="spell_effector" Description="...">
  <Engine version="1">
    <Info value="Directionless"/>
    <Info value="DontBlock"/>
    <Menu value="11"/>                   <!-- 11 = effector overlay category -->
    <ImageIDBase value="WRc1"/>          <!-- actual sprite animation reference -->
    <AttachmentPointID value="2"/>       <!-- bone attachment point -->
    <DefaultSound value="0"/>
  </Engine>
  <Game version="1">
    <Flags value="TransparentToMouse"/>  <!-- click-through -->
    <StackPriority value="0"/>           <!-- lower = drawn first -->
  </Game>
</Description>
```

### Invisible Timer (Fires Callback on Expiry)

```xml
<Description type="Unit" subType="Overlay" ID="xxx" Name="spell_icon" Description="...">
  <Engine version="1">
    <Info value="Directionless"/>
    <Info value="DontBlock"/>
    <Menu value="11"/>
    <ImageIDBase value="HRb1"/>          <!-- minimal/invisible sprite -->
    <Script type="0" cProc="0" GPLFunction="MySpell_End"/>  <!-- EXPIRY CALLBACK -->
    <DefaultSound value="0"/>
  </Engine>
  <Game version="1">
    <StackPriority value="1"/>           <!-- higher = processed after visual -->
  </Game>
</Description>
```

### Key Overlay Attributes

| Attribute | Values | Purpose |
|-----------|--------|---------|
| `Menu` | 0 (standard), 11 (effector/icon) | Display category |
| `Info value="Static"` | — | Non-animated (single frame) |
| `AttachmentPointID` | 2 (body) | Which bone point to attach to |
| `Script GPLFunction` | function name | Called when effector timer expires |
| `Flags value="TransparentToMouse"` | — | Click-through overlay |
| `StackPriority` | 0+ | Layering order (higher = on top / processed later) |

## Building Definitions

```xml
<Description type="Unit" subType="Building" ID="ABE1" Name="Guardhouse1" Description="Guardhouse">
  <Engine version="1">
    <Info value="BlockGround"/>
    <Info value="BlockFlying"/>
    <Info value="ModifyTerrainTextureOnPlacement"/>
    <CanUse value="HumanPlayer"/>        <!-- who can build it -->
    <Menu value="2"/>                    <!-- 1=guilds, 2=defenses, 3=economy... -->
    <ImageIDBase value="ABE1"/>          <!-- sprite reference -->
    <DefaultSound value="Guard_House"/>
  </Engine>
  <Game version="1">
    <DialogID value="AP17"/>
    <Cost value="600"/>
    <UpgradeTo value="Guardhouse2"/>     <!-- upgrade chain target -->
    <Multiplier value="1.25"/>           <!-- cost escalation for multiple -->
    <IncomeType value="3"/>              <!-- 2=revenue, 3=maintenance -->
    <MaxHP value="100"/>
    <SightRange value="400"/>
    <Flags value="HasHPBar"/>
    <Flags value="NumberedName"/>        <!-- auto "#1", "#2" suffix -->
    <HelpID value="h073"/>
    <Produces><Unit ID="City_Guard"/></Produces>  <!-- recruitable units -->
  </Game>
</Description>
```

### Key Building Attributes

| Attribute | Purpose | Notes |
|-----------|---------|-------|
| `UpgradeTo` | Upgrade chain | Points to next building ID |
| `Multiplier` | Cost escalation | Each additional copy costs more |
| `IncomeType` | Economic type | 2=revenue, 3=maintenance |
| `Produces` | Recruitable units | `<Unit ID="..."/>` children |
| `Flags value="NumberedName"` | Auto-numbering | Adds "#1", "#2" suffix |
| `Menu` | Build menu category | Which menu tab building appears in |

## Research/Services/Items Pattern

The engine's "recruit a character" UI can be repurposed for ANY purchasable action:

```xml
<!-- Research slot (invisible character = purchasable research) -->
<Description type="Unit" subType="Character" ID="ResearchHealing" Name="ResearchHealing" ...>
  <Engine version="1">
    <Info value="Static"/>
    <Info value="Directionless"/>
    <Info value="DontBlock"/>
    <CanUse value="HumanPlayer"/>
    <Menu value="8"/>                    <!-- Menu 8 = research/service slot in building UI -->
    <ImageIDBase value="AVk4"/>          <!-- icon sprite -->
  </Engine>
  <Game version="1">
    <MaxHP value="1"/>
    <RecruitDelay value="10000"/>        <!-- research time (ms) -->
    <Flags value="NotFlaggable"/>
    <Flags value="NotSpellTarget"/>
  </Game>
</Description>
```

Key insight: `subType="Character"` + `Menu value="8"` = research/service slot.
`RecruitDelay` = research time. `birthScript` = on-purchase callback in GPL.

---

# MQXML/MMXML Advanced Features

Discoveries from Workshop mod analysis (not in SDK documentation).

## Undocumented Tags

| Tag | Purpose | Example | Source |
|-----|---------|---------|--------|
| `<GPLSource>` | Tells engine where GPL source lives (for debugger) | `<GPLSource>GPL</GPLSource>` | WorldWarMajesty |
| `<CAM>` | Loads raw CAM archives (sound data confirmed, sprites theoretically possible) | `<CAM>Data/sounds.cam</CAM>` | MK Sound-Set Extensions |
| `<Constants>` in `<Unload>` | Implies constants.rgs is loadable/unloadable | — | SDK MQXML template |

## Multiple Mods in One MMXML

A single `.mmxml` can contain multiple `<Mod>` entries (each with unique GUID):

```xml
<Majesty>
  <Mod id="{GUID-1}">
    <Name>VariantA</Name>
    <!-- ... -->
  </Mod>
  <Mod id="{GUID-2}">
    <Name>VariantB</Name>
    <!-- ... -->
  </Mod>
</Majesty>
```

Player picks which variant to enable. StandAloneAI ships 15 variants this way.

## Dual-Dataset Mods

Ship one `<Mod>` for base game and one for expansion in the same mmxml:

```xml
<Majesty>
  <Mod id="{GUID-BASE}">
    <Name>MyMod_Base</Name>
    <DataConfiguration>
      <Dataset base="Majesty">
        <Load><GPL>Data/mod_base.bcd</GPL></Load>
      </Dataset>
    </DataConfiguration>
  </Mod>
  <Mod id="{GUID-EXPANSION}">
    <Name>MyMod_Expansion</Name>
    <DataConfiguration>
      <Dataset base="MajestyExpansion">
        <Load><GPL>Data/mod_expansion.bcd</GPL></Load>
      </Dataset>
    </DataConfiguration>
  </Mod>
</Majesty>
```

Engine auto-loads the right one based on active quest's dataset.

## Dataset Base Risks

- `base="Any"` → mod loads with ANY quest but can misbind attribute names against wrong ruleset
- Best practice: use `base="Any"` only for mods that add entirely new data or override only by function name
- Attribute writes via derived handles may silently fail in mod BCDs

## Nested Description Paths

Subdirectories work in `<Descriptions>` tags:

```xml
<Descriptions>Data/Items/Equipment_Items.xml</Descriptions>
<Descriptions>Data/Research/Research.xml</Descriptions>
```

## Mod Architecture Patterns

| Pattern | Description | Example |
|---------|-------------|---------|
| Palace prototype as entry point | Palace `birthScript` IS the mod's entry function | StandAloneAI |
| Expression-only BCD | Pure tuning mod (just constants) | GPL Scripting Reference |
| Same-name function override | Redefine stock functions | Uncapped Cheats |
| Mod load order exploitation | Later mods override earlier ones' expressions | All |

---

# Multi-Kingdom Quests (Programmatic)

The `create_quest()` API now supports multi-kingdom configurations via `slot_configs`:

```python
# 7-Kingdom FFA (like 7Kings Workshop quest)
qf = create_quest(
    "SevenKings",
    unit_patterns=[{"name": f"Kingdom{i}", "entries": [
        {"id": "ABJ1", "desc": "Palace", "cells": [65 + i]}
    ]} for i in range(7)],
    slot_configs=[
        {"name": "Human Player", "starting_gold": 30000, "sub_items": [0]},
        {"name": "AI Kingdom 1", "starting_gold": 30000, "sub_items": [1]},
        {"name": "AI Kingdom 2", "starting_gold": 30000, "sub_items": [2]},
        {"name": "AI Kingdom 3", "starting_gold": 30000, "sub_items": [3]},
        {"name": "AI Kingdom 4", "starting_gold": 30000, "sub_items": [4]},
        {"name": "AI Kingdom 5", "starting_gold": 30000, "sub_items": [5]},
        {"name": "AI Kingdom 6", "starting_gold": 30000, "sub_items": [6]},
    ],
    force_layout={
        "players": [1],  # Single-player mode only
        "entries": [{"pattern_idx": i, "position": chr(65 + i)} for i in range(7)],
    },
)
```

### Slot Config Fields

| Field | Default | Purpose |
|-------|---------|---------|
| `name` | `"playerN"` | Display name for the kingdom |
| `active` | `True` | Whether slot is enabled |
| `starting_gold` | `starting_gold` param | Starting resources |
| `sub_items` | `[index]` | Spawner block indices assigned to this kingdom |
| `index` | position in list | Slot index (0-7, with 7 = Monsters by convention) |

Monsters slot (index 7) is auto-added if not explicitly included.
