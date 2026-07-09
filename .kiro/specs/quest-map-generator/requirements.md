# Requirements Document

## Introduction

A Python tool for programmatically generating Majesty Gold HD quest map (.q) binary files, enabling automated quest creation without the RGSEditor GUI. The tool produces valid .q files containing placed objects (palaces, monster lairs, buildings) with coordinate positions, paired with terrain (.rgs) files, for use in automated mod testing workflows and CI pipelines.

## Glossary

- **Quest_Map_Generator**: The Python tool that creates .q binary map files from a programmatic API
- **Q_File**: A binary file (extension .q) containing placed game objects with positions for a quest map
- **RGS_File**: A binary terrain/heightmap file (extension .rgs, magic "RGCB" or "RGCA") defining the map's terrain grid
- **Object_Entry**: A record within the .q file representing a placed game entity (building, lair, or unit spawner)
- **Short_Entry**: A 24-byte object record used for spawner definitions (monster spawn lists for lairs)
- **Long_Entry**: A 29+ byte object record used for placed buildings/lairs with description strings and coordinates
- **Object_ID**: A 4-character ASCII identifier following the game's naming convention (e.g., ABJ1=Palace, BBw1=Ice Cave, BVr1=Ratman Champion)
- **Map_Dimensions**: The width and height of the quest map grid (typically 256x256 tiles)
- **MQXML_File**: The XML quest definition file that references the .q file via a Template element
- **Spawn_Group**: A set of Short_Entry records defining which monsters a specific lair can produce
- **RGSEditor**: The existing GUI tool for creating .q and .rgs files (replaced by this tool for programmatic use)

## Requirements

### Requirement 1: Parse Existing Q Files

**User Story:** As a modder, I want to parse existing .q files into structured Python objects, so that I can understand the format and verify my generated files match the expected structure.

#### Acceptance Criteria

1. WHEN a valid .q file path is provided, THE Quest_Map_Generator SHALL parse the file and return a structured representation containing the header, quest name, pattern name, map parameters, and all Object_Entry records
2. WHEN parsing a .q file with magic "RGMa", THE Quest_Map_Generator SHALL identify the file as editor-created format version a
3. WHEN parsing a .q file with magic "RGM6", THE Quest_Map_Generator SHALL identify the file as base-game format version 6
4. WHEN a .q file contains Short_Entry records, THE Quest_Map_Generator SHALL parse each as a 24-byte record extracting the Object_ID, associated value, and flags
5. WHEN a .q file contains Long_Entry records, THE Quest_Map_Generator SHALL parse each extracting the Object_ID, null-terminated description string, and coordinate data
6. IF a file does not begin with magic "RGMa" or "RGM6", THEN THE Quest_Map_Generator SHALL raise a descriptive error indicating the file is not a valid .q format

### Requirement 2: Generate Q File Binary Output

**User Story:** As a modder, I want to generate valid .q binary files from a Python data structure, so that I can create quest maps without using RGSEditor.

#### Acceptance Criteria

1. WHEN a quest map specification is provided with a quest name, pattern name, map dimensions, and object list, THE Quest_Map_Generator SHALL produce a binary .q file with the correct "RGMa" header format
2. THE Quest_Map_Generator SHALL write the header as: magic bytes "RGMa" at offsets 0-3 and 8-11, with zero-filled bytes at offsets 4-7 and 12-15
3. WHEN writing the quest name string, THE Quest_Map_Generator SHALL encode it as a null-terminated ASCII string starting at offset 0x10
4. WHEN writing Short_Entry records, THE Quest_Map_Generator SHALL encode each as exactly 24 bytes containing the 4-byte Object_ID, a u32 value, and 16 bytes of flags/padding
5. WHEN writing Long_Entry records, THE Quest_Map_Generator SHALL encode each containing the 4-byte Object_ID, a u32 field, a null-terminated description string, and coordinate data
6. FOR ALL valid quest map specifications, parsing a generated .q file SHALL produce a data structure equivalent to the original specification (round-trip property)

### Requirement 3: Place Objects on Map

**User Story:** As a modder, I want to place buildings, lairs, and the palace at specific map coordinates, so that I can control the layout of the generated quest.

#### Acceptance Criteria

1. WHEN a Palace object (Object_ID "ABJ1") is added with x and y coordinates, THE Quest_Map_Generator SHALL create a Long_Entry positioned at the specified map location
2. WHEN a monster lair object (Object_ID matching "BB**" pattern) is added with coordinates, THE Quest_Map_Generator SHALL create a Long_Entry with the lair's description string and position
3. WHEN a Spawn_Group is associated with a lair, THE Quest_Map_Generator SHALL create the corresponding Short_Entry records defining which monster types (Object_IDs matching "BV**") the lair produces
4. WHEN placing objects, THE Quest_Map_Generator SHALL validate that coordinates fall within the specified Map_Dimensions
5. IF an object is placed with coordinates outside the map boundaries, THEN THE Quest_Map_Generator SHALL raise a descriptive error specifying the invalid coordinates and the valid range

