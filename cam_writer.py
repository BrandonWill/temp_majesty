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


def build_cam_from_sections(sections_data):
    """
    Build a brand-new CAM file from in-memory section data (no original CAM
    file needed). This is the tool for authoring a quest-only CAM (e.g. a
    textdata.cam containing new/overridden SMNU+STRT panels) from scratch,
    as opposed to repack_cam() which modifies an existing CAM's entries.

    sections_data: list of (extension_4char: str, files: list[(name: str, data: bytes)])
        `extension_4char` is the section type (e.g. "SMNU", "STRT").
        `name` is the entry name (e.g. "MX03"), ASCII, <=20 bytes.

    Returns: new CAM file as bytes, structurally identical in layout to the
    game's own CAM files (verified via read_cam() round-trip in
    SMNUResearch/test_smnu_cam_builder.py).
    """
    section_count = len(sections_data)

    content_header_parts = [4 + 4 + len(files) * 28 for _, files in sections_data]
    content_header_length = sum(content_header_parts)

    file_header_size = 12 + 4 + 4 + 8 * section_count
    content_start = file_header_size + content_header_length

    # Calculate file data offsets
    current_offset = content_start
    file_offsets = []  # list of list of (offset, size) per section
    for _, files in sections_data:
        sec_offsets = []
        for _, data in files:
            sec_offsets.append((current_offset, len(data)))
            current_offset += len(data)
        file_offsets.append(sec_offsets)

    out = bytearray()

    # === File header ===
    out += b"CYLBPC  \x01\x00\x01\x00"
    out += struct.pack("<I", section_count)
    out += struct.pack("<I", content_header_length)

    sec_header_offset = file_header_size
    for i, (ext, files) in enumerate(sections_data):
        out += ext.encode("ascii")[:4].ljust(4, b"\x00")
        out += struct.pack("<I", sec_header_offset)
        sec_header_offset += content_header_parts[i]

    # === Content header ===
    for sec_idx, (ext, files) in enumerate(sections_data):
        out += struct.pack("<II", len(files), 0)
        for file_idx, (name, data) in enumerate(files):
            name_bytes = name.encode("ascii")[:20].ljust(20, b"\x00")
            offset, size = file_offsets[sec_idx][file_idx]
            out += name_bytes
            out += struct.pack("<II", offset, size)

    # === Content ===
    for _, files in sections_data:
        for _, data in files:
            out += data

    return bytes(out)


def pack_from_directory(input_dir):
    """
    Pack a CAM file from an extracted directory (CamTool.index + section subdirs).
    This is the inverse of cam_reader.py --extract.
    """
    import base64
    input_dir = Path(input_dir)
    index_path = input_dir / "CamTool.index"

    if not index_path.exists():
        raise FileNotFoundError(f"No CamTool.index found in {input_dir}")

    lines = index_path.read_text(encoding="ascii").strip().split("\n")
    idx = 0
    section_count = int(lines[idx]); idx += 1
    section_sizes = []
    for _ in range(section_count):
        section_sizes.append(int(lines[idx])); idx += 1

    # Read file names from index
    section_file_names = []
    for sec_size in section_sizes:
        names = []
        for _ in range(sec_size):
            names.append(lines[idx]); idx += 1
        section_file_names.append(names)

    # Detect base64 mode: if any name contains non-ASCII-printable after decode attempt
    # We just check if the directory uses base64 names by looking at actual files
    # Simple heuristic: try ASCII decode first, fall back to base64
    use_base64 = False

    # Build the CAM structure
    section_count_val = section_count
    # We need to figure out extensions from the files on disk
    sections_data = []  # list of (extension, [(name_bytes, data_bytes), ...])

    for sec_idx in range(section_count):
        sec_dir = input_dir / str(sec_idx)
        if not sec_dir.exists():
            raise FileNotFoundError(f"Section directory not found: {sec_dir}")

        # Get extension from any file in the directory
        sample_files = list(sec_dir.iterdir())
        if not sample_files:
            raise ValueError(f"Empty section directory: {sec_dir}")
        extension = sample_files[0].suffix.lstrip(".")

        files_data = []
        for name_str in section_file_names[sec_idx]:
            file_path = sec_dir / f"{name_str}.{extension}"
            if not file_path.exists():
                raise FileNotFoundError(f"Missing entry file: {file_path}")

            # Decode name back to 20-byte padded form
            if use_base64:
                name_bytes = base64.b64decode(name_str.replace("_", "/"))
            else:
                name_bytes = name_str.encode("ascii").ljust(20, b"\x00")

            data = file_path.read_bytes()
            files_data.append((name_bytes, data))

        sections_data.append((extension, files_data))

    # Build the output binary
    # File header: 12 + 4 + 4 + 8*section_count
    file_header_size = 12 + 4 + 4 + 8 * section_count

    # Content header: sum of (4 + 4 + 28*file_count) per section
    content_header_size = sum(4 + 4 + 28 * len(files) for _, files in sections_data)

    content_start = file_header_size + content_header_size

    # Calculate offsets
    current_offset = content_start
    all_offsets = []
    for _, files in sections_data:
        sec_offsets = []
        for _, data in files:
            sec_offsets.append(current_offset)
            current_offset += len(data)
        all_offsets.append(sec_offsets)

    # Write
    out = bytearray()

    # File header
    out += b"CYLBPC  \x01\x00\x01\x00"
    out += struct.pack("<I", section_count)
    out += struct.pack("<I", content_header_size)

    sec_header_offset = file_header_size
    for ext, files in sections_data:
        out += ext.encode("ascii")[:4].ljust(4, b" ")
        out += struct.pack("<I", sec_header_offset)
        sec_header_offset += 4 + 4 + 28 * len(files)

    # Content header
    for sec_idx, (ext, files) in enumerate(sections_data):
        out += struct.pack("<I", len(files))
        out += struct.pack("<I", 0)  # pause
        for file_idx, (name_bytes, data) in enumerate(files):
            out += name_bytes[:20].ljust(20, b"\x00")
            out += struct.pack("<I", all_offsets[sec_idx][file_idx])
            out += struct.pack("<I", len(data))

    # Content
    for _, files in sections_data:
        for _, data in files:
            out += data

    return bytes(out)


