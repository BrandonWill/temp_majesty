"""
sprite_injector.py - Encode PNGs back into Majesty HD TILE format
===================================================================
Takes a PNG image and encodes it into the TILE RLE format used by
maindata.cam. Can replace existing TILE entries or create new ones.

TILE format (version 3):
  [16B header][6B zeros][u32 palette_id][height × u32 offsets][row data]

Row data format (per row):
  Repeated segments: [u16 x_pos][u8 count][u8 flags][count palette bytes]
  - x_pos = absolute x column where opaque pixels start
  - count = number of consecutive opaque pixels
  - flags: 0x80 = last segment in row, 0x00 = more segments follow

Usage:
    python sprite_injector.py --encode input.png --palette-id 350 --output tile.bin
    python sprite_injector.py --roundtrip --cam maindata.cam --tile-idx 3547

Requirements:
    pip install Pillow numpy
"""

import struct
import argparse
from pathlib import Path

from cam_reader import read_cam
from sprite_extractor import (
    u16, u32, decode_tile, load_splt_palette, is_transparent_color
)


def quantize_to_palette(image, palette):
    """
    Quantize an RGBA image to a 256-color palette.
    Returns a 2D list of palette indices (0 = transparent).
    
    palette: list of 256 (R, G, B) tuples from SPLT section.
    """
    from PIL import Image
    import numpy as np

    img = image.convert("RGBA")
    w, h = img.size
    pixels = np.array(img)

    # Build palette array for distance computation (exclude transparent entries)
    pal_array = np.array(palette, dtype=np.float32)  # (256, 3)

    # Find transparent palette indices (magic pink)
    transparent_pal = set()
    transparent_pal.add(0)
    for i, (r, g, b) in enumerate(palette):
        if is_transparent_color(r, g, b):
            transparent_pal.add(i)

    # Quantize each pixel
    result = np.zeros((h, w), dtype=np.uint8)

    for y in range(h):
        for x in range(w):
            r, g, b, a = pixels[y, x]

            # Transparent pixel
            if a < 128:
                result[y, x] = 0
                continue

            # Find nearest palette color (excluding transparent entries)
            best_idx = 0
            best_dist = float("inf")
            for i in range(256):
                if i in transparent_pal:
                    continue
                pr, pg, pb = palette[i]
                dist = (int(r) - pr) ** 2 + (int(g) - pg) ** 2 + (int(b) - pb) ** 2
                if dist < best_dist:
                    best_dist = dist
                    best_idx = i

            result[y, x] = best_idx

    return result


def encode_tile(pixel_indices, palette_id, header_w2=0, header_w3=0,
                header_w4=32, header_w5=0, header_w6=0, header_w7=1):
    """
    Encode a 2D array of palette indices into the TILE binary format.

    pixel_indices: 2D numpy array or list-of-lists, shape (height, width).
                   Value 0 = transparent.
    palette_id: u32 palette index for SPLT section.

    Returns: bytes (complete TILE entry ready to be written).
    """
    import numpy as np

    pixels = np.array(pixel_indices, dtype=np.uint8)
    height, width = pixels.shape

    # Encode each row into segments
    row_blobs = []
    for y in range(height):
        row = pixels[y]
        segments = _encode_row(row)
        row_blobs.append(segments)

    # Build offset table
    # Offsets are relative to byte 26 (OFFSET_BASE)
    # Table itself takes height * 4 bytes starting at byte 26
    # So first row data starts at offset = height * 4
    OFFSET_BASE = 26
    table_size = height * 4
    
    # Calculate offsets
    offsets = []
    current_offset = table_size  # first row starts right after the table
    for blob in row_blobs:
        offsets.append(current_offset)
        current_offset += len(blob)

    # Build the full TILE entry
    # Header: 16 bytes
    header = struct.pack("<HHHHHHHH",
                         3,           # version
                         height,      # w1 = height
                         header_w2,   # w2
                         header_w3,   # w3
                         header_w4,   # w4
                         header_w5,   # w5
                         header_w6,   # w6
                         header_w7)   # w7

    # 6 bytes zeros
    padding = b'\x00' * 6

    # u32 palette_id
    pal_id_bytes = struct.pack("<I", palette_id)

    # Offset table (height × u32)
    offset_table = b''.join(struct.pack("<I", o) for o in offsets)

    # Row data
    row_data = b''.join(row_blobs)

    return header + padding + pal_id_bytes + offset_table + row_data


def _encode_row(row):
    """
    Encode a single row of palette indices into RLE segments.

    Format: repeated [u16 x_pos][u8 count][u8 flags][count bytes]
    - Consecutive non-zero pixels become one segment
    - Only index 0 is treated as transparent (skipped)
    - Magenta palette indices (248-255) are preserved as real pixel data
      since the game engine may use them for shadow/blend effects
    - flags = 0x80 for last segment, 0x00 otherwise

    Returns: bytes for this row.
    """
    segments = []
    width = len(row)
    x = 0

    while x < width:
        # Skip only index 0 (true transparent)
        if row[x] == 0:
            x += 1
            continue

        # Found start of opaque run (includes magenta indices)
        x_start = x
        run = []
        while x < width and row[x] != 0 and len(run) < 255:
            run.append(int(row[x]))
            x += 1

        segments.append((x_start, run))

    # Encode segments to bytes
    if not segments:
        # Fully transparent row — still need at least one segment
        # Write a zero-pixel segment at position 0 with last flag
        return struct.pack("<HBB", 0, 0, 0x80)

    parts = []
    for i, (x_pos, pixels) in enumerate(segments):
        is_last = (i == len(segments) - 1)
        flags = 0x80 if is_last else 0x00
        count = len(pixels)
        part = struct.pack("<HBB", x_pos, count, flags) + bytes(pixels)
        parts.append(part)

    return b''.join(parts)


