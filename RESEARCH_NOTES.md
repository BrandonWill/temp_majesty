# Majesty HD Sprite Format Research Notes

**Status:** All binary formats are **fully decoded and working**. The Python tools
(`cam_reader.py`, `sprite_extractor.py`, `sprite_injector.py`, `cam_writer.py`)
handle the complete pipeline from extraction to injection.

The container format was validated against a C# reference tool (``) that
was obtained during early reverse-engineering sessions. That tool is not part of
this repo — it was used as ground-truth to build the Python port.

---

## Container Format (use `cam_reader.py`)

### File header
```
+0    12   Fixed magic: "CYLBPC  " + 01 00 01 00
+12   4    u32: sectionCount (4 in maindata.cam)
+16   4    u32: contentHeaderLength (not used when reading)
+20   8xN  Per section: char[4] extension + u32 sectionHeaderOffset
```

### Content header (sequential, one block per section, right after file header)
```
For each section:
  +0   4     u32: filesCount
  +4   4     zeros (padding)
  +8   28xM  per file: byte[20] name (null-padded) + u32 fileOffset + u32 fileSize
```

### Content
Raw file bytes, one blob per file. Use each file's `fileOffset`/`fileSize` to slice directly.

### Section breakdown (maindata.cam)

| # | Extension | File count | Typical size | What it is |
|---|-----------|-----------:|--------------|------------|
| 0 | `IMAG`    | 380        | ~5-19 KB     | Animation-set descriptors (per-unit/building). Contains image-set table + frame descriptors + per-direction geometry. |
| 1 | `TILE`    | 17,224     | ~1-8 KB      | Per-frame sprite pixel data. 8-bit paletted, per-row RLE compressed. |
| 2 | `SPLT`    | 854        | 1032 bytes   | 256-color RGBA palettes (fixed-size). **Read-only — do not modify.** |
| 3 | `CUT `    | 20         | 886 bytes    | Small fixed-size resource (unexplored, likely UI elements). |

---

## `cam_reader.py` usage

```python
from cam_reader import read_cam
sections = read_cam("maindata.cam")
imag, tile, splt, cut = sections
for f in imag.files:
    print(f.display_name, hex(f.data_off), f.data_size)
```

---

## IMAG blob internal format (animation set, per-unit/building)

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

### Frame descriptor block (directional units)
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

## TILE sprite format (Version 3) — SOLVED

8-bit paletted sprites with per-row RLE compression.

### Header
```
+0x00   2     u16: version (always 3)
+0x02   2     u16: width
+0x04   2     u16: height
+0x06   6     zeros
+0x0C   4     u32: palette_id (index into SPLT section)
+0x10   H×4   height × u32: per-row offset table (offsets from start of pixel data)
```

### Row RLE (after offset table)
Each row is a sequence of segments:
```
[u16 x_position] [u8 count] [u8 flags] [count × u8 pixel_bytes]
```
- `x_position` — absolute column position (not relative skip)
- `count` — number of pixel bytes following
- `flags` — 0x80 = last segment in row
- Pixel bytes — palette indices (0 = transparent, 248-255 = shadow/blend)

### Key facts
- Pixel indices reference the palette at `palette_id` in the SPLT section
- Palette index 0 is always transparent
- Indices 248-255 map to shadow/blend colors (rendered as magic pink in extraction)
- `sprite_extractor.py` decodes this format; `sprite_injector.py` encodes it
- Round-trip verified: encode → decode produces identical pixel data

---

## IMAG writing for mod CAMs

Mod-loaded CAM files (quests/mods via DataConfiguration) use the same IMAG format.
The WrathOfKrolm example (`SDK/Example/Data/WrathOfKrolm_maindata.cam`) has 5 working
IMAG records that serve as known-good templates:
- `XR47DustofDeth` — 292 bytes, directionless overlay (simplest template)
- `KR0TKrolm-appear` — 364 bytes, another overlay

TILE indices in mod CAMs reference the mod's own TILE section (0-based local indices,
not the base game's global pool).

---

## Historical note

Early sessions used manual byte-offset guessing for the container format, producing
several incorrect assumptions. These were corrected once a C# reference tool
(`` from the game developers or a decompiled source) was obtained and
validated byte-for-byte against the real `maindata.cam`. All Python tools are now
authoritative — use them, not the older hand-derived notes.

## Suggestion

Even though this is proprietary, the game was published in 1999. The formats reflect
common practices of that era — simple RLE compression, fixed palettes, flat container
structures with offset tables.
