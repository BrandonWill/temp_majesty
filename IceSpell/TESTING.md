# Ice Spell Effect - Testing Instructions

## Prerequisites
- Majesty Gold HD installed via Steam
- This repo cloned on the gaming machine

## Step 1: Compile the GPL

Run `MakeGPL.bat` from the `IceSpell/` folder. This calls `gplbcc.exe` and outputs
`Data/IceSpell.bcd`.

If compilation fails, check:
- That `gplbcc.exe` exists at the path in `MakeGPL.bat` (edit the path if needed)
- The error message for undefined functions or syntax errors

## Step 2: Deploy the Mod

**Option A — deploy.bat:**

Run `deploy.bat` from the `IceSpell/` folder. It copies all mod files to:
```
C:\Users\Brandon\Documents\My Games\MajestyHD\Mods\IceSpell
```

**Option B — junction link (development setup):**

```cmd
mklink /J "C:\Users\Brandon\Documents\My Games\MajestyHD\Mods\IceSpell" "C:\Users\Brandon\Documents\Kiro\Majesty\temp_majesty\IceSpell"
```

With a junction, edits in the repo are immediately live in-game.

## Step 3: Play and Test

1. Launch Majesty Gold HD
2. Start any quest that has **Ice Caves** on the map
3. Build your kingdom, let heroes explore near Ice Caves

## What to Look For

**Success indicators:**
- Ice Cave spawns an Ice Dragon (flying blue/white dragon sprite)
- Ice Dragon approaches heroes and plays a "Cast" animation
- Target hero STOPS MOVING (frozen in place)
- Hero's HP bar slowly decreases (cold damage over time)
- After the freeze duration expires, hero resumes movement

**Failure modes:**
- Game crashes on quest load → check IMAG format in Quest_maindata.cam
  (try removing `<CAM>Data\Quest_maindata.cam</CAM>` from mmxml to isolate)
- Ice Cave spawns normal Yeti instead of Ice Dragon → the .dat override isn't taking effect
- Ice Dragon attacks normally (no freeze) → the GPL function isn't being called
- Hero freezes but never unfreezes → the freeze_icon effector callback failed

## Debug Output

The GPL uses `$DebugOut(911, ...)`. View output via the GPL Debugger
(see `SDK/Documentation/GPL Debugger.pdf`).

**Note:** Keep `gpl.log` closed in editors while the game is running — a sharing
violation on that file can cause engine instability.

## Files Reference

| File | Purpose |
|------|---------|
| `IceSpell.mmxml` | Mod definition (tells game what to load) |
| `Data/IceSpell.bcd` | Compiled GPL bytecode (freeze logic) |
| `Data/IceSpell_Actions.xml` | Ice_Freeze spell action definition |
| `Data/IceSpell_Characters.xml` | IceElemental (Ice Dragon sprite + freeze spell) |
| `Data/IceSpell_Overlays.xml` | Visual overlay definitions (effectors) |
| `Data/Quest_maindata.cam` | Custom sprites (IMAG + TILE + SPLT) |
| `GPL/IceSpell.gpl` | Source code (compile with MakeGPL.bat) |
| `GPL/IceSpell_Globals.dat` | Lair spawn override + tunable expressions |
| `GPL/IceSpell.gplproj` | Compiler project file |
