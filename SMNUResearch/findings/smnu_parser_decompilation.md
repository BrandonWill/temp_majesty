# SMNU Parser Decompilation Results

## Summary

Decompiled the SMNU panel parser from MajestyHD.exe using Ghidra MCP. The format is a
**tag-value int32 stream** — every value in the SMNU blob is a little-endian 32-bit integer.
The engine reads sequentially through an array of int32s, using tags (opcodes) to determine
how many subsequent values to consume.

---

## Crash Root Cause (0x0063A232)

**Function:** `FUN_0063a220` — a string setter method (`this->set_string(char* str)`)

**Disassembly at crash point:**
```asm
0063a232: CMP byte ptr [EBX], 0x0   ; <-- ACCESS_VIOLATION here
```

**EBX = 0x00000002** — a small integer being dereferenced as a string pointer.

**Meaning:** Something passed the integer value `2` where a `char*` pointer to a string
was expected. This happens when a widget property references the STRT string table but
the STRT section was **not loaded** (null handle), causing a raw string INDEX (2) to be
used directly as a pointer instead of being resolved to the actual string.

**Root cause:** Our custom SMNU panel either:
1. Had no matching STRT entry in the CAM file (STRT must share the same entry name), OR
2. Used tag 7 (string-from-STRT) but the STRT lookup returned the index value unchanged

---

## Architecture Overview

```
FUN_004b4870  "CYDialog loader" — top-level, creates dialog wrapper
  └─ FUN_0064de70  "SMNU section resolver" — finds SMNU data in CAM resource system
       ├─ vtable[0x38](parent, 0x554E4D53="SMNU", entry_name, 0)  — fetch section
       ├─ FUN_00648870(handle, 1)  — lock/ref the data
       └─ FUN_0064d330  "Panel factory" — allocates panel, connects STRT, parses
            ├─ new(0x120)  — allocate 288-byte panel object
            ├─ FUN_00669d00  — panel constructor (sets vtable, zeroes fields)
            ├─ FUN_00664a30  — attach to parent
            ├─ FUN_006d34d0  — LOAD STRT string table (by same entry name)
            │    └─ FUN_00679a80(entry_name, strt_name) — fetches STRT section
            ├─ vtable[0xb8] = FUN_006655e0  — PARSE PANEL HEADER properties
            ├─ vtable[0x08] = FUN_00665540  — PARSE CHILD WIDGETS
            │    └─ vtable[0x10] = FUN_00668390  — child widget factory/parser
            └─ FUN_00666930  — layout pass (compute positions)
```

---

## STRT Connection (Critical Finding)

**How SMNU finds its STRT:** By the **same entry name** in the CAM file.

In `FUN_006d34d0`:
```c
void FUN_006d34d0(int *this, int strt_name, int entry_name) {
    int handle = 0;
    if (strt_name != 0 && strt_name != -1) {
        handle = FUN_00679a80(entry_name, strt_name);
        // FUN_00679a80 calls: resource_mgr->find(entry_name, "STRT", strt_name, 0, 0x80000001, 0, 0)
    }
    this->strt_handle = handle;
}
```

The `entry_name` passed is the SAME value used to look up the SMNU section. So if your
SMNU entry is named "MX03", the engine automatically looks for an STRT entry also named "MX03".

**If STRT is not found:** `handle = 0` (null). Then when widgets use tag 7 (string lookup),
`FUN_00679ac0` is called with a null handle. It returns 0 or passes the raw index as a
"pointer" → crash.

---

## Panel Header Parser: FUN_006655e0 (vtable offset 0xb8)

The panel header is parsed from the int32 stream. Format:

```
1000                    ; Panel block marker (REQUIRED — outer loop checks for this)
  <properties...>      ; Tag-value pairs until -1
-1                     ; End of panel header properties
```

### Panel Header Tags (inside the 1000 block)

