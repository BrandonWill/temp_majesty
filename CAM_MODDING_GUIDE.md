# Majesty Gold HD — Data File Modding Guide

A task-oriented reference for modding Majesty Gold HD. Organized by "what do you want to do?"
with pointers to exactly which files you need and how to modify them.

Generated from analysis of all 47 CAM files + XML sources in this workspace.

---

## How the Game Loads Data

The game uses a **layered dataset system**:

1. **Base game** (`Data/MajestyDatasetDefinitions.xml`) loads all `Data/*.cam` files
2. **Expansion** (`DataMX/MajestyExpansionDatasetDefinitions.xml`) loads base FIRST, then overlays `DataMX/mx_*.cam` on top
3. **Mods** (`.mmxml`) and **Quests** (`.mqxml`) can load additional data on top of either dataset

Mods load XML `<Descriptions>` files DIRECTLY at runtime — you don't need to compile them into CAM.
Only sprites/audio need to go into a CAM file.

### Quest CAM Loading

Quest CAMs loaded via `<CAM>` in `.mqxml`/`.mmxml` files ARE loaded into the resource system
and **override** base/expansion entries with the same name (last-loaded wins):

| Resource Type | Quest CAM Override? | Notes |
|---------------|:-------------------:|-------|
| IMAG (animation sets) | ✅ YES | Last-loaded wins |
| TILE (sprite frames) | ✅ YES | Last-loaded wins |
| SPLT (palettes) | ✅ YES | Last-loaded wins |
| WAVE (audio) | ✅ YES | Last-loaded wins |
| SMNU (panel layouts) | ✅ YES | Last-loaded wins (confirmed by other modder) |
| STRT (string tables) | ✅ YES | Last-loaded wins (confirmed by other modder) |

**Important:** The SMNU binary must be correctly formatted (valid tag-value int32 stream
with proper terminators and matching STRT string counts). A malformed SMNU will crash the
panel parser at runtime. See `SMNUResearch/findings/smnu_parser_decompilation.md` for the
exact format specification.

**Previous incorrect finding (corrected July 2026):** Earlier testing concluded SMNU/STRT
used "first-loaded wins" and could not be overridden. This was a misdiagnosis — the actual
failure was a malformed custom SMNU binary that crashed the engine. The override mechanism
works correctly for all resource types.

---

## Quick Reference: What's In Each File

### The Big Picture

```
"I want to modify..."           → You need these files:
─────────────────────────────────────────────────────────────
A unit's stats/abilities        → unittype.cam (DUNT) or XML <Descriptions>
A spell's behavior              → action.cam (DACT) + GPL source
A unit's appearance             → maindata.cam (IMAG+TILE+SPLT)
A visual effect/overlay         → maindata.cam (sprites) + Overlays XML
Sound effects                   → soundfx.cam (WAVE) + sounddesc.cam (DSND)
Voice lines                     → voices.cam (WAVE) + sounddesc.cam (DSND)
UI/interface graphics           → interfacedata.cam (IMAG+TILE+PALT+FONT)
Terrain tiles                   → tilesetdata.cam (IMAG+TILE)
Map terrain objects             → maindata.cam (tree/rock sprites) + terrtype.cam
Loading screens/cinematics      → cinedata1.cam (PICT)
Menu text/strings               → textdata.cam (SMNU+STRT) for panel labels
Help text/descriptions          → gpltext.cam (STRT: HPTX entry)
AI status messages              → gpltext.cam (STRT: AITX entry)
AI behavior (expansion)         → mx_btdata.cam (BTDT) + GPL
Game balance/progression        → miscdata.cam (DATA: BDEP, GOPT, QDEP)
```

---

## File-by-File Reference

### `Data/unittype.cam` (145 KB) — Unit Definitions

**Sections:** DMOV (20 movement types) + DUNT (394 unit definitions)

**What it contains:**
Every game entity's definition — heroes, monsters, buildings, overlays, projectiles, particle
systems, terrain features. This is the binary compiled form of:
- `M_Characters.xml` (heroes + monsters)
- `M_Buildings.xml` (player + monster buildings)
- `M_Overlays.xml` (spell visual effects)
- `M_ParticleSystems.xml` (particle effects)
- `M_Projectiles.xml` (missiles)
- `M_TerrainFeatures.xml` (terrain objects)

**Key fields in a DUNT entry:**
- `ImageIDBase` — links to IMAG record in maindata.cam for sprites
- `DefaultSound` — links to sound definition in sounddesc.cam
- `MaxHP`, `Attack`, `Speed`, stats — gameplay values
- `AllowedSpells` — references action Names from action.cam
- `GPLFunction` (overlays/projectiles) — script callback on hit/end

**How to modify:**
For mods, you DON'T edit unittype.cam directly. Create XML files and load them via `<Descriptions>`:
```xml
<!-- In your .mmxml or .mqxml DataConfiguration -->
<Descriptions>Data/MyMod_Characters.xml</Descriptions>
```
The XML format matches SDK/OriginalQuests/Data/M_Characters.xml exactly.

**DMOV entries (movement types):**
| Name | Description |
|------|-------------|
| Class 1 | Standard ground unit |
| Class 2 | Slightly faster |
| Class 3 | Fast ground |
| Class 5 | Small flyer |
| Large Flyer | Dragons, large flying units |
| fast missile | High-speed projectiles |
| dragon_missile | Dragon breath projectile |
| Caravan | Caravan movement (special) |

---

### `Data/action.cam` (21 KB) — Spells & Actions

**Sections:** DACT (86 action definitions)

**What it contains:**
Every spell, attack, transition, and special action in the base game. Binary form of
`M_Actions.xml`. Each action defines:
- What animation to play (`ImageSet`: Walk, Attack, Cast, Die, Stand, etc.)
- What sound to trigger and when (`SoundPhase`)
- What projectile to spawn (`Projectile`)
- What GPL function to call (`GPLFunction`)
- Spell metadata: `TimeoutDuration`, `SpellType`, `CharacterLevel`, `SpellRank`

