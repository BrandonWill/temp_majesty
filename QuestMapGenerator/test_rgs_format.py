"""
Unit tests for rgs_format.py — the sequential .q file parser/writer.

Run with: python -m pytest QuestMapGenerator/test_rgs_format.py -v
Or:       python QuestMapGenerator/test_rgs_format.py
"""
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from rgs_format import (
    BinaryReader, BinaryWriter,
    SpawnerBlock, SpawnerItem, TeamDefinition, UnitInstance, UnitPattern,
    RegionEntry, ForceEntry, SlotConfig, QuestFile,
    read_quest_file, write_quest_file, create_quest,
    read_spawner_block, write_spawner_block,
    read_team_definition, write_team_definition,
    read_unit_instance,
    TERRAIN_PRESETS, LANDSCAPE_ZONES,
)

# Path to real quest files for integration tests
QUEST_DIR = Path(__file__).parent.parent / "Quests"
QUESTMX_DIR = Path(__file__).parent.parent / "QuestsMX"
MYQUEST_Q = Path(__file__).parent.parent / "MyQuest" / "Quest.q"


# =============================================================================
# BinaryReader / BinaryWriter primitives
# =============================================================================

class TestBinaryReader:
    def test_read_u32(self):
        r = BinaryReader(b"\x01\x00\x00\x00\xff\x00\x00\x00")
        assert r.read_u32() == 1
        assert r.read_u32() == 255

    def test_read_tag4(self):
        r = BinaryReader(b"gras")
        assert r.read_tag4() == "gras"

    def test_read_tag4_with_nulls(self):
        r = BinaryReader(b"AB\x00\x00")
        tag = r.read_tag4()
        assert len(tag) == 4  # Always 4 chars

    def test_read_string(self):
        r = BinaryReader(b"hello\x00extra")
        assert r.read_string() == "hello"

    def test_read_bool_u32(self):
        r = BinaryReader(b"\x01\x00\x00\x00\x00\x00\x00\x00")
        assert r.read_bool_u32() is True
        assert r.read_bool_u32() is False

    def test_read_bytes(self):
        r = BinaryReader(b"\x41\x42\x43\x44\x45")
        assert r.read_bytes(3) == b"ABC"

    def test_remaining(self):
        r = BinaryReader(b"12345678")
        r.read_u32()
        assert r.remaining == 4


class TestBinaryWriter:
    def test_write_u32(self):
        w = BinaryWriter()
        w.write_u32(42)
        assert w.getvalue() == b"\x2a\x00\x00\x00"

    def test_write_tag4(self):
        w = BinaryWriter()
        w.write_tag4("gras")
        assert w.getvalue() == b"gras"

    def test_write_tag4_pads_short(self):
        w = BinaryWriter()
        w.write_tag4("AB")
        assert len(w.getvalue()) == 4

    def test_write_string(self):
        w = BinaryWriter()
        w.write_string("hello")
        assert w.getvalue() == b"hello\x00"

    def test_write_bool_u32(self):
        w = BinaryWriter()
        w.write_bool_u32(True)
        w.write_bool_u32(False)
        assert w.getvalue() == b"\x01\x00\x00\x00\x00\x00\x00\x00"

    def test_roundtrip_u32(self):
        w = BinaryWriter()
        w.write_u32(0)
        w.write_u32(1)
        w.write_u32(0xFFFFFFFF)
        w.write_u32(12345)
        r = BinaryReader(w.getvalue())
        assert r.read_u32() == 0
        assert r.read_u32() == 1
        assert r.read_u32() == 0xFFFFFFFF
        assert r.read_u32() == 12345


# =============================================================================
# SpawnerBlock — field mapping and property aliases
# =============================================================================

