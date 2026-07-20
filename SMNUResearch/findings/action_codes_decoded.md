# SMNU Action System — Complete Decode

## Critical Discovery: Two Different Button Systems

### System A: Action Buttons (buildings)
Pattern: `[1024, 5, ACTION_ID, 6, HANDLER_CODE]`

These do NOT navigate to panel indices. They fire engine-level actions.
The "target" field is an **action ID** that maps to built-in behavior.

### System B: Panel Navigation (hero/special)
Pattern: `[1024, 3, 8, 5, PANEL_INDEX, 6, CODE, 258, ALT1, 266, ALT2, -1]`

These DO use literal panel indices. Only found in hero sub-panels (AP21, AP22, AP78).

## Action ID + Handler Code Lookup (System A)

Compiled from ALL panels in both base game and expansion:

| Action ID | Handler Code | Meaning | Found In |
|-----------|-------------|---------|----------|
| 9 | 8013 | **Return to building main panel** | All sub-panels (research, visitors, etc.) |
| 9 | 8004 | **Return to parent** (variant - hero panels) | AP21, AP22, AP78, AP94, AP95, MX01 |
| 63 | 8029 | **Zoom to building on map** | Almost every building panel |
| 63 | 8028 | **Zoom** (variant - for non-buildings?) | AP20, AP74, AP90, AP97, AP98, APa6, etc. |
| 88 | 8002 | **Destroy building** | Most building main panels |
| 85 | 8007 | **Toggle repair route** | Building panels with repair |
| 86 | 8021 | **Toggle tax route** | Building panels with taxes |
| 82 | 8851 | **Open research sub-panel** | Buildings with research |
| 83 | 8009 | **Open spell list** | Temple/guild panels |
| 83 | 8851 | **Open spell list** (variant) | MX06 Sorcerer |
| 75 | 8009 | **Recruit** | AP24 (Temple to Krolm) |
| 77 | 8200 | **Market Day action** | AP31 (Marketplace) |
| 77 | 8666 | **Special ability** | AP18 |
| 77 | 8834 | **Gambling action** | APb8 |
| 67 | 8876 | **Close Embassy** | MX22 |
| 79 | 8875 | **Open Embassy** | MX22 |
| 76 | 8004 | **Show dead heroes** | MX04, AP15 |
| 66 | 8851 | **Hall of Champions action** | MX00 |
| 27 | 9005 | **Minimap/overview** | APMK |
| 27 | 9001 | **Reward flags** | AP49 |
| 69 | 8009 | **Open visitors** (variant) | AP48 |
| 79 | 8088 | **Ring/zoom** | AP88 |
| 86 | 8995 | **Special tax/zoom** | AP46, AP80 |

## Key Insight

**Action ID 9 = "Return to parent"** is hardcoded engine behavior.
Changing its value to something else won't navigate to a different panel — 
it will either do nothing, crash, or trigger a completely different action.

The hero panel's System B (with 258/266 alternates) is the ONLY mechanism
that uses literal panel indices for navigation.

## Implications for Multi-Page Research

### The Bad News
Building sub-panels use System A (action codes). You can't simply change
the "Return to Main" button's target to navigate to another panel — 
it's not a panel index, it's action ID 9 meaning "go back."

### The Good News
The hero panel System B (literal panel indices) DOES exist in the codebase.
The question is: **can System B buttons be placed in a building sub-panel?**

If yes: add a System B navigation button to a research panel that points
to another panel. The engine would need to support System B in building 
context, which it might since both systems exist in the same SMNU format.

### Experimental Approach
Instead of patching the existing Return button (System A), try:
1. **Inject a System B button** into the MX03 panel (append 116 bytes 
   of a hero-style nav button before the double-terminator)
2. Set its target to a different panel index
3. See if the engine renders and handles it in building context

### Alternative: Repurpose action code 82 (open research)
Action 82 with code 8851 opens the research sub-panel from the main panel.
If we could make a CUSTOM action code that opens a specific panel,
we might be able to create a "More Items" action.

## Updated Test Plan

The POC test files (changing target from 9 to 5/11) will likely:
- Either still return to Bazaar main (engine treats any value with code 8013 as "return")
- Or fire action 5/11 which might be "Spell Window" or "Items Window" type actions

This is still worth testing because it tells us whether the action ID
matters at all for code 8013 behavior.

## Complete Action Handler Code Ranges

| Code Range | Category |
|-----------|----------|
| 8000-8029 | Standard building UI actions |
| 8088 | Special ring/zoom |
| 8200 | Market Day |
| 8666 | Special ability |
| 8834 | Gambling |
| 8851 | Open sub-panel (research/spells/visitors) |
| 8875-8876 | Embassy open/close |
| 8995 | Special tax/zoom variant |
| 9001-9005 | Reward/minimap system |
| 4002-4006 | Hero panel sub-page navigation (System B only) |
| 5061-5066 | Research purchase actions |
| 5500-5505 | Research progress display |
| 6061-6066 | Cost label display |
