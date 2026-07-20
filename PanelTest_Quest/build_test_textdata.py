"""
build_test_textdata.py - Build a textdata CAM for panel navigation test
========================================================================
Creates a minimal textdata.cam containing:
  SMNU section: TS01 (main panel) + TS02 (research sub-panel)
  STRT section: TS01 (main text) + TS02 (research text)

The TS01 main panel is cloned from MX02 (Magic Bazaar main) and the
TS02 research panel is cloned from MX03 (Magic Bazaar research).

If the engine resolves "action 82 + code 8851 on building with DialogID TS01"
to "open panel TS02" by naming convention (sequential), this will work.
"""
import sys, struct
from pathlib import Path

workspace_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(workspace_root))
from cam_reader import read_cam


def build_cam(sections_data):
    """
    Build a CAM file from sections data.
    sections_data: list of (extension_4char, [(name_20bytes, data_bytes), ...])
    """
    # CAM format:
    # [12] fix header: "CYLBPC  \x01\x00\x01\x00"
    # [4] section_count
    # [4] content_header_length
    # [section_count * 8] section directory: (ext[4], offset[4])
    # Content header: for each section: [4]file_count, [4]pause, then file_count * (name[20], offset[4], size[4])
    # Then all file data sequentially

    section_count = len(sections_data)

    # Calculate content header
    content_header_parts = []
    for ext, files in sections_data:
        # file_count(4) + pause(4) + files_count * (name(20) + offset(4) + size(4))
        part_size = 4 + 4 + len(files) * 28
        content_header_parts.append(part_size)
    content_header_length = sum(content_header_parts)

    # Fixed header
    fix_header = b"CYLBPC  \x01\x00\x01\x00"

    # Section directory offset starts after: fix_header(12) + section_count(4) + content_header_length(4)
    dir_start = 12 + 4 + 4
    # Content header starts after directory
    content_header_start = dir_start + section_count * 8
    # Data starts after content header
    data_start = content_header_start + content_header_length

    # Calculate file data offsets
    current_data_offset = data_start
    file_offsets = []  # list of list of (offset, size)
    for ext, files in sections_data:
        section_offsets = []
        for name, data in files:
            section_offsets.append((current_data_offset, len(data)))
            current_data_offset += len(data)
        file_offsets.append(section_offsets)

    # Build the binary
    out = bytearray()

    # Fix header
    out += fix_header

    # Section count + content header length
    out += struct.pack("<II", section_count, content_header_length)

    # Section directory
    # SectionHeaderOffset for each section - these point into the content header
    ch_offset = content_header_start
    for i, (ext, files) in enumerate(sections_data):
        out += ext.encode('ascii')[:4].ljust(4, b'\x00')
        out += struct.pack("<I", ch_offset)
        ch_offset += content_header_parts[i]

    # Content header
    for sec_idx, (ext, files) in enumerate(sections_data):
        out += struct.pack("<II", len(files), 0)  # file_count, pause
        for file_idx, (name, data) in enumerate(files):
            offset, size = file_offsets[sec_idx][file_idx]
            # Name is 20 bytes, null-padded
            name_bytes = name.encode('ascii')[:20].ljust(20, b'\x00')
            out += name_bytes
            out += struct.pack("<II", offset, size)

    # File data
    for ext, files in sections_data:
        for name, data in files:
            out += data

    return bytes(out)


def main():
    # Load MX02 and MX03 panels from the expansion as templates
    mx_data = open(workspace_root / 'DataMX' / 'mx_textdata.cam', 'rb').read()
    mx_secs = read_cam(mx_data)

    # Get MX02 SMNU + STRT (Magic Bazaar main panel)
    mx02_smnu = None
    mx02_strt = None
    mx03_smnu = None
    mx03_strt = None

    for f in mx_secs[0].files:  # SMNU section
        if f.display_name == 'MX02':
            mx02_smnu = mx_data[f.data_off:f.data_off + f.data_size]
        elif f.display_name == 'MX03':
            mx03_smnu = mx_data[f.data_off:f.data_off + f.data_size]

    for f in mx_secs[1].files:  # STRT section
        if f.display_name == 'MX02':
            mx02_strt = mx_data[f.data_off:f.data_off + f.data_size]
        elif f.display_name == 'MX03':
            mx03_strt = mx_data[f.data_off:f.data_off + f.data_size]

    print(f"MX02 SMNU: {len(mx02_smnu)} bytes")
    print(f"MX02 STRT: {len(mx02_strt)} bytes")
    print(f"MX03 SMNU: {len(mx03_smnu)} bytes")
    print(f"MX03 STRT: {len(mx03_strt)} bytes")

    # Build our test CAM:
    # TS01 = clone of MX02 (main panel with Research button)
    # TS02 = clone of MX03 (research sub-panel)
    # We use the EXACT same binary data - just rename the entries.

    sections = [
        ("SMNU", [
            ("TS01", mx02_smnu),
            ("TS02", mx03_smnu),
        ]),
        ("STRT", [
            ("TS01", mx02_strt),
            ("TS02", mx03_strt),
        ]),
    ]

    cam_bytes = build_cam(sections)

    output = Path(__file__).parent / 'Data' / 'Quest_textdata.cam'
    output.write_bytes(cam_bytes)
    print(f"\nWrote: {output} ({len(cam_bytes)} bytes)")

    # Verify by reading it back
    print("\nVerification:")
    verify_secs = read_cam(cam_bytes)
    for sec in verify_secs:
        print(f"  Section {sec.extension}: {len(sec.files)} files")
        for f in sec.files:
            print(f"    {f.display_name}: offset=0x{f.data_off:X}, size={f.data_size}")


if __name__ == '__main__':
    main()
