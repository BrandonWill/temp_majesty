# Majesty Modding Toolkit — Master TODO

Based on findings from Workshop mod analysis (10 mods/quests) + existing work.
Focus: comprehensive knowledge of engine capabilities for quest/mod creation.

---

## Quest Map Generator Enhancements

### Multi-Kingdom Support
- [ ] Add `slot_configs` parameter to `create_quest()` for >2 player kingdoms
- [ ] Support 7Kings-style FFA (up to 7 active player slots + 1 monster slot)
- [ ] Each slot gets: name, starting_gold, active flag, spawner_indices

### Landscape Objects (Trees/Rocks)
- [ ] Document which fractal refs (`xFel`, `xFer`, `xBBC`, etc.) produce which vegetation
- [ ] Test terrain presets with different fractal refs to get trees (current `grass` preset is bare)
- [ ] Consider adding "density" parameter to presets (bare, sparse, forested)

---

## GPL Knowledge Base

### Undocumented Engine Primitives (from Workshop analysis)
- [ ] Document all discovered primitives in a GPL reference file:
  - `$DoAssembly(building)` — Call to Arms
  - `$DoRageOfKrolm(building)` — temple ability
  - `$AdvanceLevel(unit, level)` — instant level-up
  - `$RandomEdgeCoord(edge)` — random map edge position
  - `$turnonSpeedTrail(agent, N)` — speed visual effect
  - `$MagicalAdjustAttribute(agent, attrib, amount)` — reversible stat change
  - `$SpecifyName(agent, "text_id")` — per-instance naming
  - `$SetPlayerTeamNumber(palace, teamNum)` — faction alliance
  - `$NewTeamNumber()` — allocate team
  - `$Setup_Quest_Music(root)` — soundtrack
  - `$createeffector(agent, "name", 0, integer)` — numeric debug channel
  - `$MiniMapAnimation(agent, "event_beacon")` — minimap ping
  - `$SetDrawEffects(agent, "red", 0)` — tint agent
  - `$make_Monster_Hunter(unit)` — convert to hunter
  - `$IsRunning(thread)` / `$KillThread(thread)` / `$SetThreadInterval(attr, ms)`
  - `$Freeze_Unit(target)` — pause actions
  - `$RandomCoord(anchor, radius)` — random position around anchor

### GPL Gotchas Document
- [ ] Extract key warnings from HTML gotchas into steering/reference:
  - Thread silent abort on undeclared attribute
  - $NewThread is recurring (not one-shot)
  - $RunThreadOnce cannot re-arm from inside
  - Heavy functions (~300 lines) never fire as thread targets
  - $RandomNumber frozen within a tick
  - foreach exit with return/break crashes
  - Building spellcasting corrupts heap
  - Gold capped at 2,000,000 from script side
  - Quest overrides don't reach stored function pointers
  - MOD vs QUEST binding differences (attribute writes via derived handles fail in mods)

### GPL Patterns Reference
- [ ] Document EventAgent pattern (recurring events)
- [ ] Document spell/buff implementation pattern (Begin/End with effectors)
- [ ] Document AI kingdom thread architecture (StandAloneAI model)
- [ ] Document debugging patterns (gold channel, floating numbers, minimap beacons)

---

## XML Schema Knowledge

### Action/Spell Definitions
- [ ] Document undiscovered attributes:
  - `<SpellRank value="N"/>` — REQUIRED for AI to cast (higher = preferred)
  - `<ValidationScript value="fn"/>` — GPL gate function
  - `<CharacterLevel value="N"/>` — level-gated spell acquisition
  - `<EffectorDuration value="N"/>` — effector lifetime (separate from timeout)
  - Multiple `<SpellType>` tags can stack (Attack + CombatUtility)
  - `<SpellType value="4"/>` — numeric encoding for self-buff
  - `<Rate min="0" max="800"/>` — action timing

