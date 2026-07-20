# SMNU Research — Future Work

## Confirmed Limitations (Exhaustively Tested)

### Building Sub-Panel Navigation
- Only action code 8013 (return to parent) works from inside a sub-panel
- Codes 4004, 8851, System B format — all silently ignored in sub-panel context
- Multi-page navigation is impossible without an exe patch

### Quest CAM Capabilities
- Quest CAMs loaded via `<CAM>` ARE loaded into the resource system (confirmed — no error)
- Quest SMNU/STRT entries with same name as base/expansion do NOT override (first-loaded wins)
- Quest CAMs DO work for: IMAG, TILE, SPLT (sprites), WAVE (audio) — these DO override
- The difference: sprites use "last loaded wins" while SMNU/STRT use "first loaded wins"
- This is a **search priority issue** in `FUN_00679a80`, not a loading issue

### Panel Modifications (Working)
- Inserting widgets into existing SMNU panels WORKS (via direct file replacement)
- The SMNU format is a tag-value int32 stream (fully decoded)
- Widget type 0 buttons can be cloned and repositioned successfully
- The CAM builder (`build_cam()`) produces byte-perfect output

### Distribution Model Required (Current State)
- **Modified mx_textdata.cam** = required for panel mods (direct file replacement)
- Cannot be quest-only WITHOUT an exe patch to fix search priority
- With exe patch (reverse search order for SMNU/STRT): quest-only distribution would work
- **Patched exe** + **modified mx_textdata.cam** = full solution
- Cannot be quest-only
- Users must install both files (game directory replacement)

---

## WILD IDEA: "Hero as Building" — Use Hero Panel for Custom UI

The hero panel has working multi-tab navigation (System B buttons with literal panel
indices). What if we create a "hero" that acts like a building?

### Concept
A Character unit that:
- Doesn't move (Speed=0, Static)
- Has a building sprite (ImageIDBase pointing to a building)
- When clicked, opens the hero-style panel with Stats/Spells/Items tabs
- Those tabs are repurposed as custom content pages
- Spawned at a fixed location via GPL, invincible

### Challenges
- [ ] Can a Character have `Info value="Static"`? Does it suppress movement?
- [ ] Does Speed=0 prevent all AI behavior?
- [ ] Can we suppress hero tracking window appearance?
- [ ] Can the hero panel's tab indices (AP21/AP22/AP78) be overridden per-unit?
- [ ] Can a static character be built from the construction menu? Or only GPL-spawned?
- [ ] What happens if a "hero" has building-style sprites (multi-frame idle)?
- [ ] Does clicking a static character show hero panel or something else?

### Quick Test
Define a Character with:
```xml
<Description type="Unit" subType="Character" ID="ZZA1" Name="ShopKeeper">
    <Engine version="1">
        <Info value="Static"/>
        <Info value="Directionless"/>
        <Info value="BlockGround"/>
        <CanUse value="HumanPlayer"/>
        <Menu value="6"/>
        <ImageIDBase value="ABl1"/>  <!-- Magic Bazaar sprite -->
        <DefaultSound value="0"/>
    </Engine>
    <Game version="1">
        <MaxHP value="9999"/>
        <Speed value="0"/>
        <SightRange value="0"/>
        <Flags value="HasHPBar"/>
    </Game>
</Description>
```

Spawn via GPL: `$SpawnUnit(palace, "ShopKeeper", 0, location);`
Click it — does it show the hero panel with Stats/Spells/Items tabs?

---

## Priority 1: EXE Patch — Fix Resource Search Priority for SMNU/STRT

### Problem (CORRECTED)
Quest CAMs ARE loaded into the resource system. The data IS there. But
`FUN_00679a80` finds the base/expansion version FIRST and stops looking.
Quest-loaded entries with the same name are shadowed (never found).

Sprites (IMAG/TILE) DO override because they use a different lookup path
that prefers last-loaded. SMNU/STRT use a "first match" lookup.

### Potential Fix
In `FUN_00679a80`, reverse the search order: look through resources
starting from MOST RECENTLY LOADED (quest CAMs) instead of oldest first.
This might be a single comparison direction change, or a linked list
traversal direction flip.

### What This Would Enable
- Quest CAMs can override ANY panel (SMNU + STRT) by entry name
- Panel mods become distributable as self-contained quest files
- No need to replace base game files
- Combined with the sub-panel navigation patch (Priority 2), enables
  full multi-page custom building panels from quest-only mods

### Ghidra Task
1. Find `FUN_00679a80` and decompile
2. Identify the loop/search that iterates over registered resources
3. Determine search direction (oldest-first vs newest-first)
4. Find the comparison/iteration that could be reversed
5. Test patched exe with quest-loaded SMNU override

