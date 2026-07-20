# Where Is the Building-to-Panel Mapping? (Exhaustive Analysis)

## Definitively Ruled Out

### 1. SMNU Button Data
The Research button (action 82 + code 8851) is **byte-for-byte identical** across all
base game buildings: `258=70, 266=84`. No building-specific target is encoded in the button.
Expansion buttons are even simpler — no 258/266 block at all.

### 2. SMNU Panel Headers
Compared main panels vs research sub-panels vs simple panels.
No "panel type" flag or "I am a research panel" marker exists in the header.
The only differences are cosmetic (background TILE index, image set name).

### 3. Building XML Definition
The `<Description>` for buildings contains no panel reference field.
Only `<DialogID>` exists, which points to the MAIN panel. No `<ResearchPanel>`,
no `<SubPanels>`, nothing.

### 4. DUNT Binary Entry
Searched every building's DUNT entry (in unittype.cam) for embedded panel name strings.
**Result: NO research panel names (APa2, APa3, MX03, etc.) found anywhere in DUNT data.**

The DUNT entry contains:
```
[flags/info] [engine fields] ... [DialogID string] [u32 cost] [UpgradeTo ID or null]
[UpgradeFrom ID or null] [multiplier float] [income fields] [MaxHP] [SightRange] [flags]
```

No panel reference of any kind.

## Where It MUST Be

The mapping exists only at runtime in the engine. Possible mechanisms:

### Theory A: Naming Convention (MOST LIKELY)
The engine derives the research panel name from the building's DialogID.

Evidence for this being the strongest theory:
- Base game: AP31 -> APa3. Pattern: "AP" + first digit + second char shifted?
  - AP02 -> APa2? But AP02 shares APa2 with AP26 (Library)...
  - Actually maybe: AP02's research panel is NOT APa2 — we assumed it but never verified
- Expansion: MX02 -> MX03 (sequential +1)

The expansion pattern (sequential) is the simplest and cleanest. The base game might
use a different convention or a registration mechanism.

### Theory B: Panel Self-Registration
When textdata.cam is loaded, each panel "registers" itself with the engine.
The engine might look at the panel's SMNU content (specifically the "Return" button
with target=9) to determine "this panel is a sub-panel that returns to some building."
Then it uses the panel's position/name/content to associate it with the right building.

### Theory C: Hardcoded Table in Engine
A compiled lookup table. Unlikely because the expansion added new buildings with
new panels (Magic Bazaar, Sorcerer's Abode, Outpost) without recompiling the base game exe.
The HD remaster exe would need to include all expansion panel mappings.

## Test Strategy

The `PanelTest_Quest` uses sequential naming (TS01 main -> TS02 research) matching
the expansion convention. If this doesn't work, try:
1. Rename to match base game conventions (try several)
2. Use Ghidra to find the actual resolution code

## Raw Data: DUNT Structure Around DialogID

```
Building        DialogID  Offset  After DialogID (hex)
Blacksmith      AP02      340     f401000041424332 (cost=500, UpgTo=ABC2)
Guardhouse      AP17      340     5802000041424532 (cost=600, UpgTo=ABE2)
Inn             AP23      325     9001000000000000 (cost=400, no upgrade)
Library         AP26      334     5802000041424732 (cost=600, UpgTo=ABG2)
Marketplace     AP31      342     dc05000041424832 (cost=1500, UpgTo=ABH2)
Palace          AP39      332     0000000041424a32 (cost=0, UpgTo=ABJ2)
Trading Post    AP51      343     5802000000000000 (cost=600, no upgrade)
Magic Bazaar    MX02      342     7805000041426c32 (cost=1400, UpgTo=ABl2)
Sorcerer        MX06      348     d007000041427132 (cost=2000, UpgTo=ABq2)
```

No hidden fields between known values. The DUNT format is compact with no room
for unaccounted panel reference data.
