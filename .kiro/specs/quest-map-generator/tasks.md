# Implementation Plan: Quest Map Generator Refactoring

## Overview

Refactor the existing working `QuestMapGenerator/quest_map_generator.py` to align with correct RGS terminology (PlacedGroup→UnitPattern, PlacedEntry→UnitInstance, positions→candidate_cells), add Team/Player and Region Pattern parsing, and update all docstrings. The template-based writer and overall architecture remain unchanged.

## Tasks

- [ ] 1. Rename data model classes and fields
  - [ ] 1.1 Rename `PlacedEntry` class to `UnitInstance`, rename `positions` field to `candidate_cells`
    - Update all references throughout the file (parser, writer, formatter, validator, CLI)
    - Update docstring to explain candidate_cells semantics (RGS picks one randomly, NOT multiple placements)
    - _Requirements: 1.5, 2.2, 2.3, 2.4_
  - [ ] 1.2 Rename `PlacedGroup` class to `UnitPattern`, add `resolution` field (default 5)
    - Update all references throughout the file
    - Update docstring to explain Unit Pattern as mid-level placement structure with 5×5 grid
    - _Requirements: 1.5, 2.1_
  - [ ] 1.3 Rename `Faction` class to `ForceEntry`, rename `home_position` to `map_position`
    - Update QuestMap field from `factions` to `force_pattern`
    - Update docstring to explain Force Pattern as top-level map layout
    - _Requirements: 1.7_
  - [ ] 1.4 Rename `validate_unique_positions` to `validate_placements`
    - Keep same logic, update parameter type from `list[PlacedEntry]` to `list[UnitInstance]`
    - _Requirements: 5.1, 5.2, 5.3_

- [ ] 2. Add TeamDefinition and RegionPatternInfo data classes
  - [ ] 2.1 Add `TeamDefinition` dataclass with name, active, team_id fields
    - Add `teams: list[TeamDefinition]` field to QuestMap
    - _Requirements: 1.1_
  - [ ] 2.2 Add `RegionPatternInfo` dataclass with pattern_name, patch_count, terrain_codes fields
    - Add `region_info: Optional[RegionPatternInfo]` field to QuestMap
    - _Requirements: 1.1_

- [ ] 3. Update parser to populate new fields
  - [ ] 3.1 Add Team/Player definition parsing after spawner section
    - Parse "Human Player\0", "player2_ai\0", etc. with active flags
    - Populate `qmap.teams` list
    - _Requirements: 1.1_
  - [ ] 3.2 Add Region Pattern metadata extraction
    - Parse pattern name reference and patch count
    - Extract terrain codes from region patches
    - Populate `qmap.region_info`
    - _Requirements: 1.1_
  - [ ] 3.3 Update placed group parsing to use UnitPattern/UnitInstance names
    - Rename internal variables from `placed_groups`/`placed_entries` to `unit_patterns`/`unit_instances`
    - Rename `_find_placed_groups` to `_find_unit_patterns`
    - Rename `_parse_placed_entries` to `_parse_unit_instances`
    - _Requirements: 1.5_
  - [ ] 3.4 Update Force Pattern parsing to use ForceEntry
    - Rename internal variables and ensure `qmap.force_pattern` is populated
    - _Requirements: 1.7_

- [ ] 4. Checkpoint — Verify parser still passes all 37 files
  - Run `python QuestMapGenerator/test_all_quests.py` and ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 5. Update writer to use new terminology
  - [ ] 5.1 Rename `_encode_placed_entry` to `_encode_unit_instance`
    - Update parameter from `PlacedEntry` to `UnitInstance`, field access from `.positions` to `.candidate_cells`
    - _Requirements: 2.2, 2.3, 2.4_
  - [ ] 5.2 Rename `_encode_placed_group` to `_encode_unit_pattern`
    - Update parameter from `PlacedGroup` to `UnitPattern`, field access from `.entries` to `.entries` (same)
    - _Requirements: 2.1_
  - [ ] 5.3 Update `write_q_file` signature and internals
    - Parameter name from `placed_groups` to `unit_patterns` (or accept QuestMap)
    - Update internal variable names and comments
    - _Requirements: 2.1, 2.5, 2.6_
  - [ ] 5.4 Update `write_q_file_simple` to use UnitInstance
    - Parameter from `entries: list[PlacedEntry]` to `entries: list[UnitInstance]`
    - _Requirements: 2.1_

