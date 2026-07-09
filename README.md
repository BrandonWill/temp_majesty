# Majesty Gold HD Modding Toolkit

A complete toolset for extracting, modifying, and injecting sprites, spell effects,
and unit definitions in Majesty Gold HD. Fully reverse-engineered and verified in-game.

## Status

| Component | Status |
|-----------|--------|
| CAM container format | ✅ Fully decoded |
| TILE sprite pixel format | ✅ **Cracked** — 8-bit paletted, per-row RLE, absolute x-positioning |
| SPLT palette system | ✅ Decoded (854 palettes, 256 RGBA entries each) — **read-only** |
| IMAG animation metadata | ✅ Image sets, frame descriptors, 8-direction blocks |
| PNG sprite extraction | ✅ Working with correct colors and transparency |
| TILE encoder (PNG → game format) | ✅ Round-trip verified, in-game confirmed |
| CAM repacker | ✅ Identity repack + modified tiles verified in-game |
| In-game pixel modification | ✅ **Confirmed working** in original game mode |
| Unit type modification (unittype.cam) | ✅ Stats, sprite swaps, verified in-game |
| Expansion mode modding | ✅ Uses `DataMX/mx_maindata.cam` + `DataMX/mx_Unittype.cam` |
| Spell/effect animation modding | ✅ Same TILE format — overlays, particles, projectiles all moddable |
| SPLT palette modification | ❌ Crashes the game — palettes are read-only |

## Tools

| File | Purpose |
|------|---------|
| `cam_reader.py` | Parse CAM archive files (sections, file entries, offsets) |
| `sprite_extractor.py` | Extract sprites as PNGs with correct palette colors |
| `sprite_injector.py` | Encode PNGs back into TILE RLE format |
| `cam_writer.py` | Repack CAM archives with modified/replaced entries |

## Quick Start

```bash
# List all sprite records
python sprite_extractor.py --cam maindata.cam --list

# Show a unit's animation sets
python sprite_extractor.py --cam maindata.cam --dump-anim AVA1

# Extract all walk frames with correct colors
python sprite_extractor.py --cam maindata.cam --extract AVA1 Walk

# Extract a single tile frame
python sprite_extractor.py --cam maindata.cam --extract-tile 3547

# Round-trip test (decode → re-encode → verify)
python sprite_injector.py --cam maindata.cam --roundtrip --tile-idx 3547

# Repack CAM with a modified tile
python cam_writer.py --cam maindata.cam --replace-tile 3547 --tile-data new.bin --output modded.cam

# Identity repack (verify repacker)
python cam_writer.py --cam maindata.cam --identity --output test.cam
```

## Game Modes and Data Loading

The game has two modes with independent data pipelines:

**Original mode** — loads from `Data/` only:
```
Data/MajestyDatasetDefinitions.xml → loads Data/maindata.cam, Data/unittype.cam, etc.
```

**Expansion mode** — loads base `Data/` first, then overlays `DataMX/`:
```
DataMX/MajestyExpansionDatasetDefinitions.xml → base="Majesty" (inherits base data)
  → then loads DataMX/mx_maindata.cam, DataMX/mx_Unittype.cam, etc.
  → expansion entries OVERRIDE base entries with same IDs
```

### Targeting Your Mod

| Target | Sprite file | Unit type file |
|--------|-------------|---------------|
| Original only | `Data/maindata.cam` | `Data/unittype.cam` |
| Expansion only | `DataMX/mx_maindata.cam` | `DataMX/mx_Unittype.cam` |
| Both modes | Modify all four files |

### Data File Sizes

| File | IMAG records | TILE frames | SPLT palettes |
|------|-------------|-------------|---------------|
| `Data/maindata.cam` (91.6 MB) | 380 | 17,224 | 854 |
| `DataMX/mx_maindata.cam` (53.8 MB) | 166 | 9,031 | 288 |

## What Can Be Modded

### Unit Sprites (characters, buildings, monsters)
Every unit has an IMAG record in `maindata.cam` containing animation metadata:
- Multiple image sets: Walk, Stand, Attack, Cast, Die, Dead, Special, etc.
- 6-8 directions per set (isometric facings)
- Variable frame count per direction (typically 7-8 for walk cycles)

