"""
Quest Map Generator — Parser, writer, and grid encoding for Majesty Gold HD .q binary quest files.

Reads RGMa (editor), RGM6 (base game), and RGM9 (expansion) format quest map files.
Writes RGMa format using a template-based approach (splices Unit Patterns into a known-good base).

Usage:
    from quest_map_generator import parse_q_file, write_q_file, grid_to_byte, byte_to_grid
    qmap = parse_q_file("Quests/fertile_plain.q")
    write_q_file(qmap.unit_patterns, "output/Quest.q", template="MyQuest/Quest.q")
"""

from __future__ import annotations
import struct
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# =============================================================================
# Exceptions
# =============================================================================

class QFormatError(Exception):
    """Raised when a .q file has invalid format or structure."""
    pass


# =============================================================================
# Data Model
# =============================================================================

@dataclass
class MapParams:
    width: int = 256
    height: int = 256
    num_factions: int = 4
    starting_gold: int = 2000
    secondary_resource: int = 10000


@dataclass
class SpawnerEntry:
    object_id: str  # 4-char ID (e.g., "BVr1")
    spawn_level: int  # Spawn count/level value


@dataclass
class SpawnerBlock:
    entries: list[SpawnerEntry] = field(default_factory=list)
    lair_resource: int = 0


@dataclass
class UnitInstance:
    """A single building/monster/landmark entry within a UnitPattern.

    Each UnitInstance is placed exactly once on the map. When candidate_cells
    contains multiple positions, the RGS randomly selects ONE cell for placement.
    This provides positional variety across map generations — it does NOT mean
    the unit is placed at all listed cells simultaneously.
    """
    object_id: str  # 4-char ID (e.g., "ABJ1" = Palace, "BBw1" = Ice Cave)
    description: str  # Human-readable name
    candidate_cells: list[int] = field(default_factory=list)
    # Grid position bytes (ASCII 'A'-'Y', 65-89).
    # Multiple entries = RGS picks one randomly. NOT multiple placements.

    @staticmethod
    def grid_col(pos_byte: int) -> int:
        """Column from position byte: (byte - 65) % 5"""
        return (pos_byte - 65) % 5

    @staticmethod
    def grid_row(pos_byte: int) -> int:
        """Row from position byte: (byte - 65) // 5"""
        return (pos_byte - 65) // 5


@dataclass
class UnitPattern:
    """A mid-level placement structure: a 5x5 Layout Grid with resolution.

    Contains one or more UnitInstance entries. The entire pattern is placed
    as a cluster on the map, with positions relative to the grid. The grid
    is randomly rotated (0/90/180/270) at generation time.
    """
    terrain_code: str = "gras"  # 4-char terrain type for this pattern
    resolution: int = 5  # Tile spacing between grid cells (from [u32 5] marker)
    entries: list[UnitInstance] = field(default_factory=list)
    faction_name: str = ""  # Owner faction (from metadata block after entries)


@dataclass
class TeamDefinition:
    """A team/player slot definition from the Team section.

    Defines the available factions for the quest (Human Player, AI players, Monsters).
    """
    name: str  # e.g., "Human Player", "player2_ai", "Monsters"
    active: bool = True  # Whether this team slot is in use
    team_id: int = 0  # Team identifier byte


@dataclass
class RegionPatternInfo:
    """Metadata about the Region Pattern section (terrain generation).

    The actual terrain data is preserved opaquely by the template writer.
    We only parse enough to know what's there for display/validation.
    """
    pattern_name: str = ""  # e.g., "pattpattpattern"
    patch_count: int = 0  # Number of Region Patches defined
    terrain_codes: list[str] = field(default_factory=list)  # e.g., ["gras", "snow"]


@dataclass
class ForceEntry:
    """A faction's position within the Force Pattern (top-level map layout).

    The Force Pattern determines WHERE on the overall map each faction's
    UnitPattern cluster is placed. Uses its own 5x5 grid.
    """
    short_code: str  # 4-char code (e.g., "Play", "Gobl", "Mons")
    full_name: str  # Full name (e.g., "Player1", "Goblin Kingdom")
    active: bool = True  # Whether this faction is active in the quest
    map_position: int = 77  # Grid position byte on the Force Pattern grid (A-Y)


@dataclass
class QuestMap:
    """Complete parsed representation of a .q quest template file."""
    magic: str = "RGMa"
    quest_name: str = ""
    pattern_name: bytes = b""
    params: MapParams = field(default_factory=MapParams)
    spawner_blocks: list[SpawnerBlock] = field(default_factory=list)
    teams: list[TeamDefinition] = field(default_factory=list)
    region_info: Optional[RegionPatternInfo] = None
    unit_patterns: list[UnitPattern] = field(default_factory=list)
    force_pattern: list[ForceEntry] = field(default_factory=list)


# =============================================================================
# Grid Position Encoding/Decoding
# =============================================================================

CENTER = ord('M')  # 77 — center of the 5x5 grid (2, 2)


def grid_to_byte(col: int, row: int) -> int:
    """Convert grid (col, row) to position byte. col/row must be 0-4."""
    if not (0 <= col < 5):
        raise ValueError(f"col must be 0-4, got {col}")
    if not (0 <= row < 5):
        raise ValueError(f"row must be 0-4, got {row}")
    return 65 + row * 5 + col


