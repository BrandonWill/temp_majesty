# Ice Spell Visual Verification — Current Test

## Status: CUSTOM CAM SPRITES CONFIRMED RENDERING (XR47 test passed)

The WoK "Dust of Death" (XR47) animation rendered correctly on frozen heroes
when loaded from a quest-loaded CAM. Game was stable with no crashes once all
three overlay ImageIDBase values pointed to valid IMAG IDs.

## This Build: Custom Ice Sprites (IR01/IR02/IR03)

Now testing our actual ice sprites from the Python-built CAM.

**What to look for:**
- When the Ice Elemental freezes a hero, you should see:
  1. Hero turns grey (petrify shader from HasEffectPetrify)
  2. A blue/white shimmer overlay appears ON TOP of the grey hero
  3. The overlay is approximately 45x64 pixels (smaller than XR47's 400px dust cloud)
  4. It may be subtle — look for blue/cyan pixels around the frozen hero

**If you see the grey petrify + a blue shimmer:** Custom ice sprites are rendering! SUCCESS.

**If you see ONLY the grey petrify (no blue):** The sprites aren't rendering. The issue 
is our Python CAM writer producing TILE data the engine can't display (even though it 
loads without crashing). Compare against XR47 which DID render.

**If it crashes:** Check which ImageIDBase is causing the null pointer. All three 
(IR01, IR02, IR03) must exist as IMAG records in the loaded Quest_maindata.cam.

## Key Differences from XR47 (which worked)

| Property | XR47 (worked) | Our ice sprites |
|----------|---------------|-----------------|
| TILE size | 5-33KB per frame | ~900 bytes per frame |
| Dimensions | 150-400px wide | 45px wide |
| Frames | 21 | 6 (ice) / 5 (thaw) |
| Source | Original game developer | Python sprite_injector.py |
| Palette | WoK palette 0 | WoK palette 0 (same) |

The biggest risk: our TILE encoding (from sprite_injector.py) might produce 
data the engine can't render, even though it passes our round-trip tests.


## In-Game Screenshot Observations

**Screenshot — Grassland/Goblin Camp area (2026-07-09 22:08 session):**
The Ice Dragon (IceElemental) is visible as a blue/white flying creature in the center of the screen, hovering over Goblin Camp structures. Directly beneath/beside it is its frozen target — a unit that appears grey/stone-colored from the petrify shader, standing completely still while the dragon keeps casting on it. The grey tint from `#ATTRIB_HasEffectPetrify` + `GetProperUnitArt` IS visible in this version, confirming the petrify visual is working. However, no blue/cyan ice overlay is visible on top of the grey unit — only the base petrify grey recolor.

**Conclusion from all screenshots:**
- Grey petrify tint: ✓ visible (when HasEffectPetrify + GetProperUnitArt are used)
- Brief "hands up" petrify start animation: ✓ visible
- Custom ice overlay sprite (IR01 from Quest_maindata.cam): ✗ NOT visible — either not rendering or too small/transparent to see
