# Majesty Modding — Ghidra / EXE Patch TODO

Work that requires the Ghidra machine and MajestyHD.exe disassembly/patching.

**When you complete a task or discover new info, update THESE files:**

| What you found | Update this file |
|----------------|-----------------|
| New exe address / function ID | This file → "Known EXE Addresses" table below |
| Panel format / SMNU behavior | `SMNUResearch/findings/smnu_parser_decompilation.md` |
| Action codes / click handling | `SMNUResearch/findings/action_codes_decoded.md` |
| Panel navigation specifics | `SMNUResearch/findings/nav_button_pattern.md` |
| Widget type constructors | `SMNUResearch/findings/smnu_parser_decompilation.md` |
| Scroll widget / type 6/9 | `SMNUResearch/FUTURE_TODO.md` (Priority 3.5 section) |
| Cheat function internals | `CAM_MODDING_GUIDE.md` (new section if confirmed) |
| Particle system engine behavior | `CAM_MODDING_GUIDE.md` (particle section) |
| Resource load order / scope | `CAM_MODDING_GUIDE.md` (Quest CAM Loading section) |
| General progress / completion | `TODO.md` (root) + mark done here |

---

## Priority 1: Sub-Panel Navigation Action Code

**Goal:** Enable multi-page building research panels via a new action code.

**Steps:**
1. Find the building sub-panel click handler (the function that checks for code 8013)
2. Identify where it rejects/ignores unknown codes
3. Add new code path: `if (code == 8852) { OpenPanelByName(actionID_as_4CC, 0); }`
4. Likely requires a code cave (jump to new code in unused exe section)

**Start from:** `FUN_004b0ce0` (believed to be `OpenPanelByName` — confirm first).
Cross-ref with action code 8013 handler to find the dispatcher.

**Record results in:** `SMNUResearch/findings/action_codes_decoded.md`

**What this enables:**
- Navigation buttons in SMNU data: `[1024, 5, "PT01", 6, 8852]`
- Multi-page building research panels (6 items per page, unlimited pages)
- Quest-distributable via `<CAM>` (SMNU override confirmed working)

---

## Priority 2: New Building Panel Registration

**Goal:** Allow custom buildings (new DialogID) to have Research panels.

**Steps:**
1. Decompile `FUN_0051b150` (panel class factory) — confirm it maps DialogID → panel name
2. Find where it rejects unknown DialogIDs
3. Either extend the mapping table or add a hook for custom IDs

**Record results in:** `SMNUResearch/findings/smnu_parser_decompilation.md`

**Potential approaches:**
- Modify the panel factory function to handle new DialogIDs
- Hijack an unused building class's vtable handler
- DLL proxy that hooks the panel factory at runtime

---

## Priority 3: Scroll List Widget for Research Panels

**Goal:** Determine if type 6 (scrollable list) can replace fixed button slots in research panels.

**Steps:**
1. Decompile `FUN_00495790` (believed to be research panel populator)
2. Check: does it look for type 6 list widgets, or only fixed button widgets?
3. If buttons-only: assess patch difficulty to make it populate a type 6 list

**Record results in:** `SMNUResearch/FUTURE_TODO.md` (Priority 3.5 section)

**Context:** Type 6 and type 9 constructors are at `FUN_006d0dd0` and `FUN_006cc5d0`.
See `SMNUResearch/FUTURE_TODO.md` for geometry examples and known behavior.

---

## Priority 4: Expose Cheat Functions to GPL

**Goal:** Add GPL primitives that call internal cheat engine functions.

**Steps:**
1. Find cheat string handler in exe (handles "revelation", gold cheats, etc.)
2. Identify the internal functions cheats call (map reveal, resource add)
3. Create new GPL primitive dispatch entries pointing to those functions
4. Test: `$RevealMap()`, `$AddGold(amount)` from quest GPL

**Record results in:** `CAM_MODDING_GUIDE.md` (new "Engine Cheats" section if confirmed)

**Context:** Some cheats already call GPL (`cheat_wave_undead`, `cheat_wave_raiders`).
The reverse direction (GPL → cheat internals) should be structurally similar.

---

## Verification Tasks

| Task | Record in |
|------|-----------|
| Confirm `FUN_004b0ce0` = `OpenPanelByName` | This file (Known Addresses table) |
| Confirm `FUN_00495790` = research panel populator | This file (Known Addresses table) |
| Identify sub-panel click dispatcher function | `SMNUResearch/findings/action_codes_decoded.md` |
| Document resource search direction in `FUN_00679a80` | `CAM_MODDING_GUIDE.md` (Quest CAM Loading) |
| What does `AllocateLocalID` do for particle systems | `CAM_MODDING_GUIDE.md` (particle section) |

---

## Known EXE Addresses (MajestyHD.exe)

Update this table as you confirm/discover functions.

| Address | Function | Status | Purpose |
|---------|----------|--------|---------|
| 0x006d34d0 | STRT loader | CONFIRMED | Loads STRT by entry name |
| 0x00679a80 | Resource find | CONFIRMED | Resource manager lookup (scope flag 0x80000001) |
| 0x004b0ce0 | OpenPanelByName? | UNCONFIRMED | Opens panel by 4-char name |
| 0x0051b150 | Panel class factory | CONFIRMED | Creates building panel handler from DialogID |
| 0x0063a220 | String setter | CONFIRMED | Where STRT null crash occurs (null deref) |
| 0x0064d330 | Panel factory | CONFIRMED | Allocates panel, connects STRT, parses widgets |
| 0x00668390 | Child widget parser | CONFIRMED | Reads widget stream from SMNU |
| 0x00675b50 | Widget property parser | CONFIRMED | Processes tag-value property pairs |
| 0x006655e0 | Panel header parser | CONFIRMED | Processes panel header block (tag 1000) |
| 0x00495790 | Research populator? | UNCONFIRMED | Fills research panel content |
| 0x006d0dd0 | Type 6 constructor | CONFIRMED | Scrollable list widget (368 bytes) |
| 0x006cc5d0 | Type 9 constructor | CONFIRMED | Scrollbar/slider widget (340 bytes) |
| 0x006d3110 | Type 0 constructor | CONFIRMED | Standard button widget (340 bytes) |
| 0x006d2b80 | Type 1 constructor | CONFIRMED | Widget type 1 (340 bytes) |
| 0x006d2570 | Type 2 constructor | CONFIRMED | Widget type 2 (340 bytes) |
| 0x006d1a20 | Type 5 constructor | CONFIRMED | Text/label widget (352 bytes) |
| 0x00692a10 | Type 12 constructor | CONFIRMED | Largest widget type (464 bytes) |
