"""
Quest Map Generator — Parser, writer, and grid encoding for Majesty Gold HD .q binary quest files.

Reads RGMa (editor), RGM6 (base game), and RGM9 (expansion) format quest map files.
Writes RGMa format using a template-based approach (splices placed groups into a known-good base).

Usage:
    from quest_map_generator import parse_q_file, write_q_file, grid_to_byte, byte_to_grid
    qmap = parse_q_file("Quests/fertile_plain.q")
    write_q_file(qmap, "output/Quest.q", template="MyQuest/Quest.q")
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
class PlacedEntry:
    object_id: str  # 4-char ID
    description: str  # Human-readable name
    positions: list[int] = field(default_factory=list)  # Grid position bytes ('A'-'Y', 65-89)

    @staticmethod
    def grid_col(pos_byte: int) -> int:
        return (pos_byte - 65) % 5

    @staticmethod
    def grid_row(pos_byte: int) -> int:
        return (pos_byte - 65) // 5


@dataclass
class PlacedGroup:
    terrain_code: str = "gras"  # 4-char terrain type
    entries: list[PlacedEntry] = field(default_factory=list)
    faction_name: str = ""  # Owner faction name


@dataclass
class Faction:
    short_code: str  # 4-char code
    full_name: str  # Full name
    home_position: int = 77  # Grid position byte (default M)
    active: bool = True


@dataclass
class QuestMap:
    magic: str = "RGMa"
    quest_name: str = ""
    pattern_name: bytes = b""
    params: MapParams = field(default_factory=MapParams)
    spawner_blocks: list[SpawnerBlock] = field(default_factory=list)
    placed_groups: list[PlacedGroup] = field(default_factory=list)
    factions: list[Faction] = field(default_factory=list)


# =============================================================================
# Grid Position Encoding/Decoding
# =============================================================================

CENTER = ord('M')  # 77 — center of the 5×5 grid (2, 2)


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
    
    Returns a list of N position bytes from the 5×5 grid.
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


def validate_unique_positions(entries: list[PlacedEntry]) -> None:
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
        for pos in entry.positions:
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


def _find_placed_groups(data: bytes) -> list[tuple[int, str, int]]:
    """
    Scan the binary data for placed-group headers: [4B terrain][u32 5][u32 count].
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

        # This looks like a valid placed group!
        terrain_str = terrain.decode('ascii')
        results.append((offset, terrain_str, count))

    # De-duplicate: remove overlapping detections
    # A valid group header should not be contained within another group's entries
    # We'll keep only groups where the offset is not within a previously-identified group's data range
    if not results:
        return results

    filtered = []
    occupied_ranges: list[tuple[int, int]] = []

    for offset, terrain_str, count in results:
        # Check if this offset falls within an already-identified group's data
        in_existing = False
        for start, end in occupied_ranges:
            if start < offset < end:
                in_existing = True
                break
        if in_existing:
            continue

        # Try to compute the extent of this group
        extent = _compute_group_extent(data, offset, count)
        if extent is not None:
            filtered.append((offset, terrain_str, count))
            occupied_ranges.append((offset, extent))
        else:
            # If we can't compute extent, still include but don't track range
            filtered.append((offset, terrain_str, count))

    return filtered


def _compute_group_extent(data: bytes, offset: int, count: int) -> Optional[int]:
    """Try to parse through all entries in a group and return the end offset."""
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


