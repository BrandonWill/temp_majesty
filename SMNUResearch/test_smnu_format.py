"""
test_smnu_format.py - Unit tests for smnu_format.py

Run with:
    python -m pytest SMNUResearch/test_smnu_format.py -v
or:
    python SMNUResearch/test_smnu_format.py
"""
import sys
from pathlib import Path

workspace_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(workspace_root))
sys.path.insert(0, str(workspace_root / "SMNUResearch"))

import pytest
from smnu_format import (
    Panel, Widget, NestedPanelBlock, Property,
    parse_panel, write_panel, roundtrip_test, FormatError,
    PANEL_MARKER, END,
)
from smnu_analysis import load_panels


@pytest.fixture(scope="module")
def all_panels():
    return load_panels()


def test_roundtrip_every_real_panel(all_panels):
    """Every SMNU panel in the base game and expansion must round-trip
    byte-perfect through parse_panel() -> write_panel()."""
    failures = []
    checked = 0
    for name, p in all_panels.items():
        blob = p["smnu"]
        if not blob:
            continue
        checked += 1
        ok, msg = roundtrip_test(blob)
        if not ok:
            failures.append(f"{name}: {msg}")
    assert checked > 100, "sanity check: expected >100 real panels to test against"
    assert not failures, "roundtrip failures:\n" + "\n".join(failures)


def test_mx03_matches_known_decode(all_panels):
    """Cross-check parsed MX03 structure against the hand-verified byte
    layout in findings/MX03_full_decode.md."""
    panel = parse_panel(all_panels["MX:MX03"]["smnu"])

    # Header geometry: x=0, y=182, w=202, h=245 (tag 2)
    geom_props = [p for p in panel.header_properties if p.tag == 2]
    assert geom_props == [Property(2, [0, 182, 202, 245])]

    # Background TILE index 1001 (tag 13)
    tile_props = [p for p in panel.header_properties if p.tag == 13]
    assert tile_props == [Property(13, [1001])]

    # "Return to Main" button: widget at (3, 223, 25, 20)
    matches = [
        w for w in panel.widgets
        if isinstance(w, Widget) and w.geometry == (3, 223, 25, 20)
    ]
    assert len(matches) == 1
    return_btn = matches[0]
    action_tag6 = [p for p in return_btn.properties if p.tag == 6]
    assert action_tag6, "Return button should have an action-type tag (6)"


def test_parse_rejects_bad_marker():
    """A blob not starting with the panel marker (1000) must raise."""
    import struct
    bad = struct.pack("<III", 999, END, END)
    with pytest.raises(FormatError):
        parse_panel(bad)


def test_parse_rejects_unknown_widget_type():
    """An unknown widget type code must raise loudly rather than silently
    mis-parsing the rest of the stream."""
    import struct
    # header: marker, then immediate END (empty header)
    # then a bogus widget type 999, then END, END
    blob = struct.pack("<I", PANEL_MARKER) + struct.pack("<I", END)
    blob += struct.pack("<I", 999) + struct.pack("<I", END) + struct.pack("<I", END)
    with pytest.raises(FormatError):
        parse_panel(blob)


def test_write_panel_minimal_roundtrip():
    """A minimal hand-built panel (header only, no widgets) round-trips."""
    panel = Panel(
        header_properties=[
            Property(2, [0, 0, 100, 100]),
            Property(13, [1001]),
        ],
        widgets=[],
    )
    blob = write_panel(panel)
    reparsed = parse_panel(blob)
    assert reparsed.header_properties == panel.header_properties
    assert reparsed.widgets == []


def test_write_panel_with_positional_and_generic_widgets():
    """A hand-built panel mixing a positional-geometry widget (type 0) and
    a generic widget (type 3, geometry via tag 2) round-trips."""
    panel = Panel(
        header_properties=[Property(2, [0, 0, 50, 50])],
        widgets=[
            Widget(type=0, sub_id=2, geometry=(1, 2, 3, 4), properties=[
                Property(6, [1]),
            ]),
            Widget(type=3, sub_id=5, geometry=None, properties=[
                Property(2, [10, 20, 30, 40]),
                Property(7, [1]),
            ]),
        ],
    )
    blob = write_panel(panel)
    reparsed = parse_panel(blob)
    assert len(reparsed.widgets) == 2
    assert reparsed.widgets[0].geometry == (1, 2, 3, 4)
    assert reparsed.widgets[1].geometry is None
    assert reparsed.widgets[1].properties[0] == Property(2, [10, 20, 30, 40])


def test_array_tag_roundtrip():
    """Color array tags (e.g. tag 36) with a count prefix round-trip."""
    panel = Panel(
        header_properties=[],
        widgets=[
            Widget(type=3, sub_id=0, geometry=None, properties=[
                Property(36, [3, 0x80000000, 0x803F3F3F, 0x8000FF00]),
            ]),
        ],
    )
    blob = write_panel(panel)
    reparsed = parse_panel(blob)
    assert reparsed.widgets[0].properties[0].values == [3, 0x80000000, 0x803F3F3F, 0x8000FF00]


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
