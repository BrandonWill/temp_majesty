# SMNU Research — Future Work

## Confirmed: Sub-Panel Navigation is Dead-End Without EXE Patch

Tested all viable action codes from within a building research sub-panel:

| Code | Action ID | Result |
|------|-----------|--------|
| 8013 | 9 | Works — returns to building main (only working code) |
| 8013 | 35 | Also returns to main (code overrides target value) |
| 4004 | 7 | Nothing (hero code, ignored in building context) |
| System B full format | 6 | Nothing (hero navigation format, ignored) |
| 8851 | 83 | Nothing (open-sub-panel code, only works from MAIN panel) |

**Conclusion:** From inside a building sub-panel, the ONLY recognized action is
code 8013 (return to parent). No panel-to-panel navigation is possible without
patching the exe's click handler to support additional codes.

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

## Priority 1: EXE Patch — Enable STRT Lookup from Quest CAMs

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
