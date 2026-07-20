# Panel Navigation Test Quest — Multi-Page Router

Tests whether the engine supports multi-page research panel navigation
using MX03 override + custom sub-panels with navigation buttons.

## Architecture

```
EXE hardcodes: Magic Bazaar (MX02) → opens "MX03" for research
Our override:  MX03 = Router panel with 2 nav buttons
               PT01 = Potions page (clone of original MX03 research)
               PT02 = Equipment page (modified item names)
```

## What's Being Tested

1. **MX03 Override** — Does the quest's CAM file override the expansion's MX03 panel?
2. **Custom Nav Buttons** — Can buttons with action type 5 navigate to custom panels?
3. **Panel Index Discovery** — What indices do PT01/PT02 get assigned?

## Panel Structure

| Panel | Role | Nav Buttons |
|-------|------|-------------|
| MX03 (router) | Simple menu with 2 choices | "Potions" → PT01, "Equipment" → PT02, "Return to Main" |
| PT01 (potions) | Clone of original MX03 research items | Original research items + "← Back" → MX03 |
| PT02 (equipment) | Modified MX03 with equipment names | Modified items + "← Back" → MX03 |

## How To Test

1. Copy this folder to your Majesty Gold HD `Quests/` directory
2. Start the game in **expansion mode**, select "Panel Navigation Test"
3. Build the **Magic Bazaar** (standard expansion building)
4. Click on the Magic Bazaar → main panel appears
5. Click the **Research** button

## Expected Results

### Phase 1: MX03 Override Test

| Result | Meaning |
|--------|---------|
| Router panel appears (title: "MAGIC BAZAAR - RESEARCH") | **SUCCESS: Override works!** |
| Original research panel appears (Tonic of Speed, etc.) | Override NOT loading — CAM load order issue |
| Nothing / crash | Panel format error in our custom SMNU |

### Phase 2: Navigation Button Test (if Phase 1 passes)

| Result | Meaning |
|--------|---------|
| Clicking "Potions" opens PT01 with research items | **Nav buttons work! Panel index is correct.** |
| Clicking "Potions" does nothing | Wrong panel index — try different values |
| Clicking "Potions" crashes | Action code incompatible with building context |
| Clicking "Potions" opens wrong panel | Index mapping revealed — adjust accordingly |

### Phase 3: Back Button Test (if Phase 2 passes)

| Result | Meaning |
|--------|---------|
| "← Back" returns to router | **Full navigation loop confirmed!** |
| "← Back" returns to bazaar main panel | Back button uses "return to parent" semantics |
| "← Back" does nothing | Index for MX03 router is wrong |

## Panel Index Guesses (adjust if needed)

The expansion `mx_textdata.cam` has **35 SMNU panels** (indices 0-34).
MX03 is at index 7 in that file.

Current assumptions in `build_test_textdata.py`:
```python
PANEL_INDEX_MX03_ROUTER = 7   # Override replaces expansion's MX03 slot
PANEL_INDEX_PT01 = 35          # First new panel appended by quest CAM
PANEL_INDEX_PT02 = 36          # Second new panel appended by quest CAM
```

**If nav buttons go to wrong panels, try:**
- All indices shifted: MX03=35, PT01=36, PT02=37
- Base game panels counted too: add ~45 to all indices
- Relative within quest CAM: PT01=1, PT02=2 (0-based within our file)

## Rebuilding

```bash
cd PanelTest_Quest
python build_test_textdata.py
```

This regenerates `Data/Quest_textdata.cam` from the expansion's MX03 template.

## Files

| File | Purpose |
|------|---------|
| `Quest.mqxml` | Quest definition — expansion mode, loads only the textdata CAM |
| `Quest.q` | Map template (reused from existing quest) |
| `Quest.rgs` | Terrain data (reused) |
| `Data/Quest_textdata.cam` | SMNU+STRT for 3 panels: MX03, PT01, PT02 |
| `build_test_textdata.py` | Script that builds Quest_textdata.cam |

## Technical Details

### Nav Button Widget Pattern (100 bytes)
```
[0, 2, X, Y, W, H, tooltip_str, label_str, 10, 2, 12, "INTG", 13, TILE_idx,
 3, 2, 3, 1024, 5, TARGET_INDEX, 6, ACTION_CODE, 18, "fn11", -1]
```

- Action type 5 with target=9, code=8013 → "Return to Main" (proven working)
- Action type 5 with target=N, code=8013 → Navigate to panel index N (hypothesis)

### STRT Format (decoded)
```
[u16 count][u16 0x0200][count * u32 offsets][entries: u32_index + ASCII\0]
```

### Key Unknowns
- Whether action code 8013 works for forward-navigation (not just "return")
- Whether panel indices from a quest CAM get separate numbering or merged global
- Whether the engine renders our custom SMNU correctly in building context
