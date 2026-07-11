# Quest Map Generator

Programmatic .q binary quest template generator for Majesty Gold HD.
Generates quest packages for the Random Generation System (RGS) without requiring RGSEditor.

## Status

**All tasks COMPLETE.** Full parser + writer + CLI + validation working with correct RGS terminology.

- Parser: 37/37 quest files parse (100%) — supports RGMa, RGM6, RGM9
- Writer: Template-based, round-trip verified
- CLI: parse, validate, generate subcommands
- Validation: 37/37 files pass with 0 errors
- Convenience API: One-call quest generation
- Data model: Uses correct RGS terminology (UnitPattern, UnitInstance, ForceEntry, etc.)

## Files

| File | Purpose |
|------|---------|
| `quest_map_generator.py` | Main tool — parser, writer, grid encoding, CLI |
| `test_all_quests.py` | Test suite — validates parser against all 37 quest files |
| `constants_rgs_reference.md` | Base game terrain/landscape/fractal pattern catalog |
| `expansion_constants_reference.md` | Expansion-only patterns (Snow, Ice, quest-specific) |
| `q_format_research.py` | Exploration script used during reverse-engineering |

Spec docs: `.kiro/specs/quest-map-generator/` (requirements.md, design.md, tasks.md)

## Key Concepts (from SDK "How To Make A Quest")

The .q file is a **procedural generation template**, not a pre-rendered map. Maps are generated at load time.

### Hierarchy
- **Force Pattern** — top level, positions faction clusters on overall map (its own 5×5 grid)
- **Unit Pattern** — mid level, 5×5 Layout Grid with Resolution setting, contains Unit Instances
- **Unit Instance** — single building/lair/monster with candidate grid cells (RGS picks one randomly)

### Key behaviors
- Grid positions are **candidate locations** — multiple cells per unit = random choice, NOT multiple placements
- The grid is **randomly rotated** (0°/90°/180°/270°) at generation time
- The engine **prevents overlap** based on building sprite sizes
- Each Unit Instance is placed **exactly once**

### Position Grid (5×5, A-Y)
```
     col0  col1  col2  col3  col4
row0:  A     B     C     D     E
row1:  F     G     H     I     J
row2:  K     L     M     N     O
row3:  P     Q     R     S     T
row4:  U     V     W     X     Y
```
Encode: `byte = 65 + row*5 + col` | Decode: `col = (byte-65)%5, row = (byte-65)//5`

## Running

```bash
# Parse a .q file:
python QuestMapGenerator/quest_map_generator.py parse MyQuest/Quest.q

# Validate a .q file:
python QuestMapGenerator/quest_map_generator.py validate Quests/Krolm.q

# Generate a test quest:
python QuestMapGenerator/quest_map_generator.py generate --name IceTest --output output/IceTest --lairs "BBw1:Ice Cave:N,BBH1:Goblin Camp"

# Run test suite:
python QuestMapGenerator/test_all_quests.py
```

## Python API

```python
from quest_map_generator import generate_test_quest

# One-call quest generation
generate_test_quest(
    "IceSpellTest",
    [{"id": "BBw1", "desc": "Ice Cave", "position": "N"},
     {"id": "BBH1", "desc": "Goblin Camp"}],
    "output/IceSpellTest",
    dataset_base="MajestyExpansion"
)
```

## Terrain System

Terrain textures are in `Data/tilesetdata.cam` (808 tiles, 32×32 RGB565 pixels each).
Terrain types defined in `Data/terrtype.cam` (10 types: GR00-GR09).
Pattern definitions in `Data/constants.rgs` (base) and `DataMX/mx_constants.rgs` (expansion).

See `constants_rgs_reference.md` and `expansion_constants_reference.md` for full catalogs.

| Code | Terrain | Available In |
|------|---------|-------------|
| GR00 | Dirt | Base |
| GR01 | Plains (parent — light green) | Base |
| GR02 | Plains (child — dark green) | Base |
| GR03 | Arid (parent — dry grass) | Base |
| GR04 | Arid (child — yellow grass) | Base |
| GR05 | Scorch (parent — gray dirt) | Base |
| GR06 | Scorch (child — dark gray) | Base |
| GR07 | Swamp (parent — blue-green) | Base |
| GR08 | Swamp (child — red-brown) | Base |
| GR09 | Snow | Expansion only |

Custom terrain is theoretically possible via CAM mod loading — see reference docs for format details.
