"""
smnu_compiler.py - Panel definition compiler (SMNU + STRT backend)
=====================================================================
Compiles a structured panel definition into a matched pair of SMNU + STRT
binary blobs, ready to pack into a quest CAM.

This is the *backend* of the eventual XML-based panel authoring tool (see
SMNUResearch/FUTURE_TODO.md Priority 4). It deliberately does NOT parse XML
yet. The priority is proving the compile step reproduces known-good real
panels byte-for-byte before building a friendly authoring syntax on top of
it -- see `smnu_format.py`'s docstring for the reasoning.

Building blocks:
    - smnu_format.py  -> Panel/Widget/Property dataclasses + SMNU bytes
    - str_tool.py     -> STRT bytes (byte-perfect on all 175 real entries,
                         see tests/test_str_tool.py)

This module is the glue that pairs the two: it enforces that every STRT
string-index reference in the panel (tag 7 = text, tag 33 = tooltip)
actually resolves within the accompanying string table. That check is not
cosmetic -- an unresolved string index is exactly what crashed the original
hand-built panel attempt (a raw index value got dereferenced as a char*,
see SMNUResearch/TASK_smnu_parser_decompile.md).

Validation: compile_panel() reproduces MX03's real SMNU+STRT bytes
byte-for-byte when fed MX03's own parsed structure, and the same holds for
every other real panel in the game (see test_smnu_compiler.py).

Usage:
    python SMNUResearch/smnu_compiler.py verify-all
    python SMNUResearch/smnu_compiler.py verify MX03
"""
import copy
import sys
from dataclasses import dataclass
from pathlib import Path

workspace_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(workspace_root))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from smnu_format import Panel, Widget, NestedPanelBlock, Property, write_panel, parse_panel
from str_tool import write_strt, read_strt
from cam_writer import build_cam_from_sections

# String-reference tags: tag 7 = display text, tag 33 = tooltip text.
# Both take a single value that indexes into the panel's paired STRT table.
STRING_REF_TAGS = (7, 33)


class CompileError(ValueError):
    """Raised when a panel definition can't be compiled to valid SMNU/STRT."""


@dataclass
class PanelSource:
    """A panel definition ready to compile: a structured widget tree plus
    the string table it references by index. `strings[i]` is what tag 7/33
    property value `i` resolves to at runtime."""
    panel: Panel
    strings: list  # list[bytes]


def compile_panel(source: PanelSource) -> tuple:
    """Compile a PanelSource into (smnu_bytes, strt_bytes).

    Raises CompileError if any tag-7/tag-33 string reference is out of
    range for `source.strings` -- catching the null-STRT-handle crash class
    at compile time instead of at game load time.
    """
    _validate_string_refs(source.panel, source.strings)
    smnu_bytes = write_panel(source.panel)
    strt_bytes = write_strt(source.strings)
    return smnu_bytes, strt_bytes


def _validate_string_refs(panel: Panel, strings: list):
    max_index = len(strings) - 1
    errors = []

    def check_props(props, where):
        for p in props:
            if p.tag in STRING_REF_TAGS and p.values:
                idx = p.values[0]
                if idx < 0 or idx > max_index:
                    errors.append(
                        f"{where}: tag {p.tag} references STRT index {idx}, "
                        f"but only {len(strings)} string(s) exist "
                        f"(valid range 0..{max_index})"
                    )

    check_props(panel.header_properties, "header")
    for i, w in enumerate(panel.widgets):
        if isinstance(w, NestedPanelBlock):
            check_props(w.properties, f"widget[{i}] (nested panel)")
        else:
            check_props(w.properties, f"widget[{i}] (type={w.type})")

    if errors:
        raise CompileError("Invalid STRT string reference(s):\n" + "\n".join(errors))


def load_panel_source_from_cam(smnu_blob: bytes, strt_blob) -> PanelSource:
    """Build a PanelSource from real extracted SMNU + STRT bytes. Useful as
    a starting point for cloning/modifying an existing panel rather than
    authoring one from scratch. `strt_blob` may be None/empty for panels
    that reference no strings."""
    panel = parse_panel(smnu_blob)
    strings = read_strt(strt_blob) if strt_blob else []
    return PanelSource(panel, strings)


def clone_widget(widget: Widget) -> Widget:
    """Deep-copy a widget so it can be repositioned/repurposed without
    mutating the source panel. Matches the "clone the nav button" pattern
    documented in findings/nav_button_pattern.md."""
    return copy.deepcopy(widget)


