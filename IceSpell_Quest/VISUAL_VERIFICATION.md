# Ice Spell Visual Verification Guide

## What to look for in a screenshot

Take a screenshot of a hero that has been frozen by the Ice Elemental's attack. The agent analyzing the image should check:

### Expected visuals when freeze is applied:

1. **Grey/stone recolor** — The hero's sprite turns grey (this is the built-in petrify engine effect from `#ATTRIB_HasEffectPetrify`). This is expected and confirms the freeze mechanic is working.

2. **Ice border overlay** — ON TOP of the grey hero, there should be a semi-transparent blue/cyan border effect rendered around or over the unit. This is our custom sprite from `Quest_maindata.cam` (IMAG record IR01). The overlay:
   - Is approximately 43x57 pixels (cropped content area)
   - Uses blues, cyans, and white pixels from palette 423
   - Should appear as a shimmering/sparkling border around the frozen unit
   - Animates through 6 frames in a loop
   - Rendered on top of the hero sprite

3. **Unit is stationary** — The frozen hero should not be moving.

### What to compare against:

- **Petrify (base game Medusa)**: Unit turns grey/stone with NO additional border overlay. If this is what you see, the overlay is NOT rendering.
- **Our freeze**: Unit turns grey/stone AND has an additional blue/cyan shimmer border overlay on top. If you see any blue/icy coloring around the edges of the grey unit, the custom CAM sprites ARE rendering.

### The overlay sprites look like:

The ice_frame PNGs in `IceSpell_Quest/sprite_preview/` show exactly what should render. They are blue-white sparkle/crystal patterns about 43x57 pixels — roughly the size of a hero unit. They overlay transparently on top of whatever is beneath them.

### If the overlay is NOT visible:

It may be too subtle against the grey petrify recolor, or it might not be rendering at all. Possible reasons:
- The overlay is very small (pixel-sized at the game's render scale)
- The blue pixels blend with the grey background
- The IMAG record isn't being resolved to IR01 properly

### Verification steps for the agent:

1. Look at the frozen hero closely — is there ANY blue/cyan/white shimmer that differs from a standard petrify?
2. Compare against a Medusa petrify if possible — does the freeze look identical or does it have extra visual elements?
3. Check the edges of the frozen unit for any sparkle/crystal overlay pixels
4. The overlay renders at the unit's position — look directly on/around the hero sprite
