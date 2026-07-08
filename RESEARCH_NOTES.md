# Majesty HD Sprite Format Research Notes

**Status:** Container format (file header, sections, per-file records) is now
**fully validated** via ground-truth C# source (``), and confirmed
against the real `maindata.cam` byte-for-byte with a Python port
(`cam_reader.py`). This supersedes all the hand-derived byte-offset guessing
from earlier sessions - several of those guesses turned out to be wrong in
ways that were only caught once real source code and the real file were
available together.

**Open problem:** the pixel payload format inside `TILE` section files (the
section that actually holds character/unit animation frames) is still
unsolved. It looks like a per-row RLE/offset-table compression, not raw
uncompressed RGBA. This is the next thing to crack.

---

## Container Format (VALIDATED - do not re-derive, just use `cam_reader.py`)

Ported directly from ``'s `CamLib.Read()`. Confirmed byte-exact
against the real file.

### File header
```
+0    12   Fixed magic: "CYLBPC  " + 01 00 01 00
+12   4    u32: sectionCount (4 in maindata.cam)
+16   4    u32: contentHeaderLength (NOT used when reading - only needed
                for round-trip writing)
+20   8xN  Per section: char[4] extension + u32 sectionHeaderOffset
                (sectionHeaderOffset is likewise read but NOT used when
                reading - the content header is read sequentially right
                after the file header, in section order, regardless of
                what this field says)
```

### Content header (sequential, one block per section, right after file header)
```
For each section:
  +0   4     u32: filesCount
  +4   4     zeros (pause/padding)
  +8   28xM  per file: byte[20] name (null-padded/binary) + u32 fileOffset
                                                          + u32 fileSize
```

### Content
Raw file bytes, one blob per file. You don't need to trust ordering when
reading - just use each file's own `fileOffset`/`fileSize` to slice directly.

### Real section breakdown (confirmed against maindata.cam)

| # | Extension | File count | Typical size | What it actually is |
|---|-----------|-----------:|---------------|----------------------|
| 0 | `IMAG`    | 380        | ~5-19 KB, variable | Per-unit/per-building **animation-set descriptor blobs** (this is what earlier sessions called "records" - e.g. `AVA1Adept`, `BBt1chest1`). Contains the image-set table + frame descriptors + per-direction geometry, but NOT raw pixel data. |
| 1 | `TILE`    | **17,224** | variable, ~1-8 KB+ | **This is where actual per-frame sprite pixel data lives.** Names are raw binary sequential indices, not ASCII. Frame descriptor indices in IMAG blobs (see below) reference entries here, not the small SPLT/CUT tables. |
| 2 | `SPLT`    | 854        | constant 1032 bytes | Small **fixed-size** resource - every single entry is exactly 1032 bytes with zero variation. Almost certainly icons/cursors/selection-markers (there are record names like `selection_ring`, `selection_red` in the IMAG section), NOT general sprite storage. |
| 3 | `CUT `    | 20         | constant 886 bytes | Another small **fixed-size** resource, only 20 entries. Unexplored - likely another small icon/UI-element set given the tiny count and fixed size. |

