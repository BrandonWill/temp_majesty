# SMNU Panel Research — Custom Building Sub-Panels

Reverse-engineering the SMNU dialog/panel system in Majesty Gold HD to enable
**custom multi-page building panels** with arbitrary navigation between them.

## The Core Question

When you click a button in the game UI (like "Research" on a Marketplace), the engine
fires an **action** that opens a specific sub-panel. The expansion devs added new actions
(Magic Bazaar research items, Sorcerer spells) without modifying the exe. 

**Can we define a new "open sub-panel" action that displays a custom panel?**

If yes: we can chain panels (Page 1 -> Page 2 -> Page 3) for unlimited research slots.

## What We Know So Far

### SMNU Buttons Are Just Actions

Every clickable button in a panel is: "when clicked, fire action ID X with handler code Y."

| Action ID | Code | What It Does |
|-----------|------|-------------|
| 82 | 8851 | Open research sub-panel |
| 83 | 8851 | Open spell list sub-panel |
| 9 | 8013 | Return to building main |
| 77 | 8200 | Market Day (fires GPL) |
| 88 | 8002 | Destroy building |
| 5061-5066 | (research) | Purchase bazaar items (fires GPL) |

Key insight: **code 8851 = "open a sub-panel"**. Action IDs 82 and 83 both use it
to open different sub-panels. The engine resolves which panel to display based on
the action ID + building context.

### The Expansion Created New Actions

The Magic Bazaar (expansion) added 6 purchase actions (5061-5066) that didn't exist
in the base game. The engine handled them fine. This proves actions are data-driven
to at least some degree.

### Two Button Action Formats Exist

**System A** (building panels): `[1024, 5, ACTION_ID, 6, CODE]`
- Used by all building UI buttons
- ACTION_ID + CODE fire engine-level behavior
- "Open sub-panel" uses code 8851

**System B** (hero panels only): `[1024, 3, 8, 5, PANEL_INDEX, 6, CODE, 258, ALT1, 266, ALT2, -1]`
- Uses literal panel indices for navigation
- Only found in hero detail panels (Stats/Spells/Items tabs)

### MX03 Panel Fully Decoded

The Magic Bazaar research panel (3420 bytes) has been completely mapped:
- 6 research item widgets (232 bytes each)
- 6 cost display widgets + 6 cost labels
- 1 "Return to Main" button (action 9, code 8013)
- 2 utility buttons (Track, Zoom)
- Panel header + background frame

See `findings/MX03_full_decode.md` for the complete byte-by-byte layout.

## What Ghidra Needs to Answer

The ONE critical question:

**How does the engine map (action ID + code 8851 + building type) to a specific panel?**

Possibilities:
1. **Data table** (best case): A lookup somewhere that says "for building ABl1, action 82 -> panel MX03". If we can find and extend this table, we can add new panel navigation actions.
2. **Hardcoded switch/case** (workable): The exe has `if action==82, open research; if action==83, open spells`. We'd need to find unused action IDs that route through the same handler.
3. **Naming convention** (possible): The engine derives the panel name from the building's DialogID using a pattern (e.g., DialogID "MX02" + action "research" -> panel "MX03"). If we follow the convention, new panels might Just Work.

## File Inventory

| File | Purpose |
|------|---------|
| `README.md` | This document |
| `smnu_analysis.py` | SMNU panel analysis tool (dump, list-nav, compare) |
| `smnu_patcher.py` | Panel binary patcher + POC test generator |
| `TASK_exe_disassembly.md` | Ghidra MCP task for the other machine |
| `findings/MX03_full_decode.md` | Complete Magic Bazaar panel structure |
| `findings/nav_button_pattern.md` | Hero panel nav button format (System B) |
| `findings/action_codes_decoded.md` | All known action IDs and handler codes |
| `test/` | Pre-built test CAM files for in-game validation |
