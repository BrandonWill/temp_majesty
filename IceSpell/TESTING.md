# Ice Spell Effect - Testing Instructions

## Prerequisites
- Majesty Gold HD installed via Steam
- This repo cloned on the gaming machine
- Python NOT required (only for sprite generation, not for testing)

## Step 1: Compile the GPL

1. Find `gplbcc.exe` on your system. Likely locations:
   - `C:\Program Files (x86)\Steam\steamapps\common\Majesty HD\SDK\gplbcc.exe`
   - Or wherever Steam installed the game under `SDK\gplbcc.exe`

2. Open a command prompt in the `IceSpell\GPL\` folder

3. Run the compiler:
   ```
   "PATH_TO\gplbcc.exe" -in IceSpell.gplproj -out IceSpell.bcd -stdout
   ```

4. If successful, copy the resulting `IceSpell.bcd` to `IceSpell\Data\`:
   ```
   copy IceSpell.bcd ..\Data\
   ```

**If compilation fails:** Note the exact error message. Common issues:
- Undefined function references (the mod may need access to base game GPL includes)
- Syntax errors (report the line number and text)

## Step 2: Find the Mod Installation Location

The game loads mods from a specific directory. We need to find it:

1. Open Steam, right-click Majesty Gold HD → Properties → Local Files → Browse
2. This opens the game's root folder (e.g., `C:\Program Files (x86)\Steam\steamapps\common\Majesty HD\`)
3. Look for any of these folders that contain `.mmxml` files:
   - Root level (same folder as MajestyHD.exe)
   - `SDK\Mods\`
   - A `Mods\` subfolder
   - Look for where `MyAI.mmxml` is if the MyAI mod was previously installed

4. Also check: `%USERPROFILE%\Documents\My Games\MajestyHD\` for any mod folders

5. **Report back** what folder structure you find and where `.mmxml` files live

## Step 3: Install the Mod

Once you know the correct location:

1. Copy the entire `IceSpell\` folder to that location
2. The game needs to find `IceSpell\IceSpell.mmxml` — the folder structure should be:
   ```
   <mod_location>\IceSpell\
   ├── IceSpell.mmxml
   └── Data\
       ├── IceSpell_Actions.xml
       ├── IceSpell_Characters.xml
       ├── IceSpell_Overlays.xml
       └── IceSpell.bcd
   ```

Note: `Quest_maindata.cam` is intentionally NOT loaded yet (to avoid potential crashes from unverified IMAG format). The spell logic works without it — you just won't see the ice overlay sprite.

## Step 4: Activate and Test

1. Launch Majesty Gold HD
2. Look for mod activation:
   - On the main menu or quest selection screen, there should be a way to activate mods
   - The mod is called "Ice Spell Effect"
3. Start any expansion quest that has **Ice Caves** on the map
   - Good candidates: maps with snowy/northern terrain
   - The Siege quest or your custom MyAI quest (if installed) have Ice Caves
4. Play normally — build your kingdom, let heroes explore

## What to Look For

**Success indicators:**
- Ice Cave spawns an Ice Dragon (flying blue/white dragon sprite)
- Ice Dragon approaches heroes and plays a "Cast" animation
- Target hero STOPS MOVING (frozen in place)
- Hero's HP bar slowly decreases (cold damage over time)
- After ~19 seconds (game speed dependent), hero resumes movement
- A brief visual effect plays when the freeze ends (thaw animation — may not show without CAM)

**Failure modes:**
- Game crashes on quest load → likely the mod isn't loading correctly
- Ice Cave spawns normal Yeti instead of Ice Dragon → the .dat override isn't taking effect
- Ice Dragon attacks normally (no freeze) → the GPL function isn't being called
- Hero freezes but never unfreezes → the freeze_icon effector GPLFunction callback failed

## Troubleshooting

**"Mod doesn't appear in game":**
- The folder is in the wrong location. Try moving it to different directories within the game install.
- Check if the game has a "Downloadable content" or "Custom" section accessible from the map screen (purple star icon in upper-left corner).

**"Crashes on load":**
- The GPL .bcd may reference functions not available in the base game context
- Try creating a minimal .gpl with just one empty function and compiling that to verify the toolchain works

**"Compiles but nothing happens in game":**
- The mod may be loading but the Ice_Cave override isn't being picked up
- Verify by checking if Ice Dragons appear from Ice Caves (visual confirmation)

## Files Reference

| File | Purpose |
|------|---------|
| `IceSpell.mmxml` | Mod definition (tells game what to load) |
| `Data/IceSpell.bcd` | Compiled GPL bytecode (freeze logic) |
| `Data/IceSpell_Actions.xml` | Ice_Freeze spell action definition |
| `Data/IceSpell_Characters.xml` | Ice Elemental monster (Ice Dragon sprite + freeze spell) |
| `Data/IceSpell_Overlays.xml` | Visual overlay definitions (effectors) |
| `GPL/IceSpell.gpl` | Source code (not needed at runtime, only for compilation) |
| `GPL/IceSpell_Globals.dat` | Lair spawn override (Ice Cave → IceElemental) |
| `GPL/IceSpell.gplproj` | Compiler project file |
