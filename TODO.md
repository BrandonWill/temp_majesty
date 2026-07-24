# Majesty Modding Toolkit — Master TODO

See also:
- `TODO-Ghidra.md` — EXE patching / disassembly work (requires Ghidra machine)
- `TODO-GameTests.md` — In-game verification tests (requires loading the game)
- `IceSpell/TODO.md` — IceSpell mod-specific tasks
- `SMNUResearch/FUTURE_TODO.md` — Panel system research + tooling

---

## Active Work (this machine)

### SMNU Panel Compiler
- ✅ `smnu_format.py` — structured parser/writer, byte-perfect roundtrip on all
  169 real panels (base + expansion), 7 unit tests passing (SMNUResearch/)
- ✅ `smnu_compiler.py` — compiles Panel+strings to SMNU+STRT via str_tool.py,
  validates STRT string-index refs at compile time, byte-perfect on 168/169
  real panels (1 known data quirk — GDB4, see below)
- ✅ `cam_writer.build_cam_from_sections()` + `smnu_compiler.build_textdata_cam()`
  — packs compiled SMNU+STRT panels into a fresh quest CAM from scratch.
  Verified byte-perfect end-to-end (real panel -> compile -> pack -> read back).
  9 tests passing (SMNUResearch/test_smnu_compiler.py)
- Deferred: XML front-end for `smnu_compiler.py`. Only worth building if
  modders other than us are authoring panels directly (same rationale as
  gplbcc.exe existing for GPL). We drive the Panel/Widget/Property
  dataclasses from Python directly for now. See SMNUResearch/FUTURE_TODO.md.
- [ ] **Game machine: validate compiler output loads in-game** — the new
  smnu_format.py/smnu_compiler.py work is committed to Python-level
  byte-perfect verification only; nobody has confirmed the engine accepts
  a tooling-generated CAM at load time. See TODO-GameTests.md "SMNU Panel
  Override — Passthrough Test" for the concrete test.
- [ ] Ghidra: confirm GDB4's 2 out-of-range STRT refs are dead/unreachable code
  (see TODO-Ghidra.md Priority 3.5, SMNUResearch/FUTURE_TODO.md "Known Data Quirk")

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