class TestSpawnerBlock:
    def test_default_values(self):
        b = SpawnerBlock()
        assert b.field_00 == 0
        assert b.field_04 == 0
        assert b.field_08 == 0
        assert b.field_0c == 0
        assert b.field_10 == 0

    def test_property_aliases_read(self):
        b = SpawnerBlock(field_00=500, field_04=30000, field_08=200, field_10=50)
        assert b.max_hp == 500
        assert b.spawn_rate_ms == 30000
        assert b.dispersion == 200
        assert b.hit_rate_sub == 50

    def test_property_aliases_write(self):
        b = SpawnerBlock()
        b.max_hp = 999
        b.spawn_rate_ms = 15000
        b.dispersion = 300
        b.hit_rate_sub = 100
        assert b.field_00 == 999
        assert b.field_04 == 15000
        assert b.field_08 == 300
        assert b.field_10 == 100

    def test_serialization_roundtrip(self):
        """Verify spawner block serialize/deserialize is consistent."""
        block = SpawnerBlock(
            field_00=200, field_04=15000, field_08=500, field_0c=4, field_10=50,
            team=TeamDefinition(
                name_tag="NONE", name_string="none",
                is_active=False, is_expanding=False,
                spawner_items=[
                    SpawnerItem(name="BVL1", spawn_level=60),
                    SpawnerItem(name="BVL2", spawn_level=40),
                    SpawnerItem(name="NONE", spawn_level=0),
                    SpawnerItem(name="NONE", spawn_level=0),
                ]
            ),
            extra_names=["BVL1", "BVL2"],
        )
        w = BinaryWriter()
        write_spawner_block(w, block)
        r = BinaryReader(w.getvalue())
        # RGMa = spawner_ver 3, team_ver 7, item_ver 3
        block2 = read_spawner_block(r, spawner_ver=3, team_ver=7, item_ver=3)
        assert block2.field_00 == 200
        assert block2.field_04 == 15000
        assert block2.field_08 == 500
        assert block2.field_0c == 4
        assert block2.field_10 == 50
        assert len(block2.team.spawner_items) == 4
        assert block2.team.spawner_items[0].name == "BVL1"
        assert block2.team.spawner_items[0].spawn_level == 60
        assert block2.extra_names == ["BVL1", "BVL2"]


# =============================================================================
# create_quest() API
# =============================================================================

class TestCreateQuest:
    def test_minimal_quest(self):
        """Simplest possible quest: one pattern with a palace."""
        qf = create_quest(
            "Minimal",
            [{"name": "Player1", "entries": [
                {"id": "ABJ1", "desc": "Palace", "cells": [77]}
            ]}],
        )
        assert qf.magic == "RGMa"
        assert qf.quest_name == "Minimal"
        assert qf.map_params == (256, 256)
        assert len(qf.unit_patterns_2) == 1
        assert len(qf.unit_patterns_3) == 1
        assert len(qf.region_entries) == 1
        assert len(qf.force_entries) >= 1
        assert len(qf.spawner_blocks) >= 1

    def test_write_and_read_back(self):
        """Create a quest, write it, read it back, verify fields."""
        qf = create_quest(
            "WriteTest",
            [
                {"name": "Player1", "entries": [
                    {"id": "ABJ1", "desc": "Palace", "cells": [77]}
                ]},
                {"name": "Monsters", "entries": [
                    {"id": "BBH1", "desc": "Goblin Camp", "cells": [65, 69]},
                    {"id": "BBw1", "desc": "Ice Cave", "cells": [85]},
                ]},
            ],
            map_size=(128, 128),
        )
        with tempfile.NamedTemporaryFile(suffix=".q", delete=False) as f:
            out = Path(f.name)
        try:
            write_quest_file(qf, out)
            qf2 = read_quest_file(out)
            assert qf2.quest_name == "WriteTest"
            assert qf2.map_params == (128, 128)
            assert len(qf2.unit_patterns_2) == 2
            # First pattern has 1 entry (Palace)
            assert len(qf2.unit_patterns_2[0].entries) == 1
            assert qf2.unit_patterns_2[0].entries[0].object_id == "ABJ1"
            # Second pattern has 2 entries (lairs)
            assert len(qf2.unit_patterns_2[1].entries) == 2
            assert qf2.unit_patterns_2[1].entries[0].object_id == "BBH1"
            assert qf2.unit_patterns_2[1].entries[0].candidate_cells == [65, 69]
        finally:
            out.unlink()

    def test_roundtrip_byte_perfect(self):
        """Write → read → write produces identical bytes."""
        qf = create_quest(
            "RoundTrip",
            [{"name": "P1", "entries": [{"id": "ABJ1", "desc": "Palace", "cells": [77]}]}],
        )
        with tempfile.NamedTemporaryFile(suffix=".q", delete=False) as f:
            out1 = Path(f.name)
        with tempfile.NamedTemporaryFile(suffix=".q", delete=False) as f:
            out2 = Path(f.name)
        try:
            write_quest_file(qf, out1)
            qf2 = read_quest_file(out1)
            write_quest_file(qf2, out2)
            assert out1.read_bytes() == out2.read_bytes()
        finally:
            out1.unlink()
            out2.unlink()

    def test_map_sizes(self):
        """All valid map sizes produce valid files."""
        for size in [(128, 128), (256, 256), (512, 512)]:
            qf = create_quest(
                "SizeTest",
                [{"name": "P1", "entries": [{"id": "ABJ1", "desc": "Palace", "cells": [77]}]}],
                map_size=size,
            )
            with tempfile.NamedTemporaryFile(suffix=".q", delete=False) as f:
                out = Path(f.name)
            try:
                write_quest_file(qf, out)
                qf2 = read_quest_file(out)
                assert qf2.map_params == size
            finally:
                out.unlink()


