"""
cam_reader.py - faithful Python port of 's CamLib.Read()
====================================================================
This is a direct, careful port of the validated C# source (),
not a re-derivation from scratch. Trust this over any hand-decoded
byte-offset guesses in RESEARCH_NOTES.md - those were superseded the
moment real tool source appeared.
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
    path = sys.argv[1] if len(sys.argv) > 1 else "/mnt/user-data/uploads/maindata.cam"
    sections = read_cam(path)
    for i, sec in enumerate(sections):
        print(f"Section {i}: ext={sec.extension!r}  files={len(sec.files)}")
        for f in sec.files[:5]:
            print(f"    {f.display_name!r:30s} off=0x{f.data_off:08X} size={f.data_size}")
        if len(sec.files) > 5:
            print(f"    ... and {len(sec.files)-5} more")