**This corrects a real bug from an earlier session:** hand-parsing the file
header byte-by-byte (without the C# source) mixed up which 4 bytes were a
tag vs. an offset for 2 of the 4 sections, leading to the false belief that
the `SPLT` section didn't exist in the directory and that the section at
`0x785B4` was tagged `CUT`. It's actually tagged `SPLT`. There IS a real,
separate `CUT ` section, but it only has 20 entries - not the 854 previously
attributed to "CUT".

---

## `cam_reader.py` - use this, not manual offset math

```python
from cam_reader import read_cam
sections = read_cam("maindata.cam")   # or pass raw bytes
imag, tile, splt, cut = sections
for f in imag.files:
    print(f.display_name, hex(f.data_off), f.data_size)
```

Each file object has `.name` (raw 20 bytes), `.display_name` (decoded/
stripped, only meaningful for IMAG section which uses real ASCII names),
`.data_off`, `.data_size`.

---

## IMAG blob internal format (the "animation set", per-unit/building)

Verified against real `AVA1Adept` blob (0x10F810, 6004 bytes):

```
+0x00   4     u32 n_directions header value (unclear exact meaning - doesn't
                                              cleanly match the 8-slot
                                              direction-offset array found
                                              deeper in frame descriptors)
+0x04   16    padding/reserved, zeros
+0x14   4     u32 entryCount - number of image-set entries that follow
+0x18   8xN   entries: u32 setID + u32 relOffset  <- CORRECTED: this is
                                                      8 bytes, NOT 12. There
                                                      is no frameCount field
                                                      in this table at all;
                                                      an earlier session's
                                                      12-byte-triplet
                                                      assumption produced
                                                      garbage (frame counts
                                                      in the thousands,
                                                      obviously-wrong setIDs)
                                                      once tested for real.
```

setID values (from `ImageSetIDXRef.xml`, referenced by an earlier session -
not independently re-verified this session, but internally consistent):
Walk=1, Stand=8, Attack=16, Special=64, Build=80, Die=96, Cast=128, Carry=144,
Recoil=160, Active=192, Inactive=208, Dead=224, Crumble=240, Minimap=300,
Damage=316, Hotspot=400, Sel-Underlay=500, Sel-Overlay=550, Interface=1000,
UnitTexture=4000.

### Frame descriptor block (pointed to by an image-set entry's relOffset)

For **directional** sets (units - confirmed against AVA1's Walk entry):
```
+0x00   4     u32 = 8 (type flag, meaning unconfirmed)
+0x0C   4     u32 - misc value, meaning unconfirmed (was 257 in two unrelated
                    records - BVQ1's old Stand example and AVA1's Walk - so
                    likely a shared default/fallback rather than a per-frame
                    pixel index)
+0x38   32    8x u32: relative offsets to 8 per-direction blocks (relative to
                       the SAME blob the frame descriptor lives in). Slots
                       with value 0 are unused. NOTE: header says
                       n_directions=4 but there are 8 slots here - likely
                       full 8-way facing regardless of the header field.
```

Per-direction block (112 bytes each in the one confirmed example - AVA1
Walk; **this stride may not be universal**, see caveat below):
```
+0x04   4     u32: low 16 bits + high 16 bits split - high 16 = frame count
                   (confirmed: AVA1 Walk had high16=8, and exactly 8
                   (flag,index) pairs followed at +0x30)
+0x14   4     i16,i16: x_offset, y_offset (sprite hotspot)
+0x18   4     u16,u16: width, height - CAVEAT: for AVA1 Walk this produced
                   width=13,height=12 but that does NOT match the referenced
                   TILE entries' actual byte sizes under a naive W*H*4
                   assumption (see TILE section below) - the pixel format is
                   NOT raw uncompressed RGBA at these sizes, so don't trust
                   width*height*4 as a validation check until the TILE
                   payload format itself is decoded.
+0x30   8xF   F pairs of (u32 zero/flag, u32 index) - CORRECTED: earlier
                   sessions assumed this indexed the small SPLT/CUT tables
                   (854/20 entries) and called it "CUT index". That's WRONG -
                   the values found here (3547, 3548, 3549... up to at least
                   3562 for AVA1's Walk direction blocks) exceed those small
                   tables entirely. They DO fall well within the TILE
                   section's 17,224 entries and resolve to real, sensibly-
                   sized variable-length file entries there. This is the
                   correct table to index into for per-frame pixel data.
```

**CAVEAT on the 112-byte per-direction stride and the exact +0x14/+0x18
geometry offsets:** this was derived from exactly one example (AVA1's Walk
set) and a very different, non-directional record (`BBt1` chest, a static
object) showed a different stride (~108-132 bytes, varying) and didn't
cleanly fit the same 8-direction-array indirection - simpler objects seem to
have their frame descriptor point DIRECTLY at what would otherwise be a
per-direction block, skipping the direction-offset-array layer entirely
(makes sense: a static object has no "direction"). **Don't assume the
directional-unit layout above is universal until it's checked against a
second directional unit** (try `AVB1` Barbarian or `AVL1` Warrior next -
same 8-direction structure should be confirmed or refuted quickly).

**UPDATE - checked against AVB1 (Barbarian) and AVL1 (Warrior) this
session:** the image-set table format (count + 8-byte setID/relOffset
pairs) generalizes cleanly - both units produced clean, recognizable setIDs
with no garbage. The 8-direction-offset-array structure also generalizes,
BUT:
- The direction offsets must be read as **signed** i32, not u32 - one slot
  in AVB1 was legitimately `-8` (0xFFFFFFF8), which would look like a huge
  garbage value if read unsigned. Treat offsets <= 0 as "unused slot."
- **The per-direction block stride is NOT a fixed 112 bytes** - it varies
  per record based on frame count. AVA1's Walk blocks were 112 bytes (8
  frames); AVB1's Walk blocks were 104 bytes (7 frames). The relationship
  is `stride = 48 + frameCount * 8` (48-byte fixed header + 8 bytes per
  frame index pair).
- **Don't trust the u32 field at block+0x04 (high 16 bits) as the frame
  count** - for AVB1 this read as 8 when the real count was 7, causing the
  8th "index" read to actually be garbage spilling in from the start of the
  NEXT direction block (value 0x00080001, recognizable as that same
  type-flag pattern). The reliable way to get frame count for a given
  direction slot is from the byte distance to the NEXT populated direction
  offset (`(next_offset - this_offset - 48) / 8`), not from any single
  header field. This doesn't help for the last populated slot in the array
  (no "next" offset) - that one still needs a header-field-based answer;
  hasn't been solved yet.

---

## TILE section: the real home of per-frame pixel data (UNSOLVED payload format)

Confirmed: indices referenced by IMAG frame descriptors (e.g. AVA1 Walk's
3547-3562+) resolve to real TILE entries with sensible variable sizes:

| Index | Offset | Size |
|-------|--------|------|
| 3547 | 0x24B4D39 | 1963 |
| 3548 | 0x24B54E4 | 1693 |
| 3549 | 0x24B5B81 | 1661 |
| 3555 | 0x24B834B | 2021 |

Sizes are **not** multiples of 4 (1963 is odd) - ruling out plain
uncompressed RGBA (which would always be a clean W x H x 4). Something is
compressing/packing the pixel data.

Header bytes of several TILE entries (first 16 bytes, as u16 words):

| Index | size | u16 header words |
|-------|------|-------------------|
| 0     | 1360 | 3, 61, 60, 0, 32, 29, 51, 1 |
| 1     | 1377 | 3, 61, 60, 0, 32, 29, 51, 1 |
| 3547  | 1963 | 3, 58, 44, 0, 32, 32, 46, 1 |
| 3548  | 1693 | 3, 52, 44, 0, 32, 34, 44, 1 |
| 5000  | 1756 | 3, 47, 61, 0, 32, 49, 41, 1 |
| 10000 | 1081 | 3, 42, 47, 47, 32, 15, 9, 7 |
| 100 (building, much bigger) | 7724 | 3, 135, 224, 0, 3616, 112, 74, 8 |

Observations:
- Word 0 is always `3` for the unit-scale entries checked - likely a format/
  version tag.
- Word 4 (byte offset +8) is `32` for every *unit-frame-scale* entry checked,
  but `3616` for the one much-bigger building tile checked - suggesting this
  field means something different (or scales differently) for large static
  tiles vs. small animated-unit frames. Possibly a fixed canvas width (32px)
  for unit frames specifically.
- Immediately following the header (starting around byte +0x14/20), there's
  a run of mostly-increasing u16 values (e.g. for index 3547: 350, 232, 238,
  247, 257, 267, 277, 286, 300, 315, 331, ...) - this pattern is classic for
  a **per-scanline offset table** in an RLE-style sprite format: each entry
  points to where that row's compressed run data starts, letting the
  renderer skip fully-transparent rows/runs cheaply. This is a strong
  hypothesis, not yet confirmed.

**Next session should focus entirely on this.** Concrete next steps:
1. Take a small TILE entry and try to manually decode it byte-by-byte
   assuming: `header (fixed size) + row_offset_table (height x u16) +
   compressed_row_data`.
2. Try common RLE conventions for old sprite formats: (count, color) pairs,
   or (skip_count, run_count, pixel_bytes...) triples, checking whether
   decoded row lengths add up to the claimed width (32, or whatever the
   real per-frame width field turns out to be).
3. Cross-check decoded pixel counts/dimensions against the IMAG blob's
   claimed width/height for the same frame index, once both are decoded -
   they should agree, and that agreement is the actual validation signal
   (rather than the flawed width*height*4-vs-raw-size check used previously).
4. Once one frame decodes to a recognizable image, generalize into
   `sprite_extractor.py`.

---

## Existing analysis scripts (from earlier sessions)

Historical only - superseded by `cam_reader.py` for anything about container
structure. May still be useful for ideas about IMAG blob internals.

---

*Last updated: session that obtained ground-truth `` source and
cross-validated it against the real `maindata.cam`. Container format is now
solid. Frame pixel payload format (TILE section) is the active open
problem.*


## Suggestion

Even though this is proprietary, I think something to remember is that the game was published in 1999. I can't imagine there were too many ways to achieve their goal at that time. Maybe consider old practices