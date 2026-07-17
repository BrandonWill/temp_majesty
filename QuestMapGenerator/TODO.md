# Quest Map Generator — TODO

## Needs In-Game Testing

The parser passes 37/37 files and the writer generates valid .q files that parse back
cleanly. But **no generated quest has been loaded in-game yet**.

### Test 1: Minimal generated quest loads

Generate a simple quest and verify the game loads it without crashing.

```bash
python QuestMapGenerator\quest_map_generator.py generate --name InGameTest --output utility\ingame_test --lairs "BBH1:Goblin Camp:N"
```

Then copy `utility\ingame_test\` to `Documents\My Games\MajestyHD\Quests\InGameTest\`,
select the quest in-game, and confirm:
- Map generates without crash
- Palace is present
- Goblin Camp lair spawns goblins

### Test 2: Multiple lairs + auto-distribution

```bash
python QuestMapGenerator\quest_map_generator.py generate --name MultiLair --output utility\multi_lair --lairs "BBw1:Ice Cave,BBH1:Goblin Camp,BBz1:Goblin Fortress"
```

Verify all 3 lairs appear on the generated map.

### Test 3: Terrain preset (expansion)

```bash
python QuestMapGenerator\quest_map_generator.py generate --name SnowTest --output utility\snow_test --lairs "BBw1:Ice Cave:N" --dataset MajestyExpansion
```

This currently uses the default grass terrain. The `--terrain snow` option exists in the
code but needs testing — the Region Pattern rewriting hasn't been verified.

---

## Future Scope: Full RGS Generation

The writer currently splices UnitPatterns into a template while preserving everything else.
These sections could be generated from scratch for full programmatic control:

- **Region Patterns** — terrain textures, fractal settings, landscape objects
  (terrain presets exist in code but haven't been tested in-game)
- **Force Pattern** — which map quadrant each faction's UnitPattern cluster occupies
- **Team/Player definitions** — faction names, active flags
- **Map size / random seed** — currently uses template's values

These would enable quest creation without any RGSEditor involvement.

---

## Known Limitations

- Generated quests use template's map size, seed, and spawner definitions
- Force Pattern isn't modified (template's faction layout is preserved)
- The terrain preset system (`_build_region_section`) exists but is untested
- GUID in .mqxml is random — game may or may not accept it without RGSEditor validation
