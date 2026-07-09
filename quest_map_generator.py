"""
quest_map_generator.py - Majesty Gold HD Quest Map Generator
=============================================================
Reads and writes .q binary quest map files for automated quest creation.

Supports:
  - Parsing existing .q files (RGMa, RGM6, RGM9 formats)
  - Generating new .q files (RGMa format)
  - Position grid encoding (5×5 grid, A-Y)
  - MQXML quest definition generation
  - Terrain file handling (copy .rgs templates)
  - Structural validation

Usage:
    python quest_map_generator.py parse <file.q>
    python quest_map_generator.py generate --name <name> --lairs <spec> --output <dir>
    python quest_map_generator.py validate <file.q>
"""

import struct
import argparse
import uuid
import shutil
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional


# ── Binary helpers ──────────────────────────────────────────────────────────

def u8(d, o): return d[o]
def u16(d, o): return struct.unpack_from("<H", d, o)[0]
def u32(d, o): return struct.unpack_from("<I", d, o)[0]
def i32(d, o): return struct.unpack_from("<i", d, o)[0]

def read_cstr(d, o):
    """Read null-terminated ASCII string. Returns (string, offset_after_null)."""
    end = d.find(b'\x00', o)
    if end == -1:
        return d[o:].decode('ascii', errors='replace'), len(d)
    return d[o:end].decode('ascii', errors='replace'), end + 1

def write_u32(val):
    return struct.pack("<I", val)

def write_cstr(s):
    """Encode string as null-terminated ASCII bytes."""
    return s.encode('ascii') + b'\x00'


# ── Grid Position Encoding (Task 2) ────────────────────────────────────────

CENTER = ord('M')  # Grid center position (2,2)

# Common position constants
GRID_CORNERS = [ord('A'), ord('E'), ord('U'), ord('Y')]  # (0,0) (4,0) (0,4) (4,4)
GRID_EDGES = [ord('C'), ord('K'), ord('O'), ord('W')]    # mid-top, mid-left, mid-right, mid-bottom
GRID_INNER = [ord('G'), ord('H'), ord('I'),              # ring around center
              ord('L'), ord('N'),
              ord('Q'), ord('R'), ord('S')]


def grid_to_byte(col: int, row: int) -> int:
    """Convert (col, row) grid coordinates to position byte ('A'-'Y').
    
    Args:
        col: Column 0-4 (left to right)
        row: Row 0-4 (top to bottom)
    
    Returns:
        ASCII byte value 65-89
    
    Raises:
        ValueError: If col or row is out of range [0,4]
    """
    if not (0 <= col < 5):
        raise ValueError(f"Column must be 0-4, got {col}")
    if not (0 <= row < 5):
        raise ValueError(f"Row must be 0-4, got {row}")
    return 65 + row * 5 + col


