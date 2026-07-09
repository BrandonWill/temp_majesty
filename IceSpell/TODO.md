# IceSpell Mod — TODO / Troubleshooting

## Current Status

The mod loads, the IceElemental spawns, the GPL freeze logic works correctly (targeting, guards, duration calc all confirmed in logs). **The game crashes when `$createeffector` tries to render the overlay sprite** because the IMAG records in `Quest_maindata.cam` are malformed.

---

## Resolved Issues

### 1. Mod not appearing in game
**Cause:** The hand-crafted GUID `{F1CE0001-ICE1-4A2B-B3C4-FREEZESPELL01}` was not accepted by the game. Using RGSEditor to create a `Mod.mmxml` generated a valid GUID `{2A7F2E17-5B54-40B4-88C3-9E15927B9865}`. That GUID was then replaced with another RGSEditor-generated one `{FD53F69F-B6E7-4868-8B6E-8FA5754F7233}` which is what's currently in `IceSpell.mmxml`.

**Fix applied:** Use RGSEditor-generated GUID. Future TODO: investigate if a standard UUID v4 works or if the game validates GUIDs specially.

### 2. mmxml format wrong (slashes, GPL structure)
**Cause:** Forward slashes and bare `<GPL>path</GPL>` text node instead of `<Target>`/`<Source>` sub-elements.

**Fix applied:** Backslashes, structured GPL section with `<Target>` and `<Source>`.

### 3. IceElemental "couldn't find initialization data" + BirthScript error
**Cause:** Missing required attributes in the character XML definition.

**Fix applied:** (By other agent) Added required fields. IceElemental now spawns successfully as `IceElemental#32`.

### 4. CAM file not loaded
**Cause:** `<CAM>Data\Quest_maindata.cam</CAM>` was missing from the mmxml.

**Fix applied:** Added CAM line to `IceSpell.mmxml`. File is now loaded by the engine (`Library added: ...\Quest_maindata.cam` confirmed in logs).

### 5. Deployment via junction link
**Fix applied:** Created a directory junction:
```
C:\Users\Brandon\Documents\My Games\MajestyHD\Mods\IceSpell → C:\Users\Brandon\Documents\Kiro\Majesty\temp_majesty\IceSpell
```
No more manual copying needed. Edits in the repo are immediately live.

---

## Current Crash: IMAG record format is wrong in Quest_maindata.cam

### Timeline of the crash investigation
1. First test: mmxml did NOT include `<CAM>Data\Quest_maindata.cam</CAM>`. The mod loaded, IceElemental spawned, GPL ran correctly, but the game crashed at `$createeffector(target, "freeze_effector", 0)` because the overlay's `ImageIDBase=IR01` had no IMAG data in any loaded CAM file.
2. Fix attempt: Added `<CAM>Data\Quest_maindata.cam</CAM>` to `IceSpell.mmxml` so the engine would have the IMAG/TILE/SPLT data for IR01/IR02/IR03.
3. Result: Now the game crashes EARLIER — during zone load itself, before any GPL executes. The engine loads `Quest_maindata.cam` successfully (`Library added:` line in err.log) but crashes when parsing/validating its IMAG records.

### Symptoms
- Game crashes when entering a zone with IceElemental
- err.log shows all files loaded successfully, then just stops (hard crash, no error message)
- gpl.log shows nothing (crash happens before GPL runs in this load)

### Root Cause Analysis

Compared our `IR01` IMAG record (216 bytes) against the real `MRB1` (petrify_effector, 412 bytes) from the base game's `maindata.cam`:

**Key differences at the binary level:**