def byte_to_grid(byte_val: int) -> tuple[int, int]:
    """Convert position byte (65-89) to (col, row) tuple."""
    if not (65 <= byte_val <= 89):
        raise ValueError(f"byte_val must be 65-89 ('A'-'Y'), got {byte_val}")
    idx = byte_val - 65
    return (idx % 5, idx // 5)


def letter_to_byte(letter: str) -> int:
    """Convert grid letter 'A'-'Y' to byte value 65-89."""
    if len(letter) != 1 or not ('A' <= letter <= 'Y'):
        raise ValueError(f"letter must be 'A'-'Y', got {letter!r}")
    return ord(letter)


def byte_to_letter(byte_val: int) -> str:
    """Convert byte value 65-89 to grid letter 'A'-'Y'."""
    if not (65 <= byte_val <= 89):
        raise ValueError(f"byte_val must be 65-89, got {byte_val}")
    return chr(byte_val)


def auto_distribute(n: int, exclude: Optional[list[int]] = None) -> list[int]:
    """
    Given N items to place, return grid position bytes spread around the grid,
    avoiding the center (palace) and any excluded positions.

    Returns a list of N position bytes from the 5x5 grid.
    """
    if exclude is None:
        exclude = []
    excluded_set = set(exclude) | {CENTER}

    # Priority order: corners, edges, remaining — spiraling outward from center
    priority = [
        # Corners
        65, 69, 85, 89,  # A, E, U, Y
        # Edge midpoints
        67, 75, 79, 87,  # C, K, O, W
        # Inner ring (adjacent to center)
        72, 76, 78, 82,  # H, L, N, R
        # Remaining edges
        66, 68, 70, 74, 80, 84, 86, 88,  # B, D, F, J, P, T, V, X
        # Inner corners
        71, 73, 81, 83,  # G, I, Q, S
    ]

    available = [p for p in priority if p not in excluded_set]
    if n > len(available):
        raise ValueError(
            f"Cannot distribute {n} items: only {len(available)} positions available "
            f"(25 total minus {len(excluded_set)} excluded)"
        )
    return available[:n]


def validate_placements(entries: list[UnitInstance]) -> None:
    """
    Validate that no two BUILDINGS occupy the same grid cell.
    Only AB* and BB* prefixes are buildings. BV* (monsters/trees),
    AV* (NPCs), BA* (ambient) can share cells with buildings.
    Raises ValueError if two buildings share a cell.
    """
    BUILDING_PREFIXES = ('AB', 'BB')
    seen: dict[int, str] = {}
    for entry in entries:
        if not entry.object_id[:2] in BUILDING_PREFIXES:
            continue  # Skip non-buildings
        for pos in entry.candidate_cells:
            letter = chr(pos)
            if pos in seen:
                raise ValueError(
                    f"Grid cell '{letter}' (position {pos}) is occupied by "
                    f"'{seen[pos]}' but also assigned to '{entry.object_id}' "
                    f"({entry.description})"
                )
            seen[pos] = f"{entry.object_id} ({entry.description})"


# =============================================================================
# Parser
# =============================================================================

VALID_MAGICS = {b'RGMa', b'RGM6', b'RGM9'}
KNOWN_PREFIXES = {b'AB', b'BB', b'BV', b'AV', b'AC', b'AA', b'BA', b'CB', b'AX', b'BX'}


def _read_cstr(data: bytes, offset: int) -> tuple[str, int]:
    """Read a null-terminated string. Returns (string, offset_after_null)."""
    end = data.index(0, offset)
    s = data[offset:end].decode('ascii', errors='replace')
    return s, end + 1


def _find_unit_patterns(data: bytes) -> list[tuple[int, str, int]]:
    """
    Scan the binary data for Unit Pattern headers: [4B terrain][u32 5][u32 count].
    Returns list of (offset, terrain_code, entry_count).
    """
    results = []
    # We need at least 12 bytes for the header
    for offset in range(0, len(data) - 12):
        terrain = data[offset:offset + 4]
        val5 = struct.unpack_from('<I', data, offset + 4)[0]
        count = struct.unpack_from('<I', data, offset + 8)[0]

        if val5 != 5:
            continue
        if count < 1 or count > 200:
            continue

        # Validate terrain bytes are printable ASCII (or at least non-null)
        if not all(32 <= b < 127 for b in terrain):
            continue

        # Now validate that we can actually parse entries starting at offset+12
        # The first entry must start with a plausible Object_ID (4 ASCII bytes)
        entry_start = offset + 12
        if entry_start + 8 >= len(data):
            continue

        obj_id = data[entry_start:entry_start + 4]
        # Check it's printable ASCII
        if not all(32 <= b < 127 for b in obj_id):
            continue

        # Check the zero field (u32 at offset+4 of entry)
        zero_field = struct.unpack_from('<I', data, entry_start + 4)[0]
        if zero_field != 0:
            continue

        # Try to read the description string
        desc_start = entry_start + 8
        try:
            null_pos = data.index(0, desc_start)
        except ValueError:
            continue

        # Description shouldn't be too long (< 100 chars)
        if null_pos - desc_start > 100:
            continue

        # Check that description is printable ASCII
        desc_bytes = data[desc_start:null_pos]
        if not all(32 <= b < 127 for b in desc_bytes):
            continue


        # After desc null, read position_count
        pos_count_offset = null_pos + 1
        if pos_count_offset + 4 > len(data):
            continue

        pos_count = struct.unpack_from('<I', data, pos_count_offset)[0]
        if pos_count < 1 or pos_count > 25:
            continue

        # Check position bytes are in valid range
        positions_start = pos_count_offset + 4
        if positions_start + pos_count > len(data):
            continue

        positions = data[positions_start:positions_start + pos_count]
        if not all(65 <= b <= 89 for b in positions):
            continue

        # This looks like a valid unit pattern!
        terrain_str = terrain.decode('ascii')
        results.append((offset, terrain_str, count))

    # De-duplicate: remove overlapping detections
    if not results:
        return results

    filtered = []
    occupied_ranges: list[tuple[int, int]] = []

    for offset, terrain_str, count in results:
        # Check if this offset falls within an already-identified pattern's data
        in_existing = False
        for start, end in occupied_ranges:
            if start < offset < end:
                in_existing = True
                break
        if in_existing:
            continue

        # Try to compute the extent of this pattern
        extent = _compute_group_extent(data, offset, count)
        if extent is not None:
            filtered.append((offset, terrain_str, count))
            occupied_ranges.append((offset, extent))
        else:
            filtered.append((offset, terrain_str, count))

    return filtered


def _compute_group_extent(data: bytes, offset: int, count: int) -> Optional[int]:
    """Try to parse through all entries in a unit pattern and return the end offset."""
    pos = offset + 12  # Skip header
    for i in range(count):
        if pos + 8 >= len(data):
            return None
        # Skip obj_id (4) + zero (4)
        pos += 8
        # Read description string
        try:
            null_pos = data.index(0, pos)
        except ValueError:
            return None
        if null_pos - pos > 100:
            return None
        pos = null_pos + 1
        # Read position_count
        if pos + 4 > len(data):
            return None
        pos_count = struct.unpack_from('<I', data, pos)[0]
        if pos_count < 1 or pos_count > 25:
            return None
        pos += 4
        # Skip position bytes
        if pos + pos_count > len(data):
            return None
        # Validate positions
        positions = data[pos:pos + pos_count]
        if not all(65 <= b <= 89 for b in positions):
            return None
        pos += pos_count
    return pos


def _parse_unit_instances(data: bytes, offset: int, count: int) -> tuple[list[UnitInstance], int]:
    """
    Parse count UnitInstance entries starting at offset.
    Returns (list of UnitInstance, offset after last entry).
    """
    entries = []
    pos = offset
    for i in range(count):
        if pos + 8 >= len(data):
            raise QFormatError(f"Truncated unit instance at offset {pos}")

        obj_id = data[pos:pos + 4].decode('ascii', errors='replace')
        zero_field = struct.unpack_from('<I', data, pos + 4)[0]
        pos += 8

        # Description string
        try:
            null_pos = data.index(0, pos)
        except ValueError:
            raise QFormatError(f"Unterminated description string at offset {pos}")

        desc = data[pos:null_pos].decode('ascii', errors='replace')
        pos = null_pos + 1

        # Position count (candidate cells)
        if pos + 4 > len(data):
            raise QFormatError(f"Truncated position count at offset {pos}")
        pos_count = struct.unpack_from('<I', data, pos)[0]
        pos += 4

        if pos_count < 1 or pos_count > 25:
            raise QFormatError(
                f"Invalid position_count {pos_count} for entry {obj_id!r} at offset {pos - 4}"
            )

        # Position bytes (candidate cells)
        if pos + pos_count > len(data):
            raise QFormatError(f"Truncated position bytes at offset {pos}")
        candidate_cells = list(data[pos:pos + pos_count])
        pos += pos_count

        # Validate all positions are in range
        for p in candidate_cells:
            if not (65 <= p <= 89):
                raise QFormatError(
                    f"Invalid position byte {p} (expected 65-89) in entry {obj_id!r}"
                )

        entries.append(UnitInstance(
            object_id=obj_id,
            description=desc,
            candidate_cells=candidate_cells,
        ))

    return entries, pos


def _find_spawner_blocks(data: bytes) -> list[SpawnerBlock]:
    """
    Find and parse spawner blocks marked by 'NONEnone\\0'.
    Handles both 20-byte (RGM6) and 24-byte (RGMa) entry formats.
    """
    blocks = []
    marker = b'NONEnone\x00'
    idx = 0
    while True:
        idx = data.find(marker, idx)
        if idx == -1:
            break
        # After the marker (9 bytes) there's padding zeros, then a u32 count
        search_start = idx + 9
        search_end = min(search_start + 20, len(data) - 4)

        for probe in range(search_start, search_end):
            count = struct.unpack_from('<I', data, probe)[0]
            if count == 0:
                continue
            if count > 20:
                continue

            entries_start = probe + 4
            # Try both 20-byte and 24-byte entry sizes
            found = False
            for entry_size in (24, 20):
                if entries_start + count * entry_size > len(data):
                    continue

                # Check if first entry looks like a valid spawner ID
                first_id = data[entries_start:entries_start + 4]
                if not all(32 <= b < 127 for b in first_id):
                    continue

                # Parse entries
                spawner_entries = []
                valid = True
                for i in range(count):
                    entry_off = entries_start + i * entry_size
                    eid = data[entry_off:entry_off + 4].decode('ascii', errors='replace')
                    spawn_level = struct.unpack_from('<I', data, entry_off + 4)[0]
                    if entry_size == 24:
                        active = struct.unpack_from('<I', data, entry_off + 16)[0]
                    else:
                        active = struct.unpack_from('<I', data, entry_off + 16)[0]
                    if active != 1 and active != 0:
                        valid = False
                        break
                    spawner_entries.append(SpawnerEntry(object_id=eid, spawn_level=spawn_level))

                if valid and spawner_entries:
                    lair_resource = 0
                    after_entries = entries_start + count * entry_size
                    if after_entries + 8 <= len(data):
                        sep = struct.unpack_from('<I', data, after_entries)[0]
                        if sep == 0 and after_entries + 8 <= len(data):
                            lair_resource = struct.unpack_from('<I', data, after_entries + 4)[0]

                    blocks.append(SpawnerBlock(entries=spawner_entries, lair_resource=lair_resource))
                    found = True
                    break

            if found:
                break

        idx += 9

    return blocks


def parse_q_file(filepath) -> QuestMap:
    """
    Parse a .q binary quest map file.

    Handles RGMa (editor), RGM6 (base game), and RGM9 (expansion) formats.
    Uses pattern-matching to find Unit Pattern groups rather than sequential parsing.

    Args:
        filepath: Path to the .q file

    Returns:
        QuestMap data structure with parsed content

    Raises:
        QFormatError: If the file has invalid magic or corrupted structure
        FileNotFoundError: If the file doesn't exist
    """
    filepath = Path(filepath)
    if not filepath.exists():
        raise FileNotFoundError(f"Quest file not found: {filepath}")

    data = filepath.read_bytes()
    if len(data) < 16:
        raise QFormatError(f"File too small ({len(data)} bytes): {filepath}")

    # --- Header ---
    magic_bytes = data[0:4]
    if magic_bytes not in VALID_MAGICS:
        raise QFormatError(
            f"Invalid magic {magic_bytes!r} in {filepath}. "
            f"Expected one of: {[m.decode() for m in VALID_MAGICS]}"
        )
    magic = magic_bytes.decode('ascii')

    # Verify repeated magic at offset 8
    magic2 = data[8:12]
    if magic2 != magic_bytes:
        raise QFormatError(
            f"Magic mismatch: header has {magic_bytes!r} but offset 8 has {magic2!r}"
        )

    # --- Quest name ---
    try:
        quest_name, after_name = _read_cstr(data, 16)
    except ValueError:
        raise QFormatError(f"Cannot find null-terminated quest name after header")

    # --- Pattern name (12 bytes of content, may include non-ASCII) ---
    pattern_end = after_name + 12
    if pattern_end > len(data):
        pattern_end = len(data)
    pattern_name = data[after_name:pattern_end]
    try:
        pattern_null = data.index(0, after_name)
        if pattern_null < pattern_end:
            pattern_name = data[after_name:pattern_null]
    except ValueError:
        pass


    # --- Map parameters (best effort) ---
    params = MapParams()

    # --- Spawner blocks ---
    spawner_blocks = _find_spawner_blocks(data)

    # --- Teams (placeholder — full parsing is complex and not needed) ---
    teams: list[TeamDefinition] = []

    # --- Region info (placeholder — preserved opaquely by template writer) ---
    region_info: Optional[RegionPatternInfo] = None

    # --- Unit Patterns (the critical part) ---
    pattern_candidates = _find_unit_patterns(data)
    unit_patterns = []
    for offset, terrain_code, count in pattern_candidates:
        try:
            entries, end_pos = _parse_unit_instances(data, offset + 12, count)
            pattern = UnitPattern(
                terrain_code=terrain_code,
                entries=entries,
                faction_name="",
            )
            # Try to read faction name from metadata block
            # Metadata: 10 x u32 then null-terminated string
            meta_start = end_pos
            if meta_start + 40 < len(data):
                first_val = struct.unpack_from('<I', data, meta_start)[0]
                if first_val == 0:
                    fname_start = meta_start + 40
                    if fname_start < len(data):
                        try:
                            fname, _ = _read_cstr(data, fname_start)
                            if len(fname) < 50 and all(32 <= ord(c) < 127 for c in fname):
                                pattern.faction_name = fname
                        except (ValueError, IndexError):
                            pass

            unit_patterns.append(pattern)
        except QFormatError:
            # Skip patterns that fail to parse (false positive in pattern matching)
            continue

    # --- Force Pattern (best effort) ---
    force_pattern: list[ForceEntry] = []

    return QuestMap(
        magic=magic,
        quest_name=quest_name,
        pattern_name=pattern_name,
        params=params,
        spawner_blocks=spawner_blocks,
        teams=teams,
        region_info=region_info,
        unit_patterns=unit_patterns,
        force_pattern=force_pattern,
    )


# =============================================================================
# Writer (Template-based)
# =============================================================================

# The writer uses a template .q file (e.g., MyQuest/Quest.q) and splices in
# modified Unit Pattern sections. This ensures the header, spawner blocks,
# metadata, and player sections are preserved from a known-working file.

DEFAULT_TEMPLATE = Path(__file__).parent.parent / "MyQuest" / "Quest.q"

# =============================================================================
# Terrain Presets
# =============================================================================
# Each preset defines the Region Pattern section bytes for a terrain type.
# The section structure (from MyQuest reverse-engineering) is:
#   [u32 1]["pattpattpattern\0"][7B zeros][u32 0][u32 patch_count]
#   For each patch: [4B terrain_code + settings bytes]
#   Then: [u32 landscape_count] [terrain_pattern_name\0] [landscape_name\0] [zeros] × per patch
#
# We generate the full region section from the "pattpattpattern" marker to the end
# (just before the faction name that precedes placed groups).

def _build_region_section(patches: list[dict]) -> bytes:
    """
    Build a Region Pattern binary section from patch definitions.
    
    Each patch dict has:
      - terrain_code: 4-char code (e.g., "gras")
      - terrain_value: string value after code (e.g., "3")
      - fractal_value: int (e.g., 13 for snow)
      - terrain_pattern: full pattern name (e.g., "grasgrasgrasgrass")
      - landscape_pattern: landscape ref (e.g., "xBarxGraxfla")
    """
    parts = []
    
    # Pattern header: [u32 1] "pattpattpattern\0" [7 zeros] [u32 0]
    parts.append(struct.pack('<I', 1))
    parts.append(b'pattpattpattern\x00')
    parts.append(b'\x00' * 7)
    parts.append(struct.pack('<I', 0))
    
    # Patch count
    parts.append(struct.pack('<I', len(patches)))
    
    # Each patch: [4B code][value\0][zeros to pad][u32 fractal][zeros][u32 1][zeros]
    for patch in patches:
        code = patch['terrain_code'].encode('ascii')[:4]
        value_str = patch.get('terrain_value', '3').encode('ascii') + b'\x00'
        fractal = patch.get('fractal_value', 0)
        
        parts.append(code)
        parts.append(value_str)
        # Pad to align: terrain code (4) + value_str + zeros to fill 16 bytes total from code start
        current_patch_len = len(code) + len(value_str)
        pad_needed = 16 - current_patch_len
        if pad_needed > 0:
            parts.append(b'\x00' * pad_needed)
        # Fractal/flags block
        if fractal > 0:
            parts.append(struct.pack('<I', fractal))
            parts.append(b'\x00' * 4)
        # Active flag
        parts.append(struct.pack('<I', 1))
        parts.append(b'\x00' * 4)
    
    # Landscape references: [u32 count] then for each patch: [terrain_pattern\0][landscape\0][zeros]
    parts.append(struct.pack('<I', len(patches)))
    for patch in patches:
        tp = patch['terrain_pattern'].encode('ascii') + b'\x00'
        lp = patch['landscape_pattern'].encode('ascii') + b'\x00'
        parts.append(tp)
        parts.append(lp)
        parts.append(b'\x00' * 7)  # padding between landscape entries
    
    return b''.join(parts)


# Terrain presets — each maps to known-good pattern combinations from constants.rgs
TERRAIN_PRESETS = {
    "grass": {
        "patches": [
            {
                "terrain_code": "gras",
                "terrain_value": "3",
                "fractal_value": 0,
                "terrain_pattern": "grasgrasgrasgrass",
                "landscape_pattern": "xBarxGraxfla",
            },
        ],
    },
    "grass_snow": {
        "patches": [
            {
                "terrain_code": "gras",
                "terrain_value": "3",
                "fractal_value": 0,
                "terrain_pattern": "grasgrasgrasgrass",
                "landscape_pattern": "xBarxGraxfla",
            },
            {
                "terrain_code": "snow",
                "terrain_value": "1",
                "fractal_value": 13,
                "terrain_pattern": "snowsnowsnow",
                "landscape_pattern": "xClcxSnoFS01",
            },
        ],
    },
    "scorched": {
        "patches": [
            {
                "terrain_code": "scor",
                "terrain_value": "5",
                "fractal_value": 0,
                "terrain_pattern": "#Sca#Sca#Scorched_All_Parent",
                "landscape_pattern": "xScaxSca#Scorched_Ponds_and_Misc",
            },
        ],
    },
    "swamp": {
        "patches": [
            {
                "terrain_code": "swam",
                "terrain_value": "7",
                "fractal_value": 0,
                "terrain_pattern": "#Swa#Swa#Swamp_Mostly_Parent",
                "landscape_pattern": "xSwaxSwa#Swamp_Light_Wood",
            },
        ],
    },
    "arid": {
        "patches": [
            {
                "terrain_code": "arid",
                "terrain_value": "3",
                "fractal_value": 0,
                "terrain_pattern": "#Ara#Ara#Arrid_Mosty_Parent",
                "landscape_pattern": "xAraxAra#Arid_Tiny_Rocks",
            },
        ],
    },
    "snow": {
        "patches": [
            {
                "terrain_code": "snow",
                "terrain_value": "1",
                "fractal_value": 13,
                "terrain_pattern": "snowsnowsnow",
                "landscape_pattern": "xClcxSnoFS01",
            },
        ],
    },
}


def _find_region_section_bounds(data: bytes, first_pattern_offset: int) -> tuple[int, int]:
    """
    Find the start and end of the Region Pattern section in template data.
    Start: the "pattpattpattern" marker.
    End: just before the faction name + count that precedes placed groups.
    
    Returns (region_start, region_end) offsets.
    """
    # Find "pattpattpattern" in the data (before first_pattern_offset)
    marker = b'pattpattpattern'
    region_start = data.rfind(marker, 0, first_pattern_offset)
    if region_start == -1:
        return (-1, -1)
    
    # Back up 4 bytes to include the u32 before the pattern name
    region_start -= 4
    
    # End is at the faction name block before the first placed group
    # The faction name block is: [u32 count] [faction_4+4+full_name\0] [zeros] [u32 unit_count]
    # It's right before splice_start (first_pattern_offset - 8)
    # Let's find it by looking for the last faction name before the placed groups
    # The pattern is: [u32 N] "XxxxXxxxFull Name\0" [zeros] [u32 count] [gras...]
    
    # Simple approach: region ends where the faction assignment block begins
    # That's typically 30-40 bytes before the first placed group
    # Look for the u32 faction_count + faction name pattern
    search_end = first_pattern_offset - 4
    # Scan backwards from first_pattern_offset for the faction entry count
    for probe in range(search_end, max(region_start, search_end - 60), -1):
        # Check if this is a plausible count followed by a 4+4+name pattern
        try:
            val = struct.unpack_from('<I', data, probe)[0]
            if 1 <= val <= 20:
                # Check if 4 bytes later starts a faction name (4+4+full)
                check_pos = probe + 4
                if check_pos + 8 < first_pattern_offset:
                    candidate = data[check_pos:check_pos + 8]
                    if all(32 <= b < 127 for b in candidate):
                        # Verify: does it follow 4+4 pattern?
                        if candidate[:4] == candidate[4:8]:
                            # This looks like the faction block start
                            return (region_start, probe)
        except:
            pass
    
    # Fallback: region ends 40 bytes before first group (the faction block is ~35-45 bytes)
    return (region_start, first_pattern_offset - 40)


# Standard metadata block that appears after each unit pattern's entries
# [u32 0][u32 3][u32 50][u32 50][u32 50][u32 1][u32 1][12B zeros] = 40 bytes
METADATA_BLOCK = struct.pack('<10I',
    0,    # separator
    3,    # unknown (always 3)
    50,   # resource limit?
    50,   # resource limit?
    50,   # resource limit?
    1,    # unknown flag
    1,    # unknown flag
    0, 0, 0  # padding zeros
)


def _encode_unit_instance(entry: UnitInstance) -> bytes:
    """Encode a single UnitInstance entry to binary."""
    parts = []
    # Object ID (4 bytes, ASCII)
    obj_id_bytes = entry.object_id.encode('ascii')
    if len(obj_id_bytes) != 4:
        raise QFormatError(f"Object ID must be exactly 4 chars, got {entry.object_id!r}")
    parts.append(obj_id_bytes)
    # Zero field (u32)
    parts.append(struct.pack('<I', 0))
    # Description (null-terminated)
    parts.append(entry.description.encode('ascii') + b'\x00')
    # Candidate cell count (u32)
    parts.append(struct.pack('<I', len(entry.candidate_cells)))
    # Candidate cell position bytes
    for pos in entry.candidate_cells:
        if not (65 <= pos <= 89):
            raise QFormatError(f"Invalid position {pos} in entry {entry.object_id}")
        parts.append(bytes([pos]))
    return b''.join(parts)


def _encode_unit_pattern(pattern: UnitPattern) -> bytes:
    """Encode a UnitPattern header + entries (no metadata block)."""
    parts = []
    # Terrain code (4 bytes)
    terrain = pattern.terrain_code.encode('ascii')
    if len(terrain) != 4:
        terrain = (terrain + b'    ')[:4]
    parts.append(terrain)
    # Constant marker (u32 = 5) — the resolution value
    parts.append(struct.pack('<I', 5))
    # Entry count
    parts.append(struct.pack('<I', len(pattern.entries)))
    # Entries
    for entry in pattern.entries:
        parts.append(_encode_unit_instance(entry))
    return b''.join(parts)


def _encode_faction_name_block(faction_name: str) -> bytes:
    """
    Encode the faction name that appears in the metadata gap.
    Format: [12-char name (4+4+4 pattern)]\\0[padding zeros]\\0
    """
    name_bytes = faction_name.encode('ascii')
    short = faction_name[:4]
    pattern_12 = (short * 3)[:12].encode('ascii')
    full_with_null = name_bytes + b'\x00'
    return pattern_12 + full_with_null


def _encode_pre_group_block(owner_entry_count: int) -> bytes:
    """Encode the bytes that appear just before a unit pattern: [zeros][u32 count]."""
    return struct.pack('<III', 0, 0, owner_entry_count)


def write_q_file(
    unit_patterns: list[UnitPattern],
    output_path,
    template_path=None,
    quest_name: Optional[str] = None,
    terrain: Optional[str] = None,
) -> Path:
    """
    Write a .q file using a minimal-splice approach.

    Replaces the entry data within existing template pattern slots while preserving
    all structural bytes (metadata, faction transitions, Force Pattern, Region Pattern).

    The template has 4 pattern slots. Patterns are assigned by index:
      - Index 0: "Goblin Kingdom" — enemy monster lairs
      - Index 1: "AutoExpanding" — neutral expanding faction
      - Index 2: "Player1" — human player's buildings
      - Index 3: "player2_ai" — AI opponent's buildings

    If fewer than 4 UnitPatterns are provided, unspecified slots keep their
    template entries. If a slot should be emptied, pass a UnitPattern with
    entries=[] (NOT YET SUPPORTED — leaves template entries).

    Args:
        unit_patterns: List of UnitPattern objects (max 4, mapped by index to template slots)
        output_path: Where to write the output .q file
        template_path: Path to template .q file (default: MyQuest/Quest.q)
        quest_name: Unused (preserved for API compatibility)
        terrain: Unused (terrain modification not yet validated in-game)

    Returns:
        Path to the written file

    Raises:
        QFormatError: If encoding fails or template has unexpected structure
        FileNotFoundError: If template doesn't exist
    """
    if template_path is None:
        template_path = DEFAULT_TEMPLATE
    template_path = Path(template_path)
    output_path = Path(output_path)

    if not template_path.exists():
        raise FileNotFoundError(f"Template file not found: {template_path}")

    # Read template
    template_data = bytearray(template_path.read_bytes())

    # Find all unit patterns in the template
    template_patterns = _find_unit_patterns(bytes(template_data))
    if not template_patterns:
        raise QFormatError(f"Template has no unit patterns: {template_path}")

    if len(unit_patterns) > len(template_patterns):
        raise QFormatError(
            f"Cannot write {len(unit_patterns)} patterns — template only has "
            f"{len(template_patterns)} slots. Reduce to {len(template_patterns)} or fewer."
        )

    # Splice each provided pattern into the template, working backwards
    # (so earlier offsets aren't invalidated by size changes from later splices)
    for i in reversed(range(len(unit_patterns))):
        pattern = unit_patterns[i]
        if not pattern.entries:
            continue  # Skip empty patterns — leave template entries intact

        tmpl_off, tmpl_terrain, tmpl_count = template_patterns[i]
        tmpl_extent = _compute_group_extent(bytes(template_data), tmpl_off, tmpl_count)
        if tmpl_extent is None:
            raise QFormatError(
                f"Cannot compute extent of template pattern {i} at offset 0x{tmpl_off:04x}"
            )

        # Encode new entries
        new_entry_bytes = b''.join(_encode_unit_instance(e) for e in pattern.entries)
        new_count = len(pattern.entries)

        # The pattern header is: [4B terrain][u32 5][u32 count][entries...]
        # We replace [u32 count][entries...] (from offset+8 to extent)
        count_offset = tmpl_off + 8  # After terrain(4) + resolution(4)
        entries_start = tmpl_off + 12  # After the full 12-byte header

        # Splice: replace count + entries
        new_section = struct.pack('<I', new_count) + new_entry_bytes
        template_data[count_offset:tmpl_extent] = new_section

    # Write output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(bytes(template_data))

    return output_path


def write_q_file_simple(
    entries: list[UnitInstance],
    output_path,
    template_path=None,
) -> Path:
    """
    Simplified writer: places entries in the Player1 slot (index 2).

    Automatically includes a Palace at center if not already in entries.
    This is the easiest way to generate a test quest map.
    """
    # Ensure Palace is present
    has_palace = any(e.object_id == "ABJ1" for e in entries)
    if not has_palace:
        entries = [UnitInstance("ABJ1", "Palace", [CENTER])] + entries

    pattern = UnitPattern(
        terrain_code="gras",
        entries=entries,
        faction_name="Player1",
    )

    # Place in slot 2 (Player1). Provide empty patterns for slots 0-1 to skip them.
    patterns = [
        UnitPattern(entries=[]),  # slot 0: keep template Goblin Kingdom
        UnitPattern(entries=[]),  # slot 1: keep template AutoExpanding
        pattern,                  # slot 2: Player1 — our entries
    ]
    return write_q_file(patterns, output_path, template_path)


# =============================================================================
# MQXML Generator
# =============================================================================

def generate_mqxml(
    quest_name: str,
    output_path,
    dataset_base: str = "Majesty",
    q_filename: str = None,
    rgs_filename: str = None,
    gpl_sources: list[str] = None,
    gpl_target: str = None,
    descriptions: list[str] = None,
    display_name: str = None,
    description_short: str = None,
    description_long: str = None,
    difficulty: str = "Normal",
) -> Path:
    """
    Generate a .mqxml quest definition file.

    Args:
        quest_name: Internal quest name (used in Name element)
        output_path: Where to write the .mqxml
        dataset_base: "Majesty" or "MajestyExpansion"
        q_filename: Name of the .q file (default: Quest.q)
        rgs_filename: Name of the .rgs file (default: Quest.rgs)
        gpl_sources: List of GPL source file paths
        gpl_target: GPL bytecode target path
        descriptions: List of description XML file paths
        display_name: Human-readable quest name
        description_short: Short description text
        description_long: Long description text
        difficulty: "Easy", "Normal", "Hard"

    Returns:
        Path to the written .mqxml file
    """
    import uuid

    output_path = Path(output_path)


    if q_filename is None:
        q_filename = "Quest.q"
    if rgs_filename is None:
        rgs_filename = "Quest.rgs"
    if display_name is None:
        display_name = quest_name
    if description_short is None:
        description_short = f"Test quest: {quest_name}"
    if description_long is None:
        description_long = description_short

    # Generate a GUID
    quest_guid = f"{{{str(uuid.uuid4()).upper()}}}"

    # Build Load section
    load_lines = []
    load_lines.append(f'\t\t\t\t\t<Template>{q_filename}</Template>')
    load_lines.append(f'\t\t\t\t\t<Constants>{rgs_filename}</Constants>')

    if gpl_sources or gpl_target:
        if gpl_sources:
            # Full GPL section with Target + Source entries
            load_lines.append('\t\t\t\t\t<GPL>')
            if gpl_target:
                load_lines.append(f'\t\t\t\t\t\t<Target>{gpl_target}</Target>')
            for src in gpl_sources:
                load_lines.append(f'\t\t\t\t\t\t<Source>{src}</Source>')
            load_lines.append('\t\t\t\t\t</GPL>')
        else:
            # Simple GPL — just the .bcd path
            load_lines.append(f'\t\t\t\t\t<GPL>{gpl_target}</GPL>')

    if descriptions:
        for desc_file in descriptions:
            load_lines.append(f'\t\t\t\t\t<Descriptions>{desc_file}</Descriptions>')

    load_section = '\n'.join(load_lines)

    mqxml = f'''<Majesty>
\t<Quest id="{quest_guid}">
\t\t<DataConfiguration>
\t\t\t<Dataset base="{dataset_base}">
\t\t\t\t<Load>
{load_section}
\t\t\t\t</Load>
\t\t\t</Dataset>
\t\t</DataConfiguration>
\t\t<DisplayName lang="en_US">{display_name}</DisplayName>
\t\t<Description lang="en_US">
\t\t\t<Short>{description_short}</Short>
\t\t\t<Long>{description_long}</Long>
\t\t</Description>
\t\t<Difficulty>{difficulty}</Difficulty>
\t\t<Name>{quest_name}</Name>
\t</Quest>
</Majesty>
'''

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(mqxml, encoding='utf-8')
    return output_path


# =============================================================================
# Terrain File Handling
# =============================================================================

DEFAULT_RGS_TEMPLATE = Path(__file__).parent.parent / "MyQuest" / "Quest.rgs"


def copy_terrain_template(
    output_dir,
    output_name: str = "Quest.rgs",
    template_path=None,
) -> Path:
    """
    Copy a .rgs terrain template to the output directory.

    Args:
        output_dir: Directory to copy the .rgs into
        output_name: Filename for the output .rgs
        template_path: Path to source .rgs (default: MyQuest/Quest.rgs)

    Returns:
        Path to the copied .rgs file

    Raises:
        FileNotFoundError: If template doesn't exist
        QFormatError: If template doesn't have valid RGS magic
    """
    import shutil

    if template_path is None:
        template_path = DEFAULT_RGS_TEMPLATE
    template_path = Path(template_path)

    if not template_path.exists():
        raise FileNotFoundError(f"RGS template not found: {template_path}")

    # Validate RGS magic
    with open(template_path, 'rb') as f:
        magic = f.read(4)
    if magic not in (b'RGCB', b'RGCA'):
        raise QFormatError(
            f"Invalid RGS magic {magic!r} in {template_path}. Expected RGCB or RGCA."
        )

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / output_name
    shutil.copy2(template_path, output_path)
    return output_path


# =============================================================================
# High-Level Convenience API
# =============================================================================

def generate_test_quest(
    quest_name: str,
    lairs: list[dict],
    output_dir,
    palace_position: str = "M",
    starting_gold: int = 50000,
    dataset_base: str = "MajestyExpansion",
    terrain: Optional[str] = None,
    extra_gpl_sources: list[str] = None,
    extra_gpl_target: str = None,
    extra_descriptions: list[str] = None,
    rgs_template: str = None,
) -> dict:
    """
    Generate a complete test quest package (Q file + RGS + MQXML).

    This is the one-call API for creating a minimal quest with a palace
    and specified lairs, ready for in-game loading.

    Args:
        quest_name: Quest name (used in filenames and metadata)
        lairs: List of lair specs, each a dict with keys:
            - "id": Object_ID (e.g., "BBw1")
            - "desc": Description string (e.g., "Ice Cave")
            - "position": Optional grid letter "A"-"Y" (auto-distributed if omitted)
        output_dir: Directory to write the quest package into
        palace_position: Grid letter for palace (default "M" = center)
        starting_gold: Starting gold for the quest
        dataset_base: "Majesty" or "MajestyExpansion"
        terrain: Terrain preset name (grass, grass_snow, scorched, swamp, arid, snow)
                 Default None = use template's terrain unchanged.
                 Snow requires dataset_base="MajestyExpansion".
        extra_gpl_sources: Additional GPL source files to load
        extra_gpl_target: GPL bytecode target
        extra_descriptions: Additional description XML files
        rgs_template: Custom .rgs template path (default: MyQuest/Quest.rgs)

    Returns:
        Dict with paths: {"q": Path, "rgs": Path, "mqxml": Path}

    Example:
        generate_test_quest(
            "IceTest",
            [{"id": "BBw1", "desc": "Ice Cave"}, {"id": "BBH1", "desc": "Goblin Camp"}],
            "output/IceTest"
        )
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    palace_byte = letter_to_byte(palace_position)

    # Write .q file — place all entries in slot 2 (Player1) so they're near the player
    player_entries = [UnitInstance("ABJ1", "Palace", [palace_byte])]

    # Distribute lairs into the player's pattern (near the Palace)
    lairs_needing_positions = []
    excluded = [palace_byte]

    for lair in lairs:
        if "position" in lair and lair["position"]:
            pos_byte = letter_to_byte(lair["position"])
            player_entries.append(UnitInstance(lair["id"], lair["desc"], [pos_byte]))
            excluded.append(pos_byte)
        else:
            lairs_needing_positions.append(lair)

    if lairs_needing_positions:
        positions = auto_distribute(len(lairs_needing_positions), exclude=excluded)
        for lair, pos_byte in zip(lairs_needing_positions, positions):
            player_entries.append(UnitInstance(lair["id"], lair["desc"], [pos_byte]))

    # Build pattern list: slot 0 = keep template, slot 1 = keep template, slot 2 = player + lairs
    patterns = [
        UnitPattern(entries=[]),  # slot 0: keep template Goblin Kingdom
        UnitPattern(entries=[]),  # slot 1: keep template AutoExpanding
        UnitPattern(terrain_code="gras", entries=player_entries, faction_name="Player1"),
    ]

    q_path = write_q_file(
        patterns,
        output_dir / "Quest.q",
        template_path=rgs_template if rgs_template else None,
    )

    # Copy .rgs terrain
    rgs_path = copy_terrain_template(
        output_dir,
        output_name="Quest.rgs",
        template_path=rgs_template,
    )

    # Generate .mqxml
    # The <Name> tag is the GPL init function to call. Use "DefaultQuest" which
    # is defined in QuestMapGenerator/GPL/default_quest.bcd and provides a
    # simple "destroy all enemies" victory condition.
    # Copy the default BCD into the output directory
    default_bcd = Path(__file__).parent / "GPL" / "default_quest.bcd"
    if default_bcd.exists():
        import shutil
        data_dir = output_dir / "Data"
        data_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(default_bcd, data_dir / "default_quest.bcd")
        gpl_target_final = extra_gpl_target or r"Data\default_quest.bcd"
    else:
        gpl_target_final = extra_gpl_target

    mqxml_path = generate_mqxml(
        quest_name="DefaultQuest",
        output_path=output_dir / "Quest.mqxml",
        dataset_base=dataset_base,
        display_name=quest_name,
        description_short=f"Test quest: {quest_name}",
        gpl_sources=extra_gpl_sources,
        gpl_target=gpl_target_final,
        descriptions=extra_descriptions,
    )

    return {"q": q_path, "rgs": rgs_path, "mqxml": mqxml_path}


# =============================================================================
# Pretty-print
# =============================================================================

def format_q_text(qmap: QuestMap) -> str:
    """Format a QuestMap as human-readable text."""
    lines = []
    lines.append(f"=== Quest Map: {qmap.quest_name} ===")
    lines.append(f"Magic: {qmap.magic}")
    lines.append(f"Pattern: {qmap.pattern_name}")
    lines.append(f"Map size: {qmap.params.width}x{qmap.params.height}")
    lines.append("")

    if qmap.spawner_blocks:
        lines.append(f"--- Spawner Blocks ({len(qmap.spawner_blocks)}) ---")
        for i, block in enumerate(qmap.spawner_blocks):
            ids = ', '.join(f"{e.object_id}(lv{e.spawn_level})" for e in block.entries)
            lines.append(f"  Block {i}: [{ids}] resource={block.lair_resource}")
        lines.append("")

    if qmap.teams:
        lines.append(f"--- Teams ({len(qmap.teams)}) ---")
        for t in qmap.teams:
            lines.append(f"  {t.name} (id={t.team_id}, active={t.active})")
        lines.append("")

    if qmap.region_info:
        lines.append(f"--- Region Pattern ---")
        lines.append(f"  Name: {qmap.region_info.pattern_name}")
        lines.append(f"  Patches: {qmap.region_info.patch_count}")
        lines.append(f"  Terrains: {qmap.region_info.terrain_codes}")
        lines.append("")

    if qmap.unit_patterns:
        lines.append(f"--- Unit Patterns ({len(qmap.unit_patterns)}) ---")
        for i, pattern in enumerate(qmap.unit_patterns):
            total_cells = sum(len(e.candidate_cells) for e in pattern.entries)
            lines.append(
                f"  Pattern {i}: terrain={pattern.terrain_code!r} "
                f"entries={len(pattern.entries)} candidate_cells={total_cells} "
                f"faction={pattern.faction_name!r}"
            )
            for entry in pattern.entries:
                pos_str = ''.join(chr(p) for p in entry.candidate_cells)
                lines.append(
                    f"    {entry.object_id} {entry.description!r} @ [{pos_str}]"
                )
        lines.append("")


    if qmap.force_pattern:
        lines.append(f"--- Force Pattern ({len(qmap.force_pattern)}) ---")
        for fe in qmap.force_pattern:
            lines.append(
                f"  {fe.short_code} {fe.full_name!r} pos={chr(fe.map_position)} active={fe.active}"
            )
        lines.append("")

    # Grid visualization
    lines.append("--- Grid (5x5) ---")
    grid = {}
    for pattern in qmap.unit_patterns:
        for entry in pattern.entries:
            for pos in entry.candidate_cells:
                grid[pos] = entry.object_id
    for row in range(5):
        row_cells = []
        for col in range(5):
            byte_val = 65 + row * 5 + col
            letter = chr(byte_val)
            if byte_val in grid:
                row_cells.append(f"[{grid[byte_val]}]")
            else:
                row_cells.append(f"  {letter}   ")
        lines.append("  " + " ".join(row_cells))

    return "\n".join(lines)


# =============================================================================
# Validation
# =============================================================================

@dataclass
class ValidationIssue:
    offset: int
    severity: str  # "error" or "warning"
    message: str


def validate_q_file(filepath) -> list[ValidationIssue]:
    """
    Validate a .q file's structural integrity.

    Checks magic bytes, object IDs, position bytes, and structural consistency.
    Returns a list of issues found (empty = valid).
    """
    filepath = Path(filepath)
    issues = []

    if not filepath.exists():
        issues.append(ValidationIssue(0, "error", f"File not found: {filepath}"))
        return issues

    data = filepath.read_bytes()

    # Check file size
    if len(data) < 16:
        issues.append(ValidationIssue(0, "error", f"File too small: {len(data)} bytes"))
        return issues

    # Check magic at offset 0
    magic = data[0:4]
    if magic not in VALID_MAGICS:
        issues.append(ValidationIssue(0, "error", f"Invalid magic: {magic!r}"))

    # Check magic repeated at offset 8
    magic2 = data[8:12]
    if magic2 != magic:
        issues.append(ValidationIssue(8, "error", f"Magic mismatch at offset 8: {magic2!r} != {magic!r}"))

    # Check zeros at 4-7 and 12-15
    if data[4:8] != b'\x00\x00\x00\x00':
        issues.append(ValidationIssue(4, "warning", f"Expected zeros at offset 4-7"))
    if data[12:16] != b'\x00\x00\x00\x00':
        issues.append(ValidationIssue(12, "warning", f"Expected zeros at offset 12-15"))


    # Try to parse and check unit patterns
    try:
        qmap = parse_q_file(filepath)

        # Check all object IDs are valid
        for pattern in qmap.unit_patterns:
            for entry in pattern.entries:
                oid = entry.object_id
                if len(oid) != 4:
                    issues.append(ValidationIssue(0, "error", f"Object ID not 4 chars: {oid!r}"))
                elif not all(32 <= ord(c) < 127 for c in oid):
                    issues.append(ValidationIssue(0, "error", f"Object ID has non-ASCII: {oid!r}"))

                # Check candidate cells
                for pos in entry.candidate_cells:
                    if not (65 <= pos <= 89):
                        issues.append(ValidationIssue(0, "error",
                            f"Invalid position {pos} in {oid} (expected 65-89)"))

        # Check for empty quest name
        if not qmap.quest_name:
            issues.append(ValidationIssue(16, "warning", "Empty quest name"))

        # Check unit patterns found
        if not qmap.unit_patterns:
            issues.append(ValidationIssue(0, "warning", "No unit patterns found"))

    except QFormatError as e:
        issues.append(ValidationIssue(0, "error", f"Parse error: {e}"))
    except Exception as e:
        issues.append(ValidationIssue(0, "error", f"Unexpected error: {e}"))

    return issues


def compare_q_files(generated_path, reference_path) -> list[str]:
    """
    Compare structural properties between a generated .q file and a reference.
    Returns list of difference descriptions.
    """
    diffs = []

    gen = parse_q_file(generated_path)
    ref = parse_q_file(reference_path)

    if gen.magic != ref.magic:
        diffs.append(f"Magic: {gen.magic} vs {ref.magic}")

    gen_patterns = len(gen.unit_patterns)
    ref_patterns = len(ref.unit_patterns)
    if gen_patterns != ref_patterns:
        diffs.append(f"Unit patterns: {gen_patterns} vs {ref_patterns}")

    gen_entries = sum(len(p.entries) for p in gen.unit_patterns)
    ref_entries = sum(len(p.entries) for p in ref.unit_patterns)
    if gen_entries != ref_entries:
        diffs.append(f"Total entries: {gen_entries} vs {ref_entries}")

    gen_cells = sum(len(e.candidate_cells) for p in gen.unit_patterns for e in p.entries)
    ref_cells = sum(len(e.candidate_cells) for p in ref.unit_patterns for e in p.entries)
    if gen_cells != ref_cells:
        diffs.append(f"Total candidate_cells: {gen_cells} vs {ref_cells}")

    gen_spawners = len(gen.spawner_blocks)
    ref_spawners = len(ref.spawner_blocks)
    if gen_spawners != ref_spawners:
        diffs.append(f"Spawner blocks: {gen_spawners} vs {ref_spawners}")

    return diffs


# =============================================================================
# CLI
# =============================================================================

def _cli_parse(args):
    """CLI: parse a .q file and print formatted output."""
    if not args:
        print("Usage: quest_map_generator.py parse <file.q>")
        return 1
    qmap = parse_q_file(args[0])
    print(format_q_text(qmap))
    return 0


def _cli_validate(args):
    """CLI: validate a .q file."""
    if not args:
        print("Usage: quest_map_generator.py validate <file.q> [--reference <ref.q>]")
        return 1

    filepath = args[0]
    reference = None
    if "--reference" in args:
        ref_idx = args.index("--reference")
        if ref_idx + 1 < len(args):
            reference = args[ref_idx + 1]

    print(f"Validating: {filepath}")
    issues = validate_q_file(filepath)

    if issues:
        for issue in issues:
            prefix = "ERROR" if issue.severity == "error" else "WARN"
            print(f"  [{prefix}] @0x{issue.offset:04X}: {issue.message}")
    else:
        print("  No issues found.")

    if reference:
        print(f"\nComparing to reference: {reference}")
        diffs = compare_q_files(filepath, reference)
        if diffs:
            for d in diffs:
                print(f"  DIFF: {d}")
        else:
            print("  Structures match.")

    errors = [i for i in issues if i.severity == "error"]
    return 1 if errors else 0


def _cli_generate(args):
    """CLI: generate a test quest."""
    import argparse
    parser = argparse.ArgumentParser(prog="quest_map_generator.py generate")
    parser.add_argument("--name", required=True, help="Quest name")
    parser.add_argument("--output", required=True, help="Output directory")
    parser.add_argument("--lairs", default="", help="Comma-separated lair specs: ID:Desc:Pos (pos optional)")
    parser.add_argument("--dataset", default="MajestyExpansion", choices=["Majesty", "MajestyExpansion"])
    parser.add_argument("--palace", default="M", help="Palace grid position (A-Y)")
    parser.add_argument("--map-size", type=int, default=256, choices=[128, 256, 512], help="Map size in tiles")
    parser.add_argument("--terrain", default="grass", help="Terrain preset (grass, snow, forest, etc.)")
    parser.add_argument("--use-template", action="store_true", help="Use old template-splice approach instead of create_quest()")
    parser.add_argument("--deploy", action="store_true", help="Auto-copy quest to game's Quests folder")
    parser.add_argument("--seed", type=int, default=0, help="Random seed (0 = different each play)")

    try:
        parsed = parser.parse_args(args)
    except SystemExit:
        return 1

    # Parse lair specs
    lairs = []
    if parsed.lairs:
        for spec in parsed.lairs.split(","):
            parts = spec.strip().split(":")
            if len(parts) >= 2:
                lair = {"id": parts[0], "desc": parts[1]}
                if len(parts) >= 3 and parts[2]:
                    lair["position"] = parts[2]
                lairs.append(lair)
            elif len(parts) == 1 and parts[0]:
                lairs.append({"id": parts[0], "desc": parts[0]})

    if parsed.use_template:
        # Old template-splice approach
        result = generate_test_quest(
            quest_name=parsed.name,
            lairs=lairs,
            output_dir=parsed.output,
            palace_position=parsed.palace,
            dataset_base=parsed.dataset,
        )
    else:
        # New approach: use rgs_format.create_quest()
        from rgs_format import create_quest, write_quest_file, TERRAIN_PRESETS
        from pathlib import Path
        import shutil

        output_dir = Path(parsed.output)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Build unit patterns
        palace_cell = ord(parsed.palace)
        player_entries = [{"id": "ABJ1", "desc": "Palace", "cells": [palace_cell]}]
        lair_entries = []
        auto_positions = [65, 69, 85, 70, 80, 74, 84, 68, 88]  # A,E,U,F,P,J,T,D,X
        auto_idx = 0
        for lair in lairs:
            if "position" in lair and lair["position"]:
                cells = [ord(lair["position"])]
            else:
                cells = [auto_positions[auto_idx % len(auto_positions)]]
                auto_idx += 1
            lair_entries.append({"id": lair["id"], "desc": lair["desc"], "cells": cells})

        unit_patterns = [
            {"name": "Player1", "entries": player_entries + lair_entries,
             "starting_gold": 50000},
        ]

        # Validate terrain preset
        terrain = parsed.terrain
        if terrain not in TERRAIN_PRESETS and not isinstance(terrain, dict):
            print(f"Warning: Unknown terrain preset '{terrain}', using 'grass'")
            print(f"Available: {sorted(TERRAIN_PRESETS.keys())}")
            terrain = "grass"

        qf = create_quest(
            name=parsed.name,
            unit_patterns=unit_patterns,
            map_size=(parsed.map_size, parsed.map_size),
            terrain=terrain,
            seed=parsed.seed,
        )

        q_path = write_quest_file(qf, output_dir / "Quest.q")

        # Copy .rgs terrain template
        rgs_src = Path(__file__).parent.parent / "MyQuest" / "Quest.rgs"
        rgs_path = output_dir / "Quest.rgs"
        if rgs_src.exists():
            shutil.copy2(rgs_src, rgs_path)

        # Copy default GPL bytecode
        default_bcd = Path(__file__).parent / "GPL" / "default_quest.bcd"
        data_dir = output_dir / "Data"
        data_dir.mkdir(parents=True, exist_ok=True)
        if default_bcd.exists():
            shutil.copy2(default_bcd, data_dir / "default_quest.bcd")
            gpl_target = r"Data\default_quest.bcd"
        else:
            gpl_target = None

        # Generate .mqxml
        mqxml_path = generate_mqxml(
            quest_name="DefaultQuest",
            output_path=output_dir / "Quest.mqxml",
            dataset_base=parsed.dataset,
            display_name=parsed.name,
            description_short=f"Test quest: {parsed.name}",
            gpl_target=gpl_target,
        )

        result = {"q": q_path, "rgs": rgs_path, "mqxml": mqxml_path}

    print(f"Generated quest package in: {parsed.output}")
    for key, path in result.items():
        if path.exists():
            print(f"  {key}: {path} ({path.stat().st_size} bytes)")
        else:
            print(f"  {key}: {path} (not found)")

    if parsed.deploy:
        import shutil
        deploy_dir = Path.home() / "Documents" / "My Games" / "MajestyHD" / "Quests" / parsed.name
        deploy_dir.mkdir(parents=True, exist_ok=True)
        src_dir = Path(parsed.output)
        for item in src_dir.rglob("*"):
            if item.is_file():
                rel = item.relative_to(src_dir)
                dest = deploy_dir / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, dest)
        print(f"\nDeployed to: {deploy_dir}")

    return 0


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Quest Map Generator — Majesty Gold HD")
        print()
        print("Usage:")
        print("  quest_map_generator.py parse <file.q>")
        print("  quest_map_generator.py validate <file.q> [--reference <ref.q>]")
        print("  quest_map_generator.py generate --name <name> --output <dir> [options]")
        print()
        print("Generate options:")
        print("  --lairs <specs>       Lair specs: ID:Description:Position (comma-separated)")
        print("  --map-size <128|256|512>  Map size in tiles (default: 256)")
        print("  --terrain <preset>    Terrain preset (default: grass)")
        print("  --palace <A-Y>        Palace grid position (default: M)")
        print("  --use-template        Use old template-splice approach")
        print()
        print("Terrain presets: grass, snow, grass_snow, forest, swamp, desert,")
        print("  scorched, mountain, snow_mountain, dark_forest, barren, fertile, winter, bog")
        print()
        print("Example:")
        print("  quest_map_generator.py generate --name Test --output out --lairs BBw1:Ice Cave:N,BBH1:Goblin Camp --terrain snow_mountain")
        sys.exit(1)

    cmd = sys.argv[1]
    rest = sys.argv[2:]

    if cmd == "parse":
        sys.exit(_cli_parse(rest))
    elif cmd == "validate":
        sys.exit(_cli_validate(rest))
    elif cmd == "generate":
        sys.exit(_cli_generate(rest))
    else:
        print(f"Unknown command: {cmd}")
        print("Available: parse, validate, generate")
        sys.exit(1)
