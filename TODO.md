# Majesty Modding Toolkit — Master TODO

See also:
- `TODO-Ghidra.md` — EXE patching / disassembly work (requires Ghidra machine)
- `IceSpell/TODO.md` — IceSpell mod-specific tasks
- `SMNUResearch/FUTURE_TODO.md` — Panel system research + tooling

---

## Active Work

### IceSpell — Compile and Test (game machine)
- [ ] Run `cmd /c MakeGPL.bat` in `IceSpell_Quest/` to compile GPL
- [ ] Test in-game: projectile travel, freeze overlay, thaw burst, cold stacks
- [ ] Iterate on sprite art if too subtle at game zoom level

### SMNU Panel Override via Quest CAM
- [ ] **TEST:** Deploy PanelTest_Quest with passthrough CAM (byte-identical MX03)
  - If works: confirms override mechanism is fine, our SMNU generation is the bug
  - If crashes: still a CAM-level or scope issue
- [ ] Build SMNU compiler (`smnu_compiler.py`) that produces valid panel binary
  - Must handle the custom constructor formats for widget types 0, 1, 2, 5, 6, 9
  - Validate against real game panels by roundtrip comparison

### Landscape Objects (Trees/Rocks)
- [ ] Document which fractal refs (`xFel`, `xFer`, `xBBC`, etc.) produce which vegetation
- [ ] Test terrain presets with different fractal refs to get trees (current `grass` preset is bare)
- [ ] Consider adding "density" parameter to presets (bare, sparse, forested)

---

## Needs In-Game Verification

### Particle Systems
- [ ] Does the 4th value in BirthColor/MidlifeColor/DeathColor = alpha?
- [ ] Do custom particle systems load from quest CAMs via `<Descriptions>`?
- [ ] What do AttachmentPointID values correspond to visually?

### constants.rgs Modifiability
- [ ] Can quests/mods load custom constants.rgs files?
  - MQXML has `<Constants>` in the Unload section — implies load/unload is possible
  - Need to test: reference a modified constants.rgs in MQXML, see if game loads it

### Engine Timing
- [ ] Game tick → real time ratio (test via GPL $DebugOut logging)
- [ ] `$RandomCoord(anchor, -1)` radius behavior (log coords, measure spread)

---

## Lower Priority / Future

### Workshop Integration
- [ ] `--workshop` flag for quest_map_generator to create Workshop-ready packages
- [ ] Generate .mswproj files programmatically

---

## Completed

- ✅ Quest Map Generator: parse 37/37, roundtrip, create API, spawners, terrain, force layout, multi-kingdom, CLI
- ✅ GPL Knowledge Base: primitives, gotchas, patterns, debugging (in steering files)
- ✅ XML Schema: actions, overlays, buildings, research, particle systems (in CAM_MODDING_GUIDE + steering)
- ✅ MQXML/MMXML capabilities documented (steering file)
- ✅ TILE v3 RLE fix: exclusive-end X encoding (sprite_extractor + sprite_injector)
- ✅ CAM override mechanism: all resource types override via quest CAM (last-loaded wins)
- ✅ UUID generation: uuid.uuid4() is correct
- ✅ `<CAM>` tag works for sprites (IceSpell_Quest confirmed)
- ✅ Ice Barrage refactor: projectile + animated sprites + compact CAM (15KB)
- ✅ Expansion CAM support in sprite_extractor (3-section files)
