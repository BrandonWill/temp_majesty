# Tasks

## Task 1: Implement Q File Parser (Binary → Data Model)

- [ ] Create `quest_map_generator.py` at workspace root with data model classes (QuestMap, MapParams, SpawnerEntry, SpawnerBlock, PlacedEntry, PlacedGroup, Faction)
- [ ] Implement `parse_q_file(filepath)` that reads the 16-byte header and validates magic bytes (RGMa, RGM6, RGM9)
- [ ] Parse quest name and pattern name (null-terminated strings after header)
- [ ] Parse map parameters block (width, height, factions, gold, secondary resource) handling alignment differences between format versions
- [ ] Parse spawner sections: find "NONEnone\0" markers, read u32 count, then count × 24-byte spawner entries
- [ ] Parse placed-object groups: find `[4B terrain][u32 5][u32 count]` pattern, then read variable-length placed entries (ID + u32 + cstr + u32 + u8 grid_pos)
- [ ] Parse the metadata block after each placed group (resource limits, faction name)
- [ ] Parse the player/faction section at end of file
- [ ] Verify parser against MyQuest/Quest.q (known structure: 4 spawner blocks × 4 entries, placed groups with 8+25+1+1 entries)
- [ ] Verify parser against at least 3 RGM6 files (fertile_plain.q, Brashnard.q, barren_waste.q)

## Task 2: Implement Grid Position Encoding/Decoding

- [ ] Implement `grid_to_byte(col, row)` → returns ASCII byte 65 + row*5 + col, validates 0 ≤ col < 5 and 0 ≤ row < 5
- [ ] Implement `byte_to_grid(byte_val)` → returns (col, row) tuple, validates 65 ≤ byte ≤ 89
- [ ] Implement `letter_to_byte(letter)` → converts 'A'-'Y' character to byte value
- [ ] Implement `byte_to_letter(byte_val)` → converts byte 65-89 to 'A'-'Y' character
- [ ] Add convenience: `CENTER = ord('M')`, position constants for common placements
- [ ] Add auto-distribute function: given N lairs, return grid positions that spread them around the center avoiding the palace cell

## Task 3: Implement Q File Writer (Data Model → Binary)

- [ ] Implement `write_q_file(quest_map, output_path)` that serializes a QuestMap to binary
- [ ] Write the 16-byte header with "RGMa" magic
- [ ] Write quest name as null-terminated string
- [ ] Write pattern name as 12 bytes + null (pad or truncate as needed)
- [ ] Write map parameters block (aligned u32 values)
- [ ] Write spawner sections with "NONEnone\0" separators and 24-byte entries
- [ ] Write placed-object groups with terrain code + entries + metadata blocks
- [ ] Write player/faction section at end of file
- [ ] Implement round-trip test: parse(MyQuest/Quest.q) → write(temp) → parse(temp) → assert structural equality

## Task 4: Implement MQXML Generator

- [ ] Implement `generate_mqxml(quest_name, dataset_base, rgs_filename, extra_loads, output_path)`
- [ ] Generate valid XML with Quest id (UUID), dataset_base attribute
- [ ] Include Template element referencing the .q file
- [ ] Include Constants element referencing the .rgs file
- [ ] Include Load entries for additional data files (GPL sources, CAM files, XML definitions)
- [ ] Write to output path with UTF-8 encoding and XML declaration

## Task 5: Implement Terrain File Handling

- [ ] Implement `copy_terrain_template(output_dir, template_path=None)` that copies a .rgs file
- [ ] Use MyQuest/Quest.rgs as the default template (256×256 flat grass terrain)
- [ ] Validate that template file exists and has RGCB or RGCA magic bytes
- [ ] Copy with appropriate naming (Quest_name.rgs) to output directory

## Task 6: Implement High-Level Convenience API

- [ ] Implement `generate_test_quest(quest_name, lairs, output_dir, **kwargs)` one-call API
- [ ] Auto-place Palace at center ('M') when not explicitly specified
- [ ] Auto-distribute lairs around center using the grid distribution function from Task 2
- [ ] Generate default spawner blocks (4 generic monster types per lair)
- [ ] Create output directory if it doesn't exist
- [ ] Call the writer, MQXML generator, and terrain copier to produce complete package
- [ ] Return the paths of all generated files

## Task 7: Implement Pretty-Print (Structured Text Representation)

- [ ] Implement `format_q_text(quest_map)` → human-readable multi-line string showing all fields
- [ ] Show header info, map params, spawner counts, placed entries with grid visualization
- [ ] Implement `parse_q_text(text)` → QuestMap (inverse of format_q_text)
- [ ] Verify round-trip: format_q_text(parse_q_text(text)) == text for generated text

## Task 8: Implement Validation

- [ ] Implement `validate_q_file(filepath)` that checks structural integrity
- [ ] Verify magic bytes at offsets 0-3 and 8-11
- [ ] Verify all Object_IDs are 4 ASCII characters matching known prefix patterns
- [ ] Verify grid position bytes are in range 65-89
- [ ] Verify file size consistency (no truncation, no trailing garbage beyond expected structure)
- [ ] Verify spawner entry format (24 bytes each, active flag = 1)
- [ ] Implement `compare_q_files(generated, reference)` for structural comparison
- [ ] Return list of ValidationIssue objects with byte offsets and descriptions

## Task 9: Implement CLI Interface

- [ ] Add argparse-based CLI with subcommands: parse, generate, validate
- [ ] `parse` subcommand: takes .q file path, prints formatted text to stdout
- [ ] `generate` subcommand: takes quest name, lair specifications (comma-separated ID:desc:position), output directory
- [ ] `validate` subcommand: takes .q file path, prints issues, exits non-zero on failure
- [ ] Add `--help` with usage examples for each subcommand
- [ ] Add `--reference` option to validate subcommand for comparison against known-good file
- [ ] Handle errors gracefully with descriptive messages (no stack traces for user errors)

## Task 10: Integration Testing and Documentation

- [ ] Parse ALL 23 quest files in Quests/ folder without errors
- [ ] Generate a test quest, validate it, and verify it matches expected structure
- [ ] Round-trip test: parse → write → parse all RGMa files (MyQuest, Krolm, Freestyle)
- [ ] Add docstrings to all public functions with usage examples
- [ ] Update workspace README.md with quest_map_generator.py documentation
- [ ] Update RESEARCH_NOTES.md with the complete .q format specification findings
