# Panel Navigation Test Quest

Tests whether the engine resolves sub-panels by sequential naming convention.

## What's Being Tested

A new building "Test Shop" (ID: ABz1) with DialogID="TS01" is defined.
The mod loads a textdata CAM with panels:
- **TS01** — main panel (cloned from Magic Bazaar MX02, has a Research button)
- **TS02** — research sub-panel (cloned from Magic Bazaar MX03, has 6 research items)

The Research button on TS01 fires action 82 + code 8851 (same as every building).
If the engine finds TS02 as the research panel for TS01, **naming convention is confirmed.**

## How To Test

1. Copy this folder to your Majesty Gold HD `Quests/` directory
2. Start the game, select this quest ("Panel Navigation Test")
3. Build the **Test Shop** (looks like a Magic Bazaar, costs 500g)
4. Click on it — you should see the main panel (TS01 = MX02 clone)
5. Click the **Research** button

## Expected Results

| Result | Meaning |
|--------|---------|
| Research panel opens (shows Magic Bazaar items) | **SUCCESS: Sequential naming convention confirmed (TS01+1=TS02)** |
| Nothing happens / button greyed out | Engine couldn't find a research panel for this building |
| Game crashes | The panel naming doesn't match engine expectations |
| Opens a different building's research | Engine confused about building identity |

## If Naming Convention Fails

Try renaming the panels to test other conventions. Rebuild with:
- "TS01" + "TS01a" (base game APa-prefix style)
- "TS01" + "TSa1" (AP31 -> APa3 style)
- Just try the MX naming: rename building DialogID to "MX30" and panels to "MX30"/"MX31"

## Files

| File | Purpose |
|------|---------|
| `Quest.mqxml` | Quest definition, loads the test building + panels |
| `Data/PanelTest_Buildings.xml` | Test Shop building definition (DialogID=TS01) |
| `Data/Quest_textdata.cam` | SMNU+STRT for panels TS01 and TS02 |
| `build_test_textdata.py` | Script that builds Quest_textdata.cam from MX02/MX03 templates |

## Building Definition

```xml
<Description type="Unit" subType="Building" ID="ABz1" Name="TestShop1" Description="Test Shop">
    <DialogID value="TS01"/>
    <ImageIDBase value="ABl1"/>  <!-- Reuses Magic Bazaar sprite -->
    <Cost value="500"/>
</Description>
```

## Notes

- Reuses Magic Bazaar sprite (ABl1) so no custom graphics needed
- The SMNU/STRT data is byte-for-byte identical to MX02/MX03 — only the CAM entry names changed
- If this works, multi-page panels are just a matter of adding more panels (TS03, TS04, etc.)
  with navigation buttons between them
