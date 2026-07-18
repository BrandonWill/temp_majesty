# Quest Map Generator — Research Findings

Documented failure modes, error messages, and binary format discoveries.
This file is the "lessons learned" reference for future sessions.

---

## Failure Mode: Game Freezes on Quest Scan

**Symptom:** Clicking the custom quest icon (purple star) in-game causes the UI to freeze
permanently. No error message, no crash dump. Must kill the game process.

**Cause:** A malformed `.q` file in the `Documents\My Games\MajestyHD\Quests\` folder.
The game scans all quest folders on entering the custom quest UI and chokes on invalid
binary structure.

**Specifically:** The `write_q_file()` function was producing invalid bytes in the
transition zone between Unit Patterns and the Force Pattern section. The metadata blocks,
faction name encodings, and pre-pattern headers were structurally wrong.

**Fix:** Use the minimal splice approach — replace only `[u32 count][entries...]` within
an existing pattern slot. All structural bytes (metadata, faction transitions, Force Pattern)
stay byte-identical to the template.

**Prevention:** Always validate generated .q files by parsing them back before deploying.
If possible, open in RGSEditor first — it will show errors or refuse to load bad files.

---

## Failure Mode: GplDispatcherHandle Error

**Symptom:** Dialog box on quest start: `GplDispatcherHandle error: script $YourName() doesn't exist`

