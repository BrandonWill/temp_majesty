"""
RGS Quest Map Format — Complete sequential parser/writer for Majesty Gold HD .q files.

Based on full decompilation of SDK/RGSeditor.exe.
Replaces the heuristic-based approach with exact sequential read/write matching
the C++ serialization order.

Always writes RGMa format (latest). Reads all versions (RGM1-RGM9, RGMa).
"""

from __future__ import annotations
import struct
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, BinaryIO
import io


# =============================================================================
# Version Constants
# =============================================================================

# File-level magic → component version mapping (from decompiled LoadQuest)
VERSION_MAP = {
    "RGMa": {"force": 8, "spawner": 3, "team": 7, "spawn_item": 3},
    "RGM9": {"force": 8, "spawner": 3, "team": 7, "spawn_item": 3},
    "RGM8": {"force": 7, "spawner": 3, "team": 7, "spawn_item": 3},
    "RGM7": {"force": 7, "spawner": 3, "team": 7, "spawn_item": 3},
    "RGM6": {"force": 7, "spawner": 2, "team": 7, "spawn_item": 2},
    "RGM5": {"force": 7, "spawner": 2, "team": 7, "spawn_item": 1},
    "RGM4": {"force": 6, "spawner": 2, "team": 1, "spawn_item": 1},
    "RGM3": {"force": 5, "spawner": 2, "team": 1, "spawn_item": 1},
    "RGM2": {"force": 1, "spawner": 2, "team": 1, "spawn_item": 1},
    "RGM1": {"force": 1, "spawner": 1, "team": 1, "spawn_item": 1},
}

WRITE_MAGIC = b"RGMa"  # Always write latest format


# =============================================================================
# Terrain Presets — Extracted from original quest files
# =============================================================================

# Each landscape zone defines: (body_tag, display_name, fractal_ref, texture_ref, height_ref)
# These reference resources in the game's constants.rgs terrain database.
LANDSCAPE_ZONES = {
    # --- Grasslands ---
    "grass": ("Gras", "Grassy", "xBBC", "#Pla", "Bump"),
    "grass_lush": ("Gras", "Grass", "xBBC", "#Plc", "Bump"),
    "grass_rolling": ("Fert", "Fertile #1", "xFer", "#Ple", "Roll"),
    "grass_forest": ("Fera", "Fertile #2", "xFeb", "#Pld", "Rola"),
    "grass_flat": ("Ferb", "Fertile #3", "xFec", "xGra", "Roll"),
    "grass_sparse": ("Spar", "Sparse Grass", "xBBC", "#Plc", "Bump"),
    # --- Snow ---
    "snow": ("Snow", "Snowy", "Clea", "xSno", "FS01"),
    "snow_ice": ("Icea", "Ice #2", "xDta", "xSnb", "Bump"),
    "snow_rolling": ("Ice ", "Ice #1", "xCla", "xSnc", "Rola"),
    # --- Swamp ---
    "swamp": ("Swam", "Swamp", "xSDa", "#Swa", "FS01"),
    "swamp_dark": ("Swam", "Swamp", "xSDa", "#Swd", "FS01"),
    # --- Desert / Arid ---
    "desert": ("Deaa", "Deal #2", "xDec", "#Arb", "Bump"),
    "desert_savannah": ("$Sha", "$Shovrah_Savannah", "xSha", "#Arc", "Roll"),
    # --- Scorched ---
    "scorched": ("Scor", "Scorched #1", "xLia", "#Sca", "FS01"),
    "scorched_rocky": ("Bara", "Barren #1", "xBar", "#Scb", "Bump"),
    "scorched_dark": ("Dark", "Dark Forest #1", "xDFa", "#Scb", "Roll"),
    # --- Dirt ---
    "dirt": ("Mudd", "Muddy #1", "Clea", "#All", "Bump"),
    "dirt_rolling": ("Deal", "Deal #1", "xDea", "#All", "Bump"),
    # --- Mountain ---
    "mountain": ("Slab", "Slay Dragon #3", "xSDr", "#Sca", "Moun"),
    "mountain_forest": ("$Fel", "$Feldar_Mountain", "xFea", "#Sca", "Moun"),
    # --- Forest ---
    "forest": ("Krol", "Krolm_Forest", "xFel", "#Pld", "Bump"),
    "forest_dark": ("Darb", "Dark Forest #3", "xDFo", "#Scc", "Smal"),
    "forest_swamp": ("Kroa", "Krolm_Swamp", "xLic", "#Swc", "FS01"),
    # --- Bog ---
    "bog": ("Barb", "Barren #2", "xBaa", "#Swd", "FS01"),
    # --- Wasteland ---
    "wasteland": ("Wast", "Wasted", "xGHo", "#Scc", "Bump"),
}

# Pre-built terrain presets (combinations of landscape zones with weights)
# Format: {"zone_key": weight, ...} — weight roughly maps to spawn_level (probability)
TERRAIN_PRESETS = {
    "grass": {"grass": 51},
    "snow": {"snow": 49},
    "grass_snow": {"grass": 51, "snow": 49},
    "forest": {"forest": 55, "grass_rolling": 45},
    "swamp": {"swamp": 55, "forest": 35, "dirt": 20},
    "desert": {"desert": 55, "desert_savannah": 45},
    "scorched": {"scorched": 50, "scorched_rocky": 40, "wasteland": 30},
    "mountain": {"mountain": 50, "grass_rolling": 35, "forest": 25},
    "snow_mountain": {"snow": 55, "snow_ice": 40, "mountain": 30},
    "dark_forest": {"forest_dark": 55, "scorched_dark": 40, "swamp_dark": 25},
    "barren": {"scorched_rocky": 50, "dirt": 45, "wasteland": 30},
    "fertile": {"grass_rolling": 45, "grass_forest": 40, "grass_flat": 30},
    "winter": {"snow": 60, "snow_rolling": 40},
    "bog": {"bog": 50, "swamp": 40, "forest_swamp": 30},
}
# Data Model (matches RGSEditor's internal structures)
# =============================================================================

@dataclass
class SpawnerItem:
    """Single spawner entry (monster/lair in a spawn list)."""
    name: str  # 4-char tag (e.g., "BVr1")
    spawn_level: int = 1
    field_0c: int = 0
    field_10: int = 0
    active: bool = True
    lair_resource: int = 0  # Only in spawn_item version >= 3


@dataclass
class TeamDefinition:
    """A team/player definition with its spawner list."""
    name_tag: str = "NONE"  # 4-char tag
    name_string: str = ""  # null-terminated full name
    is_active: bool = True
    is_expanding: bool = False
    spawner_items: list[SpawnerItem] = field(default_factory=list)


@dataclass
class SpawnerBlock:
    """A spawner block — per-lair override settings.

    Field mapping confirmed via Ghidra decompilation of DialogEditLairs::DoDataExchange
    (FUN_00426430) and the save handler (FUN_00427490):

        field_00 = max_hp          — Max HP for the lair (0 = use lair default). DDV 0-99999.
        field_04 = spawn_rate_ms   — Base time in ms between monster spawns (0 = default). DDV 0-999999.
        field_08 = dispersion      — Spawn dispersion range in pixels around lair (0 = default). DDV 0-99999.
        field_0c = _unused         — "Not implemented" per UI tooltip. DDV 0-10. Values 0 or 4 in data.
        field_10 = hit_rate_sub    — Each hit subtracts this ms from spawn delay (0 = default). DDV 0-9999.
                                     Only in spawner version >= 2.
    """
    field_00: int = 0  # max_hp
    field_04: int = 0  # spawn_rate_ms
    field_08: int = 0  # dispersion (pixels)
    field_0c: int = 0  # (not implemented)
    field_10: int = 0  # hit_rate_sub (only in spawner version >= 2)
    team: TeamDefinition = field(default_factory=TeamDefinition)
    extra_names: list[str] = field(default_factory=list)  # Only in spawner version 3

    # Convenience property aliases for readable access
    @property
    def max_hp(self) -> int:
        return self.field_00

    @max_hp.setter
    def max_hp(self, value: int):
        self.field_00 = value

    @property
    def spawn_rate_ms(self) -> int:
        return self.field_04

    @spawn_rate_ms.setter
    def spawn_rate_ms(self, value: int):
        self.field_04 = value

    @property
    def dispersion(self) -> int:
        return self.field_08

    @dispersion.setter
    def dispersion(self, value: int):
        self.field_08 = value

    @property
    def hit_rate_sub(self) -> int:
        return self.field_10

    @hit_rate_sub.setter
    def hit_rate_sub(self, value: int):
        self.field_10 = value