def main():
    parser = argparse.ArgumentParser(description="Majesty HD CAM repacker")
    parser.add_argument("--cam", help="Input CAM file path (for replace modes)")
    parser.add_argument("--output", required=True, help="Output CAM file path")
    parser.add_argument("--pack", metavar="DIR",
                        help="Pack CAM from extracted directory (CamTool.index + subdirs)")
    parser.add_argument("--replace-tile", type=int, metavar="IDX",
                        help="TILE index to replace")
    parser.add_argument("--replace", nargs=3, metavar=("SEC", "IDX", "FILE"),
                        action="append",
                        help="Replace entry: --replace <section_idx> <file_idx> <path>")
    parser.add_argument("--tile-data", metavar="FILE",
                        help="Binary file with new TILE data")
    parser.add_argument("--reencode", action="store_true",
                        help="Re-encode the original tile (round-trip test)")
    parser.add_argument("--identity", action="store_true",
                        help="Repack without changes (verify repacker)")
    args = parser.parse_args()

    # Pack from directory mode
    if args.pack:
        print(f"Packing from directory: {args.pack}")
        output = pack_from_directory(args.pack)
        print(f"  Output size: {len(output):,} bytes")
        with open(args.output, "wb") as f:
            f.write(output)
        print(f"  Saved: {args.output}")

        # Verify
        sections2 = read_cam(output)
        print(f"  Sections: {len(sections2)}")
        for i, s in enumerate(sections2):
            print(f"    {s.extension}: {len(s.files)} files")
        print(f"  ✓ Packed successfully")
        return

    # All other modes require --cam
    if not args.cam:
        parser.error("--cam is required for replace/identity modes")

    print(f"Loading {args.cam}...")
    with open(args.cam, "rb") as fh:
        cam_data = fh.read()
    print(f"  Original size: {len(cam_data):,} bytes")

    sections = read_cam(cam_data)

    # Print section summary (handle any number of sections)
    summary = "  ".join(f"{s.extension}: {len(s.files)}" for s in sections)
    print(f"  {summary}")

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

    # Generic --replace entries
    if args.replace:
        for sec_str, idx_str, filepath in args.replace:
            sec_idx = int(sec_str)
            file_idx = int(idx_str)
            if sec_idx >= len(sections):
                print(f"Error: section {sec_idx} out of range")
                return
            if file_idx >= len(sections[sec_idx].files):
                print(f"Error: file {file_idx} out of range in section {sec_idx}")
                return
            with open(filepath, "rb") as f:
                new_data = f.read()
            old_size = sections[sec_idx].files[file_idx].data_size
            replacements[(sec_idx, file_idx)] = new_data
            print(f"  Replacing [{sec_idx}][{file_idx}]: {old_size} -> {len(new_data)} bytes")

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

    # Spot-check entries if there's a TILE section (index 1)
    if len(sections2) > 1:
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
                print(f"  ✓ [{1}][{check_idx}]: data matches")
            else:
                print(f"  ✗ [{1}][{check_idx}]: DATA MISMATCH!")


if __name__ == "__main__":
    main()