# =============================================================================
# Per-lair spawner overrides (Priority 2)
# =============================================================================

class TestLairOverrides:
    def test_single_override(self):
        """Single lair_override dict creates one spawner block."""
        qf = create_quest("LairTest", [
            {"name": "Monsters", "entries": [
                {"id": "BBH1", "desc": "Goblin Camp", "cells": [65],
                 "lair_override": {
                     "monsters": [("BVL1", 60), ("BVL2", 40)],
                     "max_hp": 200,
                     "spawn_rate_ms": 15000,
                     "dispersion": 500,
                     "hit_rate_sub": 50,
                 }},
            ]},
        ])
        pat = qf.unit_patterns_2[0]
        assert len(pat.spawners) == 1
        assert pat._spawner_keys == [0]
        sp = pat.spawners[0]
        assert sp.max_hp == 200
        assert sp.spawn_rate_ms == 15000
        assert sp.dispersion == 500
        assert sp.hit_rate_sub == 50
        assert sp.team.spawner_items[0].name == "BVL1"
        assert sp.team.spawner_items[0].spawn_level == 60
        assert sp.team.spawner_items[1].name == "BVL2"
        assert sp.team.spawner_items[1].spawn_level == 40
        # Padded to 4
        assert len(sp.team.spawner_items) == 4
        assert sp.team.spawner_items[2].name == "NONE"

    def test_multiple_difficulty_levels(self):
        """List of overrides creates multiple spawner blocks with sequential keys."""
        qf = create_quest("MultiDiff", [
            {"name": "Monsters", "entries": [
                {"id": "BBw1", "desc": "Ice Cave", "cells": [85],
                 "lair_override": [
                     {"monsters": [("BVx1", 80)], "spawn_rate_ms": 30000},
                     {"monsters": [("BVx1", 60), ("BVm1", 40)], "max_hp": 300},
                     {"monsters": [("BVm1", 100)], "spawn_rate_ms": 20000, "hit_rate_sub": 100},
                 ]},
            ]},
        ])
        pat = qf.unit_patterns_2[0]
        assert len(pat.spawners) == 3
        assert pat._spawner_keys == [0, 1, 2]  # entry 0, sub 0/1/2

    def test_key_scheme_multiple_entries(self):
        """Keys follow entry_index * 1000 + sub_index."""
        qf = create_quest("KeyTest", [
            {"name": "Monsters", "entries": [
                {"id": "BBH1", "desc": "Camp", "cells": [65],
                 "lair_override": {"monsters": [("BVL1", 50)]}},
                {"id": "BBw1", "desc": "Cave", "cells": [85],
                 "lair_override": [
                     {"monsters": [("BVx1", 80)]},
                     {"monsters": [("BVm1", 60)]},
                 ]},
                {"id": "BBz1", "desc": "Fort", "cells": [70],
                 "lair_override": {"monsters": [("BVL1", 50)]}},
            ]},
        ])
        pat = qf.unit_patterns_2[0]
        assert pat._spawner_keys == [0, 1000, 1001, 2000]

    def test_death_monsters(self):
        """extra_names (death_monsters) are serialized correctly."""
        qf = create_quest("DeathTest", [
            {"name": "Monsters", "entries": [
                {"id": "BBH1", "desc": "Camp", "cells": [65],
                 "lair_override": {
                     "monsters": [("BVL1", 50)],
                     "death_monsters": ["BVL1", "BVL2", "BVL3"],
                 }},
            ]},
        ])
        pat = qf.unit_patterns_2[0]
        sp = pat.spawners[0]
        assert sp.extra_names == ["BVL1", "BVL2", "BVL3"]

    def test_lair_override_roundtrip(self):
        """Lair overrides survive write → read → write."""
        qf = create_quest("LairRT", [
            {"name": "Monsters", "entries": [
                {"id": "BBH1", "desc": "Camp", "cells": [65],
                 "lair_override": {
                     "monsters": [("BVL1", 60), ("BVL2", 40)],
                     "max_hp": 200,
                     "spawn_rate_ms": 15000,
                 }},
            ]},
        ])
        with tempfile.NamedTemporaryFile(suffix=".q", delete=False) as f:
            out1 = Path(f.name)
        with tempfile.NamedTemporaryFile(suffix=".q", delete=False) as f:
            out2 = Path(f.name)
        try:
            write_quest_file(qf, out1)
            qf2 = read_quest_file(out1)
            write_quest_file(qf2, out2)
            assert out1.read_bytes() == out2.read_bytes()
            # Verify values preserved
            pat = qf2.unit_patterns_2[0]
            assert len(pat.spawners) == 1
            assert pat.spawners[0].max_hp == 200
            assert pat.spawners[0].spawn_rate_ms == 15000
        finally:
            out1.unlink()
            out2.unlink()