**Cause:** The `<Name>` tag in `.mqxml` specifies the GPL initialization function to call.
If no GPL bytecode is loaded (or the loaded bytecode doesn't contain that function), the
game shows this error.

**Impact:** Cosmetic only. Click OK and the quest continues normally — just without custom
initialization or victory conditions.

**Fix options:**
1. Provide a `.bcd` with a matching function (even an empty one)
2. Use a `<Name>` that exists in the base game's bytecode
3. Accept the popup for test quests with no custom GPL

**SDK doc claim vs reality:** The SDK says "the Quest will still run" without mentioning the
error dialog. In practice, the HD remaster shows an error popup that the original may not have.

---

## Binary Format: .q File Unit Pattern Section

### Structure Between Patterns (confirmed via hex dump + RGSEditor)

```
[Pattern entries end]
[40 bytes: metadata block — u32×10: 0,3,50,50,50,1,1,0,0,0]
[Faction name: 4+4+4 short pattern + full name + \0]
[u32 0][u32 N]  ← N appears to be an "owner count" or pattern reference
[Next pattern header: terrain(4B) + u32(5) + u32(entry_count)]
```

### Structure After LAST Pattern (before Force Pattern)

```
[Pattern entries end]
[40 bytes: metadata block]
[u32 1][Faction name (4+4+4+full\0)]
[5 zero bytes]
[u32 2]NONE  ← Force Pattern section marker
```

The transition after the LAST pattern is DIFFERENT from between-pattern transitions.
It has `[u32 1]` before the faction name instead of the name appearing directly after
metadata. This is what the writer was getting wrong.

### Metadata Block (40 bytes, appears after every pattern's entries)

```
Offset  Value   Meaning (guessed)
0       u32 0   Separator
4       u32 3   Unknown (always 3)
8       u32 50  Resource limit?
12      u32 50  Resource limit?
16      u32 50  Resource limit?
20      u32 1   Unknown flag
24      u32 1   Unknown flag
28      12B 0   Padding
```

---

## Template Mapping: MyQuest/Quest.q

### Unit Patterns (confirmed via RGSEditor)

| Editor Name | Parser Idx | Offset | Entries | Role |
|---|---|---|---|---|
| Goblin Kingdom | 0 | 0x0433 | 8 | Enemy goblin lairs (2 Fortress + 6 Camp) |
| AutoExpanding | 1 | 0x0555 | 25 | Neutral expanding faction |
| Player1 | 2 | 0x07F3 | 1 | Human player's Palace |
| player2_ai | 3 | 0x0856 | 1 | AI opponent's Palace |

### Force Pattern ("MyAI", Multi-Player 2, 7 instances)

| Instance | Unit Pattern | Map Grid Position |
|---|---|---|
| 0 | Player1 | W (2,4) — bottom center |
| 1 | player2_ai | C (2,0) — top center |
| 2 | AutoExpanding | R (2,3) — center-south |
| 3 | Goblin Kingdom | S (3,3) — center-south-east |
| 4 | Goblin Kingdom | Q (1,3) — center-south-west |
| 5 | Goblin Kingdom | unknown | 
| 6 | Goblin Kingdom | unknown |

Goblin Kingdom is reused 4× for enemy distribution across the map.

### Force Pattern Options

- Allowed Players: Single Player, Two Player
- Allowed Map Sizes: Medium (128×128), Large (256×256), Huge (512×512)
- Difficulty Ratings: Money=50, Time=50, Kill All=50

---

## MQXML Format Notes

### Dataset Base Coupling

The `base` attribute in `<Dataset>` MUST match what the .q template was created with.
MyQuest/Quest.q was created with "Expansion 1: Majesty" (= `MajestyExpansion`).
Using `base="Majesty"` with this template causes the game to freeze on quest scan.

### Display Name vs Name

- `<Name>` — GPL init function name. Shows as quest identifier in some contexts.
- `<DisplayName>` — What appears in the quest selection UI.
- Both may be shown depending on context. Use distinct values.

### GUID

Random UUIDs work fine. The game accepts them. RGSEditor shows them as a numeric ID.
No special validation beyond uniqueness.

---

## RGSEditor Observations

- Located at `SDK/RGSeditor.exe`
- Decompiled sections exist in `SDK/RGSeditor/` (potential source for format details)
- Can open and correctly read our generated .q + .mqxml files
- Shows pattern names, unit lists, grid positions, Force Pattern layout
- The "Regenerate ID" button generates new GUIDs for the quest
- Region Pattern editor controls terrain textures, fractal bumpiness, landscape objects
- Force Pattern editor shows the 5×5 map grid with instance positions + Off Map checkbox

---

## What write_q_file() Got Wrong

The writer tried to:
1. Rebuild the entire pattern section from scratch
2. Output `[u32 0][u32 oc]` + `[pattern header]` + `[entries]` + `[metadata]` + `[faction name]`
3. Place the Force Pattern section from template directly after

Problems:
- Faction name encoding didn't match template's 4+4+4+full pattern
- Missing the `[u32 1]` prefix on the final faction name block
- Missing the 5 zero bytes before Force Pattern marker
- Only output 1 pattern instead of preserving all 4 template slots

The minimal splice approach avoids ALL of this by only touching entry data.


---

## SpawnerBlock Field Mapping (CONFIRMED — Ghidra Decompilation July 2026)

Confirmed via decompilation of `DialogEditLairs::DoDataExchange` (FUN_00426430)
and the save handler (FUN_00427490). Assembly at 0x0042754c-0x00427575 shows exact
struct offset writes.

### Binary Layout (read/write order in file)

```
u32 field_00 = Max HP            (DDX control 0x3f2, DDV 0-99999)
u32 field_04 = Base Spawn Rate   (DDX control 0x3f4, DDV 0-999999, in milliseconds)
u32 field_08 = Dispersion        (DDX control 0x3f5, DDV 0-99999, in pixels)
u32 field_0c = (Not implemented) (DDX control 0x466, DDV 0-10)
u32 field_10 = Hit Rate Reduction (DDX control 0x48d, DDV 0-9999, spawner_ver >= 2 only)
```

### UI Tooltips (from RGSEditor binary .rdata)

| Field | Tooltip |
|-------|---------|
| Max HP | "The maximum hit points given to the Lair. If 0, then the default value for the lair is used." |
| Base Spawn Rate | "The base time, in milliseconds that a monster is spawned from the lair. If 0, then the default value for the lair is used." |
| Dispersion | "The dispersion range used to place spawned monsters around the lair, in pixels. If 0, then the default value for the lair is used." |
| (Not implemented) | "Not implemented" |
| Hit Rate Reduction | "Each hit on the Lair will subtract this amount from the spawn rate delay, effectively speeding up the rate at which monsters are spawned. If 0, then the default value for the lair is used." |

### Decompilation Evidence

```asm
; FUN_00427490 — save dialog members to spawner struct (EAX = struct ptr)
0042754c: MOV ECX,[ESI + 0x764]    ; Dispersion (DDX ctrl 0x3f5)
00427552: MOV [EAX + 0x8],ECX      ; → field_08
00427555: MOV ECX,[ESI + 0x768]    ; Max HP (DDX ctrl 0x3f2)
0042755b: MOV [EAX],ECX            ; → field_00
0042755d: MOV ECX,[ESI + 0x76c]    ; Spawn Rate (DDX ctrl 0x3f4)
00427563: MOV [EAX + 0x4],ECX      ; → field_04
00427566: MOV ECX,[ESI + 0x770]    ; Not Implemented (DDX ctrl 0x466)
0042756c: MOV [EAX + 0xc],ECX      ; → field_0c
0042756f: MOV ECX,[ESI + 0x774]    ; Hit Rate Reduction (DDX ctrl 0x48d)
00427575: MOV [EAX + 0x10],ECX     ; → field_10
```

### Per-Lair Override Key Scheme

Spawner blocks inside `UnitPattern.spawners[]` use keys of format:
`entry_index * 1000 + sub_index`

- Entry 0 → keys 0, 1, 2, 3, 4 (sub-indices = difficulty levels)
- Entry 1 → keys 1000, 1001, 1002, ...
- Entry 2 → keys 2000, 2001, 2002, ...

Each key maps one building/lair entry to a specific spawner override at a difficulty level.

### Additional DDX Fields (from DoDataExchange FUN_00426430)

- `param_1 + 0x778-0x784` (ctrl IDs 0x4a6-0x4a9, DDV 0-1000): Monster Artifice overrides (4 slots)
- `param_1 + 0x788-0x794` (ctrl IDs 0x467-0x46a): Slider weight values for 4 monster type slots
- `SpawnerBlock.extra_names[]` (spawner_ver >= 3): "Change what monsters are released when a Lair is destroyed"

---

## Terrain/Region Pattern System

### Structure

- **Region entries**: tag + TeamDefinition whose items are landscape zone refs with weight (spawn_level) and terrain type (field_0c)
- **Force entries**: map each zone ref to actual game resources: (body_tag, name, fractal_ref, texture_ref, height_ref)

### Texture Codes (ref2 in force entries)

| Code Pattern | Meaning |
|---|---|
| `#Ple`, `#Pla-d` | Plains/grass |
| `#Sca-c`, `#Sco` | Scorched/rocky |
| `#Swa-d` | Swamp |
| `#All` | Dirt/alluvial |
| `#Ara-c`, `#Ari`, `#Arr` | Arid/desert |
| `xSno`, `xSna-c` | Snow |
| `xfor` | Forest |
| `xbog` | Bog |
| `xpla` | Plain (expansion) |
| `xroc` | Rocky (expansion) |
| `xswa` | Swamp (expansion) |
| `xmud` | Mud |

### Height Profiles (ref3 in force entries)

| Code | Terrain Shape |
|---|---|
| `Bump`, `Roll`, `Rola` | Gentle hills |
| `Subt`, `Smal`, `Slow` | Very gentle |
| `Stee`, `Moun` | Mountainous |
| `FS01` | Flat (swamp/snow) |
| `xhil`, `xlig`, `xsli`, `xfla`, `xrou` | Expansion height profiles |
