"""
Unit tests for cam_reader.py — CAM archive parser and extractor.
"""

import struct
import pytest
from pathlib import Path
import sys
import tempfile
import shutil

sys.path.insert(0, str(Path(__file__).parent.parent))
from cam_reader import read_cam, CamSection, CamSectionFile, u32


# ─── Helpers ────────────────────────────────────────────────────────────────

def build_cam(sections_data):
    """
    Build a minimal valid CAM file in memory.

    sections_data: list of (extension_str, [(name_str, data_bytes), ...])
    Returns: bytes of the CAM file.
    """
    section_count = len(sections_data)

    # File header size: 12 (magic) + 4 (count) + 4 (content_header_length) + 8*sections
    file_header_size = 12 + 4 + 4 + 8 * section_count

    # Content header: per section (4 filesCount + 4 pause + 28*files)
    content_header_size = 0
    for _, files in sections_data:
        content_header_size += 4 + 4 + 28 * len(files)

    content_start = file_header_size + content_header_size

    # Calculate all file offsets
    current_offset = content_start
    all_offsets = []
    for _, files in sections_data:
        sec_offsets = []
        for _, data in files:
            sec_offsets.append(current_offset)
            current_offset += len(data)
        all_offsets.append(sec_offsets)

    # Build the binary
    out = bytearray()

    # File header
    out += b"CYLBPC  \x01\x00\x01\x00"
    out += struct.pack("<I", section_count)
    out += struct.pack("<I", content_header_size)

    # Section extension + header offset pairs
    sec_header_offset = file_header_size
    for ext, files in sections_data:
        out += ext.encode("ascii")[:4].ljust(4, b" ")
        out += struct.pack("<I", sec_header_offset)
        sec_header_offset += 4 + 4 + 28 * len(files)

    # Content header
    for sec_idx, (ext, files) in enumerate(sections_data):
        out += struct.pack("<I", len(files))
        out += struct.pack("<I", 0)  # pause
        for file_idx, (name, data) in enumerate(files):
            out += name.encode("ascii")[:20].ljust(20, b"\x00")
            out += struct.pack("<I", all_offsets[sec_idx][file_idx])
            out += struct.pack("<I", len(data))

    # Content
    for _, files in sections_data:
        for _, data in files:
            out += data

    return bytes(out)


# ─── Tests: Basic parsing ───────────────────────────────────────────────────

class TestReadCam:
    def test_single_section_single_file(self):
        """Parse a CAM with one section containing one file."""
        data = b"Hello, Majesty!"
        cam = build_cam([("STRT", [("greeting", data)])])
        sections = read_cam(cam)

        assert len(sections) == 1
        assert sections[0].extension == "STRT"
        assert len(sections[0].files) == 1
        assert sections[0].files[0].display_name == "greeting"
        assert cam[sections[0].files[0].data_off:
                   sections[0].files[0].data_off + sections[0].files[0].data_size] == data

    def test_multiple_sections(self):
        """Parse a CAM with multiple sections."""
        cam = build_cam([
            ("IMAG", [("img1", b"\x00" * 100)]),
            ("TILE", [("tile1", b"\xFF" * 50), ("tile2", b"\xAA" * 30)]),
            ("SPLT", [("pal1", b"\x01\x02\x03" * 256)]),
        ])
        sections = read_cam(cam)

        assert len(sections) == 3
        assert sections[0].extension == "IMAG"
        assert sections[1].extension == "TILE"
        assert sections[2].extension == "SPLT"
        assert len(sections[0].files) == 1
        assert len(sections[1].files) == 2
        assert len(sections[2].files) == 1

    def test_file_data_integrity(self):
        """Verify extracted data matches what was put in."""
        data_a = b"ABCDEFGH" * 100
        data_b = bytes(range(256))
        cam = build_cam([("TEST", [("fileA", data_a), ("fileB", data_b)])])
        sections = read_cam(cam)

        fa = sections[0].files[0]
        fb = sections[0].files[1]
        assert cam[fa.data_off:fa.data_off + fa.data_size] == data_a
        assert cam[fb.data_off:fb.data_off + fb.data_size] == data_b

    def test_empty_section(self):
        """Parse a CAM with a section that has zero files."""
        cam = build_cam([("EMPT", [])])
        sections = read_cam(cam)

        assert len(sections) == 1
        assert sections[0].extension == "EMPT"
        assert len(sections[0].files) == 0

    def test_file_name_padding(self):
        """File names shorter than 20 bytes are null-padded."""
        cam = build_cam([("STRT", [("AB", b"data")])])
        sections = read_cam(cam)
        # display_name strips null padding
        assert sections[0].files[0].display_name == "AB"

    def test_invalid_magic_raises(self):
        """Non-CAM files should fail assertion."""
        bad_data = b"NOT_A_CAM_FILE_HEADER" + b"\x00" * 100
        with pytest.raises(AssertionError):
            read_cam(bad_data)

    def test_read_from_path(self, tmp_path):
        """read_cam() accepts a file path as well as bytes."""
        data = b"test content"
        cam = build_cam([("STRT", [("test", data)])])
        cam_file = tmp_path / "test.cam"
        cam_file.write_bytes(cam)

        sections = read_cam(str(cam_file))
        assert len(sections) == 1
        assert sections[0].files[0].display_name == "test"