| Tag | Values Consumed | Meaning |
|-----|----------------|---------|
| 2   | 4 values: x, y, w, h | Geometry (position + size). If x==-1 && y==-1, sets auto-center flag (0x9) |
| 3   | 1 value | OR into flags field (param_1[6]) |
| 10 (0x0A) | 1 value | If < 4: call vtable[0xc0](); else call vtable[0xbc](value) |
| 11 (0x0B) | 1 value | Palette ID → FUN_00691440 (loads PALT section) |
| 12 (0x0C) | 1 value | Image set index → FUN_006877f0 (stores at param_1[0xc]) |
| 13 (0x0D) | 1 value | TILE index → FUN_00687f30 (stores at offset 0x14) |
| 18 (0x12) | 1 value | Font → FUN_00691580 |
| 39 (0x27) | 1 value | Set dimension(0, value) via vtable[0x88] |
| 40 (0x28) | 1 value | Set dimension(1, value) via vtable[0x88] |
| 43 (0x2B) | 1 value | FUN_00687600(value) |
| 46 (0x2E) | 3 values: a, b, c | vtable[0x84](b & 0xFF | a << 16, c) |
| 47 (0x2F) | 3 values: a, b, c | vtable[0x84](b & 0xFF | a << 16 | 0x100, c) |
| 48 (0x30) | 1 value | Store at param_1[7] |
| -1  | 0 | END of header block |

### Corrected Panel Header Format:
```
1000            ; Panel marker
2               ; Geometry tag
  x, y, w, h   ; 4 int32 values (position, size)
3               ; Flags tag  
  flags_value   ; OR'd into panel flags
12              ; Image set tag
  img_set_id    ; Image set identifier (4-char code as int32)
13              ; TILE index tag
  tile_idx      ; Background tile
18              ; Font tag
  font_id       ; Font identifier (4-char code as int32)
11              ; Palette tag
  palette_id    ; Palette identifier (4-char code as int32)
-1              ; END header
```

**Important:** Tags 12, 13, 18, 11 each take a SINGLE int32 value. The "string" image/font
names we see in the MX03 decode ("IX01", "fnt4", "MMS1") are actually their 4-byte ASCII
codes packed as int32 little-endian.

---

## Child Widget Parser: FUN_00668390 (vtable offset 0x10)

After the panel header, the stream continues with child widgets. The parser loops reading
int32 type codes until -1.

### Widget Type Codes

| Type | Object Size | Constructor | Description |
|------|-------------|-------------|-------------|
| 0    | 0x154 (340B) | FUN_006d3110 | Widget type 0 |
| 1    | 0x154 (340B) | FUN_006d2b80 | Widget type 1 |
| 2    | 0x154 (340B) | FUN_006d2570 | Widget type 2 |
| 3    | 0x154 (340B) | FUN_00675140 | Generic widget (stores type at offset 0x28) |
| 4    | 0x154 (340B) | FUN_00675140 | Generic widget (stores type at offset 0x28) |
| 5    | 0x160 (352B) | FUN_006d1a20 | Text/label widget (slightly larger) |
| 6    | 0x170 (368B) | FUN_006d0dd0 | Complex widget (largest common) |
| 7    | 0x154 (340B) | FUN_00675140 | Generic widget (stores type at offset 0x28) |
| 8    | 0x154 (340B) | FUN_00675140 | Generic widget (stores type at offset 0x28) |
| 9    | 0x154 (340B) | FUN_006cc5d0 | Widget type 9 |
| 10   | 0x154 (340B) | FUN_00675140 | Generic widget (stores type at offset 0x28) |
| 11   | 0x15c (348B) | FUN_006cb890 | Widget type 11 |
| 12   | 0x1d0 (464B) | FUN_00692a10 | Widget type 12 (largest) |
| 1000 | — | FUN_006dd330 | Nested panel block (SKIPPED in child parser) |
| -1   | — | — | END of widget list |

After creating each widget, it's added to the panel tree via `vtable[0x0c](widget, parent_depth)`.

### Widget Property Format (for types 3/4/7/8/10 — FUN_00673ca0)

