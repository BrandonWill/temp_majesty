# Majesty Modding Toolkit — Master TODO

See also:
- `TODO-Ghidra.md` — EXE patching / disassembly work (requires Ghidra machine)
- `TODO-GameTests.md` — In-game verification tests (requires loading the game)
- `IceSpell/TODO.md` — IceSpell mod-specific tasks
- `SMNUResearch/FUTURE_TODO.md` — Panel system research + tooling

---

## Active Work (this machine)

### SMNU Panel Compiler
- [ ] Build `smnu_compiler.py` that produces valid panel binary
  - Must handle the custom constructor formats for widget types 0, 1, 2, 5, 6, 9
  - Validate against real game panels by roundtrip comparison

### Landscape Objects (Trees/Rocks)
- [ ] Document which fractal refs (`xFel`, `xFer`, `xBBC`, etc.) produce which vegetation
- [ ] Consider adding "density" parameter to presets (bare, sparse, forested)

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