@dataclass
class UnitInstance:
    """Single unit placement within a UnitPattern."""
    object_id: str  # 4-char code (e.g., "ABJ1", "BBw1")
    field_08: int = 0  # Unknown u32 (usually 0)
    description: str = ""  # Human-readable name
    candidate_cells: list[int] = field(default_factory=list)  # Position bytes (65-89)


@dataclass
class UnitPattern:
    """Mid-level placement pattern (5x5 grid with resolution).
    
    Field naming (from decompilation):
    - terrain_code: Actually stores the faction's 4-char SHORT code (e.g., "Gobl", "Play")
    - name: The faction's full name (e.g., "Goblin Kingdom", "Player1")
    - tag_48: The REAL terrain code (e.g., "gras", "snow", "scor")
    - field_44: The grid resolution marker (always 5 in unit patterns = 5 tiles between cells)
    """
    terrain_code: str = "gras"  # Actually: faction short code (4-char)
    name: str = ""  # Actually: faction full name
    has_alternate: bool = False  # bool at +0x28
    field_04: int = 0  # Unknown u32 (often = starting_gold for faction)
    tag_48: str = "NONE"  # The REAL terrain type (e.g., "gras")
    field_44: int = 5  # Grid resolution marker (always 5)
    entries: list[UnitInstance] = field(default_factory=list)
    spawners: list[SpawnerBlock] = field(default_factory=list)
    # Fields only in force version >= 5:
    resolution: int = 3  # Grid cell spacing in tiles
    # Fields only in force version >= 7:
    field_74: int = 50  # Difficulty: money rating
    field_78: int = 50  # Difficulty: time rating
    field_7c: int = 50  # Difficulty: kill-all rating
    flag_70: bool = True  # Allow single player
    flag_71: bool = True  # Allow two player
    flag_72: bool = False  # Unknown flag
    flag_73: bool = False  # Unknown flag
    # Field only in force version >= 8:
    flag_29: bool = False  # Unknown flag


@dataclass
class ForceEntry:
    """Faction position on the Force Pattern's map grid."""
    faction_code: str  # 4-char tag (e.g., "Play", "Mons")
    faction_name: str  # Full name (null-terminated)
    pattern_ref: str = "NONE"  # 4-char: which UnitPattern this references
    field_5: str = "NONE"  # 4-char: unknown tag
    field_6: str = "NONE"  # 4-char: unknown tag
    active: int = 1  # u32: 0 or 1
    grid_position: int = 77  # u32: grid cell (matches 'A'-'Y' encoding)


@dataclass
class RegionEntry:
    """A single region pattern entry (terrain + landscape mapping)."""
    tag: str  # 4-char terrain code (e.g., "gras", "snow")
    # The actual region data is opaque bytes — we preserve them exactly
    data: bytes = b""


@dataclass
class SlotConfig:
    """A player/team slot configuration (FUN_004835a0)."""
    index: int = 0
    name: str = ""
    active: bool = False
    starting_gold: int = 0
    field_0c: int = 0
    sub_items: list[int] = field(default_factory=list)


@dataclass
class QuestFile:
    """Complete .q file representation — mirrors RGSEditor's internal state."""
    magic: str = "RGMa"
    # Section 1: Header metadata
    quest_name: str = ""
    _tag1: str = "patt"  # Pattern short (4 bytes)
    _tag2: str = ""  # Pattern name (4 bytes)
    _tag3: int = 0  # GUID/hash (4 bytes as u32)
    _tag4: int = 0  # Field at param_2[0x32]
    map_params: tuple[int, int] = (256, 256)  # Map width, height
    # Section 2: Spawner blocks (each with external index)
    _spawner_indices: list[int] = field(default_factory=list)
    spawner_blocks: list[SpawnerBlock] = field(default_factory=list)
    # Section 3: Slot configs (player/team definitions)
    _slot_configs: list = field(default_factory=list)
    # Section 4: Three u32 values
    field_46: int = 0
    field_47: int = 0
    quest_type_code: int = 0
    # Section 5: Quest mode (only older versions read string from file)
    quest_mode_string: str = ""
    freestyle_flag: int = 0
    # Section 6: Region patterns
    region_entries: list[RegionEntry] = field(default_factory=list)
    # Section 7: Force pattern
    force_entries: list[ForceEntry] = field(default_factory=list)
    # Section 8: Unit patterns (two sets via FUN_0047bb00)
    unit_patterns_2: list[UnitPattern] = field(default_factory=list)
    unit_patterns_3: list[UnitPattern] = field(default_factory=list)
    # Section 9: Finalization
    rel_string: str = "Rel@"


# =============================================================================
# Low-Level I/O (matches decompiled primitives)
# =============================================================================

class BinaryReader:
    """Sequential binary reader matching RGSEditor's stream I/O."""

    def __init__(self, data: bytes):
        self._stream = io.BytesIO(data)
        self._size = len(data)

    @property
    def pos(self) -> int:
        return self._stream.tell()

    @property
    def remaining(self) -> int:
        return self._size - self.pos

    def read_u32(self) -> int:
        """Read 4 bytes as unsigned 32-bit integer (matches FUN_004f2520)."""
        data = self._stream.read(4)
        if len(data) < 4:
            raise EOFError(f"Unexpected EOF at offset {self.pos - len(data)}")
        return struct.unpack('<I', data)[0]

    def read_tag4(self) -> str:
        """Read 4 bytes as ASCII tag (matches FUN_004f24a0)."""
        data = self._stream.read(4)
        if len(data) < 4:
            raise EOFError(f"Unexpected EOF at offset {self.pos - len(data)}")
        return data.decode('ascii', errors='replace')

    def read_bytes(self, n: int) -> bytes:
        """Read N bytes (matches FUN_004f2440)."""
        data = self._stream.read(n)
        if len(data) < n:
            raise EOFError(f"Unexpected EOF: wanted {n}, got {len(data)}")
        return data

    def read_string(self) -> str:
        """Read null-terminated string (matches FUN_004eb2a0)."""
        chars = []
        while True:
            b = self._stream.read(1)
            if not b or b == b'\x00':
                break
            chars.append(b)
        return b''.join(chars).decode('ascii', errors='replace')

    def read_bool_u32(self) -> bool:
        """Read u32 and interpret as boolean."""
        return self.read_u32() != 0


class BinaryWriter:
    """Sequential binary writer matching RGSEditor's stream I/O."""

    def __init__(self):
        self._stream = io.BytesIO()

    def write_u32(self, val: int):
        """Write 4 bytes unsigned 32-bit (matches FUN_004f1bb0)."""
        self._stream.write(struct.pack('<I', val & 0xFFFFFFFF))

    def write_tag4(self, tag: str):
        """Write 4-byte ASCII tag (matches FUN_004f1ab0)."""
        b = tag.encode('ascii', errors='replace')
        if len(b) < 4:
            b = b + b'\x00' * (4 - len(b))
        self._stream.write(b[:4])

    def write_bytes(self, data: bytes):
        """Write raw bytes."""
        self._stream.write(data)

    def write_string(self, s: str):
        """Write null-terminated string (matches FUN_004eb180)."""
        self._stream.write(s.encode('ascii', errors='replace') + b'\x00')

    def write_bool_u32(self, val: bool):
        """Write boolean as u32 (0 or 1)."""
        self.write_u32(1 if val else 0)

    def getvalue(self) -> bytes:
        return self._stream.getvalue()