After the type code, each widget has:
```
<type>          ; Widget type (0-12)
<sub_id>        ; Stored at widget offset 0x28 (action ID / sub-type)
<properties...> ; Tag-value pairs until -1
-1              ; END widget
```

---

## Widget Property Tags (FUN_00675b50)

This is the complete opcode table for widget properties:

| Tag | Values | Meaning |
|-----|--------|---------|
| 1   | 1 | vtable[0x9c](0xF, 0, value) — set widget property |
| 2   | 4 | Geometry: x, y, w, h (w/h are relative: +x, +y). If w==-1: auto-width flag. If h==-1: auto-height flag |
| 3   | 1 | vtable[0x1c0](value) — set style/mode |
| 4   | 1 | Store at widget[0xb] (offset 0x2C) |
| 5   | 1 | FUN_006dfa00(value, 0) — set state/image index 0 |
| 6   | 1 | Store at widget[5] (offset 0x14) — action type |
| 7   | 1 | **STRING LOOKUP** from STRT by index → FUN_00679ac0(strt, 0, index) then FUN_0046a6d0(result) |
| 10 (0x0A) | 1 | vtable[0x1f0](value) |
| 11 (0x0B) | 1 | Palette → FUN_00691440(value) |
| 12 (0x0C) | 1 | Image set → FUN_0046a730(value, 0) via vtable[0x9c](0x40, value, 0) |
| 13 (0x0D) | 1 | TILE index → FUN_00477960(value) |
| 14 (0x0E) | 1 | Store at widget[0x4b] |
| 15 (0x0F) | 1 | FUN_00671770(value) |
| 17 (0x11) | 1 | Store at widget[0x13] (offset 0x4C) |
| 18 (0x12) | 1 | Font → FUN_004a2ba0(value) |
| 19 (0x13) | 1 | FUN_00671870(value) |
| 20 (0x14) | 1 | vtable[0x1d0](value) |
| 21 (0x15) | 1 | FUN_006912b0(3, 0, value) — color type 3, slot 0 |
| 22 (0x16) | 1 | FUN_006912b0(5, 0, value) — color type 5, slot 0 |
| 27 (0x1B) | 1 | Store at widget[0x15] (offset 0x54) |
| 28 (0x1C) | 1 | Store at widget[0x14] (offset 0x50) |
| 29 (0x1D) | 1 | Store at widget[0x16] (offset 0x58) |
| 30 (0x1E) | 1 | Store at widget[0x17] (offset 0x5C) |
| 31 (0x1F) | 1 | Store at widget[0x1a] (offset 0x68) |
| 32 (0x20) | 1 | Store at widget[0x1b] (offset 0x6C) |
| 33 (0x21) | 1 | **STRING LOOKUP** → FUN_00679ac0(strt, 0, index) then FUN_0046a6f0 (tooltip text) |
| 34 (0x22) | 1+N | Array: [count] then count×value → FUN_006912b0(0xE, i, val) — color array type 0xE |
| 35 (0x23) | 1+N | Array: [count] then count×value → FUN_006912b0(0xF, i, val) — color array type 0xF |
| 36 (0x24) | 1+N | Array: [count] then count×value → FUN_006912b0(3, i, val) — color array type 3 |
| 37 (0x25) | 1+N | Array: [count] then count×value → FUN_006912b0(5, i, val) — color array type 5 |
| 38 (0x26) | 1 | Store at widget[0x1f] (offset 0x7C) |
| 39 (0x27) | 1 | vtable[0x180](0, value, 0) — dimension X |
| 40 (0x28) | 1 | vtable[0x180](1, value, 0) — dimension Y |
| 42 (0x2A) | 4 | Rect: x, y, x+w, y+h → vtable[0x1b8](&rect) |
| 43 (0x2B) | 1 | vtable[0x1cc](value) + FUN_00687600(widget[0x20]) |
| 44 (0x2C) | 1 | vtable[0x1dc](value) |
| 45 (0x2D) | 1 | vtable[0x204](value) |
| 46 (0x2E) | 2 | Two values: a, b → vtable[0x180](0, b, a) — X dimension with param |
| 47 (0x2F) | 2 | Two values: a, b → vtable[0x180](1, b, a) — Y dimension with param |
| 48 (0x30) | 1 | vtable[0x54](value) |
| 49 (0x31) | 1+N | Array: FUN_006912b0(4, i, val) — color array type 4 |
| 50 (0x32) | 1+N | Array: FUN_006912b0(6, i, val) — color array type 6 |
| 51 (0x33) | 1+N | Array: FUN_006912b0(8, i, val) — color array type 8 |
| 52 (0x34) | 1+N | Array: FUN_006912b0(9, i, val) — color array type 9 |
| 53 (0x35) | 1 | FUN_0046a6d0(value) — same as vtable[0x9c](0x5C, 0, value) |
| 0x100-0x10C | 1 | FUN_006dfa00(value, tag - 0x100) — indexed image state |

