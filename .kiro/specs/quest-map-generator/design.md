# Design Document

## Overview

The Quest Map Generator is a Python tool that reads and writes Majesty Gold HD `.q` binary quest map files. It enables programmatic creation of quest maps for automated mod testing without requiring the RGSEditor GUI.

The tool targets the **RGMa format** (editor-created) since that's what RGSEditor produces and the game loads from custom quest folders. The generator can also parse RGM6/RGM9 (base game) files for reference.

## Architecture

### High-Level Design

```
┌─────────────────────────────────────────────────┐
│              quest_map_generator.py              │
├─────────────────────────────────────────────────┤
│  CLI Layer (argparse)                           │
│    parse / generate / validate subcommands      │
├─────────────────────────────────────────────────┤
│  High-Level API                                 │
│    generate_test_quest(name, lairs, output_dir) │
├─────────────────────────────────────────────────┤
│  Core Data Model                                │
│    QuestMap, PlacedGroup, PlacedEntry,          │
│    SpawnerBlock, MapParams                      │
├─────────────────────────────────────────────────┤
│  Binary I/O Layer                               │
│    QFileParser (read) / QFileWriter (write)     │
├─────────────────────────────────────────────────┤
│  MQXML Generator                                │
│    Produces .mqxml quest definition XML         │
├─────────────────────────────────────────────────┤
│  Validation Layer                               │
│    Structural checks, cross-references          │
└─────────────────────────────────────────────────┘
```

### Single-File Design

The entire tool lives in one file: `quest_map_generator.py` at the workspace root, consistent with `cam_reader.py`, `cam_writer.py`, and `sprite_extractor.py`.

## Q File Binary Format Specification (Reverse-Engineered)

### Format Versions

| Magic | Source | Notes |
|-------|--------|-------|
| `RGMa` | RGSEditor / custom quests | Our target output format |
| `RGM6` | Base game quests | Read-only support |
| `RGM9` | Expansion quests | Read-only support |

All versions share the same placed-object section format. Differences are in header parameters.

### Complete RGMa File Structure

```
┌──────────────────────────────────────────────────────┐
│ HEADER (16 bytes)                                    │
│   [4B] Magic "RGMa"                                 │
│   [4B] Zeros                                        │
│   [4B] Magic "RGMa" (repeated)                      │
│   [4B] Zeros                                        │
├──────────────────────────────────────────────────────┤
│ QUEST NAME                                           │
│   Null-terminated ASCII string (e.g., "basicAI\0")   │
├──────────────────────────────────────────────────────┤
│ PATTERN NAME                                         │
│   12 bytes + null terminator (13 total)              │
│   Format: [4B][4B][4B]\0 (three 4-char segments)     │
│   May contain non-ASCII bytes as hash/checksum       │
├──────────────────────────────────────────────────────┤
│ MAP PARAMETERS (variable offset, 4-byte aligned)     │
│   [u32] Map width (256 for test maps)                │
│   [u32] Map height (256 for test maps)               │
│   [u32] Number of player factions (typically 4)      │
│   [u32] Starting gold (e.g., 2000)                   │
│   [u32] Zero                                         │
│   [u32] Secondary resource (e.g., 10000)             │
│   [u32] Zeros × 3                                    │
├──────────────────────────────────────────────────────┤
│ SPAWNER SECTIONS (repeated per lair)                 │
│   "NONEnone\0" marker                                │
│   [padding zeros]                                    │
│   [u32] entry_count (typically 4)                    │
│   entry_count × SPAWNER_ENTRY (24 bytes each):       │
│     [4B] Monster Object_ID (e.g., "BVr1")           │
│     [u32] Spawn level/count                          │
│     [8B] Zeros                                       │
│     [u32] 1 (active flag)                            │
│     [4B] Zeros                                       │
│   [u32] 0 (separator)                                │
│   [u32] lair_resource_value (e.g., 2001, 2002...)    │
│   [u32] 0                                            │
│   [u32] secondary_resource_value                     │
│   [zeros to next section]                            │
├──────────────────────────────────────────────────────┤
│ PLACED OBJECT GROUPS (repeated per owner/faction)    │
│   [4B] Terrain code (e.g., "gras")                   │
│   [u32] 5 (constant marker)                          │
│   [u32] entry_count                                  │
│   entry_count × PLACED_ENTRY:                        │
│     [4B] Object_ID (e.g., "ABJ1", "BBz1")           │
│     [u32] 0                                          │
│     [cstr] Description (null-terminated)             │
│     [u32] 1 (active flag)                            │
│     [u8] Grid position ('A'-'Y', 5×5 grid)          │
│   METADATA BLOCK:                                    │
│     [u32] 0                                          │
│     [u32] 3                                          │
│     [u32] 50 (×3 — resource limits?)                 │
│     [u32] 1 (×2)                                     │
│     [12B] zeros                                      │
│     [cstr] Player/faction name (e.g., "Player1\0")   │
├──────────────────────────────────────────────────────┤
│ PLAYER SECTION (at end of file)                      │
│   [u32] 2                                            │
│   "NONE" marker                                      │
│   [u32] player_count                                 │
│   [u32] total_faction_count                          │
│   Faction entries (same format as placed groups):    │
│     [4B] Short faction code (e.g., "Play", "Gobl")   │
│     [u32] 5                                          │
│     [cstr] Full faction name                         │
│     [u32] 1 or 0 (active flag)                       │
│     [u8] Home grid position                          │
│   FINAL METADATA BLOCK                               │
│   [u32] 7 (always appears to be fixed)               │
│   [u32] 50 (×3)                                      │
│   Trailing data                                      │
│   "Rel@" (4 bytes, file terminator)                  │
└──────────────────────────────────────────────────────┘
```

