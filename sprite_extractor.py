"""
sprite_extractor.py - Majesty HD Sprite Extractor
===================================================
Extracts sprites from maindata.cam as PNG files.

STATUS: TILE pixel format CRACKED! Container format, IMAG blob structure,
and TILE RLE decoding are all working. Palette lookup is the remaining
piece for correct colors (grayscale/raw-index output works now).

TILE format (version 3):
  [16B header] [6B zeros] [u32 palette_id] [height × u32 offsets] [RLE row data]
  - height = u16 at byte 2; width (canvas) = u16 at byte 4
  - offsets are relative to byte 26 of the TILE entry
  - each row: repeated [u16 x_end][u8 count][u8 flags][count palette bytes]
    - x_end = exclusive end column of the opaque run (draw at [x_end-count, x_end))
    - count = opaque pixel count (palette indices follow)
    - flags: 0x80 = last segment in row
  - Pixel values are 8-bit palette indices

Usage:
    python sprite_extractor.py --list                 # list all IMAG records
    python sprite_extractor.py --dump-anim AVA1        # dump image sets for a unit
    python sprite_extractor.py --dump-frames AVA1 Walk # dump frame descriptor detail
    python sprite_extractor.py --extract AVA1 Walk 0   # extract frame as PNG

Requirements:
    pip install Pillow
"""

import struct
import argparse
from pathlib import Path

from cam_reader import read_cam

CAM_FILE = r"Data/maindata.cam"

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


# ── TILE decoder (CRACKED!) ─────────────────────────────────────────────────

def decode_tile(tile_data):
    """
    Decode a version=3 TILE entry's RLE pixel data.

    Format:
      [16B header][6B zeros][u32 palette_index][height × u32 offsets][row data]
      - height = u16 at byte 2 (header word 1)
      - width  = u16 at byte 4 (canvas width; matches max exclusive-end X)
      - u32 at byte 22 = palette index into SPLT section
      - offsets at byte 26, relative to byte 26 (self-referencing)
      - row data: repeated [u16 x_end][u8 count][u8 flags][count palette bytes]
        - x_end = exclusive end column of the opaque run
        - draw pixels at [x_end - count, x_end)
        - count = number of opaque pixels (palette indices follow)
        - flags: 0x80 = last segment in row, 0x00 = more segments follow
      - Palette index 0 = transparent

    Returns dict with 'width', 'height', 'palette_id', 'rows' where rows is
    a list of [(x_start, [pixel_indices]), ...] segments per row (starts are
    converted from on-disk exclusive ends for callers).
    Returns None on failure.
    """
    if len(tile_data) < 26:
        return None
    if u16(tile_data, 0) != 3:
        return None

    height = u16(tile_data, 2)
    header_width = u16(tile_data, 4)
    palette_id = u32(tile_data, 22)
    OFFSET_BASE = 26

    if height <= 0 or OFFSET_BASE + height * 4 > len(tile_data):
        return None

    offsets = [u32(tile_data, OFFSET_BASE + i * 4) for i in range(height)]

    rows = []
    max_end = 0

    for r in range(height):
        start = OFFSET_BASE + offsets[r]
        if r + 1 < height:
            end = OFFSET_BASE + offsets[r + 1]
        else:
            end = len(tile_data)

        if start >= len(tile_data):
            rows.append([])
            continue

        row_data = tile_data[start:end]
        segments = []
        pos = 0

        while pos + 4 <= len(row_data):
            x_end = u16(row_data, pos)
            count_word = u16(row_data, pos + 2)
            pos += 4

            count = count_word & 0xFF
            flags = (count_word >> 8) & 0xFF
            is_last = (flags & 0x80) != 0

            if count > 0 and count <= x_end and pos + count <= len(row_data):
                pixels = list(row_data[pos:pos + count])
                pos += count
                x_start = x_end - count
                segments.append((x_start, pixels))
                if x_end > max_end:
                    max_end = x_end

            if is_last:
                break

        rows.append(segments)

    width = header_width if header_width > 0 else max_end
    if max_end > width:
        width = max_end

    return {"width": width, "height": height, "palette_id": palette_id, "rows": rows}


def load_splt_palette(cam_data, splt_section, palette_id):
    """
    Load a palette from the SPLT section.
    Format: 8-byte header + 256 × 4-byte RGBA entries.
    Returns list of 256 (R, G, B) tuples, or None.
    """
    if palette_id >= len(splt_section.files):
        return None
    f = splt_section.files[palette_id]
    if f.data_size != 1032:
        return None
    data = cam_data[f.data_off:f.data_off + f.data_size]
    palette = []
    for i in range(256):
        off = 8 + i * 4
        r, g, b = data[off], data[off + 1], data[off + 2]
        palette.append((r, g, b))
    return palette


def is_transparent_color(r, g, b):
    """Check if a palette color is the 'magic pink' transparency key."""
    return r > 150 and g < 80 and b > 150 and abs(r - b) < 60


