# Ice Spell Effect - Quest Mod

A custom Ice/Freeze spell effect for Majesty Gold HD.

## What It Does

- **Ice Elemental** monster casts a freeze spell on heroes
- Target is **immobilized** (frozen in place, can't act)
- **Cold damage over time** while frozen (lethal - can kill)
- **Magic resistance** halves the freeze duration
- **Thaw/shatter animation** plays when the effect ends
- Works alongside petrify/vines — a unit can be both petrified AND frozen

## File Structure

```
IceSpell/
├── IceSpell.mqxml          # Quest definition + DataConfiguration
├── MakeGPL.bat             # Compile script
├── Data/
│   ├── IceSpell_Actions.xml    # Ice_Freeze spell action
│   ├── IceSpell_Characters.xml # Ice Elemental monster
│   ├── IceSpell_Overlays.xml   # freeze_effector, freeze_icon, thaw_effector
│   └── IceSpell.bcd            # Compiled GPL (after MakeGPL.bat)
└── GPL/
    ├── IceSpell.gplproj       # Compiler project file
    ├── IceSpell.gpl           # Freeze logic + UnFreeze_Unit override
    └── IceSpell_Globals.dat   # Tunable expressions (duration, damage, etc.)
```

## Building

1. Run `MakeGPL.bat` to compile the GPL source into `Data/IceSpell.bcd`
2. Copy the entire `IceSpell/` folder to your Majesty quests directory
3. Select "Ice Spell Test" quest in game

## Tunable Parameters (IceSpell_Globals.dat)

| Expression | Default | Description |
|---|---|---|
| `#Freeze_Duration` | 19000 | Freeze duration in game ticks |
| `#Freeze_DamagePerTick` | 5 | HP damage per tick |
| `#Freeze_DamageInterval` | 2000 | Ticks between damage applications |
| `#Freeze_ThawDuration` | 3000 | Thaw animation display time |

## Known Limitations

- The Ice Elemental reuses the Ice Dragon sprite (BVi1) as placeholder
- Overlay sprites (IR01, IR02, IR03) need IMAG/TILE data in a Quest_maindata.cam
  (currently defined in XML but the CAM file with actual sprite data is not yet built)
- The `freeze_effector` won't display visually until sprite frames are generated
  and packaged into a CAM file referenced by DataConfiguration

## Technical Notes

- Uses `$AddAttribute` for the freeze flag — independent from engine `#ATTRIB_HasEffect*`
- Damage thread uses the `$NewThread` auto-repeat pattern (returns early to terminate)
- `UnFreeze_Unit` is overridden to include ice freeze in the freeze-lock check
- Effect does NOT use `$SetDrawEffects` for color tint — relies on overlay sprite alone