def byte_to_grid(byte_val: int) -> tuple:
    """Convert position byte to (col, row) grid coordinates.
    
    Args:
        byte_val: ASCII value 65-89 ('A'-'Y')
    
    Returns:
        (col, row) tuple where col and row are 0-4
    
    Raises:
        ValueError: If byte_val is outside range [65,89]
    """
    if not (65 <= byte_val <= 89):
        raise ValueError(f"Position byte must be 65-89 ('A'-'Y'), got {byte_val}")
    idx = byte_val - 65
    return (idx % 5, idx // 5)


def letter_to_byte(letter: str) -> int:
    """Convert grid letter ('A'-'Y') to byte value."""
    if len(letter) != 1 or not ('A' <= letter <= 'Y'):
        raise ValueError(f"Grid letter must be 'A'-'Y', got {letter!r}")
    return ord(letter)


def byte_to_letter(byte_val: int) -> str:
    """Convert byte value (65-89) to grid letter ('A'-'Y')."""
    if not (65 <= byte_val <= 89):
        raise ValueError(f"Position byte must be 65-89, got {byte_val}")
    return chr(byte_val)


def auto_distribute(n: int, exclude: list = None) -> list:
    """Distribute N positions across the grid, avoiding excluded cells.
    
    Returns positions spread outward from center: inner ring first,
    then edges, then corners.
    
    Args:
        n: Number of positions needed (1-24)
        exclude: List of byte values to skip (default: [CENTER])
    
    Returns:
        List of position byte values
    
    Raises:
        ValueError: If n exceeds available cells
    """
    if exclude is None:
        exclude = [CENTER]
    
    # Priority order: inner ring, edges, corners, remaining
    priority = GRID_INNER + GRID_EDGES + GRID_CORNERS
    # Add any remaining positions not in the priority list
    all_positions = list(range(65, 90))
    remaining = [p for p in all_positions if p not in priority and p not in exclude]
    priority = priority + remaining
    
    available = [p for p in priority if p not in exclude]
    
    if n > len(available):
        raise ValueError(f"Cannot distribute {n} positions, only {len(available)} available "
                        f"(25 total minus {len(exclude)} excluded)")
    
    return available[:n]


def validate_unique_positions(placed_entries: list) -> None:
    """Raise ValueError if any two placed entries share a grid cell."""
    all_positions = []
    for entry in placed_entries:
        for pos in entry.positions:
            if pos in all_positions:
                letter = byte_to_letter(pos)
                raise ValueError(
                    f"Grid cell '{letter}' is used by multiple buildings. "
                    f"Each cell can only hold one building.")
            all_positions.append(pos)


# ── Data Model (Task 1) ────────────────────────────────────────────────────

@dataclass
class MapParams:
    width: int = 256
    height: int = 256
    num_factions: int = 4
    starting_gold: int = 2000
    secondary_resource: int = 10000


@dataclass
class SpawnerEntry:
    object_id: str          # 4-char ID (e.g., "BVr1")
    spawn_level: int        # Spawn count/level value


@dataclass
class SpawnerBlock:
    entries: list           # list[SpawnerEntry]
    lair_resource: int = 0  # Resource value for this lair


@dataclass
class PlacedEntry:
    object_id: str          # 4-char ID
    description: str        # Human-readable name
    positions: list         # list[int] - grid position bytes ('A'-'Y')


@dataclass
class PlacedGroup:
    terrain_code: str = "gras"
    entries: list = field(default_factory=list)  # list[PlacedEntry]
    faction_name: str = ""


@dataclass
class Faction:
    short_code: str         # 4-char code
    full_name: str          # Full faction name
    home_position: int      # Grid position byte
    active: bool = True


@dataclass
class QuestMap:
    magic: str = "RGMa"
    quest_name: str = ""
    pattern_name: bytes = b""
    params: MapParams = field(default_factory=MapParams)
    spawner_blocks: list = field(default_factory=list)   # list[SpawnerBlock]
    placed_groups: list = field(default_factory=list)    # list[PlacedGroup]
    factions: list = field(default_factory=list)         # list[Faction]
    raw_data: bytes = b""   # Store original bytes for round-trip


# ── Errors ──────────────────────────────────────────────────────────────────

class QFormatError(Exception):
    """Raised when a .q file has invalid format."""
    pass


class ValidationError(Exception):
    """Raised when validation fails."""
    pass


# ── Q File Parser (Task 1) ─────────────────────────────────────────────────

def parse_q_file(filepath) -> QuestMap:
    """Parse a .q binary file into a QuestMap data structure.
    
    Supports RGMa (editor), RGM6 (base game), and RGM9 (expansion) formats.
    
    Args:
        filepath: Path to the .q file
    
    Returns:
        QuestMap instance with all parsed data
    
    Raises:
        QFormatError: If file has invalid magic bytes or structure
        FileNotFoundError: If file doesn't exist
    """
    filepath = Path(filepath)
    if not filepath.exists():
        raise FileNotFoundError(f"Q file not found: {filepath}")
    
    data = filepath.read_bytes()
    
    # Validate magic
    if len(data) < 16:
        raise QFormatError(f"File too small ({len(data)} bytes), minimum is 16")
    
    magic = data[0:4].decode('ascii', errors='replace')
    magic2 = data[8:12].decode('ascii', errors='replace')
    
    if magic not in ('RGMa', 'RGM6', 'RGM9'):
        raise QFormatError(f"Invalid magic bytes: {magic!r} (expected RGMa, RGM6, or RGM9)")
    if magic != magic2:
        raise QFormatError(f"Magic mismatch: {magic!r} at offset 0 vs {magic2!r} at offset 8")
    
    qmap = QuestMap(magic=magic, raw_data=data)
    
    # Parse quest name (null-terminated string at offset 0x10)
    pos = 0x10
    qmap.quest_name, pos = read_cstr(data, pos)
    
    # Parse pattern name (null-terminated, variable length)
    pattern_start = pos
    qmap.pattern_name, pos = read_cstr(data, pos)
    
    # Parse placed groups (the most reliably identified structure)
    qmap.placed_groups = _parse_placed_groups(data)
    
    # Parse spawner blocks
    qmap.spawner_blocks = _parse_spawner_blocks(data)
    
    return qmap


def _parse_placed_groups(data: bytes) -> list:
    """Find and parse all placed-object groups in the file."""
    groups = []
    i = 0
    
    while i < len(data) - 12:
        # Look for pattern: [4B printable ASCII] [u32 == 5] [u32 count 1-200]
        candidate = data[i:i+4]
        try:
            terrain = candidate.decode('ascii')
            if not all(c.isprintable() and c != ' ' for c in terrain):
                i += 1
                continue
        except (UnicodeDecodeError, ValueError):
            i += 1
            continue
        
        if u32(data, i+4) != 5:
            i += 1
            continue
        
        count = u32(data, i+8)
        if not (1 <= count <= 200):
            i += 1
            continue
        
        # Try to parse entries
        pos = i + 12
        entries = []
        valid_group = True
        
        for _ in range(count):
            if pos + 8 > len(data):
                valid_group = False
                break
            
            try:
                eid = data[pos:pos+4].decode('ascii')
            except (UnicodeDecodeError, ValueError):
                valid_group = False
                break
            
            # Check if it looks like a valid object ID prefix
            if len(eid) != 4 or eid[0:2] not in ('BB', 'AB', 'BV', 'AV', 'AC', 'AA', 'BA'):
                valid_group = False
                break
            
            pos += 4
            val = u32(data, pos)
            pos += 4
            
            desc, pos = read_cstr(data, pos)
            
            # Read position_count and position bytes
            if pos + 4 > len(data):
                valid_group = False
                break
            
            position_count = u32(data, pos)
            pos += 4
            
            if not (1 <= position_count <= 25):
                valid_group = False
                break
            
            positions = []
            for _ in range(position_count):
                if pos >= len(data):
                    valid_group = False
                    break
                pb = data[pos]
                pos += 1
                if not (65 <= pb <= 89):
                    valid_group = False
                    break
                positions.append(pb)
            
            if not valid_group:
                break
            
            entries.append(PlacedEntry(
                object_id=eid,
                description=desc,
                positions=positions,
            ))
        
        if valid_group and entries:
            group = PlacedGroup(
                terrain_code=terrain,
                entries=entries,
            )
            groups.append(group)
            i = pos  # Skip past this group
        else:
            i += 1
    
    return groups


def _parse_spawner_blocks(data: bytes) -> list:
    """Find and parse spawner blocks (24-byte BV* entries after NONEnone markers)."""
    blocks = []
    marker = b'NONEnone\x00'
    
    pos = 0
    while True:
        idx = data.find(marker, pos)
        if idx == -1:
            break
        
        # Move past the marker
        search_start = idx + len(marker)
        
        # Skip zeros after the marker
        scan = search_start
        while scan < len(data) and data[scan] == 0:
            scan += 1
        
        if scan + 4 > len(data):
            pos = search_start
            continue
        
        # The count should be at the first non-zero aligned position
        # But it might not be perfectly aligned — try a few positions
        found_block = False
        for try_off in range(max(search_start, scan - 3), min(scan + 4, len(data) - 4)):
            count = u32(data, try_off)
            if not (1 <= count <= 20):
                continue
            
            # Verify this looks like spawner entries
            entry_start = try_off + 4
            if entry_start + count * 24 > len(data):
                continue
            
            entries = []
            valid = True
            epos = entry_start
            
            for _ in range(count):
                try:
                    eid = data[epos:epos+4].decode('ascii')
                except (UnicodeDecodeError, ValueError):
                    valid = False
                    break
                
                # Check for valid object ID (BV* primarily for spawners)
                if len(eid) != 4:
                    valid = False
                    break
                
                # Spawner entries are typically BV* but could be other prefixes
                first_two = eid[0:2]
                if first_two not in ('BV', 'BB', 'AB', 'AV', 'BA', 'AA', 'AC'):
                    valid = False
                    break
                
                spawn_level = u32(data, epos + 4)
                active_flag = u32(data, epos + 16)
                
                if active_flag != 1:
                    valid = False
                    break
                
                entries.append(SpawnerEntry(object_id=eid, spawn_level=spawn_level))
                epos += 24
            
            if valid and entries:
                blocks.append(SpawnerBlock(entries=entries))
                found_block = True
                break
        
        pos = search_start  # Continue searching after this marker
    
    return blocks


# ── Pretty-print (Task 7 partial) ──────────────────────────────────────────

def format_q_text(qmap: QuestMap) -> str:
    """Format a QuestMap as human-readable text."""
    lines = []
    lines.append(f"=== Quest Map: {qmap.quest_name} ===")
    lines.append(f"Magic: {qmap.magic}")
    lines.append(f"Pattern: {qmap.pattern_name!r}")
    lines.append("")
    
    lines.append(f"Spawner Blocks: {len(qmap.spawner_blocks)}")
    for i, block in enumerate(qmap.spawner_blocks):
        lines.append(f"  Block {i}: {len(block.entries)} entries")
        for entry in block.entries:
            lines.append(f"    {entry.object_id} level={entry.spawn_level}")
    lines.append("")
    
    lines.append(f"Placed Groups: {len(qmap.placed_groups)}")
    for i, group in enumerate(qmap.placed_groups):
        lines.append(f"  Group {i}: terrain='{group.terrain_code}' entries={len(group.entries)}")
        for entry in group.entries:
            pos_letters = ''.join(byte_to_letter(p) for p in entry.positions)
            lines.append(f"    {entry.object_id} {entry.description!r} @ [{pos_letters}]")
    lines.append("")
    
    # Grid visualization
    lines.append("Grid Layout:")
    grid = {}
    for group in qmap.placed_groups:
        for entry in group.entries:
            for pos in entry.positions:
                grid[pos] = entry.object_id[:4]
    
    lines.append("     col0  col1  col2  col3  col4")
    for row in range(5):
        row_str = f"r{row}: "
        for col in range(5):
            byte_val = grid_to_byte(col, row)
            letter = byte_to_letter(byte_val)
            obj = grid.get(byte_val, "----")
            row_str += f" [{letter}]{obj}"
        lines.append(row_str)
    
    return "\n".join(lines)


# ── Entry point ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Majesty Gold HD Quest Map Generator")
    sub = parser.add_subparsers(dest="command")
    
    # parse subcommand
    p_parse = sub.add_parser("parse", help="Parse and display a .q file")
    p_parse.add_argument("file", help="Path to .q file")
    
    # validate subcommand
    p_val = sub.add_parser("validate", help="Validate a .q file")
    p_val.add_argument("file", help="Path to .q file")
    
    # generate subcommand
    p_gen = sub.add_parser("generate", help="Generate a test quest")
    p_gen.add_argument("--name", required=True, help="Quest name")
    p_gen.add_argument("--lairs", help="Lair specs (ID:desc:pos,...)")
    p_gen.add_argument("--output", required=True, help="Output directory")
    
    args = parser.parse_args()
    
    if args.command == "parse":
        qmap = parse_q_file(args.file)
        print(format_q_text(qmap))
    elif args.command == "validate":
        try:
            qmap = parse_q_file(args.file)
            print(f"OK: Parsed {args.file}")
            print(f"  Spawner blocks: {len(qmap.spawner_blocks)}")
            print(f"  Placed groups: {len(qmap.placed_groups)}")
            total_placed = sum(len(e.positions) for g in qmap.placed_groups for e in g.entries)
            print(f"  Total placed objects: {total_placed}")
        except (QFormatError, Exception) as e:
            print(f"FAIL: {e}")
            raise SystemExit(1)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