# =============================================================================
# Sequential Reader (matches LoadQuest exactly)
# =============================================================================

def read_spawner_item(r: BinaryReader, version: int) -> SpawnerItem:
    """Read a single spawner item (FUN_0047c0e0)."""
    item = SpawnerItem(name="")
    item.name = r.read_tag4()
    item.spawn_level = r.read_u32()
    item.field_0c = r.read_u32()
    item.field_10 = r.read_u32()
    if version >= 2:
        item.active = r.read_bool_u32()
    if version >= 3:
        item.lair_resource = r.read_u32()
    return item


def read_team_definition(r: BinaryReader, team_ver: int, item_ver: int) -> TeamDefinition:
    """Read a team/player definition (FUN_0046e1c0)."""
    team = TeamDefinition()
    team.name_tag = r.read_tag4()
    team.name_string = r.read_string()
    team.is_active = r.read_bool_u32()
    team.is_expanding = r.read_bool_u32()
    # Read spawner items for this team
    count = r.read_u32()
    for _ in range(count):
        team.spawner_items.append(read_spawner_item(r, item_ver))
    return team


def read_spawner_block(r: BinaryReader, spawner_ver: int, team_ver: int,
                       item_ver: int) -> SpawnerBlock:
    """Read a spawner block body (FUN_0046e830). Index is read by caller."""
    block = SpawnerBlock()
    block.field_00 = r.read_u32()
    block.field_04 = r.read_u32()
    block.field_08 = r.read_u32()
    block.field_0c = r.read_u32()
    if spawner_ver >= 2:
        block.field_10 = r.read_u32()
    block.team = read_team_definition(r, team_ver, item_ver)
    if spawner_ver >= 3:
        extra_count = r.read_u32()
        for _ in range(extra_count):
            block.extra_names.append(r.read_tag4())
    return block


def read_unit_instance(r: BinaryReader) -> UnitInstance:
    """Read a single unit instance (FUN_00478e70)."""
    inst = UnitInstance(object_id="")
    inst.object_id = r.read_tag4()
    inst.field_08 = r.read_u32()
    inst.description = r.read_string()
    pos_count = r.read_u32()
    inst.candidate_cells = list(r.read_bytes(pos_count))
    return inst


def read_unit_pattern(r: BinaryReader, force_ver: int, spawner_ver: int,
                      team_ver: int, item_ver: int) -> UnitPattern:
    """Read a single Unit Pattern (FUN_004735c0)."""
    pat = UnitPattern()
    pat.terrain_code = r.read_tag4()
    pat.name = r.read_string()
    pat.has_alternate = r.read_bool_u32()
    pat.field_04 = r.read_u32()
    pat.tag_48 = r.read_tag4()
    pat.field_44 = r.read_u32()
    # Unit instances
    instance_count = r.read_u32()
    for _ in range(instance_count):
        pat.entries.append(read_unit_instance(r))
    # Spawner blocks within this pattern (each prefixed by u32 key, same as top-level)
    spawner_count = r.read_u32()
    pat._spawner_keys = []
    for _ in range(spawner_count):
        spawner_key = r.read_u32()  # u32 key/index before each block
        pat._spawner_keys.append(spawner_key)
        pat.spawners.append(read_spawner_block(r, spawner_ver, team_ver, item_ver))
    # Version-dependent trailing fields
    if force_ver >= 5:
        pat.resolution = r.read_u32()
    if force_ver >= 7:
        pat.field_74 = r.read_u32()
        pat.field_78 = r.read_u32()
        pat.field_7c = r.read_u32()
        pat.flag_70 = r.read_bool_u32()
        pat.flag_71 = r.read_bool_u32()
        pat.flag_72 = r.read_bool_u32()
        pat.flag_73 = r.read_bool_u32()
    if force_ver >= 8:
        pat.flag_29 = r.read_bool_u32()
    return pat


def read_unit_pattern_set(r: BinaryReader, force_ver: int, spawner_ver: int,
                          team_ver: int, item_ver: int) -> list[UnitPattern]:
    """Read a collection of Unit Patterns (FUN_0047bb00).
    
    Structure: u32 count, then for each: tag4(faction) + pattern_body.
    """
    count = r.read_u32()
    patterns = []
    for _ in range(count):
        faction_tag = r.read_tag4()  # Read faction tag before each pattern
        pat = read_unit_pattern(r, force_ver, spawner_ver, team_ver, item_ver)
        pat._faction_tag = faction_tag
        patterns.append(pat)
    return patterns


def read_force_entry(r: BinaryReader) -> ForceEntry:
    """Read a Force Pattern entry (FUN_0047ef60)."""
    entry = ForceEntry(faction_code="", faction_name="")
    entry.faction_code = r.read_tag4()
    entry.faction_name = r.read_string()
    entry.pattern_ref = r.read_tag4()
    entry.field_5 = r.read_tag4()
    entry.field_6 = r.read_tag4()
    entry.active = r.read_u32()
    entry.grid_position = r.read_u32()
    return entry


def read_force_pattern(r: BinaryReader) -> list[ForceEntry]:
    """Read the Force Pattern section (FUN_00481480)."""
    count = r.read_u32()
    entries = []
    for _ in range(count):
        entries.append(read_force_entry(r))
    return entries


def read_region_entry(r: BinaryReader) -> Optional[RegionEntry]:
    """Read a region pattern entry. Returns None if tag is 'NONE'."""
    tag = r.read_tag4()
    if tag == "NONE":
        return None
    # For now, we can't fully parse the region sub-structure without more
    # reverse engineering of FUN_0046c8f0. Store the tag and we'll handle
    # the opaque bytes via template preservation.
    return RegionEntry(tag=tag)


@dataclass
class SlotConfig:
    """A player/team slot configuration (FUN_004835a0)."""
    index: int = 0
    name: str = ""
    active: bool = False
    starting_gold: int = 0
    field_0c: int = 0
    sub_items: list[int] = field(default_factory=list)


def read_slot_config(r: BinaryReader) -> SlotConfig:
    """Read a slot configuration entry (FUN_004835a0)."""
    sc = SlotConfig()
    sc.name = r.read_string()
    sc.active = r.read_bool_u32()
    sc.starting_gold = r.read_u32()
    sc.field_0c = r.read_u32()
    sub_count = r.read_u32()
    sc.sub_items = [r.read_u32() for _ in range(sub_count)]
    return sc


