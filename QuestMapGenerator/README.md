# Quest Map Generator

Programmatic .q binary quest map generator for Majesty Gold HD.

## Status

**All 10 tasks COMPLETE.** Full parser + writer + CLI + validation working.

- Parser: 37/37 quest files parse (100%)
- Writer: Round-trip verified
- CLI: parse, validate, generate subcommands
- Validation: 37/37 files pass with 0 errors
- Convenience API: One-call quest generation

## Files

| File | Purpose |
|------|---------|
| `quest_map_generator.py` | Main tool — parser, grid encoding, data model |
| `test_mapInfo.py` | Test suite — validates parser against all 37 quest files |
| `q_format_research.py` | Exploration script used during reverse-engineering |
| `README.md` | This file |

Spec docs live at `.kiro/specs/quest-map-generator/` (design.md, tasks.md, requirements.md).

## Key Research Findings

### .q File Position Encoding (CRACKED)
- Positions are a **5×5 grid** using ASCII bytes `A` (65) through `Y` (89)
- `M` (77) = center (col 2, row 2) — always Palace location
- Decode: `col = (byte - 65) % 5`, `row = (byte - 65) // 5`
- One building per grid cell (game enforces this)

### Placed Entry Format (CORRECTED)
```
[4B Object_ID] [u32 0] [null-terminated desc] [u32 position_count] [position_count × u8 pos_byte]
```
A single entry can place multiple instances (e.g., 5 Temples at D,I,N,R,S).

### Spawner Entry Format (24 bytes)
```
[4B Monster_ID] [u32 spawn_level] [8B zeros] [u32 1] [4B zeros]
```

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

## Remaining Work (Tasks 3-10)

3. Q File Writer (binary serialization + round-trip test)
4. MQXML Generator
5. Terrain File Handling (.rgs template copy)
6. High-Level Convenience API
7. Pretty-Print text representation
8. Validation
9. CLI Interface
10. Integration Testing & Documentation
