"""
smnu_format.py - SMNU panel binary format parser/writer
=========================================================
Structured parser and byte-perfect writer for the SMNU panel format,
based on the confirmed engine decompilation in
`findings/smnu_parser_decompilation.md`.

Model
-----
An SMNU blob is a flat little-endian int32 stream:

    1000                        ; panel marker
    <header tag-value pairs>    ; see HEADER/WIDGET tag arity table
    -1                          ; end header
    <widget> <widget> ...       ; each: [type, sub_id, (geometry), tags..., -1]
    -1                          ; end of widget list (panel EOF)

Two widget "shapes" exist, based on which engine constructor a type uses
(confirmed via Ghidra decompilation, see TODO-Ghidra.md "Known EXE Addresses"):

- POSITIONAL_GEOMETRY_TYPES (dedicated constructors: 0, 1, 2, 5, 6, 9, 11, 12)
  Format: [type, sub_id, x, y, w, h, <tag-value pairs>, -1]
  Geometry is read as 4 raw values immediately after sub_id (confirmed for
  types 6/9 in FUTURE_TODO.md Priority 3.5; empirically consistent for
  0/1/2/5/11/12 against MX03_full_decode.md byte layouts).

- GENERIC_TYPES (shared constructor FUN_00675140 / FUN_00673ca0: 3, 4, 7, 8, 10)
  Format: [type, sub_id, <tag-value pairs>, -1]
  Geometry (if present) appears as an explicit tag 2 within the tag stream.

This is a hypothesis validated by round-tripping against every real panel in
Data/textdata.cam and DataMX/mx_textdata.cam (see roundtrip_all_panels()).
If a panel fails to round-trip, that's a signal the hypothesis needs revision
for that widget type -- treat failures as format bugs, not data quirks.

Usage:
    python SMNUResearch/smnu_format.py roundtrip-all
    python SMNUResearch/smnu_format.py roundtrip AP20
    python SMNUResearch/smnu_format.py dump AP20
"""
import struct
import sys
from dataclasses import dataclass, field
from pathlib import Path

workspace_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(workspace_root))

PANEL_MARKER = 1000
END = 0xFFFFFFFF  # stream terminator; stored/compared as unsigned u32.
# NOTE: the underlying stream is really an array of raw 32-bit words, not
# signed integers -- ARGB color values (e.g. 0x80000000) and packed 4-char
# resource IDs routinely exceed the signed int32 range. We read/write as
# unsigned u32 throughout and only the small set of known sentinel/tag
# values (END, PANEL_MARKER, tag numbers) are compared numerically.

# Widget types with a dedicated engine constructor. These read geometry as
# 4 raw (untagged) values immediately after sub_id.
POSITIONAL_GEOMETRY_TYPES = {0, 1, 2, 5, 6, 9, 11, 12}

# Widget types sharing the generic constructor. Geometry (if any) is an
# explicit tag 2 within the property stream, not positional.
GENERIC_TYPES = {3, 4, 7, 8, 10}

# Tags that consume exactly 1 value.
FIXED_1_TAGS = {
    1, 3, 4, 5, 6, 7, 10, 11, 12, 13, 14, 15, 17, 18, 19, 20, 21, 22,
    27, 28, 29, 30, 31, 32, 33, 38, 39, 40, 43, 44, 45, 48, 53,
}

# Tags that consume exactly 4 values.
FIXED_4_TAGS = {2, 42}

# Tags that are count-prefixed arrays: [tag] [count] [count x values].
ARRAY_TAGS = {34, 35, 36, 37, 49, 50, 51, 52}

# Tags whose arity depends on context: 3 values in a panel header block,
# 2 values inside a widget property block (per the opcode skip-function
# reference in smnu_parser_decompilation.md).
CONTEXT_DEPENDENT_TAGS = {46, 47}

# Indexed image-state tags: 0x100-0x10C, each 1 value.
INDEXED_IMAGE_TAGS = set(range(0x100, 0x10D))

# Sub-block tag: consumes values until (and including) a literal 24 marker.
SUBBLOCK_OPEN_TAG = 23
SUBBLOCK_CLOSE_VALUE = 24


class FormatError(ValueError):
    """Raised when the byte stream doesn't match the known SMNU format."""