### Overlay Definitions
- [ ] Document overlay schema features:
  - `<Info value="Static"/>` — non-animated
  - `<AttachmentPointID value="2"/>` — bone attachment
  - `<Menu value="11"/>` — invisible (effector icon)
  - `<Script GPLFunction="*_End"/>` — expiry callback
  - `<Flags value="TransparentToMouse"/>` — click-through
  - `<StackPriority value="N"/>` — layering order

### Building Definitions
- [ ] Document building schema features from Workshop mods:
  - `<UpgradeTo>` chain
  - `<Multiplier>` cost escalation
  - `<IncomeType>` (2=revenue, 3=maintenance)
  - `<Produces><Unit ID="..."/></Produces>` — recruitable units
  - `<Flags value="NumberedName"/>` — auto "#1", "#2" suffix

### Research/Items/Services System (from Majestic Majesty Revived)
- [ ] Document the "invisible character as UI slot" pattern:
  - `subType="Character"` + `Menu value="8"` = research/service slot
  - `<RecruitDelay>` = research time
  - birthScript = on-purchase callback
  - Can create item/equipment/potion systems entirely through XML + GPL

---

## MQXML/MMXML Capabilities

### Newly Discovered Tags
- [ ] Document `<GPLSource>GPL</GPLSource>` — source directory for debugger
- [ ] Document `<CAM>` tag — loads raw CAM archives (sound, potentially sprites)
- [ ] Document multiple `<Mod>` entries in one .mmxml (15 variants in StandAloneAI)
- [ ] Document dual-dataset mods (one entry for Majesty, one for MajestyExpansion)
- [ ] Document `base="Any"` risks (misbinding attributes against wrong ruleset)

### Mod Architecture Patterns
- [ ] Document palace-prototype-as-entry-point (StandAloneAI pattern)
- [ ] Document expression-only BCD as tuning mod
- [ ] Document mod load order and same-name override behavior

---

## Debugging & Testing

### Engine Debugging
- [ ] Create a GPL debugging cheat-sheet:
  - Gold channel: `$AdjustPlayerData(palace, "gold", value)` for code-reached markers
  - Numeric display: `$createeffector(agent, "got_gold", 0, value)` floats a number
  - Minimap ping: `$MiniMapAnimation(agent, "event_beacon")`
  - Visual tint: `$SetDrawEffects(agent, "red", 0)`
  - Persistent marker: `$createeffector(agent, "charm_icon", 1, "infinite")`
- [ ] Document crash dump analysis (majestyhd_crash_*.mdmp, same EIP = deterministic)
- [ ] Note: Engine primitives are searchable as plaintext in MajestyHD.exe

### Compiler Gotchas
- [ ] Document Gplbcc.exe returns exit code 0 even on failure (check file timestamp)
- [ ] Document stale build trap (old .bcd loads fine but doesn't have your changes)

---

## Steering File Updates

- [ ] Integrate key GPL gotchas into `quest-and-mod-creation.md`
- [ ] Add XML schema quick-reference (actions, overlays, buildings) to steering
- [ ] Add undocumented primitives list to steering
- [ ] Consider a dedicated `gpl-reference.md` steering file (manual inclusion)

---

## Lower Priority / Future Work

### constants.rgs Editor
- [ ] Implement RGCB format writer (create custom landscape patterns)
- [ ] Map sprite group IDs (IG08, PG10, etc.) to actual visual objects
- [ ] Enable custom tree/bush/rock density without RGSEditor

### Workshop Integration
- [ ] `--workshop` flag for quest_map_generator to create Workshop-ready packages
- [ ] Generate .mswproj files programmatically
- [ ] Support multiple mods in one .mmxml generation

### Engine Exploration
- [ ] Scan MajestyHD.exe for additional undocumented GPL primitives
- [ ] Verify `$RandomCoord(anchor, -1)` radius behavior (entire map?)
- [ ] Test if `<CAM>` tag works for sprite data (only proven for audio so far)
- [ ] Determine exact game tick → real time relationship (72,000ms = 1 in-game day)
