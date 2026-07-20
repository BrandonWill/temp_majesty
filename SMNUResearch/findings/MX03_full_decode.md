# MX03 (Magic Bazaar Research Panel) — Complete SMNU Decode

Total size: 3420 bytes. Ends with double 0xFFFFFFFF (panel EOF).

## Panel Structure Overview

```
[0-75]      Panel Header
[76-151]    Background frame widget
[152-287]   Title/header text area
[288-519]   Research item 1: "Tonic of Speed" (button + colors)
[520-751]   Research item 2: "Fire Balm"
[752-983]   Research item 3: "Dirgo Strength"
[984-1067]  "Research Potions" label (text widget, no button)
[1068-1299] Research item 4: "Shapeshift"
[1300-1531] Research item 5: "Regeneration"
[1532-1763] Research item 6: "Invisibility"
[1764-1855] Track button (nav/utility)
[1856-1947] Zoom button (nav/utility)
[1948-2047] "Return to Main" button (nav action=5, target=9)
[2048-2123] Progress bar 1 (cost display widget)
[2124-2199] Progress bar 2
[2200-2275] Progress bar 3
[2276-2351] Progress bar 4
[2352-2427] Progress bar 5
[2428-2503] Progress bar 6
[2504-2655] Cost label 1 ("2000" text)
[2656-2807] Cost label 2
[2808-2959] Cost label 3
[2960-3111] Cost label 4
[3112-3263] Cost label 5
[3264-3415] Cost label 6
[3416-3419] Panel EOF (double -1)
```

## Widget Types Identified

### Type 1: Panel Header (bytes 0-75)
```
[0]   1000        Panel format version
[4]   2           Panel type (2 = building sub-panel?)
[8]   0           X anchor
[12]  182         Y anchor (top of panel area)
[16]  202         Panel width
[20]  245         Panel height
[24]  10          (constant)
[28]  2           (constant)
[32]  10          (constant)
[36]  0x00040000  Flags (262144)
[40]  12          Image ref type
[44]  "IX01"      Background image set (expansion interface)
[48]  13          TILE ref type
[52]  1001        TILE index for panel background
[56]  18          Font ref type
[60]  "fnt4"      Default font
[64]  11          Palette ref type
[68]  "MMS1"      Color palette
[72]  -1          Header terminator
```

### Type 2: Background Frame (bytes 76-151)
```
[76]  0           Separator
[80]  2           Widget type
[84]  0           X
[88]  0           Y
[92]  202         Width (= panel width)
[96]  245         Height (= panel height)
[100] 10          (constant)
[104] 2           (constant)
[108] 12          Image ref
[112] "INBg"      Building background frame image set
[116] 13          TILE ref
[120] 1024        TILE idx for frame background (NOTE: same value as ACTION_BLOCK!)
[124] 3           (constant)
[128] 128         (flags?)
[132] 6           Action type = 6 (no-click? display-only?)
[136] 1           (param)
[140] 38          (param)
[144] 0           (param)
[148] -1          Terminator
```

### Type 3: Research Item Button (bytes 288-519, repeating)

Each research item is **232 bytes**. Structure:

```
+0    0           Separator
+4    2           Widget type (clickable)
+8    26          X position
+12   Y_POS       Y position (61, 87, 113, ... incrementing by 26px per item)
+16   172         Width
+20   23          Height
+24   42          (constant — click area flag?)
+28   1           (constant)
+32   2           (sub-type: research item button)
+36   128         (flags)
+40   20          (param)
+44   7           String group indicator
+48   STR_NAME    String index for item NAME (1, 3, 5, 8, 10, 12)
+52   33          Tooltip string base
+56   STR_DESC    String index for item DESCRIPTION (2, 4, 6, 9, 11, 13)
+60   10          (constant)
+64   2           (constant)
+68   12          Image ref
+72   "INBb"      Building button image set
+76   13          TILE ref
+80   TILE_IDX    TILE index for item icon (1021, 1022, 1023, 1027, 1024, 1025)
+84   20          (constant)
+88   1           (constant)
+92   20          (constant)
+96   8           (constant)
+100  20          (constant)
+104  4           (constant)
+108  3           (constant)
+112  2           (constant)
+116  3           (constant)
+120  1024        ACTION_BLOCK marker
+124  5           Action type = 5 (research/purchase? — NOT navigation!)
+128  ACTION_ID   Action target (84, 70, 68, 83, 82, 73 — building-specific IDs)
+132  6           Secondary action marker
+136  CODE        Action code (5061, 5062, 5063, 5066, 5064, 5065)
+140  18          Font ref
+144  "fnt4"      Font
+148  36          (color block marker)
+152  3           Color set count
+156  0x8000003F  Color: normal state (ARGB)
+160  0x40000000  Color: hover?
+164  0x40000000  Color: pressed?
+168  37          Color category (button border?)
+172  3           Count
+176  0x80FFFFFF  Color: white
+180  0x807F7F7F  Color: gray
+184  0x80FFFFFF  Color: white
+188  34          Color category (background?)
+192  3           Count
+196  0x80000000  Color: black
+200  0x803F3F3F  Color: dark gray
+204  0x8000FF00  Color: GREEN (researched indicator!)
+208  35          Color category (text?)
+212  3           Count
+216  0x80FFFFFF  Color: white
+220  0x807F7F7F  Color: gray
+224  0x80FFFFFF  Color: white
+228  -1          Terminator
```