### Position Grid Encoding (CRACKED)

The position byte maps to a 5×5 grid using ASCII letters 'A' (65) through 'Y' (89):

```
     col 0   col 1   col 2   col 3   col 4
row 0:  A       B       C       D       E
row 1:  F       G       H       I       J
row 2:  K       L       M       N       O
row 3:  P       Q       R       S       T
row 4:  U       V       W       X       Y
```

- **M (77)** = center position (2,2) — always used for the Palace
- Grid position `byte` decodes to: `col = (byte - 65) % 5`, `row = (byte - 65) // 5`
- Encodes to: `byte = 65 + row * 5 + col`
- This grid is INDEPENDENT of map tile dimensions (works the same on 256×256 or 32768×32768 maps)
- **One building per grid cell — no two buildings may share the same position byte**
- A single placed entry can define multiple instances of the same type at different cells (e.g., 5 Temples of Krolm at D, I, N, R, S)
- Verified across all 23 quest files: exactly 25 unique values (65-89) appear

#### Grid Cell Occupancy (Constraint)

The game enforces one building per grid cell — you cannot place a building on top of another building, the same as in the RGSEditor. With 25 cells available (A-Y), a quest map can hold up to 25 placed buildings.

Note: The physical size of each grid zone depends on the map size category (small, medium, large, huge, gigantic). On smaller maps, zones are physically smaller, which limits how large a building can be placed without conflicting with adjacent-zone buildings. The .q format does NOT store pixel-precise positions — only the grid zone letter. The game engine resolves exact tile placement at load time based on the building's sprite footprint and the .rgs terrain.

The generator must:
1. **Enforce unique positions** — raise an error if two buildings are assigned the same cell
2. Spread lairs across different cells when auto-distributing
3. Always place Palace at 'M' (center), consuming that cell
4. Use the template .rgs file's dimensions (which implicitly define zone physical size)

### Spawner Entry Format (24 bytes)

```
Offset  Size  Field
0       4     Object_ID (ASCII, e.g., "BVr1" = Ratman Champion)
4       4     spawn_level (u32, values like 9-17)
8       8     zeros (reserved)
16      4     active_flag (u32, always 1)
20      4     zeros (padding)
```

### Placed Entry Format (variable length)

```
Offset  Size     Field
0       4        Object_ID (ASCII, e.g., "ABJ1", "BBz1")
4       4        zero (u32, always 0)
8       variable Description string (null-terminated)
n       4        position_count (u32, number of instances to place)
n+4     N        position_bytes (N = position_count × 1 byte, each 'A'-'Y')
```

Each position byte represents a UNIQUE grid cell. A single entry can place multiple instances of the same building type at different cells (e.g., `ABS1 "Temple to Krolm" count=5 positions=[D,I,N,R,S]`).

**Constraint: No two buildings may occupy the same grid cell.** The game enforces one building per cell. With 25 cells available (A-Y), a quest can have up to 25 placed buildings total.

### Object ID Conventions

| Prefix | Category | Examples |
|--------|----------|----------|
| AB | Player buildings | ABJ1=Palace, ABJ2=Palace Lvl 2, ABe1=Housing, ABE1=Guardhouse |
| BB | Monster lairs | BBz1=Goblin Fortress, BBH1=Goblin Camp, BBx1=Rat's Nest, BBw1=Ice Cave, BBS1=Snake Pit, BBB1=Dark Castle |
| BV | Monsters (spawners) | BVr1=Ratman Champion, BVs1=Ratman, BVq1=Goblin, BVQ1=Goblin Champion, BVN1=Daemonwood, BVP1=Bear |
| AA | Special buildings | (rare, appears in some quests) |
| AV | NPCs/Heroes | (pre-placed heroes) |
| AC | Decorations | (rare) |
| BA | Ambient objects | (terrain features) |