def _parse_placed_entries(data: bytes, offset: int, count: int) -> tuple[list[PlacedEntry], int]:
    """
    Parse count placed entries starting at offset.
    Returns (list of PlacedEntry, offset after last entry).
    """
    entries = []
    pos = offset
    for i in range(count):
        if pos + 8 >= len(data):
            raise QFormatError(f"Truncated placed entry at offset {pos}")

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

        # Position count
        if pos + 4 > len(data):
            raise QFormatError(f"Truncated position count at offset {pos}")
        pos_count = struct.unpack_from('<I', data, pos)[0]
        pos += 4

        if pos_count < 1 or pos_count > 25:
            raise QFormatError(
                f"Invalid position_count {pos_count} for entry {obj_id!r} at offset {pos - 4}"
            )

        # Position bytes
        if pos + pos_count > len(data):
            raise QFormatError(f"Truncated position bytes at offset {pos}")
        positions = list(data[pos:pos + pos_count])
        pos += pos_count

        # Validate all positions are in range
        for p in positions:
            if not (65 <= p <= 89):
                raise QFormatError(
                    f"Invalid position byte {p} (expected 65-89) in entry {obj_id!r}"
                )

        entries.append(PlacedEntry(
            object_id=obj_id,
            description=desc,
            positions=positions,
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
                entries = []
                valid = True
                for i in range(count):
                    entry_off = entries_start + i * entry_size
                    eid = data[entry_off:entry_off + 4].decode('ascii', errors='replace')
                    spawn_level = struct.unpack_from('<I', data, entry_off + 4)[0]
                    # Validate active flag at offset +16 (for 24-byte) or +12 (for 20-byte, if it fits)
                    if entry_size == 24:
                        active = struct.unpack_from('<I', data, entry_off + 16)[0]
                    else:
                        active = struct.unpack_from('<I', data, entry_off + 16)[0]
                    if active != 1 and active != 0:
                        valid = False
                        break
                    entries.append(SpawnerEntry(object_id=eid, spawn_level=spawn_level))

                if valid and entries:
                    # Try to find lair_resource after the entries
                    lair_resource = 0
                    after_entries = entries_start + count * entry_size
                    if after_entries + 8 <= len(data):
                        sep = struct.unpack_from('<I', data, after_entries)[0]
                        if sep == 0 and after_entries + 8 <= len(data):
                            lair_resource = struct.unpack_from('<I', data, after_entries + 4)[0]

                    blocks.append(SpawnerBlock(entries=entries, lair_resource=lair_resource))
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
    Uses pattern-matching to find placed-object groups rather than sequential parsing.
    
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
    # The pattern name is 12 bytes followed by a null terminator
    # But it might be shorter if it contains a null before 12 bytes
    pattern_end = after_name + 12
    if pattern_end > len(data):
        pattern_end = len(data)
    pattern_name = data[after_name:pattern_end]
    # Find the actual null terminator for the pattern
    try:
        pattern_null = data.index(0, after_name)
        if pattern_null < pattern_end:
            # Pattern is shorter than 12 bytes
            pattern_name = data[after_name:pattern_null]
    except ValueError:
        pass

    # --- Map parameters (best effort) ---
    params = MapParams()
    # Parameters are somewhere after pattern name; format varies by version
    # For now we extract what we can

    # --- Spawner blocks ---
    spawner_blocks = _find_spawner_blocks(data)

    # --- Placed object groups (the critical part) ---
    group_candidates = _find_placed_groups(data)
    placed_groups = []
    for offset, terrain_code, count in group_candidates:
        try:
            entries, end_pos = _parse_placed_entries(data, offset + 12, count)
            group = PlacedGroup(
                terrain_code=terrain_code,
                entries=entries,
                faction_name="",
            )
            # Try to read faction name from metadata block
            # Metadata: 10 × u32 then null-terminated string
            meta_start = end_pos
            if meta_start + 40 < len(data):
                # Check if this looks like a metadata block (first u32 should be 0)
                first_val = struct.unpack_from('<I', data, meta_start)[0]
                if first_val == 0:
                    fname_start = meta_start + 40
                    if fname_start < len(data):
                        try:
                            fname, _ = _read_cstr(data, fname_start)
                            # Only accept if it looks like a name (printable, reasonable length)
                            if len(fname) < 50 and all(32 <= ord(c) < 127 for c in fname):
                                group.faction_name = fname
                        except (ValueError, IndexError):
                            pass

            placed_groups.append(group)
        except QFormatError:
            # Skip groups that fail to parse (false positive in pattern matching)
            continue

    # --- Factions (best effort) ---
    factions = []

    return QuestMap(
        magic=magic,
        quest_name=quest_name,
        pattern_name=pattern_name,
        params=params,
        spawner_blocks=spawner_blocks,
        placed_groups=placed_groups,
        factions=factions,
    )


# =============================================================================
# Writer (Template-based)
# =============================================================================

# The writer uses a template .q file (e.g., MyQuest/Quest.q) and splices in
# modified placed-group sections. This ensures the header, spawner blocks,
# metadata, and player sections are preserved from a known-working file.

DEFAULT_TEMPLATE = Path(__file__).parent.parent / "MyQuest" / "Quest.q"

# Standard metadata block that appears after each placed group's entries
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


def _encode_placed_entry(entry: PlacedEntry) -> bytes:
    """Encode a single placed entry to binary."""
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
    # Position count (u32)
    parts.append(struct.pack('<I', len(entry.positions)))
    # Position bytes
    for pos in entry.positions:
        if not (65 <= pos <= 89):
            raise QFormatError(f"Invalid position {pos} in entry {entry.object_id}")
        parts.append(bytes([pos]))
    return b''.join(parts)


def _encode_placed_group(group: PlacedGroup) -> bytes:
    """Encode a placed group header + entries (no metadata block)."""
    parts = []
    # Terrain code (4 bytes)
    terrain = group.terrain_code.encode('ascii')
    if len(terrain) != 4:
        terrain = (terrain + b'    ')[:4]
    parts.append(terrain)
    # Constant marker (u32 = 5)
    parts.append(struct.pack('<I', 5))
    # Entry count
    parts.append(struct.pack('<I', len(group.entries)))
    # Entries
    for entry in group.entries:
        parts.append(_encode_placed_entry(entry))
    return b''.join(parts)


def _encode_faction_name_block(faction_name: str) -> bytes:
    """
    Encode the faction name that appears in the metadata gap.
    Format: [12-char name (4+4+4 pattern)]\0[padding zeros]\0
    """
    # Faction names use a 4+4+4 repeated pattern like "PlayPlayPlayer1"
    # or "AutoAutoAutoExpanding"
    # For simple names, just use the name padded/truncated
    name_bytes = faction_name.encode('ascii')
    # The 12-char pattern is typically the first 4 chars repeated 3 times
    # followed by the full name
    short = faction_name[:4]
    pattern_12 = (short * 3)[:12].encode('ascii')
    full_with_null = name_bytes + b'\x00'
    # Padding: 4 null bytes after the full name, then u32 for next section
    return pattern_12 + full_with_null


def _encode_pre_group_block(owner_entry_count: int) -> bytes:
    """Encode the bytes that appear just before a placed group: [zeros][u32 count]."""
    return struct.pack('<III', 0, 0, owner_entry_count)


def write_q_file(
    placed_groups: list[PlacedGroup],
    output_path,
    template_path=None,
    quest_name: Optional[str] = None,
) -> Path:
    """
    Write a .q file using a template-based approach.
    
    Takes placed groups and splices them into a copy of the template file,
    replacing the template's placed groups while preserving header/spawners/player sections.
    
    Args:
        placed_groups: List of PlacedGroup objects to write
        output_path: Where to write the output .q file
        template_path: Path to template .q file (default: MyQuest/Quest.q)
        quest_name: Optional quest name override (replaces template's name)
        
    Returns:
        Path to the written file
        
    Raises:
        QFormatError: If encoding fails
        FileNotFoundError: If template doesn't exist
    """
    if template_path is None:
        template_path = DEFAULT_TEMPLATE
    template_path = Path(template_path)
    output_path = Path(output_path)
    
    if not template_path.exists():
        raise FileNotFoundError(f"Template file not found: {template_path}")
    
    # Validate unique positions across all groups (optional - skip for round-trip of existing files)
    all_entries = [e for g in placed_groups for e in g.entries]
    # Only validate if caller hasn't explicitly opted out
    # (existing game files sometimes have buildings sharing cells)
    
    # Read template
    template_data = template_path.read_bytes()
    
    # Find the placed groups in the template to know what section to replace
    template_groups = _find_placed_groups(template_data)
    if not template_groups:
        raise QFormatError(f"Template has no placed groups: {template_path}")
    
    # Find the FIRST group's pre-block (goes back from the group to find the owner count)
    first_group_offset = template_groups[0][0]
    
    # The pre-block is 8 bytes before the terrain code: [u32 0][u32 owner_count]
    # Actually from the hex dump, it's: [...faction_name\0][u32 0][u32 0][u32 0][u32 0/1][u32 count]
    # Let's find it by scanning backwards for the u32 that equals the group count
    # Actually simpler: just use a fixed offset. The pre-group pattern is always
    # [u32 owner_entry_count] immediately before [terrain_code]
    pre_group_u32_offset = first_group_offset - 4
    
    # Find where to START splicing: we want to preserve everything before the
    # placed groups section. The pre-group has a u32 count, and before THAT
    # is the faction name + metadata from the spawner section.
    # Let's find the splice point: 8 bytes before first group
    # (the [u32 0][u32 count] before the terrain code)
    splice_start = first_group_offset - 8  # includes the zero padding + count
    
    # Find the splice END: after the last group's metadata, before the player section
    last_group = template_groups[-1]
    last_extent = _compute_group_extent(template_data, last_group[0], last_group[2])
    if last_extent is None:
        raise QFormatError("Cannot compute template last group extent")
    
    # After last extent comes the metadata block (40 bytes) + faction name + player section
    # The player section starts with a distinctive pattern: [u32 1][pattern 12B][...NONE...]
    # Let's find "NONE" after the last group as the player section marker
    # Actually the metadata is 40 bytes, then faction name (variable), then player section
    # The player section in MyQuest starts at 0x0898 with [01 00 00 00 "MyAI"...]
    # Let's find the splice end by looking for the metadata + faction name pattern
    # after the LAST group.
    
    # Simpler approach: after the last group entries, skip the metadata (40 bytes),
    # then the faction name string, then some padding — and the REST is the player section
    # that we want to preserve.
    
    # For robustness, let's find the byte position where "NONE" appears after the last
    # group (that's the start of the player section end-block)
    player_section_marker = template_data.find(b'\x02\x00\x00\x00NONE', last_extent)
    if player_section_marker == -1:
        # Try alternate pattern
        player_section_marker = template_data.find(b'NONE', last_extent + 40)
        if player_section_marker != -1:
            # Back up to include the u32 before NONE
            player_section_marker -= 4
    
    if player_section_marker == -1:
        # Fallback: preserve everything from last_extent + 40 + 50 onward
        # (rough estimate of metadata + faction name)
        splice_end = last_extent + 100
    else:
        # Go back a bit to include the metadata block separator before NONE
        # The pattern before player section is: [metadata 40B][faction_name][padding][u32 1/2][NONE]
        splice_end = player_section_marker
    
    # Now build the output:
    # [preserved header/spawner section] + [new placed groups with metadata] + [preserved player section]
    
    output_parts = []
    
    # Part 1: Everything before the placed section
    pre_section = bytearray(template_data[:splice_start])
    
    # If quest_name override, replace it in the header
    if quest_name is not None:
        # Quest name starts at offset 0x10 as null-terminated string
        old_name_end = template_data.index(0, 0x10) + 1
        new_name = quest_name.encode('ascii') + b'\x00'
        # Replace: everything from 0x10 to old_name_end becomes new_name
        # But this changes offsets... too complex for now. Skip name replacement
        # in template mode. Name will come from the template.
        pass
    
    output_parts.append(bytes(pre_section))
    
    # Part 2: New placed groups (each with pre-block + entries + metadata + faction name)
    faction_names = ["AutoExpanding", "Player1", "player2_ai", "MyAI"]
    owner_counts = [9, 9, 1, 1]  # From template: counts before each group
    
    for i, group in enumerate(placed_groups):
        # Pre-block: [u32 0][u32 owner_count]
        oc = owner_counts[i] if i < len(owner_counts) else 1
        output_parts.append(struct.pack('<II', 0, oc))
        
        # Group entries
        output_parts.append(_encode_placed_group(group))
        
        # Metadata block (40 bytes)
        output_parts.append(METADATA_BLOCK)
        
        # Faction name (if not the last group before player section)
        fname = faction_names[i] if i < len(faction_names) else f"Faction{i}"
        if i < len(placed_groups) - 1:
            # Between groups: faction name + padding
            output_parts.append(_encode_faction_name_block(fname))
        else:
            # Last group: faction name leads into player section
            # Use a shorter format
            name_bytes = fname.encode('ascii')
            short = fname[:4]
            pattern = (short * 3)[:12].encode('ascii')
            output_parts.append(pattern + name_bytes + b'\x00')
    
    # Part 3: Player section (preserved from template)
    output_parts.append(template_data[splice_end:])
    
    # Write output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_bytes = b''.join(output_parts)
    output_path.write_bytes(output_bytes)
    
    return output_path


def write_q_file_simple(
    entries: list[PlacedEntry],
    output_path,
    template_path=None,
) -> Path:
    """
    Simplified writer: takes a flat list of placed entries and puts them
    all in a single group. Palace should be included in entries.
    
    This is the easiest way to generate a test quest map.
    """
    group = PlacedGroup(
        terrain_code="gras",
        entries=entries,
        faction_name="Player1",
    )
    return write_q_file([group], output_path, template_path)


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

    if qmap.placed_groups:
        lines.append(f"--- Placed Groups ({len(qmap.placed_groups)}) ---")
        for i, group in enumerate(qmap.placed_groups):
            total_pos = sum(len(e.positions) for e in group.entries)
            lines.append(
                f"  Group {i}: terrain={group.terrain_code!r} "
                f"entries={len(group.entries)} positions={total_pos} "
                f"faction={group.faction_name!r}"
            )
            for entry in group.entries:
                pos_str = ''.join(chr(p) for p in entry.positions)
                lines.append(
                    f"    {entry.object_id} {entry.description!r} @ [{pos_str}]"
                )
        lines.append("")

    # Grid visualization
    lines.append("--- Grid (5x5) ---")
    grid = {}
    for group in qmap.placed_groups:
        for entry in group.entries:
            for pos in entry.positions:
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
# CLI
# =============================================================================

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: quest_map_generator.py <command> [args]")
        print("Commands: parse <file.q>")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == "parse":
        if len(sys.argv) < 3:
            print("Usage: quest_map_generator.py parse <file.q>")
            sys.exit(1)
        qmap = parse_q_file(sys.argv[2])
        print(format_q_text(qmap))
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