### Type 4: "Return to Main" Navigation Button (bytes 1948-2047)
```
[1948] 0           Separator
[1952] 2           Widget type
[1956] 3           X position
[1960] 223         Y position (bottom of panel)
[1964] 25          Width
[1968] 20          Height
[1972] 33          Tooltip string index (33 = generic)
[1976] 16          Label string index (16 = "Return to this building's Main Window.")
[1980] 10          (constant)
[1984] 2           (constant)
[1988] 12          Image ref
[1992] "INTG"      Navigation button image set
[1996] 13          TILE ref
[2000] 1005        TILE index (back arrow icon)
[2004] 3           (constant)
[2008] 2           (constant)
[2012] 3           (constant)
[2016] 1024        ACTION_BLOCK
[2020] 5           Action type = 5 (NAVIGATE)
[2024] 9           *** TARGET PANEL INDEX = 9 (goes to building main) ***
[2028] 6           Secondary
[2032] 8013        Action code (8013 = return to building main?)
[2036] 18          Font ref
[2040] "fn11"      Font
[2044] -1          Terminator
```

**THIS IS THE KEY WIDGET.** It's a simple nav button: action type 5, target = 9.
Panel index 9 would be MX02 (Magic Bazaar main panel) in the expansion's context.
To create a "More Items →" button, we clone this widget and change:
- Target panel index (offset 2024)
- String index (offset 1976) 
- Icon TILE (offset 2000)
- Position X/Y (offsets 1956/1960)

### Type 5: Progress Bar / Cost Widget (bytes 2048-2123, repeating)

Small widget (76 bytes) for displaying research cost/progress:
```
+0    0           Separator
+4    2           Widget type
+8    3           X
+12   60/112/...  Y position (aligned with research items)
+16   25          Width
+20   25          Height
+24   10          (constant)
+28   2           (constant)
+32   12          Image ref
+36   "IX02"      Progress/cost image set
+40   13          TILE ref
+44   TILE_IDX    TILE for cost icon (1006, 1002, 1005, 1004, 1003, 1001)
+48   3           (constant)
+52   128         (flags)
+56   6           Action type = 6 (display only / cost indicator)
+60   CODE        5500-5505 (sequential per item — links to research slot)
+64   38          (constant)
+68   0           (constant)
+72   -1          Terminator
```

### Type 6: Cost Label Text (bytes 2504-2655, repeating)

Text display widget (152 bytes) showing "2000" gold cost:
```
+0    5           Widget start marker (different from type 2/3!)
+4    2           Widget type
+8    154         X position (all same)
+12   Y_POS       Y position (64, 90, 116, 142, 168, 194)
+16   40          Width
+20   17          Height
+24   7           (constant)
+28   STR_IDX     String index (17-22 = "2000" x6)
+32   10          (constant)
+36   2           (constant)
+40   10          (constant)
+44   0x00040000  Flags
+48   10          (constant)
+52   0x00080000  Flags
+56   12          Image ref
+60   "INTI"      Image set
+64   13          TILE ref
+68   1016        TILE index
+72-148 ...       Font, color, size block (same pattern as research items)
+148  -1          Terminator
```

## Key Discoveries

1. **Action type 5 means DIFFERENT things in different contexts:**
   - In nav buttons (Type 4): target is a PANEL INDEX → navigates to that panel
   - In research items (Type 3): target is a RESEARCH ACTION ID → triggers research

   The distinction is likely the action CODE that follows:
   - Codes 8000-8013 = navigation actions
   - Codes 5061-5066 = research purchase actions
   - Codes 5500-5505 = research progress/display

2. **The "Return to Main" button (Type 4) is only 100 bytes** — much simpler than
   the full nav buttons in the hero panel (116 bytes) because it lacks the
   258/266 alternate targets block. This is the simplest form of navigation.

3. **Widget start markers:**
   - `0` = standard separator between widgets
   - `5` = text/label widget start (used for cost labels)
   - `-1 (0xFFFFFFFF)` = end of previous widget's action block

4. **Research items use action code 5061-5066** — sequential per slot. A new page
   would need new codes (5067+) or reuse existing slots with modified GPL.

5. **The panel background uses TILE 1024** — same numeric value as the ACTION_BLOCK
   marker. The engine distinguishes them by context (after image ref = TILE index,
   standalone = action marker).

## For Multi-Page Implementation

The simplest approach: **clone the "Return to Main" button (100 bytes at offset 1948)**
and repurpose it as a "Page 2 →" button:

1. Change offset 2024 from `9` to your Page 2 panel index
2. Change offset 1976 from `16` to a new string "More Items →"
3. Change offset 2000 from `1005` to a forward-arrow icon TILE
4. Change position to fit in the panel layout (maybe replace one research slot)

On Page 2, have a reciprocal button pointing back to Page 1.
