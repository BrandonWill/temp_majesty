# SMNU Navigation Button Widget — Fully Decoded

## Complete Widget Structure (116 bytes)

Each navigation button is a **116-byte widget block**. Here's the full structure
as decoded from AP21 (Hero Statistics panel) which has 3 identical nav buttons:

```
OFFSET  SIZE  VALUE           FIELD NAME / PURPOSE
──────────────────────────────────────────────────────────────────
+0      u32   0              Separator (0 between widgets, -1 at end of panel)
+4      u32   2              Widget type (2 = clickable button)
+8      u32   X_pos          X position in pixels (65, 92, 120 etc.)
+12     u32   Y_pos          Y position in pixels (225)
+16     u32   Width          Button width in pixels (20)
+20     u32   Height         Button height in pixels (20)
+24     u32   TOOLTIP_STR    String index in STRT for tooltip text
+28     u32   LABEL_STR      String index in STRT for button label
+32     u32   10             Constant (font/alignment?)
+36     u32   2              Constant (render mode?)
+40     u32   12             Image set reference type
+44     4B    "INDe"         Image set name (ASCII LE: 0x65444E49)
+48     u32   13             TILE reference type
+52     u32   TILE_IDX       TILE index for button icon (1014, 1015, 1016)
+56     u32   3              Constant
+60     u32   2              Constant
+64     u32   3              Constant
+68     u32   1024 (0x400)   ACTION BLOCK MARKER
+72     u32   3              Constant (param count?)
+76     u32   8              Constant (format version?)
+80     u32   5              ACTION TYPE = NAVIGATE TO PANEL
+84     u32   TARGET         Primary target panel index
+88     u32   6              Secondary action marker
+92     u32   CODE           Action sub-code (4004/4002/4006/5000)
+96     u32   258 (0x102)    Alternate target block 1 marker
+100    u32   ALT_1          Alternate panel index 1 (contextual)
+104    u32   266 (0x10A)    Alternate target block 2 marker
+108    u32   ALT_2          Alternate panel index 2 (contextual)
+112    u32   0xFFFFFFFF     Widget terminator
```

**Total: 29 u32 fields = 116 bytes per nav button widget.**

## All 10 Instances Found

All found in hero sub-panels (AP21, AP22, AP78) — these are the "STATS", "SPELLS", 
"ITEMS" tab buttons that appear at the bottom of hero detail panels.

| Panel | Offset | Target | Code | Alt1 | Alt2 | Icon TILE |
|-------|--------|--------|------|------|------|-----------|
| AP03  | 340    | 66 (AP75) | 5000 | - | - | - |
| AP21  | 4744   | 69 (AP78 Spells) | 4004 | 90 (APa0) | 67 (AP76) | 1015 |
| AP21  | 4860   | 73 (AP83 Quest) | 4002 | 73 | 73 | 1014 |
| AP21  | 4976   | 84 (AP94 Items) | 4006 | 83 (AP93) | 84 | 1016 |
| AP22  | 2484   | 69 (AP78 Spells) | 4004 | 90 (APa0) | 67 (AP76) | 1015 |
| AP22  | 2600   | 73 (AP83 Quest) | 4002 | 73 | 73 | 1014 |
| AP22  | 2716   | 84 (AP94 Items) | 4006 | 83 (AP93) | 84 | 1016 |
| AP78  | 1304   | 84 (AP94 Items) | 4006 | 83 (AP93) | 84 | 1016 |
| AP78  | 1420   | 69 (AP78 Spells) | 4004 | 90 (APa0) | 67 (AP76) | 1015 |
| AP78  | 1536   | 73 (AP83 Quest) | 4002 | 73 | 73 | 1014 |

## Field Analysis

### Position (offsets +8 to +20)
- X positions: 65, 92, 120 (buttons are 27px apart horizontally)
- Y position: 225 (all same row)
- Size: 20×20 px (small square icon buttons)

### String References (offsets +24, +28)
- Tooltip at +24: index 33 (same for all — probably "Navigation" generic tooltip)
- Label at +28: 54, 55, 56 (sequential — maps to STRT strings for each tab name)

### Image Set (offsets +40 to +52)
- `12, "INDe", 13, TILE_IDX` is the icon definition pattern
- "INDe" = the "hero" image set in interfacedata.cam (IMAG entry INDe)
- TILE_IDX 1014/1015/1016 = specific icon frames within that set

### Action Codes (offset +92)
| Code | Associated Panel Type |
|------|----------------------|
| 4004 | Spells panel |
| 4002 | Quest/status panel |
| 4006 | Items/inventory panel |
| 5000 | (seen in AP03 only — different context) |

Theory: these codes tell the engine what TYPE of sub-panel to render,
which may affect how data is populated (spell list vs item list vs quest log).

### Alternate Targets (offsets +100, +108)
The alternates appear to be **building-context-specific** variants:
- When viewing a hero at a Fairgrounds → use panel 90 (APa0)
- When viewing a hero at a Ballista Tower → use panel 67 (AP76)
- Otherwise → use primary target

For a simple "Page 2" button, setting ALT_1 = ALT_2 = TARGET (same value)
should be safe — no conditional switching needed.

## How to Create a "More Items →" Button

Clone the 116-byte block and modify:
1. **+8 (X_pos):** Position appropriately in your panel layout
2. **+12 (Y_pos):** Position appropriately
3. **+28 (LABEL_STR):** Point to a STRT string "More Items →"
4. **+52 (TILE_IDX):** Choose an appropriate icon sprite
5. **+84 (TARGET):** Set to your Page 2 panel's index
6. **+92 (CODE):** Use 4004 or 5000 (generic navigation — needs testing)
7. **+100 (ALT_1):** Same as TARGET (no conditional)
8. **+108 (ALT_2):** Same as TARGET (no conditional)

## Risks and Unknowns

1. **Action code significance:** We don't know if codes 4004/4002/4006 trigger
   different rendering modes. Using the wrong code might cause the target panel
   to render incorrectly or crash. Testing with 5000 (from AP03) or matching
   the code of whatever panel type you're navigating TO would be safest.

2. **Image set "INDe":** This references the hero dialog image set. A building
   panel might need a different image set (e.g., "INBg" for building graphics).
   The Magic Bazaar MX03 SMNU should be checked for its own image set refs.

3. **Panel index calculation:** When adding new panels via expansion CAM overlay,
   the index = base_panel_count + expansion_index. Need to verify the engine
   uses a unified index across both base and expansion textdata.cam files.

4. **The 0/(-1) separator:** Value 0 between widgets, -1 at end of widget list.
   A second -1 at the very end of the panel marks EOF. Must preserve this.