# =============================================================================
# Terrain presets (Priority 4)
# =============================================================================

class TestTerrainPresets:
    def test_all_presets_exist(self):
        """All documented presets are defined."""
        expected = {"grass", "snow", "grass_snow", "forest", "swamp", "desert",
                    "scorched", "mountain", "snow_mountain", "dark_forest",
                    "barren", "fertile", "winter", "bog"}
        assert expected.issubset(set(TERRAIN_PRESETS.keys()))

    def test_all_presets_reference_valid_zones(self):
        """Every preset only references zones that exist in LANDSCAPE_ZONES."""
        for preset_name, zones in TERRAIN_PRESETS.items():
            for zone_key in zones:
                assert zone_key in LANDSCAPE_ZONES, \
                    f"Preset '{preset_name}' references unknown zone '{zone_key}'"

    def test_all_presets_produce_valid_files(self):
        """Every preset creates a file that roundtrips correctly."""
        for preset_name in TERRAIN_PRESETS:
            qf = create_quest(
                f"T_{preset_name}",
                [{"name": "P1", "entries": [{"id": "ABJ1", "desc": "Palace", "cells": [77]}]}],
                terrain=preset_name,
            )
            with tempfile.NamedTemporaryFile(suffix=".q", delete=False) as f:
                out1 = Path(f.name)
            with tempfile.NamedTemporaryFile(suffix=".q", delete=False) as f:
                out2 = Path(f.name)
            try:
                write_quest_file(qf, out1)
                qf2 = read_quest_file(out1)
                write_quest_file(qf2, out2)
                assert out1.read_bytes() == out2.read_bytes(), \
                    f"Terrain preset '{preset_name}' failed roundtrip"
            finally:
                out1.unlink()
                out2.unlink()

    def test_custom_dict_terrain(self):
        """Custom dict terrain blend works."""
        qf = create_quest(
            "CustomBlend",
            [{"name": "P1", "entries": [{"id": "ABJ1", "desc": "Palace", "cells": [77]}]}],
            terrain={"snow_ice": 60, "mountain": 40},
        )
        assert len(qf.force_entries) == 2
        assert len(qf.region_entries) == 1
        team = getattr(qf.region_entries[0], '_team', None)
        assert team is not None
        assert len(team.spawner_items) == 2

    def test_custom_list_terrain(self):
        """Fully custom list terrain works."""
        qf = create_quest(
            "CustomList",
            [{"name": "P1", "entries": [{"id": "ABJ1", "desc": "Palace", "cells": [77]}]}],
            terrain=[
                {"tag": "MyGr", "name": "My Grass", "fractal": "xBBC",
                 "texture": "#Pla", "height": "Roll", "weight": 55},
                {"tag": "MySn", "name": "My Snow", "fractal": "xCla",
                 "texture": "xSno", "height": "FS01", "weight": 45, "field_0c": 13},
            ],
        )
        team = getattr(qf.region_entries[0], '_team', None)
        assert team.spawner_items[0].name == "MyGr"
        assert team.spawner_items[0].spawn_level == 55
        assert team.spawner_items[1].name == "MySn"
        assert team.spawner_items[1].field_0c == 13

    def test_invalid_zone_raises(self):
        """Unknown zone key in custom dict raises ValueError."""
        with pytest.raises(ValueError, match="Unknown landscape zone"):
            create_quest(
                "Bad",
                [{"name": "P1", "entries": [{"id": "ABJ1", "desc": "Palace", "cells": [77]}]}],
                terrain={"nonexistent_zone": 50},
            )