**Array tags (34-37, 49-52):** Format is `[tag] [count] [val0] [val1] ... [valN-1]`.
These are color arrays with `count` entries.

---

## Data Format Key Insight: String References

There are TWO ways strings appear in widget properties:

1. **Tag 7** — STRT string by index. The value is an INDEX into the panel's STRT table.
   Resolved at parse time via `FUN_00679ac0(strt_handle, 0, index)`.
   
2. **Tag 33 (0x21)** — STRT string by index (for tooltips). Same mechanism.

3. **Tags 12, 11, 18** — These take 4-char ASCII identifiers packed as int32 (e.g., "INTG" = 0x47544E49).
   These are NOT string table lookups — they're resource identifiers.

**The crash occurred because tag 7 was used with value 2, but STRT was null, so the
engine tried to dereference 0x00000002 as a char pointer.**

---

## Opcode Size Reference (from FUN_006dd1e0 — the skip function)

This function is used to skip over opcodes without processing them. It reveals the
byte-size of every opcode:

| Category | Opcodes | Values consumed (after tag) |
|----------|---------|---------------------------|
| 1 value  | 1, 3-15, 17-22, 27-33, 35, 38-41, 43-45, 48, 0x100+ | 1 |
| 4 values | 2, 42 (0x2A) | 4 |
| 2 values (if parent==1000) | 46, 47 | 3 in panel header, 2 in widget |
| Variable | 34-37, 49-52 (0x22-0x25, 0x31-0x34) | 1 + [count] |
| Sub-block | 23 (0x17) | Read until tag 24 (0x18) |

---

## Complete SMNU Binary Stream Format

```
; === STREAM START ===
; Outer loop: reads widget blocks until -1

1000                    ; PANEL HEADER BLOCK
  ; Panel property tags (see table above)
  2, x, y, w, h        ; Geometry
  3, flags              ; Panel flags
  12, image_set_id      ; Background image set (4-char as i32)
  13, tile_idx          ; Background TILE
  18, font_id           ; Default font (4-char as i32)
  11, palette_id        ; Color palette (4-char as i32)
  ...                   ; Other optional tags
  -1                    ; END panel header

; === CHILD WIDGETS (parsed by FUN_00668390) ===
; Each widget: [type] [sub_id] [properties...] [-1]

<widget_type>           ; 0-12 (see widget type table)
  <sub_id>              ; Action/sub-type identifier (stored at widget+0x28)
  ; Widget property tags (see table above)
  2, x, y, w, h        ; Position & size
  7, strt_index         ; Display text (from STRT)
  33, strt_index        ; Tooltip text (from STRT)
  12, image_set_id      ; Widget image set
  13, tile_idx          ; Widget TILE
  18, font_id           ; Widget font
  6, action_type        ; Action identifier
  ...                   ; Other properties
  -1                    ; END widget

<widget_type>           ; Next widget...
  ...
  -1

-1                      ; END of entire widget list (stream terminator)
```

---

## Panel Object Layout (0x120 = 288 bytes)

From the constructor `FUN_00669d00`:

