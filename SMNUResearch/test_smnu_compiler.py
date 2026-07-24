"""
test_smnu_compiler.py - Unit tests for smnu_compiler.py

Run with:
    python -m pytest SMNUResearch/test_smnu_compiler.py -v
"""
import sys
from pathlib import Path

workspace_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(workspace_root))
sys.path.insert(0, str(workspace_root / "SMNUResearch"))

import pytest
from smnu_format import Panel, Widget, Property, parse_panel
from smnu_compiler import (
    PanelSource, compile_panel, CompileError,
    load_panel_source_from_cam, clone_widget, add_string,
    build_textdata_cam, verify_against_real_panel,
)
from str_tool import read_strt
from cam_reader import read_cam


@pytest.fixture(scope="module")
def all_panels():
    from smnu_analysis import load_panels
    return load_panels()


def test_verify_all_real_panels_except_known_gdb4_quirk(all_panels):
    """Every real panel except GDB4 (documented data quirk, see
    SMNUResearch/FUTURE_TODO.md 'Known Data Quirk: GDB4') must compile
    byte-perfect from its own parsed structure."""
    failures = []
    checked = 0
    for name in all_panels:
        if not all_panels[name]["smnu"]:
            continue
        if name == "GDB4":
            continue  # documented exception, see FUTURE_TODO.md
        checked += 1
        ok, msg = verify_against_real_panel(name.replace("MX:", ""))
        if not ok:
            failures.append(f"{name}: {msg}")
    assert checked > 150
    assert not failures, "compile failures:\n" + "\n".join(failures)


def test_gdb4_fails_with_clear_error(all_panels):
    """GDB4 is EXPECTED to fail compilation -- its own shipped STRT is
    missing entries for 2 of its own widgets' string refs. The compiler
    must catch this loudly, not silently produce a would-crash panel."""
    ok, msg = verify_against_real_panel("GDB4")
    assert not ok
    assert "STRT index 28" in msg or "STRT index 29" in msg


def test_compile_panel_rejects_out_of_range_string_ref():
    """A hand-built panel referencing a nonexistent string index must be
    rejected at compile time, not deferred to a runtime crash."""
    panel = Panel(
        header_properties=[],
        widgets=[
            Widget(type=0, sub_id=2, geometry=(0, 0, 10, 10), properties=[
                Property(7, [5]),  # index 5, but we only have 1 string
            ]),
        ],
    )
    source = PanelSource(panel, strings=[b"only one string"])
    with pytest.raises(CompileError, match="STRT index 5"):
        compile_panel(source)


def test_compile_panel_accepts_valid_string_ref():
    """A panel whose string refs are all in range compiles successfully."""
    panel = Panel(
        header_properties=[],
        widgets=[
            Widget(type=0, sub_id=2, geometry=(0, 0, 10, 10), properties=[
                Property(7, [0]),
                Property(33, [1]),
            ]),
        ],
    )
    source = PanelSource(panel, strings=[b"Label", b"Tooltip"])
    smnu_bytes, strt_bytes = compile_panel(source)
    assert read_strt(strt_bytes) == [b"Label", b"Tooltip"]
    reparsed = parse_panel(smnu_bytes)
    assert reparsed.widgets[0].properties[0] == Property(7, [0])


def test_load_panel_source_from_cam_and_recompile(all_panels):
    """Loading a real panel via load_panel_source_from_cam() and
    recompiling reproduces the original bytes (spot check on MX03)."""
    p = all_panels["MX:MX03"]
    source = load_panel_source_from_cam(p["smnu"], p["strt"])
    smnu_out, strt_out = compile_panel(source)
    assert smnu_out == p["smnu"]
    assert strt_out == p["strt"]