class BinaryReader:
    __slots__ = ("data", "off")

    def __init__(self, data: bytes):
        self.data = data
        self.off = 0

    def read_u32(self) -> int:
        if self.off + 4 > len(self.data):
            raise FormatError(f"Unexpected EOF at offset {self.off}")
        val = struct.unpack_from("<I", self.data, self.off)[0]
        self.off += 4
        return val

    def remaining(self) -> int:
        return len(self.data) - self.off


class BinaryWriter:
    __slots__ = ("chunks",)

    def __init__(self):
        self.chunks = []

    def write_u32(self, val: int):
        # Accept python ints that may be negative (e.g. sentinel -1) by
        # masking to the unsigned 32-bit range -- the underlying stream has
        # no signedness of its own.
        self.chunks.append(struct.pack("<I", val & 0xFFFFFFFF))

    def write_u32s(self, vals):
        for v in vals:
            self.write_u32(v)

    def getvalue(self) -> bytes:
        return b"".join(self.chunks)


@dataclass
class Property:
    """A single tag-value entry. `values` excludes the tag itself."""
    tag: int
    values: list = field(default_factory=list)


@dataclass
class Widget:
    type: int
    sub_id: int
    geometry: tuple | None  # (x, y, w, h) if positional-geometry type, else None
    properties: list  # list[Property]


@dataclass
class NestedPanelBlock:
    """A `1000` marker found inside the widget list. Parsed like a header
    (tag-value pairs until -1), per FUN_006dd330 being 'skipped' by the
    child widget parser -- treated here as an opaque sibling entry."""
    properties: list  # list[Property]


@dataclass
class Panel:
    header_properties: list  # list[Property]
    widgets: list  # list[Widget | NestedPanelBlock]


def _tag_arity(tag: int, context: str):
    """Return how many values a tag consumes, or a sentinel string for
    variable-length tags ('array', 'subblock'). Raises FormatError if the
    tag is unknown -- this is intentional so parsing failures surface loudly
    instead of silently mis-consuming bytes."""
    if tag in CONTEXT_DEPENDENT_TAGS:
        return 3 if context == "header" else 2
    if tag in FIXED_4_TAGS:
        return 4
    if tag in FIXED_1_TAGS or tag in INDEXED_IMAGE_TAGS:
        return 1
    if tag in ARRAY_TAGS:
        return "array"
    if tag == SUBBLOCK_OPEN_TAG:
        return "subblock"
    raise FormatError(f"Unknown tag {tag} in {context} context")


def parse_tag_stream(r: BinaryReader, context: str) -> list:
    """Parse tag-value pairs until a terminating -1. `context` is 'header'
    or 'widget' to resolve tags 46/47's context-dependent arity."""
    props = []
    while True:
        tag = r.read_u32()
        if tag == END:
            break
        arity = _tag_arity(tag, context)
        if arity == "array":
            count = r.read_u32()
            vals = [count] + [r.read_u32() for _ in range(count)]
        elif arity == "subblock":
            vals = []
            while True:
                v = r.read_u32()
                if v == SUBBLOCK_CLOSE_VALUE:
                    break
                vals.append(v)
        else:
            vals = [r.read_u32() for _ in range(arity)]
        props.append(Property(tag, vals))
    return props


def parse_widgets(r: BinaryReader) -> list:
    """Parse the child widget list until the panel-ending -1."""
    widgets = []
    while True:
        t = r.read_u32()
        if t == END:
            break
        if t == PANEL_MARKER:
            props = parse_tag_stream(r, context="header")
            widgets.append(NestedPanelBlock(props))
            continue
        sub_id = r.read_u32()
        geometry = None
        if t in POSITIONAL_GEOMETRY_TYPES:
            x = r.read_u32()
            y = r.read_u32()
            w = r.read_u32()
            h = r.read_u32()
            geometry = (x, y, w, h)
        elif t not in GENERIC_TYPES:
            raise FormatError(f"Unknown widget type {t} at offset {r.off}")
        props = parse_tag_stream(r, context="widget")
        widgets.append(Widget(t, sub_id, geometry, props))
    return widgets


def parse_panel(blob: bytes) -> Panel:
    r = BinaryReader(blob)
    marker = r.read_u32()
    if marker != PANEL_MARKER:
        raise FormatError(f"Expected panel marker {PANEL_MARKER}, got {marker}")
    header_props = parse_tag_stream(r, context="header")
    widgets = parse_widgets(r)
    if r.remaining() != 0:
        raise FormatError(f"{r.remaining()} trailing bytes after panel EOF")
    return Panel(header_props, widgets)