| Offset | Field | Set By |
|--------|-------|--------|
| 0x00 | vtable pointer | constructor |
| 0x04 | param_2 (x? / parent ref) | constructor |
| 0x08 | param_3 (y?) | constructor |
| 0x0C | param_4 (w?) | constructor |
| 0x10 | param_5 (h?) | constructor |
| 0x14 | param_6 (style) | constructor |
| 0x18 | param_8 (flags) | constructor |
| 0x1C | field_1c | 0 (zeroed) |
| 0x20 | child_count / depth | 0 |
| 0x24-0x28 | reserved | 0 |
| 0x2C | strt_handle? | tag processing |
| 0x30 | image_set | tag 12 (FUN_006877f0) |
| 0x38-0x3C | reserved | 0 |
| 0x40 | layout_mode | 0 |
| 0x44 | child_widget_ptr | vtable[0x11] alloc |

---

## Validation Against MX03 Decode

Cross-referencing with `MX03_full_decode.md`:

| Our prior assumption | Decompilation confirms |
|---------------------|----------------------|
| "12, IMG_NAME" is tag 12 + image ID | ✅ Tag 12 takes 1 value (4-char packed int32) |
| "13, tile" is tag 13 + TILE index | ✅ Tag 13 takes 1 value |
| "18, font" is tag 18 + font ID | ✅ Tag 18 takes 1 value |
| "11, pal" is tag 11 + palette ID | ✅ Tag 11 takes 1 value |
| -1 terminates sections | ✅ -1 ends header, ends widgets, ends stream |
| Tag 2 = geometry (x,y,w,h) | ✅ 4 values consumed |
| Tag 3 = flags | ✅ 1 value, OR'd into panel flags |
| "1000" starts a panel | ✅ Outer loop checks for 1000 |
| Tag 7 = string from STRT | ✅ Resolved via FUN_00679ac0 |
| Widget types start with a type code | ✅ Types 0-12 handled |
| Widgets have a sub-ID after type | ✅ First value after type stored at offset 0x28 |

**Key correction from decompilation:** The prior decode labeled some values wrong:
- What was called "separator 0" before each widget is actually the **widget type code** (type 0 = first widget type)
- The "2" after the type code is the **geometry tag**, not a "widget type"

---

## Why Our Custom Panel Crashed

The crash at `FUN_0063a220` with EBX=2 means:

1. Our custom SMNU CAM had an SMNU entry but **no matching STRT entry** with the same name
2. The engine loaded the SMNU, found `tag 7` (or `tag 33`) with a string index value
3. Called `FUN_00679ac0(null_strt_handle, 0, string_index)`
4. Since handle was null/invalid, the function returned the raw index (2) as if it were a pointer
5. The string setter tried to read bytes from address 0x00000002 → ACCESS_VIOLATION

**Fix:** Always include a STRT section with the same entry name as the SMNU section. The STRT
must contain all strings referenced by tag 7 and tag 33 indices in the widget properties.

---

## Next Steps

1. **Validate with original data:** Extract MX03 SMNU+STRT from `DataMX/mx_textdata.cam`,
   repack as-is into a Quest_textdata.cam, and confirm no crash (proves override works).

2. **Build SMNU writer:** Now that we know the exact format, build a Python tool that can:
   - Parse existing SMNU blobs into structured widget trees
   - Modify individual widget properties (change string indices, positions, etc.)
   - Serialize modified trees back to valid SMNU binary

3. **STRT format:** Need to also decompile the STRT reader (vtable[0xc] on the STRT object)
   to confirm the string table format (likely: array of null-terminated strings, indexed by
   ordinal position).

4. **Test minimal panel:** Create a panel with:
   - Valid header (1000 block with geometry + image + palette)
   - One simple widget (type 3 with geometry only, no string refs)
   - Matching empty STRT
   - Confirm no crash

5. **Document remaining widget constructors:** Decompile FUN_006d3110 (type 0), FUN_006d2b80
   (type 1), FUN_006d2570 (type 2) to understand what makes them different from the generic
   type 3/4/7/8/10 widgets.
