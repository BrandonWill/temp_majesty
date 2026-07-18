"""
str_tool.py - Majesty STRT string table converter
====================================================
Converts between the binary STRT format (used inside CAM archives for
game text/translations) and editable TXT files.

STRT format:
  Header (4 bytes):
    u16 line_count
    u8  unicode_flag  (0x00 = ASCII/cp1250, 0x08 = Unicode)
    u8  version_flag  (0x02 = HD with u32 offsets, 0x00 = original with u16 offsets)

  Offset table:
    line_count × (u16 or u32) absolute offsets to each string

  Content:
    Null-terminated strings in windows-1250 encoding

Usage:
    # Export a single .STRT file to .TXT
    python str_tool.py --export input.STRT output.txt

    # Import a .TXT file back to .STRT
    python str_tool.py --import input.txt output.STRT

    # Batch export a directory of .STRT files
    python str_tool.py --export input_dir/ output_dir/

    # Batch import a directory of .TXT files
    python str_tool.py --import input_dir/ output_dir/

Reference: Based on the STRT format used by Majesty Gold HD.
"""

import struct
import argparse
from pathlib import Path


# Text encoding used by the game (Central/Eastern European Windows codepage)
TEXT_ENCODING = "cp1250"
# End-of-line marker used in exported TXT files to preserve multiline strings
EOL_MARKER = "<EOL>"


def read_strt(data):
    """
    Parse a binary STRT string table.
    Returns list of byte strings (raw encoded lines).
    """
    if len(data) < 4:
        raise ValueError("STRT file too short (< 4 bytes)")

    line_count = struct.unpack_from("<H", data, 0)[0]
    unicode_flag = data[2]
    version_flag = data[3]

    pos = 4

    # Read offset table
    offsets = []
    for _ in range(line_count):
        if version_flag == 0x00:
            # Original (PL) format: u16 offsets
            off = struct.unpack_from("<H", data, pos)[0]
            pos += 2
        else:
            # HD format (0x02): u32 offsets
            off = struct.unpack_from("<I", data, pos)[0]
            pos += 4
        offsets.append(off)

    # Read strings using offsets
    lines = []
    for i in range(line_count):
        start = offsets[i]
        if i + 1 < line_count:
            end = offsets[i + 1] - 1  # minus null terminator
        else:
            end = len(data) - 1  # minus final null terminator

        # Safety bounds check
        if start >= len(data):
            lines.append(b"")
            continue
        if end > len(data):
            end = len(data)

        line = data[start:end]
        lines.append(line)

    return lines


def write_strt(lines, version_flag=0x02):
    """
    Write a binary STRT string table from a list of byte strings.
    Always writes in HD format (u32 offsets, version_flag=0x02).
    """
    line_count = len(lines)

    # Calculate header size
    header_size = 4  # u16 count + u8 unicode + u8 version
    offset_table_size = line_count * 4  # u32 per line (HD format)

    # Calculate content offsets
    content_start = header_size + offset_table_size
    offsets = []
    current = content_start
    for line in lines:
        offsets.append(current)
        current += len(line) + 1  # +1 for null terminator

    # Build output
    out = bytearray()

    # Header
    out += struct.pack("<H", line_count)
    out += struct.pack("B", 0x00)  # ASCII/cp1250 mode
    out += struct.pack("B", version_flag)

    # Offset table
    for off in offsets:
        out += struct.pack("<I", off)

    # Content
    for line in lines:
        out += line
        out += b"\x00"

    return bytes(out)


def strt_to_txt(strt_data):
    """Convert binary STRT data to editable text string (UTF-8).
    Uses latin-1 for lossless byte preservation, since every byte 0x00-0xFF
    has a valid latin-1 codepoint. Translators edit the readable parts.
    """
    lines = read_strt(strt_data)
    if not lines:
        return ""  # Empty STRT → empty TXT
    text_lines = []
    for line in lines:
        # latin-1 is a perfect 1:1 byte mapping — no data loss
        decoded = line.decode("latin-1")
        text_lines.append(decoded + EOL_MARKER)
    return "\n".join(text_lines) + "\n"


def txt_to_strt(text, version_flag=0x02):
    """Convert edited text (UTF-8) back to binary STRT data.
    Re-encodes using latin-1 for lossless byte preservation.
    """
    # Empty text → empty STRT (0 lines)
    if not text or text.strip() == "":
        return write_strt([], version_flag)

    # Split on EOL marker + newline — each part is one logical line
    parts = text.split(EOL_MARKER + "\n")
    # The split always produces a trailing empty string after the last EOL+\n
    # Remove only the final empty trailing element
    if parts and parts[-1] == "":
        parts.pop()
    # Handle case where last line has EOL but no trailing newline
    if parts and parts[-1].endswith(EOL_MARKER):
        parts[-1] = parts[-1][:-len(EOL_MARKER)]

    lines = []
    for part in parts:
        # latin-1 encode is lossless for bytes 0x00-0xFF
        encoded = part.encode("latin-1", errors="replace")
        lines.append(encoded)

    return write_strt(lines, version_flag)


def export_file(input_path, output_path):
    """Export a single .STRT file to .TXT."""
    data = Path(input_path).read_bytes()
    text = strt_to_txt(data)
    # Write as binary to avoid OS newline conversion (\r\n on Windows)
    Path(output_path).write_bytes(text.encode("utf-8"))
    lines = read_strt(data)
    print(f"  Exported {len(lines)} strings -> {output_path}")


def import_file(input_path, output_path):
    """Import a single .TXT file back to .STRT."""
    # Read as binary to avoid OS newline conversion
    raw = Path(input_path).read_bytes()
    text = raw.decode("utf-8")
    data = txt_to_strt(text)
    Path(output_path).write_bytes(data)
    lines = read_strt(data)
    print(f"  Imported {len(lines)} strings -> {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Majesty STRT string table converter (for translations)")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--export", "-e", action="store_true",
                       help="Export: STRT -> TXT")
    group.add_argument("--import", "-i", dest="do_import", action="store_true",
                       help="Import: TXT -> STRT")
    parser.add_argument("input", help="Input file or directory")
    parser.add_argument("output", help="Output file or directory")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    is_export = args.export

    if input_path.is_file():
        if is_export:
            export_file(input_path, output_path)
        else:
            import_file(input_path, output_path)

    elif input_path.is_dir():
        output_path.mkdir(parents=True, exist_ok=True)
        if is_export:
            files = sorted(set(
                list(input_path.glob("*.STRT")) + list(input_path.glob("*.strt"))
            ))
        else:
            files = sorted(set(
                list(input_path.glob("*.TXT")) + list(input_path.glob("*.txt"))
            ))

        if not files:
            print(f"No matching files found in {input_path}")
            return

        print(f"{'Export' if is_export else 'Import'} {len(files)} files "
              f"from {input_path} to {output_path}")

        for f in files:
            if is_export:
                out_file = output_path / f"{f.stem}.TXT"
                export_file(f, out_file)
            else:
                out_file = output_path / f"{f.stem}.STRT"
                import_file(f, out_file)
    else:
        print(f"Error: {input_path} is not a valid file or directory")


if __name__ == "__main__":
    main()
