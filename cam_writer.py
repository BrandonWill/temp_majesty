"""
cam_writer.py - Repack maindata.cam with modified TILE entries
================================================================
Based on the CamLib format from cam_reader.py.

The CAM file format:
  [File header]
    12B magic: "CYLBPC  " + 01 00 01 00
    4B u32 sectionCount
    4B u32 contentHeaderLength
    8B × sectionCount: char[4] extension + u32 sectionHeaderOffset

  [Content header] (sequential, one block per section)
    Per section:
      4B u32 filesCount
      4B zeros (pause)
      28B × filesCount: byte[20] name + u32 fileOffset + u32 fileSize

  [Content] (raw file data, sequential)

To modify a TILE entry:
  - Replace its data blob
  - Update the fileSize in the content header
  - Recalculate all fileOffsets (since sizes changed)
  - Recalculate contentHeaderLength and sectionHeaderOffsets
  - Write the complete new file

Usage:
    python cam_writer.py --cam maindata.cam --replace-tile 3547 new_tile.bin --output modded.cam
    python cam_writer.py --cam maindata.cam --replace-tile 3547 --reencode --output modded.cam
"""

import struct
import argparse
from pathlib import Path

from cam_reader import read_cam, u32 as read_u32


def repack_cam(cam_data, sections, replacements=None):
    """
    Repack a CAM file with optional data replacements.

    cam_data: original CAM file bytes
    sections: list of CamSection from read_cam()
    replacements: dict of {(section_idx, file_idx): new_bytes}

    Returns: new CAM file as bytes.
    """
    if replacements is None:
        replacements = {}

    section_count = len(sections)

    # Gather all file data (original or replaced)
    all_file_data = []  # list of list of bytes per section
    for sec_idx, sec in enumerate(sections):
        sec_files = []
        for file_idx, f in enumerate(sec.files):
            key = (sec_idx, file_idx)
            if key in replacements:
                sec_files.append(replacements[key])
            else:
                sec_files.append(cam_data[f.data_off:f.data_off + f.data_size])
        all_file_data.append(sec_files)

    # Calculate sizes for the file header
    # File header: 12 + 4 + 4 + (8 * sectionCount) bytes
    file_header_size = 12 + 4 + 4 + 8 * section_count

    # Content header size: sum of (4 + 4 + 28 * filesCount) per section
    content_header_size = 0
    for sec in sections:
        content_header_size += 4 + 4 + 28 * len(sec.files)

    # Content starts after file header + content header
    content_start = file_header_size + content_header_size

    # Calculate file offsets within the content area
    current_offset = content_start
    file_offsets = []  # list of list of offsets per section
    for sec_idx, sec in enumerate(sections):
        sec_offsets = []
        for file_idx in range(len(sec.files)):
            sec_offsets.append(current_offset)
            current_offset += len(all_file_data[sec_idx][file_idx])
        file_offsets.append(sec_offsets)

    # Build the output
    out = bytearray()

    # === File header ===
    out += b"CYLBPC  \x01\x00\x01\x00"  # 12B magic
    out += struct.pack("<I", section_count)  # u32 sectionCount
    out += struct.pack("<I", content_header_size)  # u32 contentHeaderLength

    # Section header offsets (not actually used when reading, but
    # let's compute them correctly for a valid round-trip)
    # Each section's header starts sequentially after the file header
    sec_header_offset = file_header_size
    for sec in sections:
        out += sec.extension.encode("ascii")[:4].ljust(4, b' ')
        out += struct.pack("<I", sec_header_offset)
        sec_header_offset += 4 + 4 + 28 * len(sec.files)

    # === Content header ===
    for sec_idx, sec in enumerate(sections):
        out += struct.pack("<I", len(sec.files))  # filesCount
        out += struct.pack("<I", 0)  # pause/padding

        for file_idx, f in enumerate(sec.files):
            # Name: 20 bytes (original name preserved)
            out += f.name
            # Offset and size
            out += struct.pack("<I", file_offsets[sec_idx][file_idx])
            out += struct.pack("<I", len(all_file_data[sec_idx][file_idx]))

    # === Content (file data) ===
    for sec_idx in range(section_count):
        for file_idx in range(len(sections[sec_idx].files)):
            out += all_file_data[sec_idx][file_idx]

    return bytes(out)