def read_quest_file(filepath) -> QuestFile:
    """
    Parse a .q file using exact sequential reading matching RGSEditor (FUN_00467670).

    Args:
        filepath: Path to the .q binary file

    Returns:
        QuestFile with all parsed sections

    Raises:
        ValueError: On invalid magic or format errors
        EOFError: On truncated file
    """
    filepath = Path(filepath)
    data = filepath.read_bytes()
    r = BinaryReader(data)

    qf = QuestFile()

    # --- Section 1: Header (16 bytes) ---
    magic = r.read_tag4()
    if magic not in VERSION_MAP:
        raise ValueError(f"Invalid magic: {magic!r}")
    qf.magic = magic
    versions = VERSION_MAP[magic]
    force_ver = versions["force"]
    spawner_ver = versions["spawner"]
    team_ver = versions["team"]
    item_ver = versions["spawn_item"]

    r.read_u32()  # zeros at offset 4
    magic2 = r.read_tag4()  # repeated magic at offset 8
    r.read_u32()  # zeros at offset 12

    # --- Quest name + 4 tags + 2 map params ---
    qf.quest_name = r.read_string()
    # 4 tag reads: pattern_short, pattern_name, GUID hash, field_0x32
    qf._tag1 = r.read_tag4()  # "patt" (pattern short)
    qf._tag2 = r.read_tag4()  # "MyAI" (pattern name)
    qf._tag3 = r.read_u32()   # GUID/hash bytes
    qf._tag4 = r.read_u32()   # field at param_2[0x32]
    qf.map_params = (r.read_u32(), r.read_u32())

    # --- Spawner blocks (each prefixed by u32 index) ---
    spawner_count = r.read_u32()
    qf._spawner_indices = []
    for _ in range(spawner_count):
        idx = r.read_u32()  # spawner index
        qf._spawner_indices.append(idx)
        block = read_spawner_block(r, spawner_ver, team_ver, item_ver)
        qf.spawner_blocks.append(block)

    # --- Slot configs (player/team definitions, FUN_004835a0) ---
    qf._slot_configs = []
    slot_count = r.read_u32()
    for _ in range(slot_count):
        idx = r.read_u32()
        sc = read_slot_config(r)
        sc.index = idx
        qf._slot_configs.append(sc)

    # --- Three u32 values ---
    qf.field_46 = r.read_u32()
    qf.field_47 = r.read_u32()
    qf.quest_type_code = r.read_u32()

    # NOTE: No quest mode string is read from file for ANY version.
    # For RGMa/RGM9: quest mode is derived in-memory via FUN_00461d20 + FUN_00457060
    # For RGM1-RGM7: param_2[3] and param_2[4] come from the tag/u32 already read above

    # --- Region Patterns (FUN_0047e8d0) — sequential parse ---
    region_count = r.read_u32()
    for _ in range(region_count):
        tag = r.read_tag4()
        if tag != "NONE":
            # Read team-definition-like structure (FUN_0046e1c0)
            team = read_team_definition(r, team_ver, item_ver)
            qf.region_entries.append(RegionEntry(tag=tag, data=b""))
            qf.region_entries[-1]._team = team
        else:
            qf.region_entries.append(RegionEntry(tag="NONE"))

    # --- Force Pattern (FUN_00481480) ---
    # Caller reads tag4, then FUN_0047ef60 reads: tag4 + string + tag4×3 + u32×2
    force_count = r.read_u32()
    for _ in range(force_count):
        caller_tag = r.read_tag4()
        body_tag = r.read_tag4()
        fname = r.read_string()
        ref1 = r.read_tag4()
        ref2 = r.read_tag4()
        ref3 = r.read_tag4()
        val1 = r.read_u32()
        val2 = r.read_u32()
        qf.force_entries.append(ForceEntry(
            faction_code=caller_tag,
            faction_name=fname,
            pattern_ref=body_tag,
            field_5=ref1,
            field_6=ref2,
            active=val1,
            grid_position=val2,
        ))
        # Store the extra body_tag and refs for roundtrip
        qf.force_entries[-1]._body_tag = body_tag
        qf.force_entries[-1]._ref1 = ref1
        qf.force_entries[-1]._ref2 = ref2
        qf.force_entries[-1]._ref3 = ref3

    # --- Unit Patterns (two sets via FUN_0047bb00) ---
    qf.unit_patterns_2 = read_unit_pattern_set(
        r, force_ver, spawner_ver, team_ver, item_ver
    )
    # Second set may not exist in older files (file ends after first set)
    if r.remaining >= 4:
        qf.unit_patterns_3 = read_unit_pattern_set(
            r, force_ver, spawner_ver, team_ver, item_ver
        )
    else:
        qf.unit_patterns_3 = []

    # --- Finalization (4-byte tag, NOT null-terminated string) ---
    if magic in ("RGM7", "RGM6", "RGM5", "RGM4", "RGM3", "RGM2", "RGM1"):
        qf.rel_string = "Rel@"
    else:
        if r.remaining >= 4:
            qf.rel_string = r.read_tag4()

    return qf


# =============================================================================
# Sequential Writer (matches SaveQuest exactly — always RGMa)
# =============================================================================

def write_spawner_item(w: BinaryWriter, item: SpawnerItem):
    """Write a spawner item (RGMa = spawn_item version 3)."""
    w.write_tag4(item.name)
    w.write_u32(item.spawn_level)
    w.write_u32(item.field_0c)
    w.write_u32(item.field_10)
    w.write_bool_u32(item.active)
    w.write_u32(item.lair_resource)


def write_team_definition(w: BinaryWriter, team: TeamDefinition):
    """Write a team definition (RGMa = team version 7)."""
    w.write_tag4(team.name_tag)
    w.write_string(team.name_string)
    w.write_bool_u32(team.is_active)
    w.write_bool_u32(team.is_expanding)
    w.write_u32(len(team.spawner_items))
    for item in team.spawner_items:
        write_spawner_item(w, item)


def write_spawner_block(w: BinaryWriter, block: SpawnerBlock):
    """Write a spawner block (RGMa = spawner version 3)."""
    w.write_u32(block.field_00)
    w.write_u32(block.field_04)
    w.write_u32(block.field_08)
    w.write_u32(block.field_0c)
    w.write_u32(block.field_10)
    write_team_definition(w, block.team)
    w.write_u32(len(block.extra_names))
    for name in block.extra_names:
        w.write_tag4(name)


def write_unit_instance(w: BinaryWriter, inst: UnitInstance):
    """Write a single unit instance (FUN_004785c0)."""
    w.write_tag4(inst.object_id)
    w.write_u32(inst.field_08)
    w.write_string(inst.description)
    w.write_u32(len(inst.candidate_cells))
    for pos in inst.candidate_cells:
        w.write_bytes(bytes([pos]))


def write_unit_pattern(w: BinaryWriter, pat: UnitPattern):
    """Write a single Unit Pattern (FUN_00472ca0) — RGMa format."""
    w.write_tag4(pat.terrain_code)
    w.write_string(pat.name)
    w.write_bool_u32(pat.has_alternate)
    w.write_u32(pat.field_04)
    w.write_tag4(pat.tag_48)
    w.write_u32(pat.field_44)
    # Unit instances
    w.write_u32(len(pat.entries))
    for inst in pat.entries:
        write_unit_instance(w, inst)
    # Spawner blocks (each prefixed by u32 key)
    w.write_u32(len(pat.spawners))
    spawner_keys = getattr(pat, '_spawner_keys', None) or [0] * len(pat.spawners)
    for key, block in zip(spawner_keys, pat.spawners):
        w.write_u32(key)
        write_spawner_block(w, block)
    # Force version 5+ fields (RGMa = force 8)
    w.write_u32(pat.resolution)
    # Force version 7+ fields
    w.write_u32(pat.field_74)
    w.write_u32(pat.field_78)
    w.write_u32(pat.field_7c)
    w.write_bool_u32(pat.flag_70)
    w.write_bool_u32(pat.flag_71)
    w.write_bool_u32(pat.flag_72)
    w.write_bool_u32(pat.flag_73)
    # Force version 8+ field
    w.write_bool_u32(pat.flag_29)


def write_unit_pattern_set(w: BinaryWriter, patterns: list[UnitPattern]):
    """Write a set of Unit Patterns (FUN_0047a230)."""
    w.write_u32(len(patterns))
    for pat in patterns:
        faction_tag = getattr(pat, '_faction_tag', pat.terrain_code[:4])
        w.write_tag4(faction_tag)
        write_unit_pattern(w, pat)