def tile_to_image(tile_data, palette=None, cam_data=None, splt_section=None):
    """
    Decode a TILE entry and produce a PIL Image (RGBA).

    If palette is provided (list of 256 RGB tuples), uses it directly.
    If cam_data and splt_section are provided, auto-loads the palette
    from the SPLT section using the tile's embedded palette_id.
    If neither, uses grayscale (index value = brightness).
    """
    from PIL import Image

    decoded = decode_tile(tile_data)
    if decoded is None:
        return None

    w, h = decoded["width"], decoded["height"]
    if w == 0 or h == 0:
        return None

    # Auto-load palette if not provided
    if palette is None and cam_data is not None and splt_section is not None:
        palette = load_splt_palette(cam_data, splt_section, decoded["palette_id"])

    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))

    for y, segments in enumerate(decoded["rows"]):
        for x_start, pixels in segments:
            for dx, idx in enumerate(pixels):
                if idx == 0:
                    continue
                if palette:
                    r, g, b = palette[idx]
                    if is_transparent_color(r, g, b):
                        continue
                    img.putpixel((x_start + dx, y), (r, g, b, 255))
                else:
                    img.putpixel((x_start + dx, y), (idx, idx, idx, 255))

    return img


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


def extract_single_tile(cam_data, tile_section, tile_idx, splt_section=None):
    """Extract a single TILE entry as a PNG with correct palette colors."""
    from PIL import Image

    if tile_idx >= len(tile_section.files):
        print(f"TILE[{tile_idx}] out of range (max {len(tile_section.files)-1})")
        return

    tf = tile_section.files[tile_idx]
    td = cam_data[tf.data_off:tf.data_off + tf.data_size]

    img = tile_to_image(td, cam_data=cam_data, splt_section=splt_section)
    if img is None:
        print(f"Failed to decode TILE[{tile_idx}] (size={tf.data_size}, version={u16(td,0) if len(td)>=2 else '?'})")
        return

    # Crop to content
    bbox = img.getbbox()
    if bbox:
        img = img.crop(bbox)

    out_path = f"tile_{tile_idx}.png"
    img.save(out_path)
    print(f"Saved: {out_path} ({img.size[0]}x{img.size[1]})")


def extract_frames(cam_data, imag_section, tile_section, extract_args, splt_section=None):
    """Extract animation frames as PNGs with correct palette colors."""
    from PIL import Image

    if len(extract_args) < 2:
        print("Usage: --extract RECORD_ID SET_NAME [dir_slot] [frame_idx]")
        return

    record_id = extract_args[0]
    set_name = extract_args[1]
    dir_filter = int(extract_args[2]) if len(extract_args) > 2 else None
    frame_filter = int(extract_args[3]) if len(extract_args) > 3 else None

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

    fd = parse_directional_frame_descriptor(blob, match["relOff"])

    out_dir = Path(f"{record_id}_{set_name}")
    out_dir.mkdir(exist_ok=True)

    count = 0
    for d in fd["directions"]:
        if dir_filter is not None and d["slot"] != dir_filter:
            continue

        for frame_idx, tile_idx in enumerate(d["tile_indices"]):
            if frame_filter is not None and frame_idx != frame_filter:
                continue

            if tile_idx >= len(tile_section.files):
                print(f"  TILE[{tile_idx}] out of range, skipping")
                continue

            tf = tile_section.files[tile_idx]
            td = cam_data[tf.data_off:tf.data_off + tf.data_size]

            img = tile_to_image(td, cam_data=cam_data, splt_section=splt_section)
            if img is None:
                print(f"  Failed to decode TILE[{tile_idx}]")
                continue

            # Crop to content
            bbox = img.getbbox()
            if bbox:
                img = img.crop(bbox)

            out_path = out_dir / f"dir{d['slot']}_frame{frame_idx:02d}_tile{tile_idx}.png"
            img.save(str(out_path))
            count += 1

    print(f"Extracted {count} frames to {out_dir}/")



# ── Entry point ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Majesty HD sprite extractor")
    parser.add_argument("--cam", default=CAM_FILE, help="Path to maindata.cam")
    parser.add_argument("--list", action="store_true", help="List all IMAG records")
    parser.add_argument("--dump-anim", metavar="ID", help="Dump image-set table for a record")
    parser.add_argument("--dump-frames", nargs=2, metavar=("ID", "SETNAME"),
                         help="Dump frame descriptor detail, e.g. --dump-frames AVA1 Walk")
    parser.add_argument("--extract", nargs='+', metavar="ARG",
                         help="Extract frames: --extract AVA1 Walk [dir_slot] [frame_idx]")
    parser.add_argument("--extract-tile", type=int, metavar="IDX",
                         help="Extract a single TILE entry by index as PNG")
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
    elif args.extract:
        extract_frames(cam_data, imag, tile, args.extract, splt_section=splt)
    elif args.extract_tile is not None:
        extract_single_tile(cam_data, tile, args.extract_tile, splt_section=splt)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