- [ ] 6. Update formatter and validator
  - [ ] 6.1 Update `format_q_text` to use new class names and field names
    - Reference `.candidate_cells` instead of `.positions`
    - Reference `.unit_patterns` instead of `.placed_groups`
    - Reference `.force_pattern` instead of `.factions`
    - Include teams and region_info in output when present
    - _Requirements: 9.1, 9.2, 9.3_
  - [ ] 6.2 Update `validate_q_file` to use new terminology
    - Internal variable renames
    - _Requirements: 10.1, 10.2, 10.3_
  - [ ] 6.3 Update `compare_q_files` to use new terminology
    - _Requirements: 10.5_

- [ ] 7. Update convenience API and CLI
  - [ ] 7.1 Update `generate_test_quest` internals to use UnitInstance/UnitPattern
    - Keep the same public API signature (dict-based lair specs)
    - Internal construction uses UnitInstance instead of PlacedEntry
    - _Requirements: 8.1, 8.2, 8.3_
  - [ ] 7.2 Update CLI subcommand handlers to use new names
    - `_cli_parse`, `_cli_validate`, `_cli_generate` internal variable names
    - _Requirements: 11.1, 11.2, 11.3_

- [ ] 8. Update test file to use new class names
  - [ ] 8.1 Update `QuestMapGenerator/test_all_quests.py` imports and assertions
    - Import `UnitInstance` instead of `PlacedEntry`
    - Update `validate_unique_positions` calls to `validate_placements`
    - Update assertions referencing `.placed_groups` to `.unit_patterns`
    - Update assertions referencing `.positions` to `.candidate_cells`
    - _Requirements: 1.5, 2.7_

- [ ] 9. Checkpoint — Full regression test
  - Run `python QuestMapGenerator/test_all_quests.py` and verify all 37 files still parse
  - Verify grid encoding tests still pass
  - Verify auto-distribute and validation tests still pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ]* 10. Write property tests for grid encoding
  - [ ]* 10.1 Write property test for grid encoding bijectivity
    - **Property 1: Grid encoding round-trip**
    - For any (col, row) in [0,4]×[0,4], grid_to_byte then byte_to_grid returns original pair
    - For any byte in 65-89, byte_to_grid then grid_to_byte returns original byte
    - For any letter 'A'-'Y', letter_to_byte then byte_to_letter returns original letter
    - **Validates: Requirements 3.1, 3.2, 3.3**
  - [ ]* 10.2 Write property test for invalid grid input rejection
    - **Property 4: Invalid grid input rejection**
    - For any col or row outside [0,4], grid_to_byte raises ValueError
    - For any byte outside 65-89, byte_to_grid raises ValueError
    - For any character not in 'A'-'Y', letter_to_byte raises ValueError
    - **Validates: Requirements 3.5, 3.6**

- [ ]* 11. Write property tests for auto-distribute and validation
  - [ ]* 11.1 Write property test for auto-distribute correctness
    - **Property 3: Auto-distribution produces valid non-overlapping positions**
    - For any N in [1,24], returns exactly N unique positions all in 65-89, none equal to CENTER
    - For any N and exclusion set, no excluded positions appear in result
    - **Validates: Requirements 4.1, 4.2, 4.5**
  - [ ]* 11.2 Write property test for building conflict detection
    - **Property 5: Validation detects all building conflicts**
    - For any two UnitInstance entries with AB*/BB* prefixes sharing a candidate_cell, validate_placements raises ValueError
    - For any BV*/AV*/BA* entry sharing a cell with AB*/BB*, no error raised
    - **Validates: Requirements 5.1, 5.2, 5.3**

- [ ]* 12. Write property test for write-parse round-trip
  - [ ]* 12.1 Write property test for UnitPattern write-parse round-trip
    - **Property 2: UnitPattern write-parse round-trip**
    - For any valid list of UnitInstance entries (4-char IDs with valid prefixes, non-empty descriptions, candidate_cells in 65-89), writing via template and parsing back produces equivalent data
    - **Validates: Requirements 2.1, 2.7**
  - [ ]* 12.2 Write property test for parse produces valid position bytes
    - **Property 6: Parse produces valid position bytes**
    - For any .q file that parses successfully, every candidate_cell in every UnitInstance is in range 65-89
    - **Validates: Requirements 1.5, 10.3**

- [ ] 13. Final checkpoint — Complete validation
  - Run all tests and verify everything passes
  - Verify `python QuestMapGenerator/test_all_quests.py` reports 37/37 files pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster delivery
- The refactoring is purely internal — no behavioral changes to the tool's output
- Property tests require `hypothesis` library (`pip install hypothesis`)
- Each task builds on previous ones — do NOT skip the checkpoint tasks
- The writer's template approach is correct and unchanged — only names/types change
