# IceSpell Mod — TODO

## Needs In-Game Testing

### 1. Verify freeze_effector cleanup

Added `$DeleteEffector(ThisAgent, "freeze_effector")` to `Ice_Freeze_End`.
Previously the visible ice overlay was created with duration 0 (persistent) and
never deleted — it would remain on the unit after unfreezing.

**Test:** Freeze a hero, wait for unfreeze, confirm no lingering overlay sprite.

### 2. Verify stability without $DebugOut

All `$DebugOut` calls removed from both IceSpell and IceSpell_Quest GPL.
The debug spam was flooding gpl.log at hundreds of lines/second and contributing
to sharing violation crashes.

**Test:** Run a game session for 5+ minutes with active Ice Elementals. Confirm no
crashes. Check that gpl.log stays quiet (or doesn't exist).

### 3. Ice overlay visibility (LOW PRIORITY)

Custom ice sprites (IR01/IR02/IR03) load without crashing but may be too subtle to see
in-game. The petrify grey tint is visible, but the blue shimmer overlay hasn't been
confirmed visually.

**Options if not visible:**
- Increase sprite size (currently ~45×64px, vs XR47's 150-400px)
- Increase opacity / more solid fills
- Add brighter white highlights

---

## Not A Bug (Confirmed Normal)

**Targeting spam** — The IceElemental re-evaluates and calls Ice_Freeze_Begin on
already-frozen targets. This is normal monster AI behavior (Gorgon does the same).
The `HasEffectPetrify` guard returns early with no state changes. The real problem
was $DebugOut flooding — now fixed.

---

## Deployment

- **Compile GPL:** Run `MakeGPL.bat` from the `IceSpell/` folder
- **Deploy:** Run `deploy.bat` (copies to `Documents\My Games\MajestyHD\Mods\IceSpell`)
- Junction link from repo → mod folder also works (edits are immediately live in-game)
