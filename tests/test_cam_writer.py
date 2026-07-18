"""
Unit tests for cam_writer.py — CAM archive repacker.
"""

import struct
import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from cam_reader import read_cam
from cam_writer import repack_cam, pack_from_directory


# ─── Helpers ────────────────────────────────────────────────────────────────

def build_cam(sections_data):
    """Build a minimal valid CAM file in memory."""
    section_count = len(sections_data)
    file_header_size = 12 + 4 + 4 + 8 * section_count
    content_header_size = 0
    for _, files in sections_data:
        content_header_size += 4 + 4 + 28 * len(files)
    content_start = file_header_size + content_header_size
    current_offset = content_start
    all_offsets = []
    for _, files in sections_data:
        sec_offsets = []
        for _, data in files:
            sec_offsets.append(current_offset)
            current_offset += len(data)
        all_offsets.append(sec_offsets)

    out = bytearray()
    out += b"CYLBPC  \x01\x00\x01\x00"
    out += struct.pack("<I", section_count)
    out += struct.pack("<I", content_header_size)
    sec_header_offset = file_header_size
    for ext, files in sections_data:
        out += ext.encode("ascii")[:4].ljust(4, b" ")
        out += struct.pack("<I", sec_header_offset)
        sec_header_offset += 4 + 4 + 28 * len(files)
    for sec_idx, (ext, files) in enumerate(sections_data):
        out += struct.pack("<I", len(files))
        out += struct.pack("<I", 0)
        for file_idx, (name, data) in enumerate(files):
            out += name.encode("ascii")[:20].ljust(20, b"\x00")
            out += struct.pack("<I", all_offsets[sec_idx][file_idx])
            out += struct.pack("<I", len(data))
    for _, files in sections_data:
        for _, data in files:
            out += data
    return bytes(out)


# ─── Tests: repack_cam ─────────────────────────────────────────────────────

class TestRepackCam:
    def test_identity_repack(self):
        """Repack with no replacements produces identical output."""
        original = build_cam([
            ("STRT", [("file1", b"Hello"), ("file2", b"World")]),
        ])
        sections = read_cam(original)
        repacked = repack_cam(original, sections)
        assert repacked == original

    def test_identity_repack_multi_section(self):
        """Identity repack with multiple sections."""
        original = build_cam([
            ("IMAG", [("img", b"\x00" * 64)]),
            ("TILE", [("t1", b"\xFF" * 32), ("t2", b"\xAA" * 16)]),
            ("SPLT", [("p1", b"\x01\x02\x03" * 100)]),
        ])
        sections = read_cam(original)
        repacked = repack_cam(original, sections)
        assert repacked == original

    def test_replace_entry_smaller(self):
        """Replacing an entry with smaller data adjusts offsets."""
        original = build_cam([
            ("STRT", [("file1", b"AAAA" * 100), ("file2", b"BBBB")]),
        ])
        sections = read_cam(original)
        new_data = b"XX"  # much smaller
        repacked = repack_cam(original, sections, {(0, 0): new_data})

        # Verify by re-reading
        sections2 = read_cam(repacked)
        f = sections2[0].files[0]
        assert repacked[f.data_off:f.data_off + f.data_size] == new_data
        # Second file should still be intact
        f2 = sections2[0].files[1]
        assert repacked[f2.data_off:f2.data_off + f2.data_size] == b"BBBB"

    def test_replace_entry_larger(self):
        """Replacing an entry with larger data adjusts offsets."""
        original = build_cam([
            ("STRT", [("file1", b"A"), ("file2", b"B")]),
        ])
        sections = read_cam(original)
        new_data = b"X" * 1000
        repacked = repack_cam(original, sections, {(0, 0): new_data})

        sections2 = read_cam(repacked)
        f = sections2[0].files[0]
        assert repacked[f.data_off:f.data_off + f.data_size] == new_data
        f2 = sections2[0].files[1]
        assert repacked[f2.data_off:f2.data_off + f2.data_size] == b"B"

    def test_replace_multiple_entries(self):
        """Replace entries in different sections simultaneously."""
        original = build_cam([
            ("IMAG", [("img1", b"original_img")]),
            ("TILE", [("t1", b"original_tile1"), ("t2", b"original_tile2")]),
        ])
        sections = read_cam(original)
        repacked = repack_cam(original, sections, {
            (0, 0): b"new_img",
            (1, 1): b"new_tile2",
        })

        sections2 = read_cam(repacked)
        f_img = sections2[0].files[0]
        assert repacked[f_img.data_off:f_img.data_off + f_img.data_size] == b"new_img"
        f_t1 = sections2[1].files[0]
        assert repacked[f_t1.data_off:f_t1.data_off + f_t1.data_size] == b"original_tile1"
        f_t2 = sections2[1].files[1]
        assert repacked[f_t2.data_off:f_t2.data_off + f_t2.data_size] == b"new_tile2"

    def test_file_counts_preserved(self):
        """Repack preserves the number of files in each section."""
        original = build_cam([
            ("IMAG", [("a", b"1"), ("b", b"2"), ("c", b"3")]),
            ("TILE", [("d", b"4")]),
        ])
        sections = read_cam(original)
        repacked = repack_cam(original, sections, {(0, 1): b"replaced"})
        sections2 = read_cam(repacked)
        assert len(sections2[0].files) == 3
        assert len(sections2[1].files) == 1

    def test_file_names_preserved(self):
        """Repack preserves original file names."""
        original = build_cam([
            ("STRT", [("MyFileName", b"data")]),
        ])
        sections = read_cam(original)
        repacked = repack_cam(original, sections)
        sections2 = read_cam(repacked)
        assert sections2[0].files[0].display_name == "MyFileName"


