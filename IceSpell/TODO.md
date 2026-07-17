# IceSpell Mod — Status & Next Steps

## Current Status

The mod is functional. The freeze spell works end-to-end (targeting, immobilize, damage, unfreeze).
Custom sprites load without crashing using the XR47 template approach for IMAG records.

- ✓ Mod loads (GUID valid, mmxml format correct)
- ✓ IceElemental spawns from Ice Cave
- ✓ GPL freeze logic runs correctly
- ✓ TILE sprite frames are valid (round-trip verified, palette_id=0)
- ✓ SPLT palette correct
- ✓ CAM structure correct (3 sections matching WrathOfKrolm structure)
- ✓ IMAG records load (XR47 template approach — confirmed via VISUAL_VERIFICATION)
- ✓ Custom CAM loads from quest DataConfiguration without crashing

---

## Remaining Issues

### 1. Ice overlay visibility (LOW PRIORITY)

Custom ice sprites (IR01/IR02/IR03) load without crashing but may be too subtle to see
in-game. The petrify grey tint is visible, but the blue shimmer overlay hasn't been
confirmed visually on top of it.

**Options:**
- Increase sprite size (currently ~45×64px, vs XR47's 150-400px)
- Increase opacity / more solid fills
- Add brighter white highlights

### 2. Targeting spam (MEDIUM PRIORITY)

The IceElemental re-casts Ice_Freeze_Begin every frame on already-frozen targets.
Guards catch it and return early, but this wastes AI cycles and floods gpl.log.

**Options:**
- Add cooldown via `TimeoutDuration` in the Action XML
- Use `$SpecifyIntent` on the caster after a successful cast to force a pause
- Add a "find unfrozen target" check in the targeting logic

### 3. Remove debug logging (LOW PRIORITY)

Strip `$DebugOut` calls from GPL for stability once the spell logic is finalized.
The debug spam contributes to the gpl.log sharing violation crashes noted in
`IceSpell_Quest/crash_troubleshooting.md`.

---

## Deployment

- **Mod folder:** `C:\Users\Brandon\Documents\My Games\MajestyHD\Mods\IceSpell`
- **Deploy:** Run `deploy.bat` from the `IceSpell/` folder (copies files to Mods folder)
- **Compile GPL:** Run `MakeGPL.bat` from the `IceSpell/` folder
- Junction link from repo → mod folder also works (edits are immediately live in-game)

---

## File Structure

```
IceSpell/
├── IceSpell.mmxml              # Mod definition (game loads this)
├── MakeGPL.bat                 # Compile GPL → Data/IceSpell.bcd
├── deploy.bat                  # Deploy to Mods folder
├── Data/
│   ├── IceSpell.bcd            # Compiled GPL bytecode
│   ├── IceSpell_Actions.xml    # Ice_Freeze spell action
│   ├── IceSpell_Characters.xml # IceElemental (Ice Dragon sprite)
│   ├── IceSpell_Overlays.xml   # freeze_effector, freeze_icon, thaw_effector
│   └── Quest_maindata.cam      # Sprite data (IMAG + TILE + SPLT)
├── GPL/
│   ├── IceSpell.gpl            # Freeze logic source
│   ├── IceSpell_Globals.dat    # IceElemental data + Ice_Cave override
│   └── IceSpell.gplproj        # Compiler project file
├── sprites/                    # Raw TILE frame data (ice + thaw frames)
├── preview/                    # PNG previews of overlay sprites
└── utility/                    # Python tools for sprite generation
    ├── ice_overlay_generator.py
    └── ice_palette_analyzer.py
```

---

## Technical Notes

### IMAG Template Approach (what worked)

The WrathOfKrolm mod CAM (`SDK/Example/Data/WrathOfKrolm_maindata.cam`) has working
IMAG records for mod-loaded CAMs. We used `XR47DustofDeth` (292 bytes, directionless
overlay) as a template structure for our IR01/IR02/IR03 records.

Key insight: mod CAM TILE indices are 0-based (local to the mod's own TILE section),
not global indices into the base game's maindata.cam.

### Workaround (testing freeze mechanics without custom sprites)

Remove `<CAM>Data\Quest_maindata.cam</CAM>` from mmxml and change overlay XML to use
`ImageIDBase value="MRB1"` (petrify sprite from base game). This confirms the full
freeze/unfreeze cycle works.