Each frame is a TILE entry using the same RLE format.

### Spell & Effect Animations
Spells use three types of visuals, all stored as standard TILE sprites:

| Type | Defined in | Example | IMAG prefix |
|------|-----------|---------|-------------|
| Caster animation | Unit's own IMAG "Cast" set | Adept raising staff | `AVA1` |
| Overlays (persistent effects) | `M_Overlays.xml` | Fire shield glow | `WRb2` |
| Particle systems | `M_ParticleSystems.xml` | Meteor storm, fireballs | `XL20` |
| Projectiles | `M_Projectiles.xml` | Lightning bolt, acid bolt | `WRC1` |

Effect IMAG records in maindata.cam include:
- `WRd1teleport_e` — Teleport visual effect
- `WRc1fire_blast_e` — Fire blast explosion
- `WRC1lightng_bolt` — Lightning bolt
- `XL14Firestorm` — Firestorm particles
- `XL20MeteorStrmEffct` — Meteor storm effect
- `HRA1healing_e` — Healing glow
- `WPe1fireball_missil` — Fireball projectile

All use the same TILE RLE format and can be extracted/modified identically to unit sprites.

### Unit Stats and Behavior
`unittype.cam` (DUNT section) defines every unit's properties:
- HP, speed, attack, defense, resistances
- ImageIDBase (which sprite set to use)
- Allowed weapons, armor, spells
- Movement class, recruitment cost/delay

These are read live and can be freely modified.

### Spell Definitions
`action.cam` (DACT section) defines spell behavior:
- Which animation set to play (ImageSet = "Cast")
- Sound effects
- GPL script function to execute
- Duration, cooldown, level requirements

## TILE Pixel Format (Technical)

```
[16 bytes]  Header: version(3), height(u16), w2, w3, w4(32), w5, w6, w7
[6 bytes]   Zeros (padding)
[4 bytes]   u32 palette_id (index into SPLT section — DO NOT MODIFY SPLT)
[height×4]  u32 offset table (offsets relative to byte 26, self-referencing)
[variable]  Row data (RLE compressed pixel runs)
```

**Row format** — repeated segments until last flag set:
```
[u16 x_position]  Absolute column where opaque pixels begin
[u8  count]       Number of opaque pixels
[u8  flags]       0x80 = last segment in row, 0x00 = more follow
[count bytes]     Palette indices (one byte per pixel)
```

**Transparency:**
- Palette index 0 = fully transparent
- Palette indices 248-255 = "magic pink" (game renders as shadow/blend, not opaque)
- Any gap between segments = transparent pixels

## Key Constraints

| Rule | Detail |
|------|--------|
| **Don't modify SPLT palettes** | Crashes the game. Use existing palette colors only. |
| **Original mode for base mods** | `Data/maindata.cam` changes only visible in original game mode |
| **Expansion uses DataMX** | Expansion mode reads `DataMX/mx_maindata.cam` for sprites |
| **Preserve pixel format** | Keep RLE segment structure intact; only change pixel byte values |
| **Quest mods can override** | Quest CAM files may override base entries — needs testing for sprites |

## Architecture

```
unittype.cam (DUNT section)
  └── Unit definition: ImageIDBase = "AVA1"
        └── maindata.cam IMAG section: "AVA1Adept"
              └── Image sets (Walk, Stand, Attack, Cast, Die...)
                    └── Frame descriptors → TILE indices
                          └── TILE[3547..3594] = Walk frames (6 dirs × 8 frames)
                                └── Pixel bytes = palette indices
                                      └── SPLT[350] = 256-color RGBA palette

action.cam (DACT section)
  └── Spell definition: "teleport_short"
        ├── ImageSet = "Cast" (uses unit's Cast animation)
        └── GPLFunction = "Teleport_Short_Effect" (spawns visual effect)
              └── Overlay/Particle definition (M_Overlays.xml)
                    └── ImageIDBase = "DRa1" → maindata.cam IMAG "DRa1teleport_shrt_e"
                          └── TILE frames (same RLE format)
```

## Requirements

```
pip install Pillow numpy
```