**Action naming conventions:**
| Prefix | Category | Examples |
|--------|----------|----------|
| `A0xx` | Basic actions | basic_attack, basic_death, basic_idle |
| `TXxx` | Transitions | stand-to-walk, active, inactive |
| `AXxx` | Ranged attacks | Ranger_arrow, elf_arrow, ballista_bolt |
| `BXxx` | Monster ranged | goblin_arrow, rust_spit, dragon_fire |
| `XRxx` | System effects | level_up, message_flag, got_gold |
| `ARa1` | Adept spells | teleport_short |
| `CRxx` | Cultist spells | charm_monster, camouflage, change_shape |
| `HRxx` | Healer spells | healer_heal, meditation, aura_of_peace |
| `LRxx` | Paladin spells | shield_of_light |
| `MRxx` | Monk spells | iron_will, hands_of_steel, stone_skin |
| `NRxx` | Necromancer spells | acid_bolt, electrical_fury, vortex |
| `PRxx` | Priestess spells | drain_life, animate_skeleton, control_undead |
| `SRxx` | Solarii spells | sun_scorch, inferno, radiate_energy |
| `WRxx` | Wizard spells | energy_blast, fire_shield, fire_ball, meteor_storm |

**How to modify:**
Create an actions XML and load it via `<Descriptions>Data/MyMod_Actions.xml</Descriptions>`.
Example spell definition:
```xml
<Description type="Action" subType="Standard" ID="ICa1" Name="ice_freeze" Description="Ice Freeze">
    <Engine version="1">
        <ImageSet value="Cast"/>
        <CompletionImageSet value="Stand"/>
        <Sound value="Petrify"/>
        <SoundPhase begin="Begin"/>
        <Script type="0" cProc="0" GPLFunction="Freeze_Begin"/>
    </Engine>
    <Game version="1">
        <Flags value="IsSpell"/>
        <TimeoutDuration value="15000"/>
        <SpellType value="Attack"/>
        <CharacterLevel value="1"/>
        <SpellRank value="1"/>
    </Game>
</Description>
```

---

### `Data/maindata.cam` (87.4 MB) — Sprites & Graphics

**Sections:** IMAG (380) + TILE (17,224) + SPLT (854) + CUT (20)

**The single biggest and most important file.** Contains ALL game entity sprites:
- Every hero, monster, building, spell effect, terrain object
- All animation frames (walk, attack, cast, die, idle, etc.)
- All color palettes used by those sprites

**How IMAG → TILE → SPLT work together:**
1. `IMAG` record (e.g., "AVA1 Adept") defines the animation metadata: frame count, dimensions, which TILE indices contain its frames
2. `TILE` entries are the actual pixel data (RLE-encoded, palette-indexed)
3. `SPLT` entries are the 256-color palettes (768 bytes: R,G,B × 256 entries)
4. Each IMAG record has a `palette_id` that points to a SPLT entry

**Animation set IDs** (from `ImageSetIDXRef.xml`):
| Name | ID | Notes |
|------|-----|-------|
| Walk | 1-4 | 8-directional walk (4 variants) |
| Stand | 8 | Idle stance |
| Attack | 16-19 | Attack animations (4 variants) |
| Special | 64-67 | Special ability animations |
| Build | 80-83 | Construction animations |
| Die | 96-103 | Death animations (8 variants) |
| Cast | 128-131 | Spellcasting animations |
| Carry | 144-147 | Carrying item animations |

**Entity categories in maindata.cam:**
| Prefix | Category | Count | Examples |
|--------|----------|-------|----------|
| `AB` | Player buildings | 53 | ABB1 (Ballista Tower), ABM1 (Wizard Tower) |
| `AV` | Player heroes | 32 | AVA1 (Adept), AVB1 (Barbarian), AVC1 (Cultist) |
| `BB` | Monster lairs | 38 | BBA1 (Animal Den), BBB1 (Dark Castle) |
| `BV` | Monsters | 32 | BVA1 (Evil Oculus), BVD1 (Dragon) |
| `MR` | Spell overlays | 14 | MRB1 (Petrify), MRA1 (Stone Skin) |
| `WR` | Wizard effects | 21 | WRc1 (Fire Blast), WRe2 (Fireball) |
| `NR` | Necro effects | 20 | NRa2 (Acid Bolt), NRe1 (Paralytic Gaze) |
| `xG` | Terrain objects | ~40 | PG07 (plains trees), WG07 (swamp trees) |
| `XL` | Particles/system | 13 | XL00 (placeholder), XL20 (Meteor Storm) |

**⚠️ CRITICAL: SPLT palettes are READ-ONLY.** Modifying them crashes the game.
New sprites must use colors from existing palettes.

**How to modify sprites:**
```bash
# Extract a sprite to PNG
python sprite_extractor.py --cam Data/maindata.cam --extract AVA1 Walk

# Encode new PNGs back to TILE format
python sprite_injector.py --cam Data/maindata.cam --roundtrip --tile-idx 3547

# Repack CAM with modified tiles
python cam_writer.py --cam Data/maindata.cam --replace-tile 3547 --tile-data new.bin --output modded.cam
```

For quest/mod custom sprites, pack them into a Quest_maindata.cam and load via `<CAM>`.

---

### `Data/interfacedata.cam` (42.5 MB) — UI Graphics

**Sections:** PALT (7 palettes) + IMAG (60) + TILE (2,624) + FONT (2)

**What it contains:**
All user interface graphics — menus, buttons, dialog frames, cursors, icons, fonts.

**Key sprite groups:**
| Name | # Frames | Purpose |
|------|----------|---------|
| Tactical Cursor | 31 | In-game mouse cursors |
| Quest Icons | 26 | Quest selection screen icons |
| Char spell icon | 24 | Spell icons in character panel |
| research icon | 17 | Research upgrade icons |
| main menu 2 | 270 | Main menu background/buttons |
| building frame | 137 | Building info dialog graphics |
| options main | 30 | Options menu graphics |
| high_scores | 33 | High scores screen |