def write_force_entry(w: BinaryWriter, entry: ForceEntry):
    """Write a Force Pattern entry (FUN_0047ee90)."""
    w.write_tag4(entry.faction_code)
    w.write_string(entry.faction_name)
    w.write_tag4(entry.pattern_ref)
    w.write_tag4(entry.field_5)
    w.write_tag4(entry.field_6)
    w.write_u32(entry.active)
    w.write_u32(entry.grid_position)


def write_force_pattern(w: BinaryWriter, entries: list[ForceEntry]):
    """Write the Force Pattern section (FUN_0047fef0)."""
    w.write_u32(len(entries))
    for entry in entries:
        write_force_entry(w, entry)


def write_region_pattern(w: BinaryWriter, entries: list[RegionEntry]):
    """Write the Region Pattern section (FUN_0047d1e0)."""
    # Count includes NONE entries that are skipped
    # For simplicity, write only real entries + mark rest as NONE
    w.write_u32(len(entries))
    for entry in entries:
        if entry.tag == "NONE":
            continue
        w.write_tag4(entry.tag)
        w.write_bytes(entry.data)


def write_quest_file(qf: QuestFile, output_path) -> Path:
    """
    Write a complete .q file in RGMa format (matches SaveQuest FUN_00465f90).

    Args:
        qf: QuestFile data structure
        output_path: Where to write the binary

    Returns:
        Path to the written file
    """
    output_path = Path(output_path)
    w = BinaryWriter()

    # --- Header (16 bytes) ---
    w.write_tag4("RGMa")
    w.write_u32(0)
    w.write_tag4("RGMa")
    w.write_u32(0)

    # --- Quest name + tags + map params ---
    w.write_string(qf.quest_name)
    w.write_tag4(qf._tag1)
    w.write_tag4(qf._tag2)
    w.write_u32(qf._tag3)
    w.write_u32(qf._tag4)
    w.write_u32(qf.map_params[0])
    w.write_u32(qf.map_params[1])

    # --- Spawner blocks (each prefixed by index) ---
    indices = getattr(qf, '_spawner_indices', None) or list(range(len(qf.spawner_blocks)))
    w.write_u32(len(qf.spawner_blocks))
    for idx, block in zip(indices, qf.spawner_blocks):
        w.write_u32(idx)
        write_spawner_block(w, block)

    # --- Slot configs ---
    slot_configs = getattr(qf, '_slot_configs', [])
    w.write_u32(len(slot_configs))
    for sc in slot_configs:
        w.write_u32(sc.index)
        w.write_string(sc.name)
        w.write_bool_u32(sc.active)
        w.write_u32(sc.starting_gold)
        w.write_u32(sc.field_0c)
        w.write_u32(len(sc.sub_items))
        for sub in sc.sub_items:
            w.write_u32(sub)

    # --- Three u32 values ---
    w.write_u32(qf.field_46)
    w.write_u32(qf.field_47)
    w.write_u32(qf.quest_type_code)

    # NOTE: No quest mode string written — it's derived in-memory, not stored in file

    # --- Region Patterns ---
    w.write_u32(len(qf.region_entries))
    for entry in qf.region_entries:
        w.write_tag4(entry.tag)
        if entry.tag != "NONE":
            team = getattr(entry, '_team', None)
            if team:
                write_team_definition(w, team)

    # --- Force Pattern ---
    w.write_u32(len(qf.force_entries))
    for fe in qf.force_entries:
        w.write_tag4(fe.faction_code)
        body_tag = getattr(fe, '_body_tag', fe.pattern_ref)
        w.write_tag4(body_tag)
        w.write_string(fe.faction_name)
        ref1 = getattr(fe, '_ref1', fe.field_5)
        ref2 = getattr(fe, '_ref2', fe.field_6)
        ref3 = getattr(fe, '_ref3', "NONE")
        w.write_tag4(ref1)
        w.write_tag4(ref2)
        w.write_tag4(ref3)
        w.write_u32(fe.active)
        w.write_u32(fe.grid_position)

    # --- Unit Patterns (two sets) ---
    write_unit_pattern_set(w, qf.unit_patterns_2)
    write_unit_pattern_set(w, qf.unit_patterns_3)

    # --- Finalization (written as tag4, not null-terminated string) ---
    w.write_tag4(qf.rel_string)

    # Write to disk
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(w.getvalue())
    return output_path


# =============================================================================
# High-Level Quest Generation API
# =============================================================================

