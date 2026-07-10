# Ice Spell Visual Verification — Results

## Status: Spell mechanics WORKING, visual overlay NOT rendering

### What works (confirmed via logs + in-game observation)

- IceElemental spawns from Ice Cave ✓
- IceElemental casts freeze spell on nearby units (heroes, skeletons, anything in range) ✓
- `$createeffector("freeze_effector")` succeeds without crash ✓
- `$createeffector("freeze_icon")` succeeds (timer with duration) ✓
- Target stops moving ✓
- Target stays frozen for ~19000 game ticks ✓
- `Ice_Freeze_End` fires and unfreezes the target ✓
- Target resumes normal behavior after unfreeze ✓
- Re-freeze guard works (already-frozen targets rejected) ✓
- Dead target guard works ✓
- Building/Lair guard works ✓
- Multiple IceElementals active simultaneously ✓
- Multiple freeze/unfreeze cycles confirmed ✓

### What does NOT work

1. **No ice overlay sprite visible** — The `freeze_effector` overlay is created (confirmed in logs) but produces NO visible output. Frozen units look like normal stopped units with no visual difference at all.

2. **No grey/stone recolor** — This version removed the `#ATTRIB_HasEffectPetrify` + `GetProperUnitArt` calls, so there is no engine-level grey tint applied. The frozen unit has zero visual feedback.

### Visual observation

A frozen Skeleton looked identical to a normal stationary skeleton. No grey tint, no blue shimmer, no overlay of any kind. The only way to tell a unit is frozen is that it doesn't move.

**Update — petrify start animation IS playing:**
When the freeze first hits a hero, there IS a brief grey "turning to stone" animation where the unit raises its arms (the engine's built-in petrify start sequence). This is visible as a grey/white figure with hands-up pose. However, this is just a brief animation at the moment of impact — after it plays, the unit returns to looking normal but stays stationary. There is no persistent grey tint or persistent overlay while frozen. The sequence is:
1. Freeze hits → brief grey "hands up" petrify animation plays
2. Unit returns to normal appearance but is stuck in place
3. No ice overlay visible at any point

This start animation is likely triggered by `#intent_petrified` or the petrify attribute being set. It confirms the engine recognizes the freeze state, but there's no persistent visual feedback during the frozen duration.

### Root cause

The `Quest_maindata.cam` file contains IMAG records (IR01, IR02, IR03) that the engine loads without crashing, but the IMAG records do not correctly point to renderable TILE frame data. Likely causes:

- The IMAG record's frame table references TILE indices that resolve to transparent/empty pixels
- The IMAG dimensions or offset fields are wrong, causing the engine to render nothing
- The binary IMAG format differences identified earlier (see `IceSpell/TODO.md`) mean the engine can't locate the frame data even though it doesn't crash

### Comparison with IceSpell mod (separate from this quest)

The `IceSpell/` mod version crashes when loading the zone because its `Quest_maindata.cam` has IMAG records that are MORE malformed (causes hard crash during zone load). The `IceSpell_Quest/` version doesn't crash, suggesting its IMAG records are partially correct — enough to not crash but not enough to render.

### What the next agent needs to do

1. **Fix IMAG record format** — The IMAG records need to correctly reference TILE frame data. Compare against real IMAG records (MRB1 petrify effector is 412 bytes with known-working structure) and match the binary layout exactly. Key differences identified in `IceSpell/TODO.md`:
   - Offset 44: real has 256, ours has 0
   - Offset 104: real has packed field 0x00240001, ours missing
   - Frame table stride and header metadata differ

2. **Consider re-adding grey tint as interim visual** — Adding back `$SetAttribute(target, #ATTRIB_HasEffectPetrify, 1)` and `$GetProperUnitArt(target)` would give an immediate visual cue (grey recolor) while the overlay sprite issue is fixed. This was present in an earlier version but removed.

3. **Test with known-working ImageIDBase** — As a quick validation, change `IceSpell_Overlays.xml` to use `ImageIDBase value="MRB1"` (the base game's petrify effector sprite). If that renders visibly, it confirms the overlay system works and the problem is purely our custom IMAG/TILE data.

### Log evidence (2026-07-09 20:59, IceSpell_Quest)

```
911 ICE: Caster= IceElemental#171  Target= Skeleton#321
911 ICE: About to createeffector freeze_effector...
911 ICE: freeze_effector created OK
911 ICE: About to createeffector freeze_icon...
911 ICE: freeze_icon created OK
911 ICE: ===== Ice_Freeze_Begin COMPLETE =====

911 ICE: ===== Ice_Freeze_End ENTERED =====
911 ICE: Agent= Ranger#193
911 ICE: No other freeze locks, unfreezing...
911 ICE: Reset_Tasks OK
911 ICE: ResumeThread OK
911 ICE: ===== Ice_Freeze_End COMPLETE =====
```

No errors. No crashes. Spell logic is solid. Only the visual overlay needs fixing.
