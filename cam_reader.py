"""
cam_reader.py - CAM archive parser
====================================================================
Parses the CAM container format used by Majesty Gold HD. Validated
byte-for-byte against real game data files. Trust this over any
hand-decoded byte-offset guesses in RESEARCH_NOTES.md.
"""

import struct
from pathlib import Path


def u32(data, off):
    return struct.unpack_from("<I", data, off)[0]


class CamSectionFile:
    __slots__ = ("name", "data_off", "data_size")
    def __init__(self, name, data_off, data_size):
        self.name = name
        self.data_off = data_off
        self.data_size = data_size

    @property
    def display_name(self):
        return self.name.rstrip(b"\x00").decode("ascii", errors="replace")


class CamSection:
    __slots__ = ("extension", "files")
    def __init__(self, extension, files):
        self.extension = extension
        self.files = files


def read_cam(path_or_bytes):
    """Faithful port of CamLib.Read(). Returns list of CamSection."""
    if isinstance(path_or_bytes, (bytes, bytearray)):
        cam = path_or_bytes
    else:
        with open(path_or_bytes, "rb") as f:
            cam = f.read()

    pos = 0
    fix_header = cam[pos:pos+12]; pos += 12
    assert fix_header == b"CYLBPC  \x01\x00\x01\x00", f"bad fix header: {fix_header!r}"

    section_count = u32(cam, pos); pos += 4
    content_header_length = u32(cam, pos); pos += 4  # not needed for reading (sequential)

    extensions = []
    for _ in range(section_count):
        ext = cam[pos:pos+4].decode("ascii", errors="replace"); pos += 4
        pos += 4  # SectionHeaderOffset - read but unused by CamLib.Read, kept for round-trip only
        extensions.append(ext)

    # Content header: sequential per section (NOT via the offsets just read)
    sections_file_meta = []  # list of list[(name_bytes, offset, size)]
    for i in range(section_count):
        files_count = u32(cam, pos); pos += 4
        pos += 4  # Pause
        file_meta = []
        for _ in range(files_count):
            name = cam[pos:pos+20]; pos += 20
            f_off = u32(cam, pos); pos += 4
            f_size = u32(cam, pos); pos += 4
            file_meta.append((name, f_off, f_size))
        sections_file_meta.append(file_meta)

    sections = []
    for i in range(section_count):
        files = [CamSectionFile(name, off, size) for (name, off, size) in sections_file_meta[i]]
        sections.append(CamSection(extensions[i], files))

    return sections


if __name__ == "__main__":
    import sys
    import argparse

    parser = argparse.ArgumentParser(description="Majesty HD CAM archive reader/extractor")
    parser.add_argument("cam", nargs="?", default="Data/maindata.cam",
                        help="CAM file to read (default: Data/maindata.cam)")
    parser.add_argument("--extract", metavar="DIR",
                        help="Extract all entries to DIR (creates section subdirs)")
    parser.add_argument("--section", type=int, metavar="IDX",
                        help="Only extract/list this section index")
    parser.add_argument("--entry", type=int, metavar="IDX",
                        help="Only extract this entry index (requires --section)")
    parser.add_argument("--base64-names", action="store_true",
                        help="Use base64-encoded filenames (handles non-ASCII names)")
    args = parser.parse_args()

    import base64

    path = args.cam
    with open(path, "rb") as fh:
        cam_data = fh.read()
    sections = read_cam(cam_data)

    if args.extract:
        # Extract mode: dump entries to disk
        out_dir = Path(args.extract)
        out_dir.mkdir(parents=True, exist_ok=True)

        # Write index file (compatible with CamTool format)
        sec_range = [args.section] if args.section is not None else range(len(sections))

        index_lines = []
        index_lines.append(str(len(sections)))
        for sec in sections:
            index_lines.append(str(len(sec.files)))

        for sec_idx in range(len(sections)):
            sec = sections[sec_idx]
            for f in sec.files:
                if args.base64_names:
                    encoded = base64.b64encode(f.name).decode("ascii").replace("/", "_")
                else:
                    encoded = f.name.rstrip(b"\x00").decode("ascii", errors="replace")
                index_lines.append(encoded)

        index_path = out_dir / "CamTool.index"
        index_path.write_text("\n".join(index_lines) + "\n", encoding="ascii")
        print(f"Wrote index: {index_path}")

        # Write entry files
        extracted = 0
        for sec_idx in sec_range:
            sec = sections[sec_idx]
            sec_dir = out_dir / str(sec_idx)
            sec_dir.mkdir(parents=True, exist_ok=True)

            entry_range = [args.entry] if args.entry is not None else range(len(sec.files))
            for file_idx in entry_range:
                f = sec.files[file_idx]
                if args.base64_names:
                    name = base64.b64encode(f.name).decode("ascii").replace("/", "_")
                else:
                    name = f.name.rstrip(b"\x00").decode("ascii", errors="replace")
                file_path = sec_dir / f"{name}.{sec.extension}"
                file_path.write_bytes(cam_data[f.data_off:f.data_off + f.data_size])
                extracted += 1

        print(f"Extracted {extracted} entries to {out_dir}/")

    else:
        # List mode (default)
        for i, sec in enumerate(sections):
            if args.section is not None and i != args.section:
                continue
            print(f"Section {i}: ext={sec.extension!r}  files={len(sec.files)}")
            for f in sec.files[:5]:
                print(f"    {f.display_name!r:30s} off=0x{f.data_off:08X} size={f.data_size}")
            if len(sec.files) > 5:
                print(f"    ... and {len(sec.files)-5} more")