---

## Priority 2: EXE Patch — Sub-Panel Navigation Action Code

### Problem
Quest CAMs loaded via `<CAM>` in mqxml/mmxml do NOT register their STRT entries
in the resource scope that `FUN_006d34d0` searches. The SMNU override loads (engine
finds "MX03" in our CAM), but the matching STRT lookup fails → null handle → crash
when tag 7 (string reference) is encountered.

### Root Cause (from Ghidra)
In `FUN_006d34d0`, the STRT is found via:
```c
handle = FUN_00679a80(entry_name, strt_name);
// internally: resource_mgr->find(entry_name, "STRT", strt_name, 0, 0x80000001, 0, 0)
```

The `0x80000001` is a **search scope flag**. Quest-loaded CAMs likely register under
a different scope, so this lookup misses them.

### Potential Fix
1. Find the instruction that pushes `0x80000001` at the call site in `FUN_006d34d0`
2. Change it to `0xFFFFFFFF` (search all scopes) or the quest scope ID
3. This would be a 4-byte patch in MajestyHD.exe

### Alternative Fix
Add a null-check fallback: if the first lookup returns 0, try again with broader scope.
This would require a code cave (more complex patch) but safer.

### What's Needed
- Ghidra MCP session to find exact byte offset of the `0x80000001` push
- Test patched exe to confirm STRT resolves from quest CAM
- If successful: quest-loaded panels would fully work (SMNU + STRT override)

---

## Priority 2: Multi-Page Panel (File Replacement Approach)

### Current Viable Path (no exe patch needed)
1. Modify `DataMX/mx_textdata.cam` directly (file replacement)
2. Add router panel as MX03 override + new panels PT01/PT02
3. Use `cam_writer.py` to repack the expansion textdata
4. Distribute as a direct file replacement mod

### Steps
- [ ] Build a modified mx_textdata.cam with router MX03 + sub-pages
- [ ] Use correct SMNU format (tag-value int32 stream, from Ghidra decompilation)
- [ ] Use correct STRT format (from str_tool.py: u16 count + u8 + u8 + u32 offsets + strings)
- [ ] Test in-game with direct file replacement
- [ ] If panels render: test nav buttons between pages

---

## Priority 3: EXE Patch — New Building Panel Registration

### Problem
Building-to-panel mapping is hardcoded in per-building vtable methods.
New custom buildings (new DialogID) can't have Research panels without exe patching.

### Potential Approaches
- Modify the panel factory function (0x0051b150) to handle new DialogIDs
- Or: hijack an unused building class's vtable handler to point to custom panel name
- Or: DLL proxy that hooks the panel factory and adds new mappings at runtime

---

## Key Addresses (MajestyHD.exe)

| Address | Function | Purpose |
|---------|----------|---------|
| 0x006d34d0 | STRT loader | Loads STRT by entry name — **PATCH TARGET** for scope fix |
| 0x00679a80 | Resource find | Resource manager lookup (takes scope flag 0x80000001) |
| 0x004b0ce0 | OpenPanelByName | Opens panel by 4-char name |
| 0x0051b150 | Panel class factory | Creates building panel handler from DialogID |
| 0x0063a220 | String setter | Where crash occurs (null deref from failed STRT) |
| 0x0064d330 | Panel factory | Allocates panel, connects STRT, parses widgets |
| 0x00668390 | Child widget parser | Reads widget stream |
| 0x00675b50 | Widget property parser | Processes tag-value property pairs |
| 0x006655e0 | Panel header parser | Processes panel header block |

## Confirmed Format Knowledge

### SMNU: Tag-value int32 stream
- Panel: `1000 [tags...] -1` then `[widget_type sub_id [tags...] -1]...` then `-1`
- Tags consume 1 value (most), 4 values (tag 2 = geometry), or 1+N (color arrays)
- Tag 7 = string from STRT by index
- Tag 33 = tooltip from STRT by index
- Tag 12 = image set (4-char packed as i32)
- Tag 6 = action identifier (stored at widget+0x14)
- Widget types: 0-12, each with specific constructors

### STRT: Header + offset table + strings
- Header: u16 count, u8 unicode_flag (0x00), u8 version (0x02)
- Offsets: count × u32 absolute byte positions
- Content: null-terminated strings (no index prefix)
- STRT is found by SAME entry name as SMNU in the CAM

### CAM Override Behavior
- SMNU entries from quest CAM DO override base/expansion entries (panel loads)
- STRT entries from quest CAM are NOT found by the resource manager lookup
- Workaround: direct file replacement of textdata.cam / mx_textdata.cam
