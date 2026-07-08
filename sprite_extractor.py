"""
sprite_extractor.py - Majesty HD Sprite Extractor
===================================================
Extracts sprites from maindata.cam as PNG files.

STATUS: Container format (sections/files) is solid - built on cam_reader.py,
a validated port of the real  unpacker. IMAG blob structure
(image-set table, frame descriptors, per-direction geometry) is understood
and validated against 3 different unit records. The TILE section is
confirmed as the real home of per-frame pixel data, but ITS internal
payload format (likely some per-row RLE) is NOT yet decoded - so PNG
extraction for animated units doesn't work yet. See RESEARCH_NOTES.md.

Usage:
    python sprite_extractor.py --list                 # list all IMAG records
    python sprite_extractor.py --dump-anim AVA1        # dump image sets for a unit
    python sprite_extractor.py --dump-frames AVA1 Walk # dump frame descriptor detail

Requirements:
    pip install Pillow
"""

import struct
import argparse
from pathlib import Path

from cam_reader import read_cam

CAM_FILE = r"C:\Program Files (x86)\Steam\steamapps\common\Majesty HD\Data\maindata.cam"

ANIM_HEADER_SIZE   = 0x14   # u32 n_directions + 16 bytes padding, then u32 entryCount
IMAGE_SET_ENTRY_SZ = 8      # u32 setID + u32 relOffset (corrected from a wrong 12-byte guess)
DIR_HEADER_SIZE    = 0x30   # per-direction block fixed header size before the index array
DIR_GEOMETRY_OFF   = 0x14   # x_off,y_off (i16,i16) then width,height (u16,u16) at +0x18
N_DIRECTION_SLOTS  = 8

IMAGE_SET_NAMES = {
    1: 'Walk', 2: 'Walk-2', 3: 'Walk-3', 4: 'Walk-4',
    8: 'Stand', 16: 'Attack', 17: 'Attack-2', 18: 'Attack-3', 19: 'Attack-4',
    64: 'Special', 80: 'Build', 96: 'Die', 128: 'Cast', 144: 'Carry',
    160: 'Recoil', 192: 'Active', 208: 'Inactive', 224: 'Dead', 240: 'Crumble',
    300: 'Minimap', 316: 'Damage', 400: 'Hotspot',
    500: 'Sel-Underlay', 550: 'Sel-Overlay',
    1000: 'Interface', 4000: 'UnitTexture',
    # seen in real data, meaning not yet confirmed:
    1001: 'Unknown-1001', 1002: 'Unknown-1002',
}


def u16(d, o): return struct.unpack_from("<H", d, o)[0]
def i16(d, o): return struct.unpack_from("<h", d, o)[0]
def u32(d, o): return struct.unpack_from("<I", d, o)[0]
def i32(d, o): return struct.unpack_from("<i", d, o)[0]


# ── IMAG blob parsing ──────────────────────────────────────────────────────

def parse_anim_set(blob):
    """
    Parse an IMAG section blob's image-set table.

    Format (validated against AVA1 Adept, AVB1 Barbarian, AVL1 Warrior):
        +0x00  u32  n_directions header value (meaning still unconfirmed)
        +0x04  16 bytes padding
        +0x14  u32  entryCount
        +0x18  entryCount x 8 bytes: (u32 setID, u32 relOffset)

    Returns (n_dirs, [{"setID":, "setName":, "relOff":}, ...])
    """
    n_dirs = u32(blob, 0)
    entry_count = u32(blob, ANIM_HEADER_SIZE)

    image_sets = []
    pos = ANIM_HEADER_SIZE + 4
    for _ in range(entry_count):
        if pos + IMAGE_SET_ENTRY_SZ > len(blob):
            break
        set_id = u32(blob, pos)
        rel_off = u32(blob, pos + 4)
        image_sets.append({
            "setID": set_id,
            "setName": IMAGE_SET_NAMES.get(set_id, f"setID_{set_id}"),
            "relOff": rel_off,
        })
        pos += IMAGE_SET_ENTRY_SZ

    return n_dirs, image_sets


