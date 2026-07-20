# SMNU Navigation Test - Instructions

## What We're Testing

We discovered that building panel buttons use **action codes** (not panel indices).
The "Return to Main" button uses action ID=9 with handler code 8013, which is a
hardcoded "go back to parent building" action.

HOWEVER, we still want to test what happens when we change the action ID from 9 to
another value — does it fire that action instead? This tells us whether the action
system is flexible enough to chain panels.

## Key Context

- **Action ID 9 + Code 8013** = "Return to building main" (confirmed used universally)
- **Action ID 82 + Code 8851** = "Open research sub-panel" (used in main panels)
- **Action ID 83 + Code 8009** = "Open spell list" (used in temples/guilds)

The test changes the action ID from 9 to other values while keeping code 8013.

## Setup

1. Back up your game's `DataMX/mx_textdata.cam`
2. Copy one of the test files to replace it (rename to `mx_textdata.cam`)

## Test Files

| File | Change | What it might do |
|------|--------|-----------------|
| `mx_textdata_test_A_target5.cam` | Action ID: 9->5 | Unknown — 5 is "navigate" in System B |
| `mx_textdata_test_C_target11.cam` | Action ID: 9->11 | Unknown — not a recognized action |

## Test Procedure

1. Start game in **Expansion mode** (quest with Magic Bazaar)
2. Build a **Magic Bazaar**
3. Click Magic Bazaar -> Click "Research" 
4. Click the **"Return to Main"** button (bottom-left)
5. Note: Does it go back to Bazaar main? Go somewhere else? Crash? Do nothing?

## Interpreting Results

| Result | Meaning |
|--------|---------|
| Still returns to Bazaar main | Code 8013 completely controls behavior, action ID is ignored |
| Goes to a different panel | Action ID matters! We can redirect navigation |
| Button does nothing | Action ID 5/11 is not valid for code 8013 |
| Game crashes | Engine can't handle invalid action IDs |
| Opens spell list or research | Action ID changed the target behavior |

## What To Try Next (If Tests Are Inconclusive)

1. **Change BOTH action ID AND code**: Try setting to (82, 8851) = "Open research"
   - At offset 0x6F60: change to `52 00 00 00` (action=82)
   - At offset 0x6F68: change to `93 22 00 00` (code=8851)
   
2. **Inject a System B button**: The hero panel uses a 116-byte button format
   with literal panel indices. Try appending one to this panel before the terminator.
   (This would require inserting bytes and adjusting the CAM structure.)

3. **Use Ghidra MCP**: Disassemble the game exe to find how code 8013 handles
   the action ID parameter. Does it use it? Ignore it? Index into a table?

## Restoring Original

Copy `mx_textdata_ORIGINAL.cam` back to `DataMX/mx_textdata.cam`.

## File Offset Reference

- Offset: `0x6F60` — the action ID value (4 bytes LE)
- Offset: `0x6F64` — the marker byte (always 6)
- Offset: `0x6F68` — the handler code (4 bytes LE, currently 8013 = `0D 1F 00 00`)
- Original bytes at 0x6F60: `09 00 00 00 06 00 00 00 4D 1F 00 00`

## Setup

1. Back up your game's `DataMX/mx_textdata.cam`
2. Copy one of the test files to replace it (rename to `mx_textdata.cam`):
   - **Test A:** `mx_textdata_test_A_target5.cam` (target changed to 5)
   - **Test C:** `mx_textdata_test_C_target11.cam` (target changed to 11)

## Test Procedure

1. Start the game in **Expansion mode** (a quest where Magic Bazaar is buildable)
2. Build a **Magic Bazaar**
3. Click on the Magic Bazaar to open its main panel
4. Click **"Research"** to open the research panel (MX03)
5. Click the **"Return to Main"** button (bottom-left, back arrow icon)
6. Observe: where does it go?

## Expected Results Matrix

| Test | Target Value | If literal expansion index | If special code system |
|------|-------------|---------------------------|----------------------|
| Original | 9 | Would go to MX05 (Mausoleum) | Goes to Bazaar main (confirmed) |
| Test A | 5 | Would go to MX01 (Hall of Champions) | Unknown |
| Test C | 11 | Would go to MX07 (Sorcerer spells) | Unknown |

### Scenario 1: Tests navigate to the listed panels
- Target IS a literal local index
- We just need to figure out why original=9 goes to Bazaar main
  (maybe MX02's Dialog maps to expansion index 9 via some offset)
- Multi-page navigation is confirmed possible

### Scenario 2: Tests still go back to Bazaar main
- Target value 9 is a special code meaning "return to parent"
- Changing it has no effect (engine ignores the value for "return" buttons)
- We'd need to find a different button type that DOES use literal targets

### Scenario 3: Tests crash or button does nothing
- Target value matters but our mapping is wrong
- Need to investigate the correct indexing scheme
- Try values like 134+11=145 (base_count + expansion_index as global)

### Scenario 4: Game loads but button is visually broken
- Partial success - the engine tried to load a panel but something's off
- Tells us the system IS data-driven but we have a configuration issue

## Additional Tests to Try If Scenario 2 or 3

If the simple value change doesn't work, try these additional target values
(edit the hex directly at file offset 0x6F60):

| Value (decimal) | Hex (LE) | Rationale |
|-----------------|----------|-----------|
| 6 | 06 00 00 00 | MX02 local index (Magic Bazaar main) |
| 145 | 91 00 00 00 | 134 + 11 (base_count + MX07 expansion index) |
| 140 | 8C 00 00 00 | 134 + 6 (base_count + MX02 expansion index) |
| 0 | 00 00 00 00 | Might mean "stay on current panel" or "first panel" |

## Restoring Original

Copy `mx_textdata_ORIGINAL.cam` back to `DataMX/mx_textdata.cam`.

## File Offset Reference

- Offset to modify: `0x6F60` (decimal 28512) in mx_textdata.cam
- This is the u32 (4 bytes, little-endian) target value
- Original bytes at that offset: `09 00 00 00`

## Quick Hex Edit

If you want to try different values without regenerating:
```
Open mx_textdata.cam in a hex editor
Go to offset 0x6F60
Change the 4 bytes there (little-endian u32)
Save and test in game
```

## Additional Test File

### Test D: `mx_textdata_test_D_action82_code8851.cam`

Changes BOTH the action ID and handler code:
- Action ID: 9 -> 82 (same as "Open Research" buttons in main panels)
- Handler Code: 8013 -> 8851 (the "open sub-panel" handler)

**Expected behavior:** If this works, clicking "Return" in the research panel
would try to open a research sub-panel (possibly re-opening itself, or going
to a different research panel). This would confirm that we can trigger sub-panel
navigation from within a sub-panel.

**If it crashes:** The engine might not support opening a sub-panel from within
a sub-panel (no nesting allowed).

**If it does nothing:** The "open research" action might be context-dependent
and only valid from a building main panel.

**Hex changes:**
- Offset 0x6F60: `52 00 00 00` (82 in LE)
- Offset 0x6F68: `93 22 00 00` (8851 in LE)
