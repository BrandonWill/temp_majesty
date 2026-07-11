"""
Test the quest_map_generator parser against ALL quest files.

Validates that every .q file in Quests/, QuestsMX/, and MyQuest/ can be parsed
without errors, and reports summary statistics.

Run from workspace root:
    python QuestMapGenerator/test_all_quests.py
"""
import sys
import os
from pathlib import Path

# Ensure we can import from this folder and chdir to workspace root
sys.path.insert(0, str(Path(__file__).parent))
os.chdir(Path(__file__).parent.parent)

from quest_map_generator import (
    parse_q_file, QFormatError,
    grid_to_byte, byte_to_grid, letter_to_byte, byte_to_letter,
    auto_distribute, validate_placements,
    CENTER, UnitInstance
)


def main():
    print("=" * 70)
    print("QUEST MAP GENERATOR — FULL VALIDATION TEST")
    print("=" * 70)

    # --- Grid encoding tests ---
    print("\n[1] Grid Position Encoding/Decoding")
    print("-" * 40)

    # grid_to_byte
    assert grid_to_byte(0, 0) == 65  # A
    assert grid_to_byte(2, 2) == 77  # M (center)
    assert grid_to_byte(4, 4) == 89  # Y
    assert grid_to_byte(1, 0) == 66  # B
    assert grid_to_byte(4, 0) == 69  # E
    assert grid_to_byte(0, 4) == 85  # U
    print("  grid_to_byte: PASS")

    # byte_to_grid
    assert byte_to_grid(65) == (0, 0)
    assert byte_to_grid(77) == (2, 2)
    assert byte_to_grid(89) == (4, 4)
    assert byte_to_grid(66) == (1, 0)
    assert byte_to_grid(69) == (4, 0)
    assert byte_to_grid(85) == (0, 4)
    print("  byte_to_grid: PASS")


    # Round-trip all 25 positions
    for byte_val in range(65, 90):
        col, row = byte_to_grid(byte_val)
        assert grid_to_byte(col, row) == byte_val
    print("  Round-trip all 25 positions: PASS")

    # letter_to_byte / byte_to_letter
    for ch in "ABCDEFGHIJKLMNOPQRSTUVWXY":
        assert byte_to_letter(letter_to_byte(ch)) == ch
    print("  letter/byte conversion: PASS")

    # auto_distribute
    positions = auto_distribute(5)
    assert len(positions) == 5
    assert CENTER not in positions
    assert len(set(positions)) == 5
    positions_max = auto_distribute(24)
    assert len(positions_max) == 24
    assert CENTER not in positions_max
    print(f"  auto_distribute(5): {[chr(p) for p in positions]} PASS")
    print(f"  auto_distribute(24): all 24 non-center cells PASS")

    # validate_placements
    entries_ok = [
        UnitInstance("ABJ1", "Palace", [77]),
        UnitInstance("BBw1", "Ice Cave", [78]),
    ]
    validate_placements(entries_ok)
    try:
        entries_bad = [
            UnitInstance("ABJ1", "Palace", [77]),
            UnitInstance("BBw1", "Ice Cave", [77]),
        ]
        validate_placements(entries_bad)
        assert False, "Should have raised ValueError"
    except ValueError:
        pass
    print("  validate_placements: PASS")

    # Error handling
    try:
        grid_to_byte(5, 0)
        assert False
    except ValueError:
        pass
    try:
        byte_to_grid(64)
        assert False
    except ValueError:
        pass
    try:
        byte_to_grid(90)
        assert False
    except ValueError:
        pass
    print("  Error handling: PASS")


    # --- Parse ALL quest files ---
    print("\n[2] Parse ALL Quest Files")
    print("-" * 40)

    quest_dirs = [
        ("Quests", Path("Quests")),
        ("QuestsMX", Path("QuestsMX")),
        ("MyQuest", Path("MyQuest")),
    ]

    all_files = []
    for label, qdir in quest_dirs:
        if qdir.exists():
            files = sorted(qdir.glob("*.q"))
            all_files.extend([(label, f) for f in files])

    success = 0
    failed = 0
    total_patterns = 0
    total_entries = 0
    total_cells = 0
    failures = []

    print(f"\n{'File':<40} {'Magic':<6} {'Quest Name':<25} {'Patterns':<9} {'Entries':<8} {'Cells':<9}")
    print("-" * 97)

    for label, qf in all_files:
        rel_path = f"{label}/{qf.name}"
        try:
            qm = parse_q_file(qf)
            n_patterns = len(qm.unit_patterns)
            n_entries = sum(len(p.entries) for p in qm.unit_patterns)
            n_cells = sum(len(e.candidate_cells) for p in qm.unit_patterns for e in p.entries)
            total_patterns += n_patterns
            total_entries += n_entries
            total_cells += n_cells
            print(f"  {rel_path:<38} {qm.magic:<6} {qm.quest_name:<25} {n_patterns:<9} {n_entries:<8} {n_cells:<9}")
            success += 1
        except Exception as e:
            print(f"  {rel_path:<38} FAILED: {e}")
            failures.append((rel_path, str(e)))
            failed += 1

    # --- Summary ---
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"  Files tested:      {success + failed}")
    print(f"  Passed:            {success}")
    print(f"  Failed:            {failed}")
    print(f"  Total patterns:    {total_patterns}")
    print(f"  Total entries:     {total_entries}")
    print(f"  Total cells:       {total_cells}")
    print(f"  Success rate:      {success}/{success + failed} ({100*success/(success+failed):.1f}%)")

    if failures:
        print(f"\n  FAILURES:")
        for path, err in failures:
            print(f"    {path}: {err}")

    print("\n" + "=" * 70)
    if failed == 0:
        print("ALL TESTS PASSED")
    else:
        print(f"SOME TESTS FAILED ({failed} failures)")
    print("=" * 70)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
