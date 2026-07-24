# Majesty Modding — In-Game Test TODO

Tasks that require loading the game to verify. Run on the game machine.

**When you complete a test, record results in:**

| What was tested | Update this file |
|-----------------|-----------------|
| IceSpell visual/gameplay | `IceSpell_Quest/VISUAL_VERIFICATION.md` |
| Panel override / SMNU | `SMNUResearch/FUTURE_TODO.md` (mark confirmed/failed) |
| Particle system behavior | `CAM_MODDING_GUIDE.md` (particle section) |
| Terrain/landscape visuals | `QuestMapGenerator/FINDINGS.md` |
| Quest CAM loading behavior | `CAM_MODDING_GUIDE.md` (Quest CAM Loading section) |
| Engine timing / GPL logging | `CAM_MODDING_GUIDE.md` (GPL section) |
| General progress | `TODO.md` (root) + mark done here |

---

## IceSpell Quest — Full Test

**Prerequisite:** Run `cmd /c MakeGPL.bat` in `IceSpell_Quest/` first.

- [ ] Projectile travels from Ice Elemental to target (visible 20×20 blue bolt)
- [ ] Cold stacks accumulate (5 hits to freeze)
- [ ] Freeze overlay appears (48×64 animated ice shimmer on grey unit)
- [ ] DOT ticks during freeze (5 damage every 2 seconds)
- [ ] Thaw burst plays after 10 seconds (32×32 shard explosion)
- [ ] Immunity window prevents re-freeze for 5 seconds
- [ ] No crash on cast, freeze, or thaw

---

## SMNU Panel Override — Passthrough Test

- [ ] Deploy PanelTest_Quest with byte-identical MX03 passthrough CAM
  - If no crash: override mechanism works, our custom SMNU is the bug
  - If crash: still a CAM-level or scope issue
- [ ] STRT-only override test: change "Market Day" text via quest CAM
- [ ] Original MX03 SMNU + modified same-count STRT
- [ ] Minimally modified MX03 SMNU (one cloned widget)

---

## Particle Systems

- [ ] Does the 4th color value = alpha? (observe fade behavior)
- [ ] Do custom particle systems load from quest CAMs via `<Descriptions>`?
- [ ] What do AttachmentPointID values correspond to visually?
  - Test: create particle with each ID (0-3), observe attachment point

---

## Landscape / Terrain

- [ ] Which fractal refs produce trees? (`xFel`, `xFer`, `xBBC`, etc.)
- [ ] Test terrain presets with different fractal refs to get vegetation
- [ ] Verify custom constants.rgs loads from MQXML `<Constants>` tag

---

## Engine Timing / GPL Verification

- [ ] Game tick → real time ratio
  - Method: `$NewThread` at 1000ms, count iterations over known real-time span
- [ ] `$RandomCoord(anchor, -1)` radius behavior
  - Method: Log 20+ returned coords, plot against map bounds
- [ ] Use `revelation` cheat + GPL test to validate coord spread

---

## Quest Map Generator — Visual Verification

- [ ] Load generated quest with different terrain presets, verify terrain looks correct
- [ ] Verify spawner configurations produce expected monster density
- [ ] Test multi-kingdom (4P+) slot configs load without crash
