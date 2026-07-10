# Ice Spell Visual Verification Guide

## Test Results — 2026-07-09 20:45 (IceSpell_Quest)

### CONFIRMED WORKING ✓

The full freeze/unfreeze cycle works end-to-end:

**From gpl.log:**
1. ✓ `IceElemental#166` spawns from Ice Cave and casts at heroes
2. ✓ `Ice_Freeze_Begin` fires on `Rogue#74` — all guards pass (not dead, not building, not already petrified)
3. ✓ `$createeffector("freeze_effector")` succeeds — **no crash** (Quest_maindata.cam loaded correctly)
4. ✓ `$createeffector("freeze_icon")` succeeds (timer effector with duration)
5. ✓ `HasEffectPetrify` set, `GetProperUnitArt`, `StopMoving`, `SuspendThread`, `IsFrozen`, `SpecifyIntent` — all OK
6. ✓ Re-freeze guard works — subsequent casts say "Target already petrified, returning"
7. ✓ `Ice_Freeze_End` fires after timer expires — clears attributes, resets tasks, resumes thread
8. ✓ Hero unfreezes and gets re-frozen again (second complete cycle confirmed)
9. ✓ Multiple IceElementals active (IceElemental#166, IceElemental#458)
10. ✓ Dead target guard works (`Ice_Freeze_End` on dead `Rogue#268` — "Agent is dead, returning")

**From err.log:**
- `Quest_maindata.cam` loaded without crash
- All description XMLs loaded
- No script errors or missing attribute errors
- Game ran stably for 14000+ frames

### Visual Observations (from screenshot)

- **Grey recolor visible** ✓ — frozen unit clearly turns stone/grey (from `#ATTRIB_HasEffectPetrify` triggering the engine's built-in petrify shader)
- **Unit is stationary** ✓ — frozen hero does not move
- **Ice overlay (IR01 sprite)** — NOT visibly distinguishable from the screenshot. The `freeze_effector` was created successfully (log confirms), so either:
  - The overlay IS rendering but is too subtle/small to see at this zoom level
  - The overlay is rendering but blends with the grey petrify recolor
  - The IMAG record in Quest_maindata.cam, while not crashing, may not point to valid TILE frame data (the overlay could be rendering as 0-pixel transparent frames)

### Known Issues

1. **Targeting spam** — IceElemental keeps casting on the same already-frozen target every frame instead of switching to a new target. The guard clause catches it, but it wastes AI cycles. Need to either:
   - Add a `SpellTarget` constraint in `IceSpell_Actions.xml` to filter to non-frozen units
   - Or have the IceElemental's AI decision tree pick a different target when the current one is frozen

2. **Overlay visibility unknown** — Need a closer zoom screenshot or a comparison against standard Medusa petrify to confirm whether the ice overlay sprite is rendering on top

### Performance Note

The err.log shows many frames taking 200-470ms (floating average 30-140). This is partly the debug output spam but also the aggressive AI re-casting loop. Removing the `$DebugOut` calls and fixing the targeting will improve performance significantly.