## Data Model

```python
@dataclass
class MapParams:
    width: int = 256          # Map tile width
    height: int = 256         # Map tile height
    num_factions: int = 4     # Number of player/AI factions
    starting_gold: int = 2000
    secondary_resource: int = 10000

@dataclass 
class SpawnerEntry:
    object_id: str            # 4-char ID (e.g., "BVr1")
    spawn_level: int          # Spawn count/level value

@dataclass
class SpawnerBlock:
    entries: list[SpawnerEntry]
    lair_resource: int        # Resource value for this lair

@dataclass
class PlacedEntry:
    object_id: str            # 4-char ID
    description: str          # Human-readable name
    positions: list[int]      # List of grid position bytes ('A'-'Y', 65-89)
                              # Each byte is a unique cell on the 5×5 grid
    
    @staticmethod
    def grid_col(pos_byte: int) -> int:
        return (pos_byte - 65) % 5
    
    @staticmethod
    def grid_row(pos_byte: int) -> int:
        return (pos_byte - 65) // 5

@dataclass
class PlacedGroup:
    terrain_code: str = "gras"  # 4-char terrain type
    entries: list[PlacedEntry]
    faction_name: str = ""      # Owner faction name

@dataclass
class Faction:
    short_code: str             # 4-char code (e.g., "Play", "Gobl")
    full_name: str              # Full name (e.g., "Player1", "Goblin Kingdom")
    home_position: int          # Grid position byte
    active: bool = True

@dataclass
class QuestMap:
    magic: str = "RGMa"
    quest_name: str = ""
    pattern_name: bytes = b""   # 12 bytes + null
    params: MapParams
    spawner_blocks: list[SpawnerBlock]
    placed_groups: list[PlacedGroup]
    factions: list[Faction]
```

## Key Design Decisions

### 1. Generate RGMa format only

We only need to WRITE RGMa (editor format) since that's what the game loads from custom quest folders. We can READ all formats for analysis/validation.

### 2. Position grid is the ONLY coordinate system

The game resolves the 5×5 grid cell to actual tile coordinates internally based on the map dimensions defined in the .rgs terrain file. Our generator places objects by grid cell letter, not pixel coordinates.

### 3. Template-based terrain

Rather than generating .rgs terrain files (complex binary format), we copy an existing flat-terrain .rgs as a template. The MyQuest/Quest.rgs file serves as the default template (256×256 flat grass).

### 4. Spawner blocks are optional for test quests

For a minimal test quest that just needs a Palace and some lairs on the map, spawner definitions can use sensible defaults (4 monster types per lair at standard levels).

### 5. MQXML generation uses string templates

The .mqxml format is simple XML. We generate it with f-strings rather than pulling in an XML library dependency, keeping the tool self-contained like the other workspace scripts.

### 6. Round-trip validation

Every generated .q file must be parseable back to an equivalent data structure. This is the primary correctness check since the game provides no error messages on load failure.

## MQXML Output Format

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Quest id="{guid}" dataset_base="Majesty">
  <DataConfiguration>
    <Template>{quest_name}.q</Template>
    <Constants>{quest_name}.rgs</Constants>
    <Load>
      <!-- Additional data files referenced here -->
    </Load>
  </DataConfiguration>
</Quest>
```

## Convenience API Design

```python
def generate_test_quest(
    quest_name: str,
    lairs: list[dict],         # [{"id": "BBw1", "desc": "Ice Cave", "position": "N"}]
    output_dir: str,
    palace_position: str = "M",  # Center by default
    starting_gold: int = 50000,  # High for testing
    extra_loads: list[str] = None,  # Additional files to load
) -> None:
    """Generate a complete quest package (q + rgs + mqxml) for testing."""
```

## CLI Interface

```
quest_map_generator.py parse <file.q>              # Print parsed structure
quest_map_generator.py generate --name <name> --lairs <spec> --output <dir>
quest_map_generator.py validate <file.q>           # Check structural validity
```

## Error Handling

- Invalid magic bytes → `QFormatError` with file path and expected magic
- Position byte out of range → `ValueError` with valid range explanation
- Object ID not 4 chars → `ValueError` with the invalid ID
- Missing terrain template → `FileNotFoundError` with searched paths
- Round-trip mismatch → `ValidationError` with byte-level diff location

## Testing Strategy

- **Round-trip tests**: Parse known .q files → serialize back → compare byte-for-byte
- **Grid position tests**: Verify A-Y encoding/decoding matches expected (col, row) pairs
- **Cross-validation**: Parse generated files with the same parser, verify structural equivalence
- **Known-good reference**: Compare generated test quest against MyQuest/Quest.q structure
