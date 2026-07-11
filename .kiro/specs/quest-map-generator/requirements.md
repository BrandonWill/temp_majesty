# Requirements Document

## Introduction

A Python tool for programmatically generating Majesty Gold HD quest template (.q) binary files for the Random Generation System (RGS). The .q file is a procedural generation template — maps are NOT pre-rendered but generated at load time using placement patterns and a random seed. The tool enables automated quest creation for mod testing workflows without using the RGSEditor GUI. The primary use case is generating minimal test quests with specific buildings/lairs placed so modders can quickly test mod features (spells, GPL scripts, new units) in-game.

## Glossary

- **Quest_Map_Generator**: The Python tool that creates .q binary quest template files from a programmatic API
- **Q_File**: A binary file (extension .q) encoding RGS placement patterns for procedural map generation at load time
- **RGS**: Random Generation System — the Majesty engine subsystem that generates the actual map terrain and object placement from a .q template at quest load time
- **Force_Pattern**: The top-level placement structure defining where each faction's Unit_Pattern cluster appears on the overall map; uses its own 5x5 grid (positions A-Y) for map quadrant assignment
- **Unit_Pattern**: A mid-level placement structure containing a 5x5 Layout Grid with a Resolution setting; holds one or more Unit_Instance entries that the RGS places relative to the grid
- **Unit_Instance**: A single building, monster, or landmark entry within a Unit_Pattern; marked at one or more grid cells as candidate positions (RGS picks one randomly); each instance is placed exactly once
- **Layout_Grid**: A 5x5 grid (25 cells labeled A-Y) used by both Unit_Patterns and Force_Patterns; positions are encoded as ASCII bytes 65-89
- **Resolution**: The tile spacing between Layout_Grid cells; a resolution of N means each cell is N×32 pixels from its neighbor (e.g., resolution 3 = 96 pixels between cells)
- **Candidate_Position**: When a Unit_Instance is marked at multiple grid cells, the RGS randomly selects one cell for final placement; this provides positional variety across map generations
- **Grid_Rotation**: The RGS randomly rotates the Layout_Grid (0°/90°/180°/270°) at generation time; positions are approximate guidance, not fixed coordinates
- **Spawner_Block**: A set of entries defining which monster types a specific lair can produce, separated by "NONEnone\0" markers in the binary format
- **Region_Pattern**: Terrain definition section encoding terrain textures, fractal height settings, and landscape objects (trees/rocks) for procedural terrain generation
- **Object_ID**: A 4-character ASCII identifier following game conventions (AB*=player buildings, BB*=monster lairs, BV*=monsters/characters, AV*=NPCs, BA*=ambient objects)
- **RGS_File**: A binary terrain file (extension .rgs, magic "RGCB" or "RGCA") containing terrain heightmap/type data referenced by the quest template
- **MQXML_File**: The XML quest definition file that references the .q file via a Template element and configures data loading
- **Template_Writer**: The approach used by the tool — splicing custom Unit_Pattern groups into a known-good .q file while preserving header, spawners, teams, region patterns, and Force_Pattern from the template
- **Overlap_Prevention**: Engine behavior where the RGS enforces minimum spacing between placed objects based on sprite sizes, preventing buildings from overlapping at generation time

## Requirements

### Requirement 1: Parse Existing Q Files

**User Story:** As a modder, I want to parse existing .q files into structured Python objects, so that I can understand the format, verify generated files, and inspect existing quest templates.

#### Acceptance Criteria

1. WHEN a valid .q file path is provided, THE Quest_Map_Generator SHALL parse the file and return a QuestMap structure containing the magic identifier, quest name, pattern name, map parameters, Spawner_Blocks, Unit_Pattern placed groups, and Force_Pattern factions
2. WHEN parsing a .q file with magic "RGMa", THE Quest_Map_Generator SHALL identify the file as RGSEditor-created format
3. WHEN parsing a .q file with magic "RGM6", THE Quest_Map_Generator SHALL identify the file as base-game format
4. WHEN parsing a .q file with magic "RGM9", THE Quest_Map_Generator SHALL identify the file as expansion format
5. WHEN a .q file contains Unit_Pattern placed groups, THE Quest_Map_Generator SHALL parse each group extracting the terrain code, entry count, and for each Unit_Instance the Object_ID, description string, and list of Candidate_Position bytes (A-Y, 65-89)
6. WHEN a .q file contains Spawner_Blocks separated by "NONEnone\0" markers, THE Quest_Map_Generator SHALL parse each block extracting the monster Object_IDs and spawn level values
7. WHEN a .q file contains Force_Pattern entries, THE Quest_Map_Generator SHALL parse each faction extracting the short code, full name, active flag, and map grid position byte
8. IF a file does not begin with a recognized magic ("RGMa", "RGM6", or "RGM9"), THEN THE Quest_Map_Generator SHALL raise a QFormatError with a descriptive message indicating the invalid magic bytes

### Requirement 2: Write Q Files Using Template Approach

