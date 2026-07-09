# Majesty HD Sprite Editor

A work-in-progress toolset for extracting, viewing, and injecting sprite graphics
into Majesty Gold HD's `maindata.cam` binary data file.

## Status

| Component                          | Status        |
|-------------------------------------|---------------|
| Container format (sections/files)  | ✅ Solid - validated against real `` C# source |
| IMAG blob parsing (image-set table)| ✅ Confirmed against 3 units (Adept, Barbarian, Warrior) |
| Frame descriptor / direction blocks| ✅ Confirmed against 2 directional units |
| TILE index resolution              | ✅ Confirmed - frame indices resolve to real, sensible TILE entries |
| TILE pixel payload format          | ✅ **CRACKED** - 8-bit paletted, per-row RLE with absolute x-positioning |
| Palette system                     | ✅ **SOLVED** - SPLT section holds 854 RGBA palettes (read-only! modifying crashes) |
| PNG extractor                      | ✅ Working with correct colors and transparency |
| PNG injector / TILE encoder        | ✅ Working - round-trip verified, in-game pixel changes confirmed |
| CAM repacker                       | ✅ Working - identity repack + pixel mods verified in-game |
| unittype.cam modification          | ✅ Working - can swap sprite sets, change stats |
| In-game sprite modification        | ✅ **CONFIRMED** - pixel changes visible in original game mode |
| Expansion mode modding             | ❌ Expansion mode ignores base CAM file changes |
| SPLT palette modification          | ❌ Crashes the game - palettes are read-only |
| Full sprite replacement            | ⬜ Next step - replace artwork using existing palette indices |
| New unit creation                   | ⬜ Requires new IMAG + TILE entries + unittype.cam definition |

## Files

- `RESEARCH_NOTES.md` — Full reverse-engineering findings, current as of the  breakthrough
- `cam_reader.py` — Faithful Python port of ``'s container-format reader. Trust this over hand-derived offset math.
- `sprite_extractor.py` — Built on `cam_reader.py`. Parses IMAG blobs (image-set tables, frame descriptors, per-direction geometry) and resolves frame indices into the TILE section. Cannot yet produce PNGs - the TILE payload format itself isn't decoded.
- `` / `proj` — Ground-truth C# unpack/pack tool source (not built/run in this environment - no .NET SDK or network access here, so it was ported to Python instead).

## Quick Start

```
python sprite_extractor.py --cam maindata.cam --list
python sprite_extractor.py --cam maindata.cam --dump-anim AVA1
python sprite_extractor.py --cam maindata.cam --dump-frames AVA1 Walk
python sprite_extractor.py --cam maindata.cam --extract AVA1 Walk
python sprite_extractor.py --cam maindata.cam --extract-tile 3547
```

## What changed this session

A previous session found the real `` source (someone else's
validated unpack/pack tool for this exact format). That's a much stronger
source of truth than continued hand-decoding, and it caught real bugs:

- The container-format section directory was being misparsed (a tag/offset
  byte-alignment bug), leading to a false belief that the pixel-index
  section was tagged `CUT` with 854 entries. It's actually tagged `SPLT`.
  A real, separate `CUT ` section exists but only has 20 entries.
- The image-set table format (inside each unit/building's IMAG blob) was
  wrong - assumed 12-byte `(setID, frameCount, relOffset)` triplets, but
  it's actually a `u32` count followed by 8-byte `(setID, relOffset)` pairs,
  with no frame-count field in this table at all.
- **The single most important finding:** neither `SPLT` (854 entries, fixed
  1032 bytes each) nor `CUT` (20 entries, fixed 886 bytes each) is where
  character animation pixel data lives - both are too small and too
  uniformly-sized. The real home is the **`TILE` section, with 17,224
  variable-sized entries** - confirmed by checking that frame descriptor
  indices (e.g. 3547+) resolve to real, sensibly-sized TILE entries, for
  two different units (Adept, Barbarian).

Frame descriptor parsing was also corrected and validated against a second
unit: direction offsets must be read as **signed**, and frame count per
direction is best derived from the byte-distance to the next populated
direction slot, not from a header field (which gave a wrong answer when
checked against Barbarian's data).

## Next Steps (for next session)

1. **Full sprite replacement** — Replace all Adept animation frames with
   modified artwork using valid existing palette indices (no palette changes).
2. **New unit creation** — Create a new unit with custom sprites by adding
   IMAG/TILE entries to maindata.cam + a new entry in unittype.cam.
3. **Quest-based modding** — Use the MyQuest framework to package mods
   as distributable quest files.

## Key Constraints Discovered

- **Original game mode only** — Base CAM file modifications only take effect
  in original game mode. Expansion mode uses its own compiled data.
- **Palettes are read-only** — Modifying SPLT entries crashes the game.
  Sprites must use colors already defined in their existing palette.
- **unittype.cam is live** — Unit stats, ImageIDBase references, and other
  properties in unittype.cam are read at runtime and can be freely modified.
- **Pixel data in TILE entries is live** — Changing pixel byte values in
  the TILE section produces visible in-game changes (confirmed: Adept walk
  frames turned solid white when all pixels set to index 1).

## Game Modes and Data Loading

The game has two modes with different data loading:

**Original mode** (`Data/MajestyDatasetDefinitions.xml`):
- Loads from `Data/` folder only
- Modify: `Data/maindata.cam` (sprites), `Data/unittype.cam` (unit defs)

**Expansion mode** (`DataMX/MajestyExpansionDatasetDefinitions.xml`):
- Loads base `Data/` first, then overlays `DataMX/` on top
- The expansion OVERRIDES base entries with same IDs
- Modify: `DataMX/mx_maindata.cam` (sprites), `DataMX/mx_Unittype.cam` (unit defs)

**Targeting your mod:**
| Target | Files to modify |
|--------|----------------|
| Original only | `Data/maindata.cam` + `Data/unittype.cam` |
| Expansion only | `DataMX/mx_maindata.cam` + `DataMX/mx_Unittype.cam` |
| Both modes | All four files above |

**Data sizes:**
| File | Sections |
|------|----------|
| `Data/maindata.cam` (91.6 MB) | 380 IMAG, 17,224 TILE, 854 SPLT |
| `DataMX/mx_maindata.cam` (53.8 MB) | 166 IMAG, 9,031 TILE, 288 SPLT |
| `Data/unittype.cam` (148 KB) | 20 DMOV, 394 DUNT |
| `DataMX/mx_Unittype.cam` (59.6 KB) | 2 DMOV, 174 DUNT |
