# IceSpell Mod — TODO

## Current Status

Mod loads, IceElemental spawns, GPL logic confirmed working in logs. 
Previous crash was caused by malformed IMAG records in Quest_maindata.cam.
IMAG format has been fixed by cloning the real MRB1 header verbatim. **Needs re-test.**

---

## What Was Fixed This Round

**IMAG record format:** The original builder guessed at the binary layout wrong:
- Direction slot offset was 0x58 (should be 0x44 — overlaps with slot array)
- Frame entries were `(u32 zero, u32 tile_idx)` — should be `(u32 tile_idx, u32 zero)`
- Direction block header was all zeros — should have metadata at offsets +4 and +16

**Fix approach:** Clone MRB1's first 128 bytes exactly as a template, then append only the frame tile index pairs. The IR01 record now byte-matches MRB1's structure with just different tile indices.

**Overlay XML:** Restored to use custom `ImageIDBase` values (IR01/IR02/IR03) pointing to our Quest_maindata.cam sprites.

---

## Next Test

1. Pull latest, recompile (`MakeGPL.bat`), redeploy
2. Game should load without crash
3. Ice Dragon casts → `$createeffector("freeze_effector", 0)` → should display ice overlay sprite
4. Check if freeze_icon timer fires `Ice_Freeze_End` after duration expires

## Open Items

- **Targeting behavior:** IceElemental tries to cast on buildings before heroes (guard clause rejects correctly but wastes AI cycles). Low priority — cosmetic issue.
- **Damage over time:** Not implemented yet in the debug GPL version. Once freeze/unfreeze cycle is confirmed working, add `$NewThread` periodic damage back.
- **Custom attribute:** Currently reusing `#ATTRIB_HasEffectPetrify` for simplicity. Once basic freeze works, switch to `$AddAttribute("is_frozen_ice", ...)` for proper stacking.
- **Ice sprite visuals:** Generated procedurally — may need artistic iteration once visible in-game.
- **Remove debug $DebugOut:** Strip verbose logging once everything is confirmed stable.

## File State

```
IceSpell/
├── IceSpell.mmxml              ✓ Working (valid GUID, correct structure)
├── Data/
│   ├── IceSpell.bcd            ✓ Compiles, GPL logic confirmed
│   ├── IceSpell_Actions.xml    ✓ Loaded
│   ├── IceSpell_Characters.xml ✓ IceElemental spawns
│   ├── IceSpell_Overlays.xml   ✓ References IR01/IR02/IR03
│   └── Quest_maindata.cam      ? FIXED — needs re-test (IMAG cloned from MRB1)
├── GPL/
│   ├── IceSpell.gpl            ✓ Debug version with $DebugOut
│   ├── IceSpell_Globals.dat    ✓ IceElemental data + Ice_Cave override
│   └── IceSpell.gplproj        ✓ Compiles
└── sprites/                    ✓ TILE frames (round-trip verified)
```