def parse_directional_frame_descriptor(blob, rel_off, debug=False):
    """
    Parse a frame descriptor for a DIRECTIONAL (unit) image set.

    Structure (validated against AVA1 Walk, AVB1 Walk):
        +0x00  u32  type flag (usually 8)
        +0x0C  u32  misc value, meaning unconfirmed (seen 257 in unrelated
                     records - likely not a per-frame pixel index)
        +0x38  8x u32 (signed!): relative offsets to per-direction blocks.
                     <= 0 means unused slot. NOT necessarily 4 despite the
                     n_directions header claiming 4 - up to 8 real slots seen.

    Per-direction block (variable size - see NOTE below):
        +0x04  u32  historically read as frameCount via high-16 bits, but
                     THIS IS UNRELIABLE (confirmed wrong on AVB1). Not used
                     here; frame count is derived from stride instead.
        +0x14  i16,i16  x_offset, y_offset (hotspot)
        +0x18  u16,u16  width, height
        +0x30  frameCount x 8 bytes: (u32 zero/flag, u32 tileIndex)
                     tileIndex indexes into the TILE section (NOT the small
                     SPLT/CUT tables - confirmed by range: values seen were
                     3500+, far beyond SPLT's 854 / CUT's 20 entries, and
                     resolve to sensible variable-size TILE entries).

    NOTE on frame count: the per-direction block size varies (48-byte fixed
    header + 8 bytes per frame). Since blocks for populated direction slots
    are typically laid out back-to-back, frame count for slot i is derived
    as (offset[i+1] - offset[i] - 0x30) / 8 using the NEXT populated slot's
    offset. The LAST populated slot has no "next" to measure against, so we
    fall back to reading until we hit a value that looks like the start of
    another block (heuristically: a (0,0x00080001)-shaped pair with high
    16 bits == 1 in the low word - i.e. a plausible type-flag leaking in).
    This fallback is a heuristic, not confirmed - treat results for the
    LAST direction slot with suspicion until validated further.
    """
    type_flag = u32(blob, rel_off + 0x00)
    misc = u32(blob, rel_off + 0x0C)

    raw_offsets = []
    for slot in range(N_DIRECTION_SLOTS):
        field = rel_off + 0x38 + slot * 4
        if field + 4 > len(blob):
            break
        raw_offsets.append(i32(blob, field))

    populated = [(slot, off) for slot, off in enumerate(raw_offsets) if off > 0]

    directions = []
    for i, (slot, dv) in enumerate(populated):
        dir_off = rel_off + dv
        if dir_off + DIR_GEOMETRY_OFF + 8 > len(blob):
            if debug:
                print(f"    [debug] slot {slot}: dir_off {dir_off} out of bounds, skipping")
            continue

        x_off = i16(blob, dir_off + DIR_GEOMETRY_OFF)
        y_off = i16(blob, dir_off + DIR_GEOMETRY_OFF + 2)
        width = u16(blob, dir_off + DIR_GEOMETRY_OFF + 4)
        height = u16(blob, dir_off + DIR_GEOMETRY_OFF + 6)

        # Derive frame count from stride to next populated slot, if any
        if i + 1 < len(populated):
            next_dir_off = rel_off + populated[i + 1][1]
            frame_count = (next_dir_off - dir_off - DIR_HEADER_SIZE) // 8
        else:
            # Heuristic fallback for the last slot - read until something
            # that looks like a leaked type-flag/header shows up, capped
            # to avoid runaway reads.
            frame_count = 0
            for f in range(64):
                pair_off = dir_off + DIR_HEADER_SIZE + f * 8
                if pair_off + 8 > len(blob):
                    break
                flag = u32(blob, pair_off)
                idx = u32(blob, pair_off + 4)
                if flag == 0 and 0 < idx < 500000:
                    frame_count += 1
                else:
                    break

        tile_indices = []
        for f in range(max(frame_count, 0)):
            pair_off = dir_off + DIR_HEADER_SIZE + f * 8
            if pair_off + 8 > len(blob):
                break
            tile_indices.append(u32(blob, pair_off + 4))

        directions.append({
            "slot": slot,
            "dir_off": dv,
            "x_off": x_off, "y_off": y_off,
            "width": width, "height": height,
            "frame_count": frame_count,
            "tile_indices": tile_indices,
        })

    return {"type_flag": type_flag, "misc": misc, "directions": directions}