**Palettes (PALT section):**
| Name | Purpose |
|------|---------|
| PLYR | Player team colors |
| RED | Red highlights |
| IBOX | Info box palette |
| GRAY | Grayscale elements |
| GRN | Green highlights |
| MMS1 | Minimap colors |
| TTIP | Tooltip palette |

**Fonts (FONT section):**
| Name | Purpose |
|------|---------|
| SM09 | Small 9pt font |
| HB12 | Header bold 12pt font |

**IMAG prefix groups:**
- `IN` (52 entries) — Main interface elements (buttons, panels, frames)
- `fn` (5 entries) — Font texture data (COPPLATE, Majestica, Tahona)
- `CU` (1 entry) — Cursor sprite set
- `DE` (1 entry) — Demo-related UI
- `IM` (1 entry) — Misc interface element

---

### `Data/soundfx.cam` (27.4 MB) — Sound Effects

**Sections:** WAVE (376 entries)

**What it contains:**
All non-voice sound effects — combat sounds, spell sounds, ambient sounds, building sounds,
UI clicks, environmental audio. Each entry is a WAV audio clip.

**How sounds are referenced:**
`soundfx.cam` stores raw WAV data. The WAVE entry names (e.g., "SL10", "AM15", "WU11")
are referenced by `sounddesc.cam` which maps logical sound names to specific WAV entries
and defines playback parameters.

**To add a new sound effect:**
1. Add a WAVE entry to your quest's CAM file (or a dedicated soundfx CAM)
2. Define a sound description in an M_Sounds.xml-style file
3. Reference the sound by name in your action/unit/overlay definitions

---

### `Data/voices.cam` (71.4 MB) — Voice Lines

**Sections:** WAVE (301 entries)

**What it contains:**
All voiced dialog — advisor announcements, quest narration, hero taunts, end-game sequences.
The largest CAM file by raw audio content.

**Entry naming:**
- `RA**` — Royal Advisor lines
- `ED**`/`EQ**`/`EN**` — Quest end/beginning narration
- `DQ**` — Quest dialog sequences
- `BP**` — Building placement confirmations

---

### `Data/sounddesc.cam` (105.5 KB) — Sound Configuration

**Sections:** DSDP (65 presets) + DSND (287 mappings) + DSDG (25 groups)

**What it contains:**
The "wiring" between game events and actual audio:

**DSDP (Sound Description Presets):**
Define playback phases — when a sound triggers during an animation:
- `AMA0` Ambient_Active — ambient sounds while unit is active
- `EEB0` Effector Begin — sound when spell effect starts
- `EEP0` Effector Peak — sound at peak of effect
- `EED0` End — sound when effect ends
- `EDH0` Death — death sound
- `EAK0` Attack — attack peak sound
- `GVxx` — Voice-triggered sounds (taunt, flee, combat, etc.)

**DSND (Sound Name → Wave mappings):**
Map a logical sound name (like "Petrify") to specific WAVE entries and define
volume, frequency variation, distance falloff, and which phase triggers it.

**DSDG (Sound Groups):**
Group related sounds for random selection (e.g., "Guild_Spell_Group" picks
a random guild spell sound each time).

---

### `Data/textdata.cam` (355 KB) — UI Dialog Layouts & Labels

**Sections:** SMNU (134 menu defs) + STRT (139 string tables)