# =============================================================================
# Integration tests — real quest files
# =============================================================================

class TestRealQuestFiles:
    """Tests that use the actual game quest files (requires Quests/ directory)."""

    @pytest.fixture
    def quest_files(self):
        files = sorted(QUEST_DIR.glob("*.q"))
        if not files:
            pytest.skip("No quest files found in Quests/")
        return files

    @pytest.fixture
    def all_quest_files(self):
        files = sorted(QUEST_DIR.glob("*.q")) + sorted(QUESTMX_DIR.glob("*.q"))
        if not files:
            pytest.skip("No quest files found")
        return files

    def test_myquest_roundtrip(self):
        """MyQuest/Quest.q roundtrips byte-perfectly."""
        if not MYQUEST_Q.exists():
            pytest.skip("MyQuest/Quest.q not found")
        qf = read_quest_file(MYQUEST_Q)
        with tempfile.NamedTemporaryFile(suffix=".q", delete=False) as f:
            out = Path(f.name)
        try:
            write_quest_file(qf, out)
            assert MYQUEST_Q.read_bytes() == out.read_bytes()
        finally:
            out.unlink()

    def test_all_files_parse(self, all_quest_files):
        """All 37+ quest files parse without errors."""
        failures = []
        for qpath in all_quest_files:
            try:
                read_quest_file(qpath)
            except Exception as e:
                failures.append(f"{qpath.name}: {type(e).__name__}: {e}")
        assert not failures, f"Parse failures:\n" + "\n".join(failures)

    def test_parse_preserves_spawner_data(self, quest_files):
        """Parsed spawner blocks have valid field ranges."""
        for qpath in quest_files[:10]:  # Check first 10
            qf = read_quest_file(qpath)
            for block in qf.spawner_blocks:
                assert 0 <= block.field_00 <= 99999, f"{qpath.name}: max_hp out of range"
                assert 0 <= block.field_04 <= 999999, f"{qpath.name}: spawn_rate out of range"
                assert 0 <= block.field_08 <= 99999, f"{qpath.name}: dispersion out of range"


# =============================================================================
# Entry point for running without pytest
# =============================================================================

if __name__ == "__main__":
    # Simple runner when pytest isn't available
    import traceback

    test_classes = [
        TestBinaryReader, TestBinaryWriter, TestSpawnerBlock,
        TestCreateQuest, TestLairOverrides, TestTerrainPresets,
    ]

    passed = 0
    failed = 0
    errors = []

    for cls in test_classes:
        instance = cls()
        methods = [m for m in dir(instance) if m.startswith("test_")]
        for method_name in methods:
            try:
                getattr(instance, method_name)()
                passed += 1
                print(f"  PASS: {cls.__name__}.{method_name}")
            except Exception as e:
                failed += 1
                errors.append(f"  FAIL: {cls.__name__}.{method_name}: {e}")
                print(f"  FAIL: {cls.__name__}.{method_name}: {e}")

    # Run integration tests manually (no fixtures)
    print("\n--- Integration tests ---")
    if MYQUEST_Q.exists():
        try:
            qf = read_quest_file(MYQUEST_Q)
            with tempfile.NamedTemporaryFile(suffix=".q", delete=False) as f:
                out = Path(f.name)
            write_quest_file(qf, out)
            if MYQUEST_Q.read_bytes() == out.read_bytes():
                print("  PASS: MyQuest roundtrip")
                passed += 1
            else:
                print("  FAIL: MyQuest roundtrip — bytes differ")
                failed += 1
            out.unlink()
        except Exception as e:
            print(f"  FAIL: MyQuest roundtrip — {e}")
            failed += 1

    # Parse all quest files
    all_q = sorted(QUEST_DIR.glob("*.q")) + sorted(QUESTMX_DIR.glob("*.q"))
    parse_fails = []
    for qpath in all_q:
        try:
            read_quest_file(qpath)
        except Exception as e:
            parse_fails.append(f"{qpath.name}: {e}")
    if parse_fails:
        print(f"  FAIL: {len(parse_fails)}/{len(all_q)} files failed to parse")
        for f in parse_fails[:5]:
            print(f"    {f}")
        failed += 1
    else:
        print(f"  PASS: All {len(all_q)} quest files parse")
        passed += 1

    print(f"\n{'='*40}")
    print(f"Results: {passed} passed, {failed} failed")
    if errors:
        print("\nFailures:")
        for e in errors:
            print(e)
    sys.exit(0 if failed == 0 else 1)