# ── Reporting / debug commands ─────────────────────────────────────────────

def list_records(imag_section):
    print(f"{'ID':<6}  {'Name':<20}  {'DataOff':>10}  {'Size':>8}")
    print("-" * 55)
    for f in sorted(imag_section.files, key=lambda f: f.display_name):
        name = f.display_name
        rid, label = name[:4], name[4:]
        print(f"{rid:<6}  {label:<20}  0x{f.data_off:08X}  {f.data_size:>8,}")
    print(f"\nTotal: {len(imag_section.files)} records")


def find_record(imag_section, record_id):
    for f in imag_section.files:
        if f.display_name.upper().startswith(record_id.upper()):
            return f
    return None


def dump_anim_set(cam_data, imag_section, record_id):
    f = find_record(imag_section, record_id)
    if f is None:
        print(f"Record '{record_id}' not found.")
        return
    blob = cam_data[f.data_off:f.data_off + f.data_size]
    n_dirs, image_sets = parse_anim_set(blob)
    print(f"{f.display_name} - {f.data_size} bytes, n_dirs header = {n_dirs}")
    print(f"{len(image_sets)} image sets:")
    for s in image_sets:
        print(f"  {s['setName']:15s} setID={s['setID']:5d}  relOff=0x{s['relOff']:X}")


def dump_frames(cam_data, imag_section, tile_section, record_id, set_name, debug=False):
    f = find_record(imag_section, record_id)
    if f is None:
        print(f"Record '{record_id}' not found.")
        return
    blob = cam_data[f.data_off:f.data_off + f.data_size]
    n_dirs, image_sets = parse_anim_set(blob)

    match = next((s for s in image_sets if s["setName"].lower() == set_name.lower()), None)
    if match is None:
        print(f"Image set '{set_name}' not found. Available: {[s['setName'] for s in image_sets]}")
        return

    fd = parse_directional_frame_descriptor(blob, match["relOff"], debug=debug)
    print(f"{f.display_name} / {match['setName']} (relOff=0x{match['relOff']:X})")
    print(f"  type_flag={fd['type_flag']} misc={fd['misc']}")
    for d in fd["directions"]:
        print(f"  slot {d['slot']}: hotspot=({d['x_off']},{d['y_off']}) "
              f"size={d['width']}x{d['height']} frames={d['frame_count']}")
        print(f"    tile_indices: {d['tile_indices']}")
        for idx in d["tile_indices"][:2]:
            if idx < len(tile_section.files):
                tf = tile_section.files[idx]
                print(f"      TILE[{idx}]: off=0x{tf.data_off:X} size={tf.data_size}")
            else:
                print(f"      TILE[{idx}]: OUT OF RANGE (only {len(tile_section.files)} tile files)")


# ── Entry point ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Majesty HD sprite extractor")
    parser.add_argument("--cam", default=CAM_FILE, help="Path to maindata.cam")
    parser.add_argument("--list", action="store_true", help="List all IMAG records")
    parser.add_argument("--dump-anim", metavar="ID", help="Dump image-set table for a record")
    parser.add_argument("--dump-frames", nargs=2, metavar=("ID", "SETNAME"),
                         help="Dump frame descriptor detail, e.g. --dump-frames AVA1 Walk")
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    print(f"Loading {args.cam}...")
    with open(args.cam, "rb") as fh:
        cam_data = fh.read()
    print(f"  Loaded {len(cam_data):,} bytes")

    sections = read_cam(cam_data)
    imag, tile, splt, cut = sections
    print(f"  IMAG: {len(imag.files)} records   TILE: {len(tile.files)} frames   "
          f"SPLT: {len(splt.files)} entries   CUT: {len(cut.files)} entries")
    print()

    if args.list:
        list_records(imag)
    elif args.dump_anim:
        dump_anim_set(cam_data, imag, args.dump_anim)
    elif args.dump_frames:
        rid, set_name = args.dump_frames
        dump_frames(cam_data, imag, tile, rid, set_name, debug=args.debug)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
