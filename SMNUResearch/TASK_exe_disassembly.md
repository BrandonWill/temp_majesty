# Task: Find Sub-Panel Resolution Logic in Game Executable

## The One Question

When you click "Research" on a building, the button fires action 82 + handler code 8851.
The engine then opens a DIFFERENT panel for each building (APa3 for Marketplace, APa2 for
Library, MX03 for Magic Bazaar). **How does the engine know which panel to open?**

The answer is NOT in the SMNU button data — we checked. Every base game Research button
is byte-for-byte identical (action=82, code=8851, 258=70, 266=84). The target panel is
resolved at runtime by the engine based on the building's identity.

## What We've Ruled Out

- NOT in the SMNU button bytes (all Research buttons are identical)
- NOT in the building's XML definition (no panel reference field exists)
- NOT a simple DialogID+1 convention (base game: AP31->APa3, AP02->APa2 don't follow one rule)
- The 258/266 values (70, 84) are the SAME across all base buildings — they're not panel refs

## What The Expansion Tells Us

The expansion added new buildings with sub-panels:
- MX02 (Magic Bazaar main) -> MX03 (research) via action 82 + 8851
- MX06 (Sorcerer's Abode main) -> MX07 (spells) via action 83 + 8851
- MX09 (Outpost main) -> has action 82 + 8851 but NO research — only visitors

Expansion buttons have NO 258/266 blocks. They just fire (action, code) and the engine resolves.

## Setup

Load the main Majesty Gold HD game executable in Ghidra (NOT RGSeditor.exe).
Use the Ghidra MCP tools to search and decompile.

## Search Strategy

### Primary: Find handler code 8851

Search for constant **0x2293** (8851 decimal) in the code. This is the "open sub-panel"
handler. When found, decompile the function and look for:

1. How it receives the action ID (82 or 83)
2. How it identifies the current building
3. How it resolves which panel to display
4. Is there a lookup table, a string derivation, or a building struct field?

### Secondary: Find the panel name registry

The engine must store panel names ("APa3", "MX03") somewhere and look them up.
Search for:
- String "APa3" or "APa2" — find where research panel names are referenced
- String "MX03" — find the expansion panel registration
- The pattern of research panel names: APa0, APa1, APa2, APa3, APa4

If these appear in a table/array together, that's the panel registry.

### Tertiary: Check how DialogID connects to sub-panels

The building's DialogID ("AP31", "MX02") is the only identifying field in the XML.
Search for "AP31" as a string and trace how it's used. Does the engine:
- Derive sub-panel names from it (AP31 -> APa3 via some rule)?
- Look it up in a mapping table alongside sub-panel references?
- Store it in a building struct that also has sub-panel pointers?

## Key Constants to Search

| Value | Hex | Context |
|-------|-----|---------|
| 8851 | 0x2293 | "Open sub-panel" handler code |
| 8013 | 0x1F4D | "Return to main" handler code |
| 82 | 0x52 | Research action ID |
| 83 | 0x53 | Spells action ID |
| 85 | 0x55 | Repair route action ID |
| 86 | 0x56 | Tax route action ID |

## Most Likely Answers

### Theory A: Naming Convention (most likely for expansion)
The engine derives: DialogID "MX02" + action type "research" = panel "MX03" (next sequential).
For base game: DialogID "AP31" + action type "research" = panel "APa3" (different convention).

### Theory B: Per-Building Struct Field
Each building object in memory has a `researchPanel` pointer or index set during loading.
The engine populates this when it loads the building definition + available panels.

### Theory C: Panel Registration During CAM Load
When textdata.cam is loaded, panels register themselves. A panel named "APa3" auto-registers
as "the research panel for the building whose main panel is AP31" based on some rule.

## What To Look For In Decompiled Code

Near the 8851 handler, expect something like:
```c
void Handler_OpenSubPanel(Building* building, int actionId) {
    Panel* subPanel = NULL;
    if (actionId == 82)
        subPanel = building->researchPanel;  // <-- WHERE DOES THIS COME FROM?
    else if (actionId == 83)
        subPanel = building->spellPanel;
    if (subPanel)
        DisplayPanel(subPanel);
}
```

OR:
```c
void Handler_OpenSubPanel(Building* building, int actionId) {
    char panelName[8];
    DeriveSubPanelName(building->dialogID, actionId, panelName);
    Panel* panel = FindPanel(panelName);
    DisplayPanel(panel);
}
```

Either way: trace how the target panel is determined.

## If You Find The Answer

If it's a **naming convention**: Document the rule. We just need to name our custom
panels correctly and they'll auto-register.

If it's a **data table**: Find where it lives (in the exe? in a CAM file? in the DUNT
binary?). If it's editable data, we can extend it.

If it's a **building struct field populated at load time**: Find what populates it.
If it scans available panels and matches by name pattern, same as naming convention.
If it's hardcoded per-building, we'd need to understand how expansion buildings get
their panels registered (since they were added post-release).