def _write_tag_stream(w: BinaryWriter, props: list):
    for p in props:
        w.write_u32(p.tag)
        if p.tag == SUBBLOCK_OPEN_TAG:
            w.write_u32s(p.values)
            w.write_u32(SUBBLOCK_CLOSE_VALUE)
        else:
            w.write_u32s(p.values)
    w.write_u32(END)


def _write_widgets(w: BinaryWriter, widgets: list):
    for entry in widgets:
        if isinstance(entry, NestedPanelBlock):
            w.write_u32(PANEL_MARKER)
            _write_tag_stream(w, entry.properties)
            continue
        w.write_u32(entry.type)
        w.write_u32(entry.sub_id)
        if entry.geometry is not None:
            w.write_u32s(entry.geometry)
        _write_tag_stream(w, entry.properties)
    w.write_u32(END)


def write_panel(panel: Panel) -> bytes:
    w = BinaryWriter()
    w.write_u32(PANEL_MARKER)
    _write_tag_stream(w, panel.header_properties)
    _write_widgets(w, panel.widgets)
    return w.getvalue()


def roundtrip_test(blob: bytes) -> tuple:
    """Parse then re-serialize a panel blob. Returns (ok, message)."""
    try:
        panel = parse_panel(blob)
    except FormatError as e:
        return False, f"parse error: {e}"
    try:
        out = write_panel(panel)
    except Exception as e:
        return False, f"write error: {e}"
    if out == blob:
        return True, f"OK ({len(blob)} bytes, {len(panel.widgets)} widgets)"
    # Find first differing byte for debugging
    n = min(len(out), len(blob))
    diff_at = next((i for i in range(n) if out[i] != blob[i]), n)
    return False, (
        f"byte mismatch at offset {diff_at} "
        f"(orig {len(blob)}B vs rewritten {len(out)}B)"
    )


def roundtrip_all_panels():
    """Round-trip every real SMNU panel from base game + expansion."""
    from smnu_analysis import load_panels

    panels = load_panels()
    passed = 0
    failed = []
    for name in sorted(panels.keys(), key=lambda n: panels[n]["index"]):
        blob = panels[name]["smnu"]
        if not blob:
            continue
        ok, msg = roundtrip_test(blob)
        if ok:
            passed += 1
        else:
            failed.append((name, msg))
            print(f"FAIL {name}: {msg}")

    total = passed + len(failed)
    print(f"\n{passed}/{total} panels round-tripped byte-perfect")
    if failed:
        print(f"\n{len(failed)} failures:")
        for name, msg in failed:
            print(f"  {name}: {msg}")
    return passed, failed


def main():
    import argparse

    parser = argparse.ArgumentParser(description="SMNU panel format parser/writer")
    parser.add_argument("command", choices=["roundtrip-all", "roundtrip", "dump"])
    parser.add_argument("panels", nargs="*", help="Panel name(s) for roundtrip/dump")
    args = parser.parse_args()

    if args.command == "roundtrip-all":
        roundtrip_all_panels()
        return

    from smnu_analysis import load_panels

    all_panels = load_panels()

    def resolve(name):
        if name in all_panels:
            return name, all_panels[name]
        if f"MX:{name}" in all_panels:
            return f"MX:{name}", all_panels[f"MX:{name}"]
        return None, None

    if args.command == "roundtrip":
        for name in args.panels:
            key, panel = resolve(name)
            if panel is None:
                print(f"Panel '{name}' not found.")
                continue
            ok, msg = roundtrip_test(panel["smnu"])
            print(f"{key}: {'OK' if ok else 'FAIL'} - {msg}")

    elif args.command == "dump":
        for name in args.panels:
            key, panel = resolve(name)
            if panel is None:
                print(f"Panel '{name}' not found.")
                continue
            parsed = parse_panel(panel["smnu"])
            print(f"\n{key} ({len(panel['smnu'])} bytes)")
            print(f"Header properties ({len(parsed.header_properties)}):")
            for p in parsed.header_properties:
                print(f"  tag={p.tag} values={p.values}")
            print(f"Widgets ({len(parsed.widgets)}):")
            for wi, entry in enumerate(parsed.widgets):
                if isinstance(entry, NestedPanelBlock):
                    print(f"  [{wi}] NestedPanelBlock ({len(entry.properties)} props)")
                    continue
                print(
                    f"  [{wi}] type={entry.type} sub_id={entry.sub_id} "
                    f"geometry={entry.geometry} props={len(entry.properties)}"
                )


if __name__ == "__main__":
    main()
