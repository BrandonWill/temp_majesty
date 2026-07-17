# Ice Spell Effect - Mod

A custom Ice/Freeze spell effect for Majesty Gold HD, packaged as a standalone mod (`.mmxml`).

## What It Does

- **Ice Elemental** (Ice Dragon sprite) casts a freeze spell on heroes
- Target is **immobilized** (frozen in place, can't act)
- **Cold damage over time** while frozen (lethal — can kill)
- **Magic resistance** halves the freeze duration
- **Thaw/shatter animation** plays when the effect ends
- Works alongside petrify/vines — a unit can be both petrified AND frozen
- Ice Caves spawn Ice Elementals instead of Yeti

## Installation

### Option A: Deploy script (recommended)

1. Compile the GPL: run `MakeGPL.bat` from this folder
2. Deploy: run `deploy.bat` — copies everything to `Documents\My Games\MajestyHD\Mods\IceSpell`
3. Launch Majesty Gold HD and activate the mod

### Option B: Junction link (development)

Create a junction from this repo folder to the game's Mods directory:
```
mklink /J "C:\Users\Brandon\Documents\My Games\MajestyHD\Mods\IceSpell" "C:\Users\Brandon\Documents\Kiro\Majesty\temp_majesty\IceSpell"
```
Edits in the repo are immediately live in-game — no copying needed.

### Playing

1. Launch Majesty Gold HD
2. On the map screen, mods should be active if installed in the Mods folder
3. Start any quest that has **Ice Caves** on the map
4. Ice Elementals will spawn from Ice Caves and freeze nearby heroes

## Testing Guide

**What to look for:**
1. Ice Dragon appears from Ice Cave lairs
2. When the dragon is within range of a hero, it casts (plays "Cast" animation)
3. Hero stops moving (frozen)
4. Hero takes periodic damage (visible in HP bar dropping)
5. After the freeze duration expires, the freeze ends
6. Hero resumes normal behavior

**Debug output:** The GPL uses `$DebugOut(911, ...)` calls. View debug output via the
GPL Debugger (see `SDK/Documentation/GPL Debugger.pdf`).

**If the game crashes:**
- Most likely cause: IMAG record format in Quest_maindata.cam
- Try removing `<CAM>Data\Quest_maindata.cam</CAM>` from the mmxml to test GPL logic without sprites
- The freeze_effector overlay won't be visible without the CAM, but the immobilization + damage still works

## File Structure

```
IceSpell/
├── IceSpell.mmxml              # Mod definition (game loads this)
├── MakeGPL.bat                 # Compile GPL source → Data/IceSpell.bcd
├── deploy.bat                  # Deploy to Documents\My Games\MajestyHD\Mods\IceSpell
├── Data/
│   ├── IceSpell.bcd            # Compiled GPL bytecode
│   ├── IceSpell_Actions.xml    # Ice_Freeze spell action
│   ├── IceSpell_Characters.xml # IceElemental (Ice Dragon sprite)
│   ├── IceSpell_Overlays.xml   # freeze_effector, freeze_icon, thaw_effector
│   └── Quest_maindata.cam      # Sprite data (IMAG + TILE + SPLT)
├── GPL/
│   ├── IceSpell.gpl            # Freeze logic source
│   ├── IceSpell_Globals.dat    # Tunable expressions + Ice_Cave override
│   └── IceSpell.gplproj        # Compiler project file
├── sprites/                    # Raw TILE frame data (ice + thaw)
├── preview/                    # PNG previews of overlay sprites
└── utility/                    # Python tools for sprite generation
    ├── ice_overlay_generator.py
    └── ice_palette_analyzer.py
```

## Building

1. Run `MakeGPL.bat` to compile GPL source into `Data/IceSpell.bcd`
2. Run `deploy.bat` to copy files to the Mods folder
3. Or use a junction link for instant updates (see Installation above)

## Tunable Parameters (IceSpell_Globals.dat)

| Expression | Default | Description |
|---|---|---|
| `#Freeze_Duration` | 19000 | Freeze duration in game ticks |
| `#Freeze_DamagePerTick` | 5 | HP damage per tick |
| `#Freeze_DamageInterval` | 2000 | Ticks between damage applications |
| `#Freeze_ThawDuration` | 3000 | Thaw animation display time |

## Known Limitations

- Ice Elemental reuses the Ice Dragon sprite (BVi1) as placeholder
- Ice overlay sprite (IR01/IR02/IR03) may be too subtle to see in-game — confirmed loading,
  but visual impact is minimal at current sprite size (~45×64px)
- Targeting spam: IceElemental re-casts on already-frozen targets (returns early but wastes cycles)

## Technical Notes

- Uses custom attribute (`is_frozen_ice`) for freeze flag — independent from `#ATTRIB_HasEffectPetrify`
- Damage thread uses `$NewThread` auto-repeat pattern (returns early to terminate)
- `UnFreeze_Unit` is overridden to include ice freeze in the freeze-lock check
- IMAG records in Quest_maindata.cam use XR47 (WrathOfKrolm) as template structure
- TILE indices in the mod CAM are 0-based (local to mod's TILE section)