def add_string(strings: list, text: bytes) -> int:
    """Append a string to a mutable string table and return its new index,
    for use in a tag 7 / tag 33 property value."""
    strings.append(text)
    return len(strings) - 1


def build_textdata_cam(named_panels: dict) -> bytes:
    """Compile multiple named panels into a single quest textdata CAM
    (SMNU + STRT sections), ready to load via a quest's `<CAM>` tag.

    named_panels: dict of {entry_name: PanelSource}. `entry_name` is the
    4-char-or-fewer ASCII name the engine looks up by (e.g. "MX03" to
    override the Magic Bazaar research panel, or a new name like "PT01"
    for a brand-new panel). Every panel's SMNU and STRT share this same
    entry name -- see smnu_parser_decompilation.md "STRT Connection" for
    why that pairing matters (a name mismatch is what causes the
    null-STRT-handle crash).

    Raises CompileError if any panel fails validation (out-of-range STRT
    string reference). Fails the whole build rather than silently emitting
    a CAM that will crash the game on one bad panel.
    """
    smnu_entries = []
    strt_entries = []
    errors = []
    for name, source in named_panels.items():
        try:
            smnu_bytes, strt_bytes = compile_panel(source)
        except CompileError as e:
            errors.append(f"{name}: {e}")
            continue
        smnu_entries.append((name, smnu_bytes))
        strt_entries.append((name, strt_bytes))

    if errors:
        raise CompileError(
            "Failed to compile one or more panels:\n" + "\n".join(errors)
        )

    return build_cam_from_sections([
        ("SMNU", smnu_entries),
        ("STRT", strt_entries),
    ])


def _verify_panel_dict_entry(p: dict) -> tuple:
    """Core verification logic shared by single-panel and bulk verify.
    `p` is one entry from smnu_analysis.load_panels() (has 'smnu'/'strt')."""
    try:
        source = load_panel_source_from_cam(p["smnu"], p["strt"])
        smnu_out, strt_out = compile_panel(source)
    except (CompileError, ValueError) as e:
        return False, f"compile error: {e}"

    if smnu_out != p["smnu"]:
        n = min(len(smnu_out), len(p["smnu"]))
        diff_at = next((i for i in range(n) if smnu_out[i] != p["smnu"][i]), n)
        return False, f"SMNU mismatch at offset {diff_at}"

    if p["strt"] is not None and strt_out != p["strt"]:
        n = min(len(strt_out), len(p["strt"]))
        diff_at = next((i for i in range(n) if strt_out[i] != p["strt"][i]), n)
        return False, f"STRT mismatch at offset {diff_at}"

    return True, f"OK (SMNU {len(smnu_out)}B, STRT {len(strt_out)}B)"


def verify_against_real_panel(name: str) -> tuple:
    """Load a real panel's SMNU+STRT, run it through compile_panel(), and
    check the output is byte-identical to the original. Returns (ok, msg)."""
    from smnu_analysis import load_panels

    all_panels = load_panels()
    key = name if name in all_panels else f"MX:{name}"
    if key not in all_panels:
        return False, f"panel '{name}' not found"
    return _verify_panel_dict_entry(all_panels[key])


def verify_all_real_panels():
    from smnu_analysis import load_panels

    panels = load_panels()
    passed = 0
    failed = []
    for name in sorted(panels.keys(), key=lambda n: panels[n]["index"]):
        if not panels[name]["smnu"]:
            continue
        ok, msg = _verify_panel_dict_entry(panels[name])
        if ok:
            passed += 1
        else:
            failed.append((name, msg))
            print(f"FAIL {name}: {msg}")

    total = passed + len(failed)
    print(f"\n{passed}/{total} panels compiled byte-perfect via smnu_compiler")
    if failed:
        print(f"\n{len(failed)} failures:")
        for name, msg in failed:
            print(f"  {name}: {msg}")
    return passed, failed


def main():
    import argparse

    parser = argparse.ArgumentParser(description="SMNU/STRT panel compiler")
    parser.add_argument("command", choices=["verify-all", "verify"])
    parser.add_argument("panels", nargs="*", help="Panel name(s) for verify")
    args = parser.parse_args()

    if args.command == "verify-all":
        verify_all_real_panels()
        return

    for name in args.panels:
        ok, msg = verify_against_real_panel(name)
        print(f"{name}: {'OK' if ok else 'FAIL'} - {msg}")


if __name__ == "__main__":
    main()