def create_quest(
    name: str,
    unit_patterns: list[dict],
    map_size: tuple[int, int] = (256, 256),
    terrain: str = "grass",
    force_layout: list[dict] = None,
    starting_gold: int = 30000,
    spawners: list[dict] = None,
    seed: int = 0,
) -> QuestFile:
    """
    Create a complete QuestFile from scratch — no template dependency.

    Args:
        name: Quest name (used as GPL init function name)
        unit_patterns: List of pattern definitions, each a dict:
            - "name": Faction name (e.g., "Player1", "Goblin Kingdom")
            - "entries": List of unit defs:
                - "id": 4-char object ID (e.g., "ABJ1", "BBH1", "BBw1")
                - "desc": Human-readable description
                - "cells": List of position bytes (65-89) or single letter strings
                - "lair_override": Optional per-lair spawner settings (dict or list of dicts):
                    - "monsters": List of (id, weight%) tuples or {"id", "weight"} dicts
                    - "max_hp": Lair max HP override (0 = default)
                    - "spawn_rate_ms": Spawn interval in ms (0 = default)
                    - "dispersion": Spawn radius in pixels (0 = default)
                    - "hit_rate_sub": Ms subtracted from spawn delay per hit (0 = default)
                    - "death_monsters": List of 4-char monster IDs released on lair death
                  If a list is provided, each entry is a difficulty level (sub-index 0, 1, 2...)
            - "terrain": Optional terrain code (default "gras")
            - "starting_gold": Optional per-pattern gold (default 30000)
            - "resolution": Optional grid spacing (default 3)
        map_size: (width, height) in tiles — (128, 128), (256, 256), or (512, 512)
        terrain: Terrain configuration. Can be:
            - A preset name (string): "grass", "snow", "grass_snow", "forest", "swamp",
              "desert", "scorched", "mountain", "snow_mountain", "dark_forest", "barren",
              "fertile", "winter", "bog"
            - A custom zone blend (dict): {"zone_key": weight, ...}
              Zone keys from LANDSCAPE_ZONES (e.g., "grass", "snow_ice", "mountain")
            - Fully custom (list of dicts): each with "tag", "name", "fractal",
              "texture", "height", "weight", and optional "field_0c"
        force_layout: Optional force pattern configuration. Can be:
            - None: Auto-layout (distribute patterns across map)
            - List of dicts (simple): [{"pattern_idx": 0, "position": "W"}, ...]
            - Dict (full control):
                - "name": Force pattern name (default: quest name)
                - "entries": List of {"pattern_idx": int, "position": str or "off_map"}
                  Position can be: single letter "M", multi-candidate "ABCDE", or "off_map"
                - "players": List of allowed player counts [1, 2, 3, 4] (default [1, 2])
                - "difficulty": Difficulty rating 0-100 (default 50)
                - "money": Money rating 0-100 (default 50)
                - "time": Time rating 0-100 (default 50)
                - "resolution": Grid cell spacing (default 3)
        starting_gold: Default starting gold for player factions
        seed: Random seed for map generation (0 = different each play, non-zero = fixed layout)

    Returns:
        QuestFile ready to write with write_quest_file()

    Example:
        qf = create_quest(
            "MyQuest",
            [
                {"name": "Player1", "entries": [
                    {"id": "ABJ1", "desc": "Palace", "cells": [77]}
                ]},
                {"name": "Enemy Lairs", "entries": [
                    {"id": "BBH1", "desc": "Goblin Camp", "cells": [65, 69],
                     "lair_override": {
                         "monsters": [("BVL1", 60), ("BVL2", 40)],
                         "max_hp": 200,
                         "spawn_rate_ms": 15000,
                         "dispersion": 500,
                         "hit_rate_sub": 50,
                     }},
                    {"id": "BBw1", "desc": "Ice Cave", "cells": [85]},
                ]},
            ],
            map_size=(256, 256),
            terrain="grass_snow",
        )
        write_quest_file(qf, "output/Quest.q")
    """
    import random

    qf = QuestFile()
    qf.magic = "RGMa"
    qf.quest_name = name

    # Metadata tags
    short = name[:4] if len(name) >= 4 else (name + "    ")[:4]
    qf._tag1 = "patt"
    qf._tag2 = short
    qf._tag3 = seed if seed != 0 else random.randint(0, 0xFFFFFFFF)
    qf._tag4 = 0
    qf.map_params = map_size

    # Spawner blocks (define what monsters come out of lairs)
    # Each block = one difficulty level. Users can customize via `spawners` param.
    if spawners:
        qf._spawner_indices = list(range(0, len(spawners) * 1000, 1000))
        for i, sp_def in enumerate(spawners):
            items = []
            for monster in sp_def.get("monsters", []):
                items.append(SpawnerItem(
                    name=monster["id"],
                    spawn_level=monster.get("level", 10),
                    field_0c=monster.get("field_0c", 0),
                    field_10=monster.get("field_10", 0),
                    active=monster.get("active", True),
                    lair_resource=monster.get("lair_resource", 0),
                ))
            block = SpawnerBlock(
                field_04=sp_def.get("lair_gold", 10000),
                team=TeamDefinition(
                    name_tag="NONE", name_string="none",
                    is_active=False, is_expanding=False,
                    spawner_items=items if items else [
                        SpawnerItem(name="BVr1", spawn_level=10),
                    ]
                ),
            )
            qf.spawner_blocks.append(block)
    else:
        # Default: 4 difficulty levels with basic monsters
        default_monsters = [
            SpawnerItem(name="BVr1", spawn_level=10),
            SpawnerItem(name="BVs1", spawn_level=10),
            SpawnerItem(name="BVq1", spawn_level=10),
        ]
        qf._spawner_indices = [2000, 2001, 2002, 2003]
        for i in range(4):
            block = SpawnerBlock(
                field_04=10000 * (1 + i // 2),
                team=TeamDefinition(
                    name_tag="NONE", name_string="none",
                    is_active=False, is_expanding=False,
                    spawner_items=list(default_monsters)
                ),
            )
            qf.spawner_blocks.append(block)

    # Slot configs (8 slots: Human, AI, 5× empty, Monsters)
    qf._slot_configs = [
        SlotConfig(index=0, name="Human Player", active=True,
                   starting_gold=starting_gold, sub_items=[0]),
        SlotConfig(index=1, name="player2_ai", active=True,
                   starting_gold=starting_gold, sub_items=[1]),
    ]
    for i in range(2, 7):
        qf._slot_configs.append(
            SlotConfig(index=i, name="No Name", active=False))
    qf._slot_configs.append(
        SlotConfig(index=7, name="Monsters", active=True,
                   sub_items=list(range(len(qf.spawner_blocks)))))

    # Three u32 values
    qf.field_46 = 0
    qf.field_47 = 0
    qf.quest_type_code = 0

    # Region + Force entries (terrain configuration)
    # The `terrain` parameter can be:
    # - A preset name (string key into TERRAIN_PRESETS)
    # - A dict of zone_key:weight pairs (custom blend)
    # - A list of dicts for fully custom landscape definitions
    if isinstance(terrain, dict):
        zone_blend = terrain
    elif isinstance(terrain, list):
        # Fully custom — list of {"tag", "name", "fractal", "texture", "height", "weight"}
        zone_blend = None  # handled separately below
    else:
        zone_blend = TERRAIN_PRESETS.get(terrain, TERRAIN_PRESETS["grass"])

    if zone_blend is not None:
        # Build from zone blend (preset or custom dict)
        region_items = []
        force_list = []
        for zone_key, weight in zone_blend.items():
            zone = LANDSCAPE_ZONES.get(zone_key)
            if zone is None:
                raise ValueError(f"Unknown landscape zone: {zone_key!r}. "
                                 f"Available: {sorted(LANDSCAPE_ZONES.keys())}")
            body_tag, display_name, fractal_ref, texture_ref, height_ref = zone
            # Region item (terrain patch probability)
            # field_0c encodes a terrain type modifier; derive from texture ref
            f0c = 0
            if "Sn" in texture_ref or "sno" in texture_ref:
                f0c = 13  # Snow terrain type
            elif "Sw" in texture_ref or "swa" in texture_ref or "bog" in texture_ref:
                f0c = 10  # Swamp
            elif "Sc" in texture_ref or "Ar" in texture_ref:
                f0c = 5   # Scorched/arid
            elif "Pl" in texture_ref or "for" in texture_ref or "Gra" in texture_ref:
                f0c = 0   # Green/default
            elif "All" in texture_ref or "mud" in texture_ref:
                f0c = 4   # Dirt
            region_items.append(SpawnerItem(
                name=body_tag, spawn_level=weight, field_0c=f0c))
            # Force entry (landscape resource references)
            fe = ForceEntry(
                faction_code=body_tag, faction_name=display_name,
                active=0, grid_position=0)
            fe._body_tag = body_tag
            fe._ref1 = fractal_ref
            fe._ref2 = texture_ref
            fe._ref3 = height_ref
            force_list.append(fe)

        region_team = TeamDefinition(
            name_tag="patt", name_string="pattern",
            is_active=False, is_expanding=False,
            spawner_items=region_items
        )
        region_entry = RegionEntry(tag="patt")
        region_entry._team = region_team
        qf.region_entries = [region_entry]
        qf.force_entries = force_list

    elif isinstance(terrain, list):
        # Fully custom terrain definitions
        region_items = []
        force_list = []
        for tdef in terrain:
            tag = tdef["tag"]
            region_items.append(SpawnerItem(
                name=tag, spawn_level=tdef.get("weight", 50),
                field_0c=tdef.get("field_0c", 0)))
            fe = ForceEntry(
                faction_code=tag, faction_name=tdef.get("name", tag),
                active=0, grid_position=0)
            fe._body_tag = tag
            fe._ref1 = tdef.get("fractal", "xBBC")
            fe._ref2 = tdef.get("texture", "#Pla")
            fe._ref3 = tdef.get("height", "Bump")
            force_list.append(fe)

        region_team = TeamDefinition(
            name_tag="patt", name_string="pattern",
            is_active=False, is_expanding=False,
            spawner_items=region_items
        )
        region_entry = RegionEntry(tag="patt")
        region_entry._team = region_team
        qf.region_entries = [region_entry]
        qf.force_entries = force_list

    # Unit patterns (set 2 — placed buildings/lairs)
    qf.unit_patterns_2 = []
    for pat_def in unit_patterns:
        pat = UnitPattern()
        pat_name = pat_def["name"]
        pat_short = pat_name[:4]
        pat._faction_tag = pat_short
        pat.terrain_code = pat_short
        pat.name = pat_name
        pat.has_alternate = True
        pat.field_04 = pat_def.get("starting_gold", starting_gold)
        pat.tag_48 = pat_def.get("terrain", "gras")
        pat.field_44 = 5
        pat.resolution = pat_def.get("resolution", 3)
        pat.field_74 = 50
        pat.field_78 = 50
        pat.field_7c = 50
        pat.flag_70 = True
        pat.flag_71 = True
        pat.flag_72 = False
        pat.flag_73 = False
        pat.flag_29 = False
        pat._spawner_keys = []
        pat.spawners = []

        for entry_def in pat_def.get("entries", []):
            cells = entry_def.get("cells", [77])
            if isinstance(cells, str):
                cells = [ord(c) for c in cells]
            elif isinstance(cells, list) and cells and isinstance(cells[0], str):
                cells = [ord(c) for c in cells]
            pat.entries.append(UnitInstance(
                object_id=entry_def["id"],
                field_08=0,
                description=entry_def.get("desc", entry_def["id"]),
                candidate_cells=cells,
            ))

        # Per-lair spawner overrides
        # Key scheme: entry_index * 1000 + sub_index
        # Each entry can have multiple override blocks (for difficulty levels)
        for entry_idx, entry_def in enumerate(pat_def.get("entries", [])):
            lair_override = entry_def.get("lair_override")
            if lair_override is None:
                continue
            # Support single override or list of overrides (for multiple difficulty levels)
            overrides = lair_override if isinstance(lair_override, list) else [lair_override]
            for sub_idx, ovr in enumerate(overrides):
                key = entry_idx * 1000 + sub_idx
                monsters = ovr.get("monsters", [])
                items = []
                for m in monsters:
                    if isinstance(m, (tuple, list)) and len(m) >= 2:
                        items.append(SpawnerItem(name=m[0], spawn_level=m[1]))
                    elif isinstance(m, dict):
                        items.append(SpawnerItem(
                            name=m["id"],
                            spawn_level=m.get("weight", 0),
                        ))
                    else:
                        items.append(SpawnerItem(name=m, spawn_level=0))
                # Pad to 4 slots with NONE entries (matches RGSEditor behavior)
                while len(items) < 4:
                    items.append(SpawnerItem(name="NONE", spawn_level=0))
                block = SpawnerBlock(
                    field_00=ovr.get("max_hp", 0),
                    field_04=ovr.get("spawn_rate_ms", 0),
                    field_08=ovr.get("dispersion", 0),
                    field_0c=0,
                    field_10=ovr.get("hit_rate_sub", 0),
                    team=TeamDefinition(
                        name_tag="NONE", name_string="none",
                        is_active=False, is_expanding=False,
                        spawner_items=items,
                    ),
                    extra_names=ovr.get("death_monsters", []),
                )
                pat._spawner_keys.append(key)
                pat.spawners.append(block)

        qf.unit_patterns_2.append(pat)

    # Unit patterns set 3 (Force Pattern — map-level placement)
    force_pat = UnitPattern()
    force_pat._faction_tag = short
    force_pat.terrain_code = short
    force_pat.name = force_layout.get("name", name) if isinstance(force_layout, dict) else name
    force_pat.has_alternate = False
    force_pat.field_04 = 0
    force_pat.tag_48 = "NONE"
    force_pat.field_44 = 4
    force_pat.resolution = 0
    force_pat._spawner_keys = []
    force_pat.spawners = []

    # Force layout configuration
    # Can be:
    #   None — auto-layout all patterns
    #   List of dicts — explicit placement entries (legacy simple format)
    #   Dict with "entries", "players", "difficulty", "resolution" — full control
    if isinstance(force_layout, dict):
        # Full force layout configuration
        fl_entries = force_layout.get("entries", [])
        fl_players = force_layout.get("players", [1, 2])
        fl_difficulty = force_layout.get("difficulty", 50)
        fl_money = force_layout.get("money", 50)
        fl_time = force_layout.get("time", 50)
        fl_resolution = force_layout.get("resolution", 3)

        force_pat.name = force_layout.get("name", name)
        force_pat.resolution = fl_resolution
        force_pat.field_74 = fl_difficulty
        force_pat.field_78 = fl_money
        force_pat.field_7c = fl_time
        force_pat.flag_70 = 1 in fl_players
        force_pat.flag_71 = 2 in fl_players
        force_pat.flag_72 = 3 in fl_players
        force_pat.flag_73 = 4 in fl_players

        for fl in fl_entries:
            idx = fl["pattern_idx"]
            ref_name = unit_patterns[idx]["name"]
            # Position: letter, list of letters (multi-candidate), or "off_map"
            pos = fl.get("position", "M")
            if pos == "off_map" or pos is None:
                cells = []
            elif isinstance(pos, str) and len(pos) == 1:
                cells = [ord(pos)]
            elif isinstance(pos, str):
                cells = [ord(c) for c in pos]  # Multi-candidate positions
            elif isinstance(pos, list):
                cells = [ord(c) if isinstance(c, str) else c for c in pos]
            else:
                cells = [ord(pos)]
            force_pat.entries.append(UnitInstance(
                object_id=ref_name[:4],
                field_08=5,
                description=ref_name,
                candidate_cells=cells,
            ))
    elif isinstance(force_layout, list):
        # Legacy simple list format
        force_pat.field_74 = 50
        force_pat.field_78 = 50
        force_pat.field_7c = 50
        force_pat.flag_70 = True
        force_pat.flag_71 = True
        force_pat.flag_72 = True
        force_pat.flag_73 = True
        for fl in force_layout:
            idx = fl["pattern_idx"]
            pos_letter = fl.get("position", "M")
            ref_name = unit_patterns[idx]["name"]
            if pos_letter == "off_map" or pos_letter is None:
                cells = []
            elif isinstance(pos_letter, str) and len(pos_letter) > 1:
                cells = [ord(c) for c in pos_letter]
            else:
                cells = [ord(pos_letter)]
            force_pat.entries.append(UnitInstance(
                object_id=ref_name[:4],
                field_08=5,
                description=ref_name,
                candidate_cells=cells,
            ))
    else:
        # Auto-layout: first pattern at bottom, rest distributed
        force_pat.field_74 = 50
        force_pat.field_78 = 50
        force_pat.field_7c = 50
        force_pat.flag_70 = True
        force_pat.flag_71 = True
        force_pat.flag_72 = True
        force_pat.flag_73 = True
        auto_positions = ["W", "C", "R", "Q", "S", "N", "M", "H", "L"]
        for i, pat_def in enumerate(unit_patterns):
            pos = auto_positions[i] if i < len(auto_positions) else "M"
            force_pat.entries.append(UnitInstance(
                object_id=pat_def["name"][:4],
                field_08=5,
                description=pat_def["name"],
                candidate_cells=[ord(pos)],
            ))

    qf.unit_patterns_3 = [force_pat]
    force_pat.flag_29 = False
    qf.rel_string = "Rel@"

    return qf


# =============================================================================
# Round-trip validation
# =============================================================================

def roundtrip_test(filepath) -> tuple[bool, str]:
    """
    Parse a .q file, write it back, and compare bytes.
    Returns (success, message).
    """
    filepath = Path(filepath)
    try:
        qf = read_quest_file(filepath)
        w = BinaryWriter()
        # Re-serialize
        output = Path(str(filepath) + ".roundtrip")
        write_quest_file(qf, output)
        # Compare
        original = filepath.read_bytes()
        generated = output.read_bytes()
        if original == generated:
            output.unlink()
            return True, f"PASS: {filepath.name} ({len(original)} bytes)"
        else:
            # Find first difference
            for i, (a, b) in enumerate(zip(original, generated)):
                if a != b:
                    return False, (
                        f"FAIL: {filepath.name} — first diff at offset 0x{i:04X} "
                        f"(orig=0x{a:02X}, gen=0x{b:02X}), "
                        f"orig={len(original)}B, gen={len(generated)}B"
                    )
            shorter = min(len(original), len(generated))
            return False, (
                f"FAIL: {filepath.name} — size mismatch "
                f"(orig={len(original)}B, gen={len(generated)}B), "
                f"first {shorter} bytes match"
            )
    except Exception as e:
        return False, f"ERROR: {filepath.name} — {type(e).__name__}: {e}"


# =============================================================================
# CLI
# =============================================================================

def _cli_inspect(filepath, section=None):
    """Inspect a .q file, optionally filtering to a specific section."""
    qf = read_quest_file(filepath)

    if section is None or section == "header":
        print(f"=== Header ===")
        print(f"  Magic: {qf.magic}")
        print(f"  Quest name: {qf.quest_name}")
        print(f"  Map size: {qf.map_params[0]}x{qf.map_params[1]}")
        print(f"  Tags: {qf._tag1} / {qf._tag2} / seed={qf._tag3}")
        if section == "header":
            return

    if section is None or section == "spawners":
        print(f"\n=== Spawner Blocks ({len(qf.spawner_blocks)}) ===")
        for i, (idx, b) in enumerate(zip(qf._spawner_indices, qf.spawner_blocks)):
            monsters = [it for it in b.team.spawner_items if it.name != "NONE"]
            m_str = ', '.join(f"{m.name}({m.spawn_level}%)" for m in monsters)
            print(f"  [{idx}] hp={b.max_hp} rate={b.spawn_rate_ms}ms "
                  f"disp={b.dispersion} hit_sub={b.hit_rate_sub} | {m_str}")
        if section == "spawners":
            return

    if section is None or section == "terrain":
        print(f"\n=== Terrain ===")
        for entry in qf.region_entries:
            team = getattr(entry, '_team', None)
            if team:
                items = ', '.join(f"{it.name}(w={it.spawn_level})" for it in team.spawner_items)
                print(f"  Region '{entry.tag}': {items}")
        print(f"  Landscape refs ({len(qf.force_entries)}):")
        for fe in qf.force_entries:
            r1 = getattr(fe, '_ref1', '?')
            r2 = getattr(fe, '_ref2', '?')
            r3 = getattr(fe, '_ref3', '?')
            print(f"    {fe.faction_code} '{fe.faction_name}' fractal={r1} tex={r2} height={r3}")
        if section == "terrain":
            return

    if section is None or section == "patterns":
        print(f"\n=== Unit Patterns (set 2: {len(qf.unit_patterns_2)}) ===")
        for i, p in enumerate(qf.unit_patterns_2):
            print(f"  [{i}] '{p.name}' (faction={p.terrain_code}) "
                  f"entries={len(p.entries)} spawners={len(p.spawners)} res={p.resolution}")
            for e in p.entries:
                cells = ''.join(chr(c) for c in e.candidate_cells) if e.candidate_cells else "(off-map)"
                print(f"      {e.object_id} '{e.description}' @ [{cells}]")
        if section == "patterns":
            return

    if section is None or section == "force":
        print(f"\n=== Force Pattern (set 3: {len(qf.unit_patterns_3)}) ===")
        for fp in qf.unit_patterns_3:
            flags = []
            if getattr(fp, 'flag_70', False): flags.append("1P")
            if getattr(fp, 'flag_71', False): flags.append("2P")
            if getattr(fp, 'flag_72', False): flags.append("3P")
            if getattr(fp, 'flag_73', False): flags.append("4P")
            print(f"  '{fp.name}' players=[{','.join(flags)}] "
                  f"diff={fp.field_74} money={fp.field_78} time={fp.field_7c} res={fp.resolution}")
            for e in fp.entries:
                cells = ''.join(chr(c) for c in e.candidate_cells) if e.candidate_cells else "(off-map)"
                print(f"    {e.object_id} '{e.description}' @ [{cells}]")


def _cli_create(config_path, output_path):
    """Create a quest from a JSON configuration file."""
    import json
    config = json.loads(Path(config_path).read_text())

    qf = create_quest(
        name=config["name"],
        unit_patterns=config["unit_patterns"],
        map_size=tuple(config.get("map_size", [256, 256])),
        terrain=config.get("terrain", "grass"),
        force_layout=config.get("force_layout"),
        starting_gold=config.get("starting_gold", 30000),
        spawners=config.get("spawners"),
        seed=config.get("seed", 0),
    )
    out = write_quest_file(qf, Path(output_path))
    print(f"Created: {out} ({out.stat().st_size} bytes)")


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("RGS Format Tool — Sequential .q file parser/writer")
        print()
        print("Usage:")
        print("  rgs_format.py inspect <file.q> [--section <name>]")
        print("  rgs_format.py create --config <quest.json> --output <file.q>")
        print("  rgs_format.py roundtrip <file.q>")
        print("  rgs_format.py test <directory>")
        print("  rgs_format.py presets")
        print()
        print("Inspect sections: header, spawners, terrain, patterns, force")
        print()
        print("JSON config format for 'create':")
        print('  {"name": "...", "unit_patterns": [...], "terrain": "...", ...}')
        print("  See create_quest() docstring for full schema.")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "inspect":
        filepath = sys.argv[2]
        section = None
        if "--section" in sys.argv:
            idx = sys.argv.index("--section")
            section = sys.argv[idx + 1]
        _cli_inspect(filepath, section)

    elif cmd == "create":
        config_path = None
        output_path = None
        args = sys.argv[2:]
        i = 0
        while i < len(args):
            if args[i] == "--config":
                config_path = args[i + 1]
                i += 2
            elif args[i] == "--output":
                output_path = args[i + 1]
                i += 2
            else:
                i += 1
        if not config_path or not output_path:
            print("Error: --config and --output are required")
            sys.exit(1)
        _cli_create(config_path, output_path)

    elif cmd == "modify":
        # Modify an existing .q file with JSON patch
        filepath = None
        patch_path = None
        output_path = None
        args = sys.argv[2:]
        i = 0
        while i < len(args):
            if args[i] == "--patch":
                patch_path = args[i + 1]
                i += 2
            elif args[i] == "--output":
                output_path = args[i + 1]
                i += 2
            elif not filepath:
                filepath = args[i]
                i += 1
            else:
                i += 1
        if not filepath:
            print("Error: source .q file is required")
            print("Usage: rgs_format.py modify <file.q> --patch <patch.json> [--output <out.q>]")
            sys.exit(1)
        import json
        qf = read_quest_file(filepath)
        if patch_path:
            patch = json.loads(Path(patch_path).read_text())
            # Apply patch fields
            if "map_size" in patch:
                qf.map_params = tuple(patch["map_size"])
            if "seed" in patch:
                qf._tag3 = patch["seed"]
            if "quest_name" in patch:
                qf.quest_name = patch["quest_name"]
        out_target = Path(output_path) if output_path else Path(filepath)
        write_quest_file(qf, out_target)
        print(f"Modified: {out_target} ({out_target.stat().st_size} bytes)")

    elif cmd == "roundtrip":
        ok, msg = roundtrip_test(sys.argv[2])
        print(msg)
        sys.exit(0 if ok else 1)

    elif cmd == "test":
        directory = Path(sys.argv[2])
        q_files = sorted(directory.rglob("*.q"))
        passed = 0
        failed = 0
        errors = 0
        for qf in q_files:
            ok, msg = roundtrip_test(qf)
            print(msg)
            if ok:
                passed += 1
            elif "ERROR" in msg:
                errors += 1
            else:
                failed += 1
        print(f"\n{passed} passed, {failed} failed, {errors} errors "
              f"out of {len(q_files)} files")

    elif cmd == "presets":
        print("Available terrain presets:")
        for name, zones in sorted(TERRAIN_PRESETS.items()):
            zone_list = ', '.join(f"{k}({v})" for k, v in zones.items())
            print(f"  {name:15s} : {zone_list}")
        print(f"\nAvailable landscape zones ({len(LANDSCAPE_ZONES)}):")
        for name, (tag, desc, frac, tex, height) in sorted(LANDSCAPE_ZONES.items()):
            print(f"  {name:18s} : {desc} (tex={tex}, height={height})")

    else:
        print(f"Unknown command: {cmd}")
        print("Available: inspect, create, roundtrip, test, presets")
        sys.exit(1)
