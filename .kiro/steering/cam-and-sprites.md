---
inclusion: manual
description: CAM archive format, TILE sprite encoding, palette system, and sprite extraction/injection workflow
---

# CAM Archive & Sprite System

## Tools

- `cam_reader.py` — Parse CAM archives, list sections and entries
- `sprite_extractor.py` — Extract sprites as PNGs from maindata.cam with correct palette colors
- `sprite_injector.py` — Encode PNGs back into TILE RLE format
- `cam_writer.py` — Repack CAM archives with modified/replaced entries
- `str_tool.py` — STRT string table converter (binary ↔ editable TXT)
- `RESEARCH_NOTES.md` — Full binary format documentation

## Reference Documentation

- #[[file:CAM_MODDING_GUIDE.md]] — Task-oriented guide: "what do I modify to achieve X?"

## CAM File Format

Container with named sections, each holding indexed file entries:
- **IMAG** — Animation metadata (frame counts, offsets, ImageIDBase mapping)
- **TILE** — Actual pixel data in RLE-compressed format
- **SPLT** — Palettes (256-color, 768 bytes each = R,G,B × 256)
- **CUT** — Cutscene data
- **DUNT** — Unit type definitions (stats, ImageIDBase, spells)
- **DACT** — Action/spell definitions
- **DMOV** — Movement data

## TILE Sprite Format (Version 3)

```
Header (variable size):
  u32 version (3)
  u32 width
  u32 height
  u16 hotspot_x
  u16 hotspot_y
  6 zero bytes
  u32 palette_id        ← index into SPLT section
  height × u32          ← row offset table (offset from start of pixel data)

Pixel data (per row):
  Repeated segments: [u16 x_position][u8 count][u8 flags][count × u8 pixel_indices]
  - x_position: ABSOLUTE column (not relative skip)
  - count: number of pixels in this segment
  - flags: 0x80 = last segment in row (end-of-row marker)
  - pixel bytes: palette indices into the SPLT palette
```

## Palette System

- **SPLT palettes are READ-ONLY** — modifying them crashes the game
- Index 0 = transparent
- Indices 248-255 = shadow/blend (render as magic pink in extraction)
- Sprites MUST use colors from an existing palette — quantize new art to target palette
- `palette_id` in TILE header references which SPLT entry to use

## Sprite Extraction Workflow

```bash
# List available sprites
python sprite_extractor.py --cam Data/maindata.cam --list

# Extract specific unit sprites
python sprite_extractor.py --cam Data/maindata.cam --extract AVA1 Walk

# Extract by TILE index
python sprite_extractor.py --cam Data/maindata.cam --tile-idx 3547
```

## Sprite Injection Workflow

```bash
# Roundtrip test (verify encoder matches original)
python sprite_injector.py --cam Data/maindata.cam --roundtrip --tile-idx 3547

# Inject modified sprite
python sprite_injector.py --cam Data/maindata.cam --inject modified.png --tile-idx 3547 --output modded.cam

# Repack CAM with replaced tile
python cam_writer.py --cam Data/maindata.cam --replace-tile 3547 --tile-data new.bin --output modded.cam
```

## Creating New Visual Effects (Overlays)

1. Create sprite frames (short animation loop, transparent background)
2. Encode as TILE data using existing SPLT palette colors
3. Add IMAG record pointing to the TILE frames
4. The overlay is non-directional (no 8-way facing needed)
5. Reference by `ImageIDBase` in overlay XML definition

Example: The `petrify_effector` (MRB1) sprite shows overlay structure.

## Critical Constraints

- **Never modify SPLT entries** — crashes the game
- **All new sprites must use existing palette colors** — quantize to target SPLT
- **TILE roundtrip verification required** — every generated TILE must decode back to identical pixels
- **In-game pixel modification confirmed** — tested: all walk frames to solid color = visible change
- **Test in original game mode** (not expansion) for base Data/ changes
- **Expansion mode** overlays DataMX/ on top of base Data/

## Key Data Files

| File | Content |
|------|---------|
| `Data/maindata.cam` | Main sprite archive (91.6 MB) — IMAG + TILE + SPLT |
| `Data/unittype.cam` | Unit definitions (DUNT section, ImageIDBase field) |
| `Data/action.cam` | Spell/action definitions (DACT section) |
| `DataMX/mx_maindata.cam` | Expansion sprites (overlays base) |
| `DataMX/mx_Unittype.cam` | Expansion unit types |

## ImageIDBase System

Units and effects are identified by 4-char codes:
- `AV**` = Player heroes/NPCs (AVA1 = Warrior, AVB1 = Ranger, etc.)
- `BV**` = Monsters (BVL1 = Goblin, BVD1 = Dragon, etc.)
- `AB**` = Player buildings (ABJ1 = Palace, ABE1 = Guardhouse)
- `BB**` = Monster lairs (BBH1 = Goblin Camp, BBw1 = Ice Cave)
- `MR**` = Overlays/effects (MRB1 = Petrify effector)

The IMAG section maps these codes to TILE frame ranges.