# ─── Tests: Extract mode ───────────────────────────────────────────────────

class TestExtract:
    def test_extract_creates_index_and_files(self, tmp_path):
        """--extract writes CamTool.index and section subdirs."""
        data_a = b"content_a"
        data_b = b"content_b"
        cam_bytes = build_cam([("STRT", [("fileA", data_a), ("fileB", data_b)])])
        cam_file = tmp_path / "test.cam"
        cam_file.write_bytes(cam_bytes)

        out_dir = tmp_path / "extracted"

        # Simulate extraction programmatically
        import base64
        sections = read_cam(cam_bytes)
        out_dir.mkdir()

        # Write index
        index_lines = [str(len(sections))]
        for sec in sections:
            index_lines.append(str(len(sec.files)))
        for sec in sections:
            for f in sec.files:
                index_lines.append(f.name.rstrip(b"\x00").decode("ascii"))
        (out_dir / "CamTool.index").write_text("\n".join(index_lines) + "\n")

        # Write files
        for sec_idx, sec in enumerate(sections):
            sec_dir = out_dir / str(sec_idx)
            sec_dir.mkdir()
            for f in sec.files:
                name = f.name.rstrip(b"\x00").decode("ascii")
                filepath = sec_dir / f"{name}.{sec.extension}"
                filepath.write_bytes(cam_bytes[f.data_off:f.data_off + f.data_size])

        # Verify
        assert (out_dir / "CamTool.index").exists()
        assert (out_dir / "0" / "fileA.STRT").read_bytes() == data_a
        assert (out_dir / "0" / "fileB.STRT").read_bytes() == data_b

    def test_extract_index_format(self, tmp_path):
        """Index file has correct structure: section_count, then sizes, then names."""
        cam_bytes = build_cam([
            ("IMAG", [("img1", b"\x00")]),
            ("TILE", [("t1", b"\x01"), ("t2", b"\x02")]),
        ])

        sections = read_cam(cam_bytes)
        index_lines = [str(len(sections))]
        for sec in sections:
            index_lines.append(str(len(sec.files)))
        for sec in sections:
            for f in sec.files:
                index_lines.append(f.name.rstrip(b"\x00").decode("ascii"))

        lines = index_lines
        assert lines[0] == "2"       # 2 sections
        assert lines[1] == "1"       # IMAG has 1 file
        assert lines[2] == "2"       # TILE has 2 files
        assert lines[3] == "img1"
        assert lines[4] == "t1"
        assert lines[5] == "t2"


# ─── Tests: Real game files ────────────────────────────────────────────────

class TestRealFiles:
    """Tests against actual game data files (skipped if not present)."""

    @pytest.fixture
    def gpltext_cam(self):
        path = Path(__file__).parent.parent / "Data" / "gpltext.cam"
        if not path.exists():
            pytest.skip("Data/gpltext.cam not available")
        return path

    @pytest.fixture
    def textdata_cam(self):
        path = Path(__file__).parent.parent / "Data" / "textdata.cam"
        if not path.exists():
            pytest.skip("Data/textdata.cam not available")
        return path

    def test_gpltext_parses(self, gpltext_cam):
        """gpltext.cam parses without errors."""
        sections = read_cam(str(gpltext_cam))
        assert len(sections) == 1
        assert sections[0].extension == "STRT"
        assert len(sections[0].files) == 96

    def test_textdata_parses(self, textdata_cam):
        """textdata.cam parses with 2 sections."""
        sections = read_cam(str(textdata_cam))
        assert len(sections) == 2
        assert sections[0].extension == "SMNU"
        assert sections[1].extension == "STRT"

    def test_gpltext_roundtrip(self, gpltext_cam):
        """Extract and repack gpltext.cam produces identical bytes."""
        from cam_writer import repack_cam
        cam_data = gpltext_cam.read_bytes()
        sections = read_cam(cam_data)
        repacked = repack_cam(cam_data, sections)
        assert repacked == cam_data