**What it contains:**
UI **dialog panel LAYOUTS** (SMNU section — widget positions, button structure, panel hierarchy)
and their associated **button LABELS** (STRT section — short text strings for buttons, tabs,
and panel titles). This defines the structural layout of info windows you see when clicking
buildings, heroes, monsters. NOT the long-form descriptive help text (that's in `gpltext.cam`).

Each entry (e.g., `AP02`) has both:
- An SMNU entry: defines button positions, panel layout, widget structure
- An STRT entry: the short labels/button text for that panel

**Entry naming:**
- `APxx` — Info panels (AP02=Blacksmith, AP20=Hero, AP76=Ballista Tower, AP97=Monster, AP98=Henchman)
- `APMK` — Marketplace panel (largest, 1 KB of text for all marketplace UI labels)

**Example content (AP02 = Blacksmith panel STRT):**
> "The Blacksmith forges new weapons and armor for your heroes. BLACKSMITH VISITORS
> Go to this building's Visitors Window. Destroy this Blacksmith. Repair this building once.
> Tax this building..."

**How to modify:**
```bash
python str_tool.py --cam Data/textdata.cam --extract --output textdata_dump/
# Edit the short label text in .txt files
python str_tool.py --cam Data/textdata.cam --inject --input textdata_dump/ --output modded.cam
```

**Summary of text file responsibilities:**
| Want to change... | Edit this file |
|-------------------|---------------|
| Building/hero/spell help descriptions | `gpltext.cam` → `HPTX` entry |
| AI status messages ("Purchasing healing potions") | `gpltext.cam` → `AITX` entry |
| Building dependency text ("requires Palace Level 3") | `gpltext.cam` → `DPTX` entry |
| Quest items, quest names | `gpltext.cam` → `QITM`, `LNTX` entries |
| Hero/equipment name tables | `gpltext.cam` → `HNxx`, `ENxx` entries |
| Dialog panel button labels | `textdata.cam` → `APxx` STRT entries |
| Dialog panel layouts (positions) | `textdata.cam` → `APxx` SMNU entries |
| Modding system UI text | `InterfaceStrings.xml` (not a CAM) |

---

### `Data/gpltext.cam` (100 KB) — Game Help Text, AI Status, Items & More

**Sections:** STRT (96 entries)

**What it contains:**
Despite the name, this is NOT just "GPL quest text." It holds much of the game's
descriptive/help content that's referenced by GPL scripts and the UI engine:

| Entry | Size | Purpose |
|-------|------|---------|
| `HPTX` | 43 KB | **ALL building/unit help descriptions** — every info panel description in the game (building purposes, hero class overviews, upgrade/research descriptions, item effects like "Heroes may purchase Healing Potions once researched", spell descriptions, etc.) This is NOT just "quest text" — it's the primary game help content. |
| `AITX` | 14 KB | **AI status messages** — what heroes report they're doing ("Purchasing healing potions", "Enchanting weapon at the Wizards Guild", "Purchasing armor at the Blacksmith", "Learning new Wizard spell at the Library", etc.) |
| `FDTX` | 8 KB | Quest/freestyle map descriptions ("Settlement starts with...", "Many strong monsters present") |
| `FNTX` | 3 KB | Quest/freestyle names |
| `DPTX` | 2.6 KB | **Building dependency text** — the prerequisite messages shown to the player ("requires a Dwarven settlement", "requires Palace Level 3", etc.) |
| `QEND` | 5.6 KB | Quest end narration text |
| `QITM` | 816 B | Quest items (Magic Sword, Shard of Combustion, Ring of Protection, Holy Chalice, etc.) |
| `LNTX` | 666 B | Quest/location names (The Forsaken Land, Wizard's Curse, etc.) |
| `LOSX` | 1.3 KB | Loss condition text |
| `GOAL` | 138 B | Quest goal strings |
| `QUES` | 611 B | Quest description text |
| `GAMX` | 213 B | Game-over text |
| `HN01`–`HN64` | varies | Hero name generation tables (per class) |
| `BN01` | 810 B | Building name generation (inn/tavern names) |
| `EN01`–`EN15` | varies | Equipment name tables (armor types per tier) |
| `NMTX` | 54 B | Placeholder name text |

**Key insight for modders:** If you want to change the help text that appears when you
click on a building, a research option, or a hero class description, you need to
modify the `HPTX` entry in `gpltext.cam` — NOT `textdata.cam`.

**How to modify:**
```bash
python str_tool.py --cam Data/gpltext.cam --extract --output gpltext_dump/
# Edit HPTX.txt, AITX.txt, etc.
python str_tool.py --cam Data/gpltext.cam --inject --input gpltext_dump/ --output Data/gpltext_modded.cam
```

---

### `Data/tilesetdata.cam` (1.6 MB) — Terrain Tiles

**Sections:** IMAG (1) + TILE (808)

**What it contains:**
The ground terrain tile graphics — grass, dirt, water, snow, lava, stone.
These are the base tiles that form the map surface.

Single IMAG record defines the tileset, with 808 TILE frames for all terrain variants,
edges, transitions, and overlaps.

---

### `Data/terrtype.cam` (1.8 KB) — Terrain Type Definitions

**Sections:** DTPT (10 terrain point types) + DTRN (1 terrain config)

**What it contains:**
Terrain tile type metadata — defines which terrain types exist and their properties.
Binary form of `M_TerrainFeatures.xml` terrain-type data.

Small file, but critical: defines what terrain IDs are valid for map generation.

---

### `Data/cinedata1.cam` (60 MB) — Cinematics

**Sections:** PICT (20 full-frame images)

**What it contains:**
Cinematic/loading screen images. Each PICT entry is a large uncompressed bitmap.

**Entries:**
- `MV01` (16 MB) — Main intro movie frame data
- `QM00`–`QM18` — Quest map/briefing screen images (1-4 MB each)

---

### `Data/miscdata.cam` (9 KB) — Game Configuration

**Sections:** DATA (4 entries)

**What it contains:**
Core game balance and configuration data:

| Entry | Size | Purpose |
|-------|------|---------|
| `BDEP` | 5.0 KB | Building dependency tree (what unlocks what) |
| `GOPT` | 833 B | Game options/settings defaults |
| `QDEP` | 2.2 KB | Quest dependency tree (unlock order) |
| `XML1` | 958 B | XML configuration data |

**Modding relevance:** If you want to change building unlock requirements or
quest progression order, this is where it lives.

---

### `Data/company.cam` (236 B) — Faction Definitions

**Sections:** DFCT (2 entries)

**What it contains:**
The two base factions:
- `0000 Player` — Human player faction
- `0001 Monsters` — Monster faction

These define the fundamental team split. Simple but essential.

---

### `Data/GPLDebuggerUI.cam` (14.4 KB) — GPL Debugger

**Sections:** SMNU (6) + STRT (6)

**What it contains:**
Menu layouts and strings for the in-game GPL debugger interface (GDB1–GDB6).
Only relevant if you're debugging GPL scripts with the debugger enabled.

---

### `Data/addinterface.cam` (314 KB) + `addinterface_se.cam` (1 MB) — Extra UI

**Sections:** IMAG + TILE

**What they contain:**
Additional interface graphics loaded on top of interfacedata.cam:
- `addinterface.cam` — Download content UI (5 TILE frames)
- `addinterface_se.cam` — Screen resolution stretch graphics, multi-session UI (77 frames)

These handle UI scaling for different resolutions (1024×768 through 1920×1200).

---

### `Data/MDL1_*.cam` — Wrath of Krolm Quest Data

These 6 files are a **self-contained quest dataset** (the "MDL1" / Wrath of Krolm DLC quest):

| File | Size | Contents |
|------|------|----------|
| `MDL1_maindata.cam` | 2.0 MB | 5 IMAG + 638 TILE + 12 SPLT (Krolm god sprite, altar, fire effects) |
| `MDL1_unittype.cam` | 7.3 KB | 20 DMOV + 9 DUNT (Krolm, enemy barbarian, summoned animals) |
| `MDL1_action.cam` | 1.3 KB | 5 DACT (Summon_Barbarian, Summon_Roc, Summon_Varg, Summon_Bear, Krolm_Teleport) |
| `MDL1_sounddesc.cam` | 11.7 KB | 65 DSDP + 6 DSND + 25 DSDG (sound configs for Krolm quest) |
| `MDL1_soundfx.cam` | 1.2 MB | 8 WAVE (Krolm-specific sound effects) |
| `MDL1_voices.cam` | 846 KB | 5 WAVE (Krolm voice lines: appears, leaves, summons, taunts, death) |

**Modding relevance:** Great template for understanding how a quest packages its own
sprites + units + actions + sounds into a self-contained set of CAM files.

---

## Expansion Files (DataMX/)

The expansion loads AFTER base game data. Entries with the same ID **override** base entries.
New entries are **added** to the game.

### `DataMX/mx_maindata.cam` (51.4 MB) — Expansion Sprites

**Sections:** IMAG (166) + TILE (9,031) + SPLT (288)

**What it adds:**
All expansion-exclusive unit sprites, spell effects, buildings. Notable additions:
- New hero types (Dwarves, Elves expanded)
- New monsters (Ice Dragon, Gorgon, Ratman Champion)
- Many new spell effects (`XR01`–`XR77`): potions, frost, chain lightning, horrify, plague, etc.
- New projectiles: `WPh1` (chain), `WPi1` (frost missile), `WPn1` (ice breath)

### `DataMX/mx_Unittype.cam` (58 KB) — Expansion Unit Definitions

**Sections:** DMOV (2) + DUNT (174)

Adds 174 new unit definitions — new heroes, monsters, buildings, overlays, projectiles
for the expansion content.

### `DataMX/mx_action.cam` (12.6 KB) — Expansion Spells

**Sections:** DACT (49 actions)

49 new spells/actions for expansion content — frost field, chain lightning, horrify,
gate, fortress attacks, supernova, etc.

### `DataMX/mx_interfacedata.cam` (26.2 MB) — Expansion UI

**Sections:** IMAG (24) + TILE (785)

Expansion-specific UI additions — new building dialogs, spell icons, menu elements
for the Northern Expansion content.

### `DataMX/mx_sounddesc.cam` (62.5 KB) — Expansion Sound Config

**Sections:** DSND (155 sound mappings)

Sound-to-wave mappings for all expansion units and spells.

### `DataMX/mx_soundfx.cam` (8.3 MB) + `mx_voices.cam` (39.3 MB)

WAVE(76) sound effects + WAVE(96) voice lines for expansion content.

### `DataMX/mx_textdata.cam` (136 KB) — Expansion Text

**Sections:** SMNU (35) + STRT (36)

Menu layouts and strings for expansion UI elements.

### `DataMX/mx_gpltext.cam` (133 KB) — Expansion GPL Text

**Sections:** STRT (78)

Text strings for expansion quest scripts.

### `DataMX/mx_tilesetdata.cam` (2.1 MB) — Expansion Terrain

**Sections:** IMAG (1) + TILE (1,052)

Additional terrain tiles for expansion biomes (ice/snow terrain, etc.).

### `DataMX/mx_terrtype.cam` (2 KB) — Expansion Terrain Types

**Sections:** DTPT (11) + DTRN (1)

One additional terrain point type for expansion (likely snow/ice terrain).

### `DataMX/mx_miscdata.cam` (15 KB) — Expansion Config

**Sections:** DATA (4 entries)

Same structure as base miscdata.cam — expansion's building/quest dependencies.

### `DataMX/mx_btdata.cam` (747 B) — Behavior Trees

**Sections:** STRT (1) + BTDT (5 entries)

**Expansion-only feature.** AI behavior tree data for the expansion's improved AI system.
This is the only file in the game with BTDT sections.

### `DataMX/mx_rgstext.cam` (19 KB) — RGS Text

**Sections:** STRT (3)

Text for the Random Generation System — terrain/biome description strings.

### `DataMX/XQD1_*.cam` — Expansion Quest 1 Data

Self-contained quest data for an expansion quest:

| File | Contents |
|------|----------|
| `XQD1_MainData.cam` | 2 IMAG (evil/light shrines) + 27 TILE + 5 SPLT |
| `XQD1_UnitType.cam` | 20 DMOV + 6 DUNT (shrine units) |
| `XQD1_SoundFX.cam` | 3 WAVE |
| `XQD1_Voices.cam` | 3 WAVE |
| `XQD1_intro.cam` | 4 IMAG + 5 TILE (intro screen graphics) |

---

## Task-Oriented Recipes

### "I want to add a new spell"

1. **Define the action** — Create XML with `type="Action"`:
   - Set `GPLFunction` for the gameplay logic
   - Set `ImageSet`, `Sound`, `Projectile` for presentation
   - Set `SpellType`, `TimeoutDuration`, `CharacterLevel` for balance

2. **Create the GPL function** — Write the spell logic in `.gpl`:
   - Use `$createeffector` for status effects
   - Use `$adjustattribute` for damage/healing
   - Guard with `$IsDead()` checks

3. **Define an overlay** (if spell has a visible effect) — XML with `type="Unit" subType="Overlay"`:
   - Set `ImageIDBase` pointing to your effect sprites
   - Optionally set `Script`/`GPLFunction` for end-of-effect callback

4. **Create sprites** (if needed) — Pack into a Quest_maindata.cam:
   - IMAG record for animation metadata
   - TILE frames for the pixel data
   - Must use an existing SPLT palette

5. **Wire it up** — Add the spell to a unit's `AllowedSpells` in your Characters XML

6. **Load it** — Reference everything in your `.mmxml` DataConfiguration

### "I want to add a new monster"

1. **Create sprites** — All animation sets (Walk, Stand, Attack, Die, optionally Cast, Special)
   - 8-directional for each (except Die which has more variants)
   - Pack into Quest_maindata.cam

2. **Define the character** — XML with `type="Unit" subType="Character"`:
   - `ImageIDBase` → your IMAG record
   - Stats: MaxHP, Attack, Speed, SightRange, etc.
   - `CanUse value="Monster"` for enemy units
   - `Attachment kind="Movement"` → pick a DMOV class

3. **Define a lair** (optional) — XML with `type="Unit" subType="Building"`:
   - `CanUse value="Monster"`
   - Links to the spawned monster type

4. **Add sounds** (optional) — Sound definition + WAVE entries

### "I want to modify a unit's stats"

The simplest mod — just create an XML that redefines the unit with the same ID:
```xml
<Description type="Unit" subType="Character" ID="AVB1" Name="Barbarian" Description="Buffed Barbarian">
    <!-- Redefine with new stats — overrides the base game definition -->
    <Game version="1">
        <MaxHP value="30"/>  <!-- was 20 -->
        <Attack value="95"/> <!-- was 85 -->
        <!-- ... rest of stats ... -->
    </Game>
</Description>
```
Load via `<Descriptions>` in your mod's DataConfiguration.

### "I want to change a unit's appearance"

**Option A: Swap ImageIDBase** (simplest — reuse existing sprites)
```xml
<Description type="Unit" subType="Character" ID="AVB1" Name="Barbarian">
    <Engine version="1">
        <ImageIDBase value="AVE1"/>  <!-- Now uses Paladin sprites -->
    </Engine>
</Description>
```

**Option B: Custom sprites** (full control)
1. Create new sprite frames as PNGs
2. Quantize to an existing SPLT palette
3. Encode with `sprite_injector.py`
4. Pack into a Quest_maindata.cam
5. Create an IMAG record pointing to your TILE frames
6. Set `ImageIDBase` to your new IMAG ID

### "I want to change game text/UI strings"

```bash
# Extract all strings from textdata.cam
python str_tool.py --cam Data/textdata.cam --extract --output text_dump/

# Edit the .txt files (they're simple key=value format)

# Repack
python str_tool.py --cam Data/textdata.cam --inject --input text_dump/ --output Data/textdata_modded.cam
```

### "I want to add a particle effect"

Define in XML with `type="Unit" subType="ParticleSystem"`:
```xml
<Description type="Unit" subType="ParticleSystem" ID="XL40" Name="my_effect">
    <Engine version="1">
        <Info value="Static"/>
        <Info value="Directionless"/>
        <Info value="DontBlock"/>
        <Info value="NoGPLAgent"/>
        <Menu value="13"/>
        <ImageIDBase value="XL40"/>
        <AttachmentPointID value="2"/>
        <DefaultSound value="0"/>
        <InitialParticles value="2"/>
        <MaxParticles value="24"/>
        <Bounds min="-1000, -1000, -1000" max="2000, 2000, 2000"/>
        <Emitter>
            <Type value="Area"/>
            <Radius value="0.07"/>
            <Rate value="8.0"/>
            <Lifespan value="2200"/>
        </Emitter>
        <Particle>
            <Lifespan value="10000"/>
            <InitialSpeed value="3.0"/>
            <BirthColor value="0.0, 0.0, 1.0, 0.0"/>
            <MidlifeColor value="0.0, 0.5, 1.0, 1.0"/>
            <DeathColor value="0.0, 0.0, 0.5, 0.0"/>
            <BirthSize value="1.0"/>
            <MaxSize value="20.0"/>
        </Particle>
    </Engine>
</Description>
```

---

## Dataset Loading Order

Understanding load order is critical for overrides:

**Base Game (Original mode):**
```
miscdata.cam → action.cam → cinedata1.cam → company.cam → gpltext.cam →
interfacedata.cam → addinterface.cam → maindata.cam → sounddesc.cam →
soundfx.cam → terrtype.cam → textdata.cam → tilesetdata.cam → unittype.cam →
voices.cam → addinterface_se.cam → GPLDebuggerUI.cam
+ Bytecode.bcd + MX_Compatibility.bcd
+ constants.rgs
+ InterfaceStrings.xml
```

**Expansion (overlays on base):**
```
[All base game files first, then:]
mx_miscdata.cam → mx_action.cam → mx_btdata.cam → mx_gpltext.cam →
mx_interfacedata.cam → mx_maindata.cam → mx_sounddesc.cam → mx_soundfx.cam →
mx_terrtype.cam → mx_textdata.cam → mx_tilesetdata.cam → mx_unittype.cam →
mx_voices.cam → mx_RgsText.cam → mx_cinedata1.cam → XQD1_intro.cam
+ MX_Build.bcd + MX_Data.bcd + MX_Decision.bcd + MX_Task.bcd
+ mx_constants.rgs (replaces base constants.rgs)
```

**Mod (.mmxml) adds on top:**
```
[Base or Expansion dataset, then:]
Your <Descriptions> XMLs (parsed at runtime)
Your <CAM> files (sprites, sounds)
Your <GPL> bytecode
```

---

## SMNU Panel Format (Reverse-Engineered)

The SMNU format has been fully decoded via Ghidra decompilation. Key findings:

### Format Overview
- SMNU is a **tag-value int32 stream** (every value is a little-endian 32-bit integer)
- Panel starts with `1000`, then tag-value property pairs, terminated by `-1`
- Child widgets follow: `[type_code] [sub_id] [tags...] [-1]` repeated
- Entire stream terminated by a final `-1`

### Widget Property Tags (Most Common)
| Tag | Values Consumed | Purpose |
|-----|----------------|---------|
| 2 | 4 (x, y, w, h) | Widget geometry/position |
| 6 | 1 | Action identifier (stored at widget offset 0x14) |
| 7 | 1 | String from STRT table (by index) — display text |
| 12 | 1 | Image set (4-char name packed as int32, e.g. "INTG") |
| 13 | 1 | TILE index — background/button graphic |
| 18 | 1 | Font (4-char name packed as int32, e.g. "fnt4") |
| 33 | 1 | Tooltip text from STRT (by index) |

### Critical: STRT Connection
- STRT is loaded by **matching entry name** — the STRT entry must have the SAME name
  as the SMNU entry in the CAM file (e.g., if SMNU entry is "MX03", engine looks for
  STRT entry also named "MX03")
- If STRT is missing or not found: engine crashes (null dereference when tag 7 is processed)

### Building-to-Panel Mapping
- The mapping from building type → panel name is **hardcoded in the exe** (vtable per building class)
- New custom buildings cannot have new panels without an exe patch
- Existing panels CAN be modified by replacing their SMNU/STRT data

### Sub-Panel Navigation
- Panel navigation from sub-panels only supports action code **8013** (return to parent)
- Other navigation codes (4004, 8851, System B format) are silently ignored in sub-panel context
- Multi-page navigation is impossible without an exe patch

### Further Details
See `SMNUResearch/` folder for full decompilation results, test findings, and format documentation.

---

## XML Definition Types Reference

All game objects use the same XML schema with `type` and `subType`:

| type | subType | Defined In | Binary Section | Purpose |
|------|---------|-----------|----------------|---------|
| Unit | Character | M_Characters.xml | DUNT | Heroes, monsters, NPCs |
| Unit | Building | M_Buildings.xml | DUNT | Player & monster buildings |
| Unit | Overlay | M_Overlays.xml | DUNT | Visual spell effects |
| Unit | ParticleSystem | M_ParticleSystems.xml | DUNT | Particle effects |
| Unit | Projectile | M_Projectiles.xml | DUNT | Missiles & bolts |
| Unit | General | M_TerrainFeatures.xml | DUNT | Trees, rocks, terrain objects |
| Action | Standard | M_Actions.xml | DACT | Spells, attacks, transitions |
| Sound | Standard | M_Sounds.xml | DSND | Sound definitions |

**Common XML fields across all unit types:**
```xml
<Engine version="1">
    <Info value="..."/>          <!-- Flags: Directionless, BlockGround, DontBlock, Static, etc. -->
    <CanUse value="..."/>       <!-- HumanPlayer or Monster -->
    <Menu value="N"/>           <!-- Menu category (2=building, 5=monster, 6=hero, etc.) -->
    <ImageIDBase value="XXYY"/> <!-- Links to IMAG record for sprites -->
    <DefaultSound value="..."/> <!-- Links to sound definition -->
    <Script type="0" cProc="0" GPLFunction="..."/>  <!-- GPL callback -->
    <Attachment kind="Movement" type="Walk" ID="..."/> <!-- Movement class -->
</Engine>
```

---

## Entity ID Naming Conventions (Complete)

The 4-character ID system used across IMAG, DUNT, DACT sections:

### Character/Unit Prefixes
| Prefix | Category | Examples |
|--------|----------|----------|
| `AV` | Player heroes | AVA1=Adept, AVB1=Barbarian, AVC1=Cultist, AVD1=Healer |
| `BV` | Monsters | BVA1=Evil Oculus, BVD1=Dragon, BVF1=Skeleton |
| `AB` | Player buildings | ABB1=Ballista, ABE1=Guardhouse, ABM1=WizTower |
| `BB` | Monster buildings | BBA1=Animal Den, BBB1=Dark Castle, BBH1=Goblin Camp |

### Effect/Overlay Prefixes
| Prefix | Category | Examples |
|--------|----------|----------|
| `AR` | Adept overlays | ARA1=mockup flag, ARA2=attack flag |
| `CR` | Cultist/Fervus | CRA1=fervus healing, CRB1=vines |
| `DR` | Druid/wind | DRA1=winged feet, DRB1=wind storm |
| `HR` | Healer/Agrela | HRA1=agrela healing, HRB1=blessing |
| `LR` | Paladin/Lunord | LRa1=shield of light |
| `MR` | Monk/Dauros | MRA1=stone skin, MRB1=petrify |
| `NR` | Necromancer/Krypta | NRa2=acid bolt, NRe1=paralytic gaze |
| `PR` | Priestess | PRA1=animate bones, PRb1=animate skeleton |
| `SR` | Solarii | SRA1=fire strike, SRB1=sun scorch |
| `WR` | Wizard/Krolm | WRA1=farseeing, WRb1=fire shield, WRc1=fire blast |
| `QR` | Quest/status | QRa1=poison icon, QRd0=magic ring |
| `XR` | System/expansion effects | XR01-XR77 (potions, frost, chain lightning, etc.) |

### Projectile Prefixes
| Prefix | Examples |
|--------|----------|
| `AP` | APB1=Ballista Bolt, APA2-APA5=Ranger/Elf arrows |
| `BP` | BPA1=Goblin Arrow |
| `NP` | NPa1=acid bolt, NPb1=electrical fury |
| `PP` | PPa1=life drain missile |
| `WP` | WPa2=wizard energy, WPe1=fireball missile |

### Terrain/Landscape Prefixes
| Prefix | Biome | Examples |
|--------|-------|----------|
| `PG` | Plains | PG01=ponds, PG07=trees big |
| `RG` | Arid | RG01=ponds, RG07=trees big |
| `WG` | Swamp | WG01=ponds, WG07=trees big |
| `CG` | Scorched | CG01=ponds, CG10=walkover |
| `FG` | Ferns | FG01=ferns trees |
| `GG` | Savannah | GG01=savannah trees |
| `LG` | Weeping willow | LG01=willow trees |
| `TG` | Cactus/desert | TG01=cactus trees |
| `UG` | Autumn | UG01=autumn trees |
| `VG` | Volcanic | VG01=lava pools |
| `YG` | Special | YG01=mud pit, YG02=gas clouds |
| `IG` | Ice | IG02, IG08 (base game ice terrain) |

### Other Prefixes
| Prefix | Purpose |
|--------|---------|
| `XL` | Placeholder/particle system sprites |
| `MV` | Movement/event markers (beacons, selection rings) |
| `BG` | Building ground effects |
| `CU` | Cursors |
| `IN` | Interface elements |
| `fn` | Font textures |

---

## Related Non-CAM Files

| File | Purpose |
|------|---------|
| `Data/ImageSetIDXRef.xml` | Maps animation names (Walk, Attack, Cast...) to numeric IDs |
| `Data/InterfaceStrings.xml` | Modding system UI text |
| `Data/MajestyDatasetDefinitions.xml` | Defines base game dataset (what CAMs to load) |
| `DataMX/MajestyExpansionDatasetDefinitions.xml` | Defines expansion dataset |
| `Data/DataSets.xml` | GPL bytecode loading groups |
| `Data/constants.rgs` | Terrain/map generation data (binary, edited by RGSEditor) |
| `Data/*.dat` | Binary data (UIData resolution configs, cinedata) |
| `Data/MusicTracks.txt` | Music playlist |
| `Data/setnames.txt` | Tileset names |

---

## Tools Summary

| Tool | Use When You Want To... |
|------|------------------------|
| `cam_reader.py` | List/extract entries from any CAM file |
| `cam_writer.py` | Repack a CAM with modified entries, or build from extracted dir |
| `sprite_extractor.py` | Get PNGs of any game sprite |
| `sprite_injector.py` | Convert PNGs back to TILE format |
| `str_tool.py` | Convert STRT string tables: extract to editable TXT and repack back to binary |
| `QuestMapGenerator/` | Generate .q quest maps programmatically |


---

## Appendix: Low-Level Binary Format Reference

> This section documents the byte-level binary formats for CAM containers, IMAG animation
> descriptors, and TILE sprite data. This is the raw format reference for tool authors and
> anyone building custom CAM files programmatically. For normal modding tasks, use the
> Python tools which handle these details automatically.

### CAM Container Format (use `cam_reader.py`)

#### File Header
```
+0    12   Fixed magic: "CYLBPC  " + 01 00 01 00
+12   4    u32: sectionCount (4 in maindata.cam)
+16   4    u32: contentHeaderLength (not used when reading)
+20   8xN  Per section: char[4] extension + u32 sectionHeaderOffset
```

#### Content Header (sequential, one block per section, right after file header)
```
For each section:
  +0   4     u32: filesCount
  +4   4     zeros (padding)
  +8   28xM  per file: byte[20] name (null-padded) + u32 fileOffset + u32 fileSize
```

#### Content
Raw file bytes, one blob per file. Use each file's `fileOffset`/`fileSize` to slice directly.

#### Section Breakdown (maindata.cam)

| # | Extension | File count | Typical size | What it is |
|---|-----------|-----------:|--------------|------------|
| 0 | `IMAG`    | 380        | ~5-19 KB     | Animation-set descriptors (per-unit/building). Contains image-set table + frame descriptors + per-direction geometry. |
| 1 | `TILE`    | 17,224     | ~1-8 KB      | Per-frame sprite pixel data. 8-bit paletted, per-row RLE compressed. |
| 2 | `SPLT`    | 854        | 1032 bytes   | 256-color RGBA palettes (fixed-size). **Read-only — do not modify.** |
| 3 | `CUT `    | 20         | 886 bytes    | Small fixed-size resource (unexplored, likely UI elements). |

---

### IMAG Blob Internal Format (animation set, per-unit/building)

```
+0x00   4     u32 n_directions header value
+0x04   16    padding/reserved, zeros
+0x14   4     u32 entryCount - number of image-set entries
+0x18   8xN   entries: u32 setID + u32 relOffset
```

setID values (from `ImageSetIDXRef.xml`):
Walk=1, Stand=8, Attack=16, Special=64, Build=80, Die=96, Cast=128, Carry=144,
Recoil=160, Active=192, Inactive=208, Dead=224, Crumble=240, Minimap=300,
Damage=316, Hotspot=400, Sel-Underlay=500, Sel-Overlay=550, Interface=1000,
UnitTexture=4000.

#### Frame Descriptor Block (directional units)
```
+0x00   4     u32 = 8 (type flag)
+0x38   32    8x u32: relative offsets to 8 per-direction blocks
              (signed i32 — treat values <= 0 as unused)
```

Per-direction block (variable stride: `48 + frameCount * 8`):
```
+0x14   4     i16,i16: x_offset, y_offset (sprite hotspot)
+0x18   4     u16,u16: width, height
+0x30   8xF   F pairs of (u32 flag, u32 tile_index) — index into TILE section
```

**Note:** The per-direction block stride varies by frame count. Use distance to next
populated direction offset to determine frame count reliably.

---

### TILE Sprite Format (Version 3) — RLE Encoding

8-bit paletted sprites with per-row RLE compression.

> **Root cause note:** An earlier revision of this guide (and older tooling) treated the
> per-segment X field as an absolute *start* column. The engine stores an **exclusive end**.
> Full write-up: `majesty-gold-hd-art-asset-extractor/docs/TILE_V3_RLE_ROOT_CAUSE.md`
> (also mirrored under this toolkit as needed).

#### Header
```
+0x00   2     u16: version (always 3)
+0x02   2     u16: height
+0x04   2     u16: width (canvas; equals max exclusive-end X over all rows)
+0x06  10     remaining header words (preserve when re-encoding)
+0x10   6     zeros
+0x16   4     u32: palette_id (index into SPLT section)  ← byte 22
+0x1A   H×4   height × u32: per-row offset table (offsets relative to byte 26)
```

#### Row RLE (after offset table)
Each row is a sequence of segments:
```
[u16 x_end] [u8 count] [u8 flags] [count × u8 pixel_bytes]
```
- `x_end` — exclusive end column of the opaque run; draw at `[x_end - count, x_end)`
- `count` — number of pixel bytes following
- `flags` — 0x80 = last segment in row
- Pixel bytes — palette indices (0 = transparent, 248-255 = shadow/blend)

#### Key Facts
- Pixel indices reference the palette at `palette_id` in the SPLT section
- Palette index 0 is always transparent
- Indices 248-255 map to shadow/blend colors (often shown as magic pink in raw previews)
- `sprite_extractor.py` decodes this format; `sprite_injector.py` encodes it
- Round-trip verified on multi-run hero tiles (e.g. AVB1 TILE 3794): decode → encode → same pixels

---

### IMAG Writing Notes for Mod CAMs

Mod-loaded CAM files (quests/mods via DataConfiguration) use the same IMAG format.
The WrathOfKrolm example (`SDK/Example/Data/WrathOfKrolm_maindata.cam`) has 5 working
IMAG records that serve as known-good templates:
- `XR47DustofDeth` — 292 bytes, directionless overlay (simplest template)
- `KR0TKrolm-appear` — 364 bytes, another overlay

TILE indices in mod CAMs reference the mod's own TILE section (0-based local indices,
not the base game's global pool). When building a Quest_maindata.cam, your IMAG frame
descriptors should use indices 0, 1, 2... referencing the TILE entries within that
same CAM file.