def test_clone_widget_is_independent_copy():
    """clone_widget() must deep-copy so mutating the clone doesn't affect
    the original (the documented 'clone the nav button' workflow)."""
    original = Widget(type=0, sub_id=2, geometry=(3, 223, 25, 20), properties=[
        Property(6, [8013]),
    ])
    clone = clone_widget(original)
    clone.geometry = (170, 223, 25, 20)
    clone.properties[0].values[0] = 9999

    assert original.geometry == (3, 223, 25, 20)
    assert original.properties[0].values == [8013]
    assert clone.geometry == (170, 223, 25, 20)
    assert clone.properties[0].values == [9999]


def test_add_string_returns_correct_index():
    strings = [b"first", b"second"]
    idx = add_string(strings, b"third")
    assert idx == 2
    assert strings == [b"first", b"second", b"third"]


def test_build_textdata_cam_roundtrips_through_cam_reader():
    """A CAM built by build_textdata_cam() must be readable by cam_reader
    and contain byte-identical SMNU/STRT entries under the right names."""
    panel = Panel(
        header_properties=[Property(2, [0, 0, 100, 100])],
        widgets=[
            Widget(type=0, sub_id=2, geometry=(0, 0, 100, 100), properties=[
                Property(7, [0]),
            ]),
        ],
    )
    source = PanelSource(panel, strings=[b"Hello Quest"])
    expected_smnu, expected_strt = compile_panel(source)

    cam_bytes = build_textdata_cam({"PT01": source})
    sections = read_cam(cam_bytes)

    assert len(sections) == 2
    smnu_sec, strt_sec = sections
    assert smnu_sec.extension == "SMNU"
    assert strt_sec.extension == "STRT"
    assert len(smnu_sec.files) == 1
    assert smnu_sec.files[0].display_name == "PT01"

    smnu_data = cam_bytes[
        smnu_sec.files[0].data_off: smnu_sec.files[0].data_off + smnu_sec.files[0].data_size
    ]
    strt_data = cam_bytes[
        strt_sec.files[0].data_off: strt_sec.files[0].data_off + strt_sec.files[0].data_size
    ]
    assert smnu_data == expected_smnu
    assert strt_data == expected_strt
    assert read_strt(strt_data) == [b"Hello Quest"]


def test_build_textdata_cam_multiple_panels_share_entry_names():
    """Multiple named panels pack into one CAM, each SMNU paired with an
    STRT of the SAME entry name (the pairing mechanism the engine relies
    on -- see smnu_parser_decompilation.md 'STRT Connection')."""
    def make_source(text):
        panel = Panel(header_properties=[], widgets=[
            Widget(type=0, sub_id=2, geometry=(0, 0, 10, 10), properties=[
                Property(7, [0]),
            ]),
        ])
        return PanelSource(panel, strings=[text])

    named_panels = {
        "MX03": make_source(b"Router"),
        "PT01": make_source(b"Potions"),
        "PT02": make_source(b"Equipment"),
    }
    cam_bytes = build_textdata_cam(named_panels)
    sections = read_cam(cam_bytes)
    smnu_names = {f.display_name for f in sections[0].files}
    strt_names = {f.display_name for f in sections[1].files}
    assert smnu_names == {"MX03", "PT01", "PT02"}
    assert strt_names == {"MX03", "PT01", "PT02"}


def test_build_textdata_cam_fails_loudly_on_bad_panel():
    """If ANY panel in the batch has an invalid string ref, the whole CAM
    build must fail rather than silently shipping a would-crash panel."""
    good_panel = Panel(header_properties=[], widgets=[])
    bad_panel = Panel(header_properties=[], widgets=[
        Widget(type=0, sub_id=2, geometry=(0, 0, 10, 10), properties=[
            Property(7, [99]),  # way out of range
        ]),
    ])
    named_panels = {
        "GOOD": PanelSource(good_panel, strings=[]),
        "BAD": PanelSource(bad_panel, strings=[b"only one"]),
    }
    with pytest.raises(CompileError, match="BAD"):
        build_textdata_cam(named_panels)


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