| Offset | Field (guessed) | Real MRB1 | Our IR01 | Notes |
|--------|-----------------|-----------|----------|-------|
| 44 | flags/palette? | 256 (0x100) | 0 | Missing value — likely critical |
| 96 | frame table offset | 68 | 88 | Different internal offset to frame data |
| 104 | packed field | 0x00240001 | 0 | Real has metadata we don't emit |
| 116 | unknown | 0x00010000 | 0 | Additional metadata missing |
| 128+ | TILE indices | 2473-2481 | — | Real references actual TILE indices in maindata.cam |
| 180+ | TILE indices | — | 1-5 | Ours uses small sequential indices (for our 11 TILE entries) |
| Total size | | 412 bytes | 216 bytes | Nearly 2x size difference |

**Conclusion:** The IMAG record builder in the CAM generation tool is producing records that don't match the engine's expected binary layout. The real IMAG has additional metadata fields between the header and the frame table that our tool doesn't emit.

### Recommended Fix (two options)

**Option A — Quick workaround (test logic without custom sprites):**
Change `IceSpell_Overlays.xml` to use `ImageIDBase value="MRB1"` (the existing petrify effector sprite from the base game). The freeze overlay will display as grey stone instead of ice, but the entire freeze/unfreeze mechanic will work for testing.

**Option B — Fix the CAM IMAG format (proper fix):**
1. Fully reverse-engineer the IMAG record format by comparing multiple real IMAG entries
2. The real MRB1 has 9 frames (TILE indices 2473-2481) in a 412-byte record
3. Key unknowns to crack:
   - Offset 44: what does 256 mean? (palette count? sprite width in pixels?)
   - Offset 104: packed field 0x00240001 — could be (36, 1) or (frame_count_related, direction_count)
   - Offset 116: 0x00010000 — another packed field
   - What's the stride between frame index entries? (appears to be 8 bytes per frame in real data)
   - Our tool uses 8-byte stride too but the header section before the frame table is wrong
4. Fix the CAM builder (`cam_writer.py` or whatever generated `Quest_maindata.cam`) to emit correct IMAG headers
5. Rebuild `Quest_maindata.cam` and re-test

---

## File State

```
IceSpell/
├── IceSpell.mmxml          ✓ Working (game loads it, GUID valid)
├── Mod.mmxml               ✗ Remove from deployed folder (duplicate GUID conflict)
├── deploy.bat              ✓ Updated (copies CAM too) — BUT junction makes this unnecessary now
├── Data/
│   ├── IceSpell.bcd        ✓ Compiles and loads, GPL logic confirmed working
│   ├── IceSpell_Actions.xml    ✓ Loaded
│   ├── IceSpell_Characters.xml ✓ Loaded, IceElemental spawns
│   ├── IceSpell_Overlays.xml   ✓ Loaded (references IR01/IR02/IR03)
│   └── Quest_maindata.cam      ✗ IMAG records malformed — causes crash
├── GPL/
│   ├── IceSpell.gpl        ✓ Debug version with extensive $DebugOut
│   ├── IceSpell_Globals.dat    ✓ Lair spawn override works
│   └── IceSpell.gplproj    ✓ Compiles successfully
├── sprites/                 ✓ TILE frames generated (round-trip verified)
└── utility/                 — Generator scripts
```

---

## GPL Logic Status (confirmed working from logs)

```
✓ IceElemental spawns from Ice Cave
✓ Ice_Freeze_Begin fires correctly
✓ Building guard clause works (rejects Warriors_Guild)
✓ IsDead check works
✓ HasEffectPetrify check works
✓ Duration calculation (19000) works
✓ MagicResistance random check works
✗ $createeffector("freeze_effector") — crashes due to missing/bad IMAG sprite data
```

---

## Next Steps

1. **Either** apply Option A (swap ImageIDBase to MRB1 for testing) **or** Option B (fix CAM IMAG format)
2. Once overlay doesn't crash, verify the full freeze cycle: freeze → damage ticks → timer expires → thaw
3. Fix targeting: IceElemental spams freeze on buildings before finding heroes (low priority, spell correctly rejects them via guard clause, just wastes AI cycles)
4. Remove debug `$DebugOut` lines from GPL once everything is confirmed working
5. Investigate GUID generation for automation (low priority — RGSEditor works for now)