# ─── Tests: pack_from_directory ────────────────────────────────────────────

class TestPackFromDirectory:
    def test_roundtrip_via_directory(self, tmp_path):
        """Extract to directory, then pack back, produces identical CAM."""
        original = build_cam([
            ("STRT", [("file1", b"Hello World"), ("file2", b"Goodbye")]),
        ])

        # Simulate extraction
        out_dir = tmp_path / "extracted"
        out_dir.mkdir()
        sections = read_cam(original)

        # Write index
        index_lines = ["1", "2", "file1", "file2"]
        (out_dir / "CamTool.index").write_text("\n".join(index_lines) + "\n")

        # Write files
        sec_dir = out_dir / "0"
        sec_dir.mkdir()
        (sec_dir / "file1.STRT").write_bytes(b"Hello World")
        (sec_dir / "file2.STRT").write_bytes(b"Goodbye")

        # Pack
        repacked = pack_from_directory(str(out_dir))

        # Verify content matches
        sections2 = read_cam(repacked)
        assert len(sections2) == 1
        assert len(sections2[0].files) == 2
        f1 = sections2[0].files[0]
        f2 = sections2[0].files[1]
        assert repacked[f1.data_off:f1.data_off + f1.data_size] == b"Hello World"
        assert repacked[f2.data_off:f2.data_off + f2.data_size] == b"Goodbye"

    def test_pack_multi_section(self, tmp_path):
        """Pack from directory with multiple sections."""
        out_dir = tmp_path / "multi"
        out_dir.mkdir()

        # Index: 2 sections, first has 1 file, second has 2 files
        (out_dir / "CamTool.index").write_text("2\n1\n2\nimgA\ntileA\ntileB\n")

        sec0 = out_dir / "0"
        sec0.mkdir()
        (sec0 / "imgA.IMAG").write_bytes(b"image_data")

        sec1 = out_dir / "1"
        sec1.mkdir()
        (sec1 / "tileA.TILE").write_bytes(b"tile1_data")
        (sec1 / "tileB.TILE").write_bytes(b"tile2_data")

        repacked = pack_from_directory(str(out_dir))
        sections = read_cam(repacked)

        assert len(sections) == 2
        assert sections[0].extension == "IMAG"
        assert sections[1].extension == "TILE"
        assert len(sections[0].files) == 1
        assert len(sections[1].files) == 2

    def test_pack_missing_index_raises(self, tmp_path):
        """pack_from_directory raises if CamTool.index is missing."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        with pytest.raises(FileNotFoundError):
            pack_from_directory(str(empty_dir))

    def test_pack_missing_file_raises(self, tmp_path):
        """pack_from_directory raises if an entry file is missing."""
        out_dir = tmp_path / "incomplete"
        out_dir.mkdir()
        (out_dir / "CamTool.index").write_text("1\n1\nmissing_file\n")
        sec0 = out_dir / "0"
        sec0.mkdir()
        # Create a dummy file so the dir isn't empty, but with wrong name
        (sec0 / "wrong_name.STRT").write_bytes(b"dummy")
        with pytest.raises(FileNotFoundError):
            pack_from_directory(str(out_dir))


# ─── Tests: Real game files ────────────────────────────────────────────────

class TestRealFileRepack:
    @pytest.fixture
    def gpltext_cam(self):
        path = Path(__file__).parent.parent / "Data" / "gpltext.cam"
        if not path.exists():
            pytest.skip("Data/gpltext.cam not available")
        return path

    def test_gpltext_identity_repack(self, gpltext_cam):
        """Identity repack of gpltext.cam produces byte-identical output."""
        cam_data = gpltext_cam.read_bytes()
        sections = read_cam(cam_data)
        repacked = repack_cam(cam_data, sections)
        assert repacked == cam_data

    def test_gpltext_extract_pack_roundtrip(self, gpltext_cam, tmp_path):
        """Full extract → pack roundtrip of gpltext.cam."""
        cam_data = gpltext_cam.read_bytes()
        sections = read_cam(cam_data)

        # Extract
        out_dir = tmp_path / "gpltext"
        out_dir.mkdir()

        index_lines = [str(len(sections))]
        for sec in sections:
            index_lines.append(str(len(sec.files)))
        for sec in sections:
            for f in sec.files:
                index_lines.append(f.name.rstrip(b"\x00").decode("ascii"))
        (out_dir / "CamTool.index").write_text("\n".join(index_lines) + "\n")

        for sec_idx, sec in enumerate(sections):
            sec_dir = out_dir / str(sec_idx)
            sec_dir.mkdir()
            for f in sec.files:
                name = f.name.rstrip(b"\x00").decode("ascii")
                filepath = sec_dir / f"{name}.{sec.extension}"
                filepath.write_bytes(cam_data[f.data_off:f.data_off + f.data_size])

        # Pack
        repacked = pack_from_directory(str(out_dir))
        assert repacked == cam_data
