# Quest Map Generator — TODO

## Status: Sequential Parser + Create API COMPLETE ✅

- **Parse: 37/37 files** (100%) ✅
- **Roundtrip: MyQuest/Quest.q = byte-perfect** ✅
- **`create_quest()` API: working, in-game validated** ✅
- **Custom spawners: supported** ✅
- **Per-lair overrides: supported** ✅
- **Terrain presets: 14 presets + custom blends** ✅
- **All RGSEditor UI fields documented** (from binary tooltip extraction) ✅

---

## Completed Work

### ~~Priority 1: Integrate `rgs_format.py` into `quest_map_generator.py`~~ ✅ DONE

CLI `generate` command now uses `create_quest()` from `rgs_format.py` by default.
Old template-splice approach available via `--use-template` flag.
New options: `--map-size` (128/256/512), `--terrain` (grass/snow/grass_snow).

### ~~Priority 2: Per-Lair Spawner Override API~~ ✅ DONE

The `create_quest()` API now supports per-lair overrides via `lair_override` on entries:

```python
create_quest("Test", [
    {"name": "Monsters", "entries": [
        {"id": "BBH1", "desc": "Goblin Camp", "cells": [65],
         "lair_override": {
             "monsters": [("BVr1", 50), ("BVs1", 50)],  # (id, weight%)
             "max_hp": 500,              # field_00
             "spawn_rate_ms": 30000,     # field_04
             "dispersion": 200,          # field_08
             "hit_rate_sub": 100,        # field_10
             "death_monsters": ["BVL1"], # extra_names (spawner_ver 3)
         }},
        {"id": "BBw1", "desc": "Ice Cave", "cells": [85],
         "lair_override": [  # List = multiple difficulty levels
             {"monsters": [("BVx1", 80)], "spawn_rate_ms": 30000},
             {"monsters": [("BVx1", 60), ("BVm1", 40)], "max_hp": 300},
         ]},
    ]},
])
```

Key scheme: `entry_index * 1000 + sub_index` (matching RGSEditor's internal model).
Roundtrip verified. Monsters auto-padded to 4 slots with NONE entries.

### ~~Priority 3: Verify SpawnerBlock Field Mapping~~ ✅ DONE

Confirmed via Ghidra decompilation of `DialogEditLairs::DoDataExchange` (FUN_00426430)
and the save handler (FUN_00427490). Assembly at 0x0042754c-0x00427575 shows exact
struct offset writes.

| Field | Meaning | UI Tooltip | DDV Range |
|-------|---------|-----------|-----------|
| `field_00` | Max HP | "The maximum hit points given to the Lair" | 0-99999 |
| `field_04` | Base Spawn Rate (ms) | "The base time, in milliseconds..." | 0-999999 |
| `field_08` | Dispersion (pixels) | "The dispersion range...in pixels" | 0-99999 |
| `field_0c` | (Not implemented) | "Not implemented" | 0-10 |
| `field_10` | Hit Rate Reduction | "Each hit...subtracts this amount from spawn rate delay" | 0-9999 |

All fields default to 0 meaning "use lair's built-in value". Only in spawner_ver >= 2.
Property aliases added to `SpawnerBlock`: `.max_hp`, `.spawn_rate_ms`, `.dispersion`, `.hit_rate_sub`.

### ~~Priority 4: Region Pattern Editing~~ ✅ DONE

Terrain is now fully configurable without templates:

1. **14 presets** (string): "grass", "snow", "grass_snow", "forest", "swamp", "desert",
   "scorched", "mountain", "snow_mountain", "dark_forest", "barren", "fertile", "winter", "bog"
2. **25 landscape zones** (dict blend): custom mix like `{"snow_ice": 60, "mountain": 40}`
3. **Fully custom** (list): raw tag/fractal/texture/height definitions

All extracted from real quest file data. Auto-derives `field_0c` terrain type from texture ref.

```python
# Preset:
create_quest("Test", [...], terrain="dark_forest")

# Custom blend:
create_quest("Test", [...], terrain={"snow_ice": 60, "mountain": 40, "forest": 20})

# Fully custom:
create_quest("Test", [...], terrain=[
    {"tag": "MyGr", "name": "My Grass", "fractal": "xBBC", "texture": "#Pla", "height": "Roll", "weight": 55},
    {"tag": "MySn", "name": "My Snow", "fractal": "xCla", "texture": "xSno", "height": "FS01", "weight": 45},
])
```

---

## Remaining Work

### ~~Priority 5: Force Pattern Layout API~~ ✅ DONE

Full control over force pattern placement:

```python
create_quest("MyQuest", [...], force_layout={
    "name": "Dragon Quest",
    "players": [1, 2],           # Allowed player counts
    "difficulty": 80,            # Difficulty rating (0-100)
    "money": 60,                 # Money rating
    "time": 70,                  # Time rating
    "resolution": 2,             # Grid spacing
    "entries": [
        {"pattern_idx": 0, "position": "W"},         # Single position
        {"pattern_idx": 1, "position": "GHILNQRS"},  # Multi-candidate
        {"pattern_idx": 2, "position": "off_map"},   # Off-map (edge spawning)
    ],
})
```

Supports: off-map placement, multi-candidate positions, player mode control (1P-4P),
difficulty/money/time ratings. Also accepts simple list format for basic use.
7 unit tests added (41 total).

### ~~Priority 6: Full CLI Replacement~~ ✅ DONE

`rgs_format.py` now has a comprehensive CLI:

```bash
# Inspect any quest file (all sections or filtered)
rgs_format.py inspect Quests/Krolm.q
rgs_format.py inspect Quests/Krolm.q --section spawners
rgs_format.py inspect Quests/Krolm.q --section force

# Create quest from JSON config
rgs_format.py create --config quest.json --output MyQuest/Quest.q

# List terrain presets and landscape zones
rgs_format.py presets

# Roundtrip test
rgs_format.py roundtrip MyQuest/Quest.q
rgs_format.py test Quests/
```

Sections: `header`, `spawners`, `terrain`, `patterns`, `force`.
JSON config accepts all `create_quest()` parameters including lair_override and force_layout.

### Other Items (from quest_map_generator.py)

- ~~**`--deploy` flag**: Auto-copy generated quest to game's Quests folder~~ ✅ DONE
- ~~**`--seed` parameter**: Fixed random seed for reproducible maps~~ ✅ DONE
- ~~**`modify` command**: Read existing .q, patch fields, write back~~ ✅ DONE
- **In-game terrain validation**: Confirm new terrain presets render correctly (manual test)

---

## Architecture Notes

### Field Naming (from decompilation — confusing but correct)
- `UnitPattern.terrain_code` = actually the **faction short code** (4 chars)
- `UnitPattern.name` = actually the **faction full name**
- `UnitPattern.tag_48` = the **real terrain code** ("gras", "snow", etc.)
- `UnitPattern.field_44` = always 5 (grid resolution constant)
- `UnitPattern._faction_tag` = read by the set reader BEFORE the pattern body

### Spawner Connection Model
- Top-level `spawner_blocks[]` define difficulty curves (indexed by `_spawner_indices`)
- `SlotConfig[7]` ("Monsters") has `sub_items` referencing spawner block indices
- Per-lair overrides are in `UnitPattern.spawners[]` (with `_spawner_keys` mapping to entries)
- Key scheme: `entry_index * 1000 + sub_index`

### Ghidra MCP
- Project: `MajestyRE` at `C:\Users\Brandon\Tools\GhidraProjects`
- Config: `.kiro/settings/mcp.json`
- RGSeditor.exe fully analyzed: 16,513 functions
- All serialization + UI tooltip strings extracted