**User Story:** As a modder, I want to generate valid .q binary files by splicing custom Unit_Pattern groups into a template, so that I can create working quest maps without generating the entire binary structure from scratch.

#### Acceptance Criteria

1. WHEN a list of Unit_Pattern placed groups and an output path are provided, THE Quest_Map_Generator SHALL produce a .q file by splicing the groups into the template while preserving the template's header, spawner sections, team definitions, Region_Pattern data, and Force_Pattern
2. THE Quest_Map_Generator SHALL encode each Unit_Instance entry as: [4B Object_ID][u32 0][null-terminated description string][u32 position_count][position_count × u8 grid positions]
3. WHEN encoding Candidate_Positions for a Unit_Instance, THE Quest_Map_Generator SHALL write each position as a single byte in the range 65-89 (ASCII 'A'-'Y') corresponding to the 5x5 Layout_Grid cells
4. WHEN a Unit_Instance has multiple Candidate_Positions, THE Quest_Map_Generator SHALL encode all positions in sequence, indicating the RGS will randomly select one cell for placement
5. WHEN a custom template path is provided, THE Quest_Map_Generator SHALL use the specified template file instead of the default MyQuest/Quest.q
6. IF the specified template file does not exist, THEN THE Quest_Map_Generator SHALL raise a FileNotFoundError with the missing path
7. FOR ALL valid placed group inputs, parsing a generated .q file SHALL produce a QuestMap with equivalent placed group data (round-trip property for the Unit_Pattern section)

### Requirement 3: Encode Layout Grid Positions

**User Story:** As a modder, I want to specify unit placements using grid coordinates or letters, so that I can control where buildings and lairs appear relative to each other on the procedurally generated map.

#### Acceptance Criteria

1. WHEN grid coordinates (col, row) in range 0-4 are provided, THE Quest_Map_Generator SHALL encode them as a single byte value (65 + row×5 + col)
2. WHEN a grid letter 'A'-'Y' is provided, THE Quest_Map_Generator SHALL convert it to the corresponding byte value 65-89
3. WHEN a position byte 65-89 is provided, THE Quest_Map_Generator SHALL decode it to the corresponding (col, row) pair and grid letter
4. THE Quest_Map_Generator SHALL define the center cell as 'M' (byte 77, coordinates 2,2)
5. IF a grid coordinate outside the range 0-4 is provided, THEN THE Quest_Map_Generator SHALL raise a ValueError specifying the invalid coordinate and valid range
6. IF a grid letter outside 'A'-'Y' is provided, THEN THE Quest_Map_Generator SHALL raise a ValueError specifying the invalid letter

### Requirement 4: Auto-Distribute Unit Placements

**User Story:** As a modder, I want the tool to automatically spread lairs and buildings across the Layout_Grid when I don't specify exact positions, so that I can quickly generate test quests without manually calculating grid layouts.

#### Acceptance Criteria

1. WHEN N items need placement and no explicit positions are specified, THE Quest_Map_Generator SHALL assign grid positions using a priority order that starts with corners, then edge midpoints, then inner ring cells
2. THE Quest_Map_Generator SHALL exclude the center cell 'M' (palace position) from auto-distribution by default
3. WHEN additional exclusions are specified, THE Quest_Map_Generator SHALL also exclude those positions from the distribution
4. IF the number of items exceeds available grid positions (25 minus excluded cells), THEN THE Quest_Map_Generator SHALL raise a ValueError specifying the count and available positions
5. WHEN auto-distributing, THE Quest_Map_Generator SHALL assign each Unit_Instance a single Candidate_Position (deterministic placement rather than random candidate selection)

### Requirement 5: Validate Unit Pattern Placements

**User Story:** As a modder, I want the tool to catch placement conflicts before writing the file, so that I avoid generating quests that will fail or produce degenerate maps at load time.

#### Acceptance Criteria

1. WHEN validating placed entries, THE Quest_Map_Generator SHALL check that no two building-type entries (Object_IDs starting with "AB" or "BB") share the same grid cell
2. WHEN a building conflict is detected, THE Quest_Map_Generator SHALL raise a ValueError identifying both conflicting entries, their Object_IDs, and the shared grid cell letter
3. THE Quest_Map_Generator SHALL allow non-building entries (Object_IDs starting with "BV", "AV", "BA") to share grid cells with building entries without raising errors

### Requirement 6: Provide Terrain File Handling

**User Story:** As a modder, I want the tool to handle .rgs terrain files, so that my generated quest has valid terrain data the RGS can use during map generation.

#### Acceptance Criteria

1. WHEN generating a quest package, THE Quest_Map_Generator SHALL copy a template .rgs file to the output directory as the terrain data for the quest
2. THE Quest_Map_Generator SHALL locate a default .rgs template from the existing quest files (MyQuest/Quest.rgs or equivalent)
3. WHEN a custom .rgs file path is provided, THE Quest_Map_Generator SHALL use the specified file instead of the default template
4. IF the specified .rgs template file does not exist, THEN THE Quest_Map_Generator SHALL raise a FileNotFoundError indicating the missing terrain file path