def main():
    parser = argparse.ArgumentParser(description="Majesty HD CAM repacker")
    parser.add_argument("--cam", required=True, help="Input maindata.cam path")
    parser.add_argument("--output", required=True, help="Output CAM file path")
    parser.add_argument("--replace-tile", type=int, metavar="IDX",
                        help="TILE index to replace")
    parser.add_argument("--tile-data", metavar="FILE",
                        help="Binary file with new TILE data")
    parser.add_argument("--reencode", action="store_true",
                        help="Re-encode the original tile (round-trip test)")
    parser.add_argument("--identity", action="store_true",
                        help="Repack without changes (verify repacker)")
    args = parser.parse_args()

    print(f"Loading {args.cam}...")
    with open(args.cam, "rb") as fh:
        cam_data = fh.read()
    print(f"  Original size: {len(cam_data):,} bytes")

    sections = read_cam(cam_data)
    imag, tile, splt, cut = sections
    print(f"  IMAG: {len(imag.files)}  TILE: {len(tile.files)}  "
          f"SPLT: {len(splt.files)}  CUT: {len(cut.files)}")

    replacements = {}

    if args.identity:
        # No replacements — just repack as-is to verify the writer
        pass

    elif args.replace_tile is not None:
        tile_idx = args.replace_tile
        if tile_idx >= len(tile.files):
            print(f"Error: TILE[{tile_idx}] out of range")
            return

        if args.reencode:
            # Round-trip: decode original, re-encode, use that
            from sprite_extractor import decode_tile
            from sprite_injector import encode_tile
            import numpy as np

            tf = tile.files[tile_idx]
            original = cam_data[tf.data_off:tf.data_off + tf.data_size]
            decoded = decode_tile(original)
            if decoded is None:
                print(f"Error: failed to decode TILE[{tile_idx}]")
                return

            # Reconstruct pixel array
            w, h = decoded["width"], decoded["height"]
            pixels = np.zeros((h, w), dtype=np.uint8)
            for y, segments in enumerate(decoded["rows"]):
                for x_start, px_list in segments:
                    for dx, idx in enumerate(px_list):
                        pixels[y, x_start + dx] = idx

            from sprite_extractor import u16
            new_data = encode_tile(
                pixels, decoded["palette_id"],
                header_w2=u16(original, 4),
                header_w3=u16(original, 6),
                header_w4=u16(original, 8),
                header_w5=u16(original, 10),
                header_w6=u16(original, 12),
                header_w7=u16(original, 14),
            )
            replacements[(1, tile_idx)] = new_data  # section 1 = TILE
            print(f"  Re-encoded TILE[{tile_idx}]: {tf.data_size} -> {len(new_data)} bytes")

        elif args.tile_data:
            with open(args.tile_data, "rb") as f:
                new_data = f.read()
            replacements[(1, tile_idx)] = new_data  # section 1 = TILE
            print(f"  Replacing TILE[{tile_idx}]: {tile.files[tile_idx].data_size} "
                  f"-> {len(new_data)} bytes")

        else:
            print("Error: specify --tile-data or --reencode")
            return

    print(f"\n  Repacking...")
    output = repack_cam(cam_data, sections, replacements)
    print(f"  New size: {len(output):,} bytes "
          f"(diff: {len(output) - len(cam_data):+,})")

    with open(args.output, "wb") as f:
        f.write(output)
    print(f"  Saved: {args.output}")

    # Verify by re-reading
    print(f"\n  Verifying...")
    sections2 = read_cam(output)
    for i, (s1, s2) in enumerate(zip(sections, sections2)):
        if len(s1.files) != len(s2.files):
            print(f"  ✗ Section {i}: file count mismatch!")
            return
    print(f"  ✓ All sections readable, file counts match")

    # Spot-check a few tiles
    for check_idx in [0, 100, 3547, 5000, 17000]:
        if check_idx >= len(sections2[1].files):
            continue
        f2 = sections2[1].files[check_idx]
        data2 = output[f2.data_off:f2.data_off + f2.data_size]

        if (1, check_idx) in replacements:
            expected = replacements[(1, check_idx)]
        else:
            f1 = sections[1].files[check_idx]
            expected = cam_data[f1.data_off:f1.data_off + f1.data_size]

        if data2 == expected:
            print(f"  ✓ TILE[{check_idx}]: data matches")
        else:
            print(f"  ✗ TILE[{check_idx}]: DATA MISMATCH!")


if __name__ == "__main__":
    main()