def roundtrip_test(cam_data, tile_section, splt_section, tile_idx):
    """
    Decode a TILE entry, re-encode it, and verify the output matches
    the original (or at least produces an identical image).
    """
    from PIL import Image
    import numpy as np

    tf = tile_section.files[tile_idx]
    original = cam_data[tf.data_off:tf.data_off + tf.data_size]

    # Decode original
    decoded = decode_tile(original)
    if decoded is None:
        print(f"Failed to decode TILE[{tile_idx}]")
        return False

    palette_id = decoded["palette_id"]
    palette = load_splt_palette(cam_data, splt_section, palette_id)

    # Convert decoded segments to a 2D pixel array
    w, h = decoded["width"], decoded["height"]
    pixels = np.zeros((h, w), dtype=np.uint8)
    for y, segments in enumerate(decoded["rows"]):
        for x_start, px_list in segments:
            for dx, idx in enumerate(px_list):
                pixels[y, x_start + dx] = idx

    # Read original header fields for re-encoding
    header_w2 = u16(original, 4)
    header_w3 = u16(original, 6)
    header_w4 = u16(original, 8)
    header_w5 = u16(original, 10)
    header_w6 = u16(original, 12)
    header_w7 = u16(original, 14)

    # Re-encode
    reencoded = encode_tile(
        pixels, palette_id,
        header_w2=header_w2, header_w3=header_w3,
        header_w4=header_w4, header_w5=header_w5,
        header_w6=header_w6, header_w7=header_w7
    )

    # Compare
    if reencoded == original:
        print(f"✓ TILE[{tile_idx}]: perfect round-trip ({len(original)} bytes)")
        return True
    else:
        print(f"  TILE[{tile_idx}]: size {len(original)} -> {len(reencoded)} "
              f"(diff={len(reencoded)-len(original)})")

        # Decode re-encoded to verify image matches
        decoded2 = decode_tile(reencoded)
        if decoded2 is None:
            print(f"  ✗ Re-encoded data failed to decode!")
            return False

        # Compare pixel content
        pixels2 = np.zeros((decoded2["height"], decoded2["width"]), dtype=np.uint8)
        for y, segments in enumerate(decoded2["rows"]):
            for x_start, px_list in segments:
                for dx, idx in enumerate(px_list):
                    pixels2[y, x_start + dx] = idx

        # Trim to same size for comparison
        min_h = min(pixels.shape[0], pixels2.shape[0])
        min_w = min(pixels.shape[1], pixels2.shape[1])
        p1 = pixels[:min_h, :min_w]
        p2 = pixels2[:min_h, :min_w]

        if np.array_equal(p1, p2):
            print(f"  ✓ Image content matches (different byte encoding, same pixels)")
            return True
        else:
            diff_count = np.sum(p1 != p2)
            print(f"  ✗ Pixel mismatch: {diff_count} pixels differ")
            return False


def main():
    parser = argparse.ArgumentParser(description="Majesty HD sprite injector")
    parser.add_argument("--cam", default="Data/maindata.cam", help="Path to maindata.cam")
    parser.add_argument("--encode", metavar="PNG", help="Encode a PNG to TILE format")
    parser.add_argument("--palette-id", type=int, default=350,
                        help="SPLT palette index to use (default: 350 = Adept)")
    parser.add_argument("--output", metavar="FILE", help="Output file for encoded tile")
    parser.add_argument("--roundtrip", action="store_true",
                        help="Test round-trip: decode then re-encode a TILE")
    parser.add_argument("--tile-idx", type=int, default=3547,
                        help="TILE index for round-trip test (default: 3547)")
    args = parser.parse_args()

    print(f"Loading {args.cam}...")
    with open(args.cam, "rb") as fh:
        cam_data = fh.read()

    sections = read_cam(cam_data)
    imag, tile, splt, cut = sections
    print(f"  IMAG: {len(imag.files)}  TILE: {len(tile.files)}  "
          f"SPLT: {len(splt.files)}  CUT: {len(cut.files)}")

    if args.roundtrip:
        roundtrip_test(cam_data, tile, splt, args.tile_idx)

    elif args.encode:
        from PIL import Image

        # Load palette
        palette = load_splt_palette(cam_data, splt, args.palette_id)
        if palette is None:
            print(f"Failed to load palette {args.palette_id}")
            return

        # Load and quantize image
        img = Image.open(args.encode)
        print(f"  Input: {img.size[0]}x{img.size[1]} ({img.mode})")

        print("  Quantizing to palette...")
        pixel_indices = quantize_to_palette(img, palette)

        print("  Encoding to TILE format...")
        tile_data = encode_tile(pixel_indices, args.palette_id)

        out_path = args.output or Path(args.encode).with_suffix(".tile")
        with open(out_path, "wb") as f:
            f.write(tile_data)
        print(f"  Saved: {out_path} ({len(tile_data)} bytes)")

        # Verify by decoding
        decoded = decode_tile(tile_data)
        if decoded:
            print(f"  Verify: {decoded['width']}x{decoded['height']} pixels, "
                  f"palette_id={decoded['palette_id']}")
        else:
            print("  ✗ Verification failed!")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