### Requirement 7: Generate MQXML Quest Definition

**User Story:** As a modder, I want the tool to generate a matching .mqxml file that references the .q map template, so that the game can load the complete quest package with all required data files.

#### Acceptance Criteria

1. WHEN generating a quest package, THE Quest_Map_Generator SHALL produce a valid .mqxml XML file containing the quest metadata and DataConfiguration section
2. THE Quest_Map_Generator SHALL include a Template element in the MQXML_File referencing the generated .q file path
3. THE Quest_Map_Generator SHALL include a Constants element in the MQXML_File referencing the .rgs terrain file path
4. WHEN a dataset base is specified (either "Majesty" or "MajestyExpansion"), THE Quest_Map_Generator SHALL set the Dataset base attribute accordingly
5. WHEN additional data load entries are specified (GPL sources, Description XMLs, CAM files), THE Quest_Map_Generator SHALL include them in the DataConfiguration Load section
6. THE Quest_Map_Generator SHALL generate a unique quest GUID in the standard format for the Quest id attribute

### Requirement 8: Provide a High-Level Convenience API

**User Story:** As a modder, I want a simple one-call API to generate a minimal test quest with a palace and specific lairs, so that I can set up test environments with minimal code for rapid mod iteration.

#### Acceptance Criteria

1. WHEN called with a quest name, a list of lair types (Object_IDs and descriptions), and an output directory, THE Quest_Map_Generator SHALL produce a complete quest package (Q_File, RGS_File, and MQXML_File) ready for game loading
2. THE Quest_Map_Generator SHALL automatically place the Palace (Object_ID "ABJ1") at the center grid cell 'M' when using the convenience API
3. THE Quest_Map_Generator SHALL automatically distribute lairs at available grid positions using the auto-distribution algorithm when explicit positions are not specified
4. WHEN Spawner_Block definitions are provided for lairs, THE Quest_Map_Generator SHALL associate the correct monster spawn lists with each lair
5. WHEN the output directory does not exist, THE Quest_Map_Generator SHALL create it
6. WHEN additional mod data entries (GPL sources, custom XMLs) are specified, THE Quest_Map_Generator SHALL include them in the generated MQXML_File

### Requirement 9: Format Q File as Human-Readable Text

**User Story:** As a modder, I want to convert a parsed .q file into a human-readable text representation, so that I can inspect quest templates, debug generation issues, and understand what a given .q file encodes.

#### Acceptance Criteria

1. WHEN a parsed QuestMap structure is provided, THE Quest_Map_Generator SHALL produce a text representation showing the magic, quest name, map parameters, all Spawner_Blocks with their entries, all Unit_Pattern placed groups with their Unit_Instances and grid positions, and Force_Pattern factions
2. WHEN formatting Unit_Instance entries, THE Quest_Map_Generator SHALL display each entry's Object_ID, description, and Candidate_Positions as grid letters (A-Y) with (col, row) annotations
3. WHEN formatting Force_Pattern factions, THE Quest_Map_Generator SHALL display each faction's short code, full name, active status, and map grid position letter

### Requirement 10: Validate Generated Q Files

**User Story:** As a modder, I want the tool to validate generated .q files against known structural constraints, so that I can catch errors before loading in-game where the engine crashes silently with no diagnostics.

#### Acceptance Criteria

1. THE Quest_Map_Generator SHALL verify that every generated .q file begins with a recognized magic at bytes 0-3 repeated at bytes 8-11
2. THE Quest_Map_Generator SHALL verify that all Object_IDs in placed groups conform to the 4-character ASCII pattern with a recognized two-letter prefix (AB, BB, BV, AV, BA, AC, AA, CB, AX, BX)
3. THE Quest_Map_Generator SHALL verify that position bytes within Unit_Instance entries are in the valid range 65-89 (A-Y)
4. WHEN validation fails, THE Quest_Map_Generator SHALL report all detected issues with descriptive messages including byte offsets where applicable
5. WHEN a known-good reference .q file is provided, THE Quest_Map_Generator SHALL compare structural properties (placed group count, entry counts per group, object types present) between the generated file and the reference

### Requirement 11: Command-Line Interface

**User Story:** As a modder, I want to use the tool from the command line, so that I can integrate it into scripts and quickly inspect or generate quest files without writing Python code.

#### Acceptance Criteria

1. WHEN invoked with a "parse" subcommand and a .q file path, THE Quest_Map_Generator SHALL print the parsed structure to stdout in the human-readable text format
2. WHEN invoked with a "generate" subcommand and quest configuration parameters (quest name, lair list, output directory), THE Quest_Map_Generator SHALL produce the complete quest package in the specified output directory
3. WHEN invoked with a "validate" subcommand and a .q file path, THE Quest_Map_Generator SHALL report validation results to stdout with a non-zero exit code on failure
4. IF required arguments are missing, THEN THE Quest_Map_Generator SHALL display a usage message describing the expected arguments and subcommands