### Requirement 4: Provide Terrain File Handling

**User Story:** As a modder, I want the tool to handle .rgs terrain files, so that my generated quest has valid terrain data the game can load.

#### Acceptance Criteria

1. WHEN generating a quest map, THE Quest_Map_Generator SHALL copy a template .rgs file to the output directory as the terrain data for the quest
2. THE Quest_Map_Generator SHALL include a default flat-terrain .rgs template suitable for minimal test maps
3. WHEN a custom .rgs file path is provided, THE Quest_Map_Generator SHALL use the specified file instead of the default template
4. IF the specified .rgs template file does not exist, THEN THE Quest_Map_Generator SHALL raise a descriptive error indicating the missing terrain file path

### Requirement 5: Generate MQXML Quest Definition

**User Story:** As a modder, I want the tool to generate a matching .mqxml file that references the .q map, so that the game can load the complete quest package.

#### Acceptance Criteria

1. WHEN generating a quest package, THE Quest_Map_Generator SHALL produce a valid .mqxml XML file containing the quest metadata and DataConfiguration section
2. THE Quest_Map_Generator SHALL include a Template element in the MQXML_File referencing the generated .q file path
3. THE Quest_Map_Generator SHALL include a Constants element in the MQXML_File referencing the .rgs terrain file path
4. WHEN a dataset base is specified (either "Majesty" or "MajestyExpansion"), THE Quest_Map_Generator SHALL set the Dataset base attribute accordingly
5. WHEN additional data load entries are specified (GPL sources, Descriptions XMLs, CAM files), THE Quest_Map_Generator SHALL include them in the DataConfiguration Load section
6. THE Quest_Map_Generator SHALL generate a unique quest GUID in the standard format for the Quest id attribute

### Requirement 6: Provide a High-Level Convenience API

**User Story:** As a modder, I want a simple one-call API to generate a minimal test quest with a palace and specific lairs, so that I can set up test environments with minimal code.

#### Acceptance Criteria

1. WHEN called with a quest name, a list of lair types, and an output directory, THE Quest_Map_Generator SHALL produce a complete quest package (Q_File, RGS_File, and MQXML_File) ready for game loading
2. THE Quest_Map_Generator SHALL automatically place the Palace at the map center when using the convenience API
3. THE Quest_Map_Generator SHALL automatically distribute lairs at reasonable spacing around the Palace when positions are not explicitly specified
4. WHEN the output directory does not exist, THE Quest_Map_Generator SHALL create it

### Requirement 7: Serialize and Deserialize Q File Structure (Pretty-Print)

**User Story:** As a modder, I want to convert between the binary .q format and a human-readable text representation, so that I can inspect, debug, and manually edit quest map definitions.

#### Acceptance Criteria

1. WHEN a parsed Q_File structure is provided, THE Quest_Map_Generator SHALL produce a human-readable text representation showing all headers, parameters, and object entries with their properties
2. WHEN a text representation is provided in the defined format, THE Quest_Map_Generator SHALL parse it back into the internal Q_File structure
3. FOR ALL valid Q_File structures, converting to text and parsing back SHALL produce an equivalent structure (round-trip property)

### Requirement 8: Validate Generated Files

**User Story:** As a modder, I want the tool to validate generated .q files against known constraints, so that I can catch errors before loading in-game where crashes produce no useful diagnostics.

#### Acceptance Criteria

1. THE Quest_Map_Generator SHALL verify that every generated .q file begins with the correct magic bytes at offsets 0-3 and 8-11
2. THE Quest_Map_Generator SHALL verify that all Object_IDs in a generated file conform to the 4-character ASCII pattern (two uppercase letters followed by one letter and one digit)
3. THE Quest_Map_Generator SHALL verify that the total file size is consistent with the number of Short_Entry and Long_Entry records encoded
4. WHEN validation fails, THE Quest_Map_Generator SHALL report all detected issues with byte offsets and expected values
5. WHEN a known-good reference .q file is provided, THE Quest_Map_Generator SHALL compare structural properties (entry count, object types, map dimensions) between the generated file and the reference

### Requirement 9: Command-Line Interface

**User Story:** As a modder, I want to use the tool from the command line, so that I can integrate it into scripts and CI pipelines without writing Python code.

#### Acceptance Criteria

1. WHEN invoked with a "parse" subcommand and a .q file path, THE Quest_Map_Generator SHALL print the parsed structure to stdout in the human-readable text format
2. WHEN invoked with a "generate" subcommand and a quest configuration (quest name, lair list, output directory), THE Quest_Map_Generator SHALL produce the complete quest package in the specified output directory
3. WHEN invoked with a "validate" subcommand and a .q file path, THE Quest_Map_Generator SHALL report validation results to stdout with a non-zero exit code on failure
4. IF required arguments are missing, THEN THE Quest_Map_Generator SHALL display a usage message describing the expected arguments and subcommands
