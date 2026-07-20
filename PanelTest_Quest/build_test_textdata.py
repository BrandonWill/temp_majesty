"""
build_test_textdata.py - Build a textdata CAM for multi-page panel navigation test
====================================================================================
Creates a textdata.cam containing THREE panels to test router-based navigation:

  SMNU section: MX03 (router), PT01 (potions page), PT02 (equipment page)
  STRT section: MX03 (router strings), PT01 (potions strings), PT02 (equipment strings)

Strategy:
  - MX03 override: The exe hardcodes Magic Bazaar (MX02) to open MX03 for research.
    By naming our router panel "MX03", the mod's CAM overrides the base MX03.
  - PT01: Clone of original MX03 research items (potions) + Back button to router
  - PT02: Second page (equipment items, reusing MX03 structure) + Back button to router

Navigation uses the "Return to Main" widget pattern from MX03:
  [0, 2, X, Y, W, H, tooltip_str, label_str, 10, 2, 12, "INTG", 13, TILE_idx,
   3, 2, 3, 1024, 5, TARGET_INDEX, 6, CODE, 18, "fn11", -1]

Panel indices are UNKNOWN until tested in-game. We use placeholder values and
document what to adjust based on test results.
"""
import sys, struct, uuid
from pathlib import Path

workspace_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(workspace_root))
from cam_reader import read_cam

# --------------------------------------------------------------------------
# CAM builder (same as before, proven working)
# --------------------------------------------------------------------------

def build_cam(sections_data):
    """
    Build a CAM file from sections data.
    sections_data: list of (extension_4char, [(name_20bytes, data_bytes), ...])
    """
    section_count = len(sections_data)

    # Calculate content header part sizes
    content_header_parts = []
    for ext, files in sections_data:
        part_size = 4 + 4 + len(files) * 28
        content_header_parts.append(part_size)
    content_header_length = sum(content_header_parts)

    fix_header = b"CYLBPC  \x01\x00\x01\x00"

    dir_start = 12 + 4 + 4
    content_header_start = dir_start + section_count * 8
    data_start = content_header_start + content_header_length

    # Calculate file data offsets
    current_data_offset = data_start
    file_offsets = []
    for ext, files in sections_data:
        section_offsets = []
        for name, data in files:
            section_offsets.append((current_data_offset, len(data)))
            current_data_offset += len(data)
        file_offsets.append(section_offsets)

    out = bytearray()
    out += fix_header
    out += struct.pack("<II", section_count, content_header_length)

    # Section directory
    ch_offset = content_header_start
    for i, (ext, files) in enumerate(sections_data):
        out += ext.encode('ascii')[:4].ljust(4, b'\x00')
        out += struct.pack("<I", ch_offset)
        ch_offset += content_header_parts[i]

    # Content header
    for sec_idx, (ext, files) in enumerate(sections_data):
        out += struct.pack("<II", len(files), 0)
        for file_idx, (name, data) in enumerate(files):
            offset, size = file_offsets[sec_idx][file_idx]
            name_bytes = name.encode('ascii')[:20].ljust(20, b'\x00')
            out += name_bytes
            out += struct.pack("<II", offset, size)

    # File data
    for ext, files in sections_data:
        for name, data in files:
            out += data

    return bytes(out)


# --------------------------------------------------------------------------
# SMNU Panel Binary Builders
# --------------------------------------------------------------------------

def pack_u32(val):
    """Pack a single u32 (handles signed values like -1 = 0xFFFFFFFF)."""
    if val < 0:
        return struct.pack("<i", val)
    return struct.pack("<I", val)


def pack_str4(s):
    """Pack a 4-char ASCII string as 4 bytes."""
    return s.encode('ascii')[:4].ljust(4, b'\x00')


def build_widget(fields):
    """
    Build a widget from a list of field values.
    Each value is either an int (packed as u32) or a str (packed as 4-byte ASCII).
    """
    out = bytearray()
    for f in fields:
        if isinstance(f, str):
            out += pack_str4(f)
        else:
            out += pack_u32(f)
    return bytes(out)


def build_panel_header(panel_type=2, x=0, y=182, w=202, h=245,
                       bg_img="IX01", bg_tile=1001, font="fnt4", palette="MMS1"):
    """
    Build a standard panel header (76 bytes).
    Cloned from MX03 panel header structure.
    """
    return build_widget([
        1000,       # Panel format version
        panel_type, # Panel type (2 = building sub-panel)
        x, y,       # Anchor position
        w, h,       # Panel dimensions
        10, 2, 10,  # Constants
        0x00040000, # Flags
        12, bg_img, # Background image set
        13, bg_tile,# Background TILE index
        18, font,   # Default font
        11, palette,# Color palette
        -1,         # Header terminator
    ])


def build_background_frame(w=202, h=245, img="INBg", tile=1024):
    """
    Build background frame widget (76 bytes).
    Cloned from MX03 offset 76-151.
    """
    return build_widget([
        0,          # Separator
        2,          # Widget type
        0, 0,       # X, Y
        w, h,       # Width, Height (= panel dims)
        10, 2,      # Constants
        12, img,    # Frame image set
        13, tile,   # Frame TILE
        3, 128,     # Constants/flags
        6, 1,       # Action type 6 (display-only)
        38, 0,      # Params
        -1,         # Terminator
    ])


def build_nav_button(x, y, w, h, tooltip_str, label_str, tile_idx,
                     target_index, action_code, font="fn11"):
    """
    Build a navigation button widget (100 bytes).
    Uses the simplified MX03 "Return to Main" pattern (NOT the 116-byte hero pattern).

    From MX03 decode at offset 1948-2047:
    [0, 2, X, Y, W, H, tooltip_str, label_str, 10, 2, 12, "INTG", 13, TILE,
     3, 2, 3, 1024, 5, TARGET, 6, CODE, 18, "fn11", -1]
    """
    return build_widget([
        0,              # Separator
        2,              # Widget type (clickable)
        x, y,           # Position
        w, h,           # Size
        tooltip_str,    # Tooltip string index in STRT
        label_str,      # Label string index in STRT
        10, 2,          # Constants
        12, "INTG",     # Navigation button image set
        13, tile_idx,   # TILE index for button icon
        3, 2, 3,        # Constants
        1024,           # ACTION_BLOCK marker
        5,              # Action type 5 (navigate)
        target_index,   # Target panel index
        6,              # Secondary action marker
        action_code,    # Action handler code
        18, font,       # Font reference
        -1,             # Terminator
    ])


def build_title_text(x, y, w, h, str_idx, font="fnt4"):
    """
    Build a title/label text widget.
    Based on the MX03 title area structure (simplified).
    Uses widget start marker 5 (text/label type).
    """
    return build_widget([
        5,              # Text widget start marker
        2,              # Widget type
        x, y,           # Position
        w, h,           # Size
        7, str_idx,     # String group + string index
        10, 2,          # Constants
        10, 0x00040000, # Flags
        10, 0x00080000, # More flags
        12, "INTI",     # Image set for text area
        13, 1016,       # TILE for text background
        18, font,       # Font
        36, 3,          # Color block
        0x80FFFFFF,     # Color: white
        0x80FFFFFF,     # Color: white
        0x80FFFFFF,     # Color: white
        37, 3,          # Border colors
        0x80FFFFFF,
        0x807F7F7F,
        0x80FFFFFF,
        34, 3,          # Background colors
        0x80000000,
        0x80000000,
        0x80000000,
        35, 3,          # Text colors
        0x80FFFFFF,
        0x80FFFFFF,
        0x80FFFFFF,
        -1,             # Terminator
    ])


def build_panel_eof():
    """Panel EOF: double 0xFFFFFFFF (8 bytes)."""
    return struct.pack("<ii", -1, -1)


# --------------------------------------------------------------------------
# Panel Index Placeholders
# --------------------------------------------------------------------------
# These are the BIG UNKNOWN. Panel indices are assigned sequentially as panels
# are loaded from CAM files. The expansion mx_textdata.cam has 35 SMNU panels.
#
# When a quest adds a CAM via <CAM> tag, its panels are appended AFTER the
# base + expansion panels. So our panels would start at index 35+ (0-based)
# or higher depending on what other files load first.
#
# For the FIRST TEST, we just need to verify MX03 override works at all.
# The nav button targets can be adjusted after observing in-game behavior.
#
# Current guesses (to be verified):
#   MX03 (router) = index 7 (overrides expansion's MX03 at position 7)
#   PT01 = index 35 (first new panel after expansion's 35)
#   PT02 = index 36 (second new panel)
#
# If override doesn't replace at index 7 but appends, then:
#   MX03 = index 35, PT01 = index 36, PT02 = index 37
#
# The "Return to Main" (action 9, code 8013) is hardcoded engine behavior
# that always goes back to the building main panel regardless of index.

PANEL_INDEX_MX03_ROUTER = 7      # Where MX03 sits (override of expansion's slot 7)
PANEL_INDEX_PT01 = 35            # First new panel added by quest CAM
PANEL_INDEX_PT02 = 36            # Second new panel added by quest CAM

# Alternative indices if our CAM appends ALL panels (including the MX03 override):
# PANEL_INDEX_MX03_ROUTER = 35
# PANEL_INDEX_PT01 = 36
# PANEL_INDEX_PT02 = 37


# --------------------------------------------------------------------------
# STRT String Table Builder
# --------------------------------------------------------------------------

def build_strt(strings):
    """
    Build a STRT (string table) binary blob.

    Actual STRT format (decoded from mx_textdata.cam):
      [u16 count] [u16 format=0x0200]
      [count * u32 absolute_offsets]  (point to each string entry)
      [string entries: u32_index + null-terminated ASCII]

    Each string entry is: [u32 sequential_index][ASCII string bytes][0x00]
    The offsets point to the u32 index prefix of each entry.
    """
    count = len(strings)
    format_id = 0x0200

    # Calculate sizes
    header_size = 4  # u16 count + u16 format
    offset_table_size = count * 4
    data_start = header_size + offset_table_size

    # Build string entries and calculate offsets
    entries = []
    offsets = []
    current_offset = data_start
    for i, s in enumerate(strings):
        entry = struct.pack("<I", i) + s.encode('ascii', errors='replace') + b'\x00'
        offsets.append(current_offset)
        entries.append(entry)
        current_offset += len(entry)

    # Assemble
    out = bytearray()
    out += struct.pack("<HH", count, format_id)
    for off in offsets:
        out += struct.pack("<I", off)
    for entry in entries:
        out += entry

    return bytes(out)


def parse_strt(data):
    """
    Parse a STRT binary blob and return list of strings.
    Format: [u16 count][u16 format][count * u32 offsets][entries: u32 idx + ASCII\0]
    """
    count = struct.unpack_from("<H", data, 0)[0]
    # format_id = struct.unpack_from("<H", data, 2)[0]

    offsets = []
    for i in range(count):
        off = struct.unpack_from("<I", data, 4 + i * 4)[0]
        offsets.append(off)

    strings = []
    for i, off in enumerate(offsets):
        # Skip the u32 index prefix
        str_start = off + 4
        # Find null terminator
        end = str_start
        while end < len(data) and data[end] != 0:
            end += 1
        s = data[str_start:end].decode('ascii', errors='replace')
        strings.append(s)

    return strings


# --------------------------------------------------------------------------
# Router Panel (MX03 override) — SMNU data
# --------------------------------------------------------------------------

def build_router_panel_smnu():
    """
    Build the MX03 router panel SMNU data.
    A minimal panel with:
      - Panel header (same dims as original MX03)
      - Background frame
      - Title: "MAGIC BAZAAR - RESEARCH" (string index 0)
      - Button 1: "Potions" → navigates to PT01
      - Button 2: "Equipment" → navigates to PT02
      - Return to Main button (action 9, code 8013)
    """
    parts = []

    # Panel header
    parts.append(build_panel_header())

    # Background frame
    parts.append(build_background_frame())

    # Title text - "MAGIC BAZAAR - RESEARCH" at top
    parts.append(build_title_text(
        x=10, y=5, w=182, h=20,
        str_idx=0,  # STRT index 0 = title
    ))

    # Navigation button: "Potions" → PT01
    # Position: left side, middle of panel
    parts.append(build_nav_button(
        x=20, y=70, w=160, h=25,
        tooltip_str=1,          # STRT index 1 = tooltip
        label_str=2,            # STRT index 2 = "Potions"
        tile_idx=1005,          # Arrow icon (same as Return to Main)
        target_index=PANEL_INDEX_PT01,
        action_code=8013,       # Using 8013 (nav code) — may need testing
    ))

    # Navigation button: "Equipment" → PT02
    parts.append(build_nav_button(
        x=20, y=110, w=160, h=25,
        tooltip_str=3,          # STRT index 3 = tooltip
        label_str=4,            # STRT index 4 = "Equipment"
        tile_idx=1005,          # Arrow icon
        target_index=PANEL_INDEX_PT02,
        action_code=8013,
    ))

    # Return to Main button (bottom-left, same as original MX03)
    parts.append(build_nav_button(
        x=3, y=223, w=25, h=20,
        tooltip_str=5,          # STRT index 5
        label_str=6,            # STRT index 6 = "Return to Main"
        tile_idx=1005,          # Back arrow icon
        target_index=9,         # 9 = return to building main (hardcoded behavior)
        action_code=8013,
    ))

    # Panel EOF
    parts.append(build_panel_eof())

    return b''.join(parts)


def build_router_panel_strt():
    """Build STRT strings for the router panel (MX03)."""
    return build_strt([
        "MAGIC BAZAAR - RESEARCH",            # 0: title
        "View potion research items",         # 1: potions tooltip
        "Potions",                            # 2: potions button label
        "View equipment research items",      # 3: equipment tooltip
        "Equipment",                          # 4: equipment button label
        "Return to this building's Main Window.",  # 5: return tooltip
        "Return to Main",                     # 6: return label
    ])


# --------------------------------------------------------------------------
# PT01 Panel (Potions page) — Clone of original MX03 + Back button
# --------------------------------------------------------------------------

def build_pt01_smnu(original_mx03_smnu):
    """
    Build PT01 SMNU: original MX03 research panel with the "Return to Main"
    button replaced by a "Back to Router" button pointing to MX03 (router).

    The original MX03's Return button is at offset 1948-2047 (100 bytes).
    We replace its target from 9 (building main) to MX03_ROUTER index,
    and change its action code.

    Actually, for safety we keep the original panel INTACT and just APPEND
    a Back button before the EOF. The original Return to Main stays (it still
    works). We add our Back button that goes to the router.
    """
    # The original MX03 ends with double -1 (8 bytes) at offset 3412-3419
    # Remove the EOF, append our back button, then re-add EOF
    if original_mx03_smnu[-8:] == struct.pack("<ii", -1, -1):
        panel_body = original_mx03_smnu[:-8]
    else:
        # Try just double 0xFFFFFFFF
        panel_body = original_mx03_smnu[:-8]

    # Append a "← Back" button that navigates to router (MX03 at its index)
    back_button = build_nav_button(
        x=170, y=223, w=25, h=20,
        tooltip_str=23,         # "Return to Research menu" (appended to STRT)
        label_str=24,           # "<- Back" (appended to STRT)
        tile_idx=1005,          # Back arrow
        target_index=PANEL_INDEX_MX03_ROUTER,
        action_code=8013,
    )

    return panel_body + back_button + build_panel_eof()


def build_pt01_strt(original_mx03_strt):
    """
    Build PT01 STRT: use the original MX03 string table but append extra
    strings for the Back button.

    Original MX03 has 23 strings (indices 0-22).
    The Back button uses string indices from the SMNU widget:
      tooltip_str=33 → we use a high index, but the widget refs the STRT directly
      label_str=34 → needs to exist in the STRT

    Since our PT01 SMNU is a clone of MX03 (which refs string indices 0-22 + 33 for
    the Return button tooltip), we just need to ensure those indices exist.
    The SMNU widget stores the literal string INDEX which maps to STRT position.

    Approach: clone original strings, add our Back button string at the end.
    The Back button in our appended widget uses tooltip_str and label_str as
    indices into THIS panel's STRT. We set them to indices within range.

    For PT01, the Back button uses:
      tooltip_str=33 (original "Return to Main" tooltip - already exists if original has 23+ strings)
      Actually the original has indices 0-22 (23 strings). Index 33 is out of range.
      The original MX03 Return button uses tooltip=33, label=16.

    Looking at the SMNU decode: the Return button at offset 1948 has tooltip_str=33 and label_str=16.
    But the STRT only has 23 strings (0-22). This means:
      - String index 33 might be handled differently (maybe ignored or from a global table?)
      - OR the STRT has more entries and we're miscounting

    For safety, we'll use indices within our range for the Back button.
    We set tooltip_str=23 and label_str=24 (appended strings).
    """
    original_strings = parse_strt(original_mx03_strt)

    # Add our Back button strings
    extended_strings = original_strings + [
        "Return to Research menu",  # index 23 = tooltip for Back button
        "<- Back",                  # index 24 = label for Back button
    ]

    return build_strt(extended_strings)


# --------------------------------------------------------------------------
# PT02 Panel (Equipment page) — Clone of MX03 with modified strings + Back
# --------------------------------------------------------------------------

def build_pt02_smnu(original_mx03_smnu):
    """
    Build PT02 SMNU: same structure as original MX03 (6 research items)
    but will display different text (from PT02's own STRT).
    Also adds a Back button to the router.

    We reuse the same panel binary — the STRT strings give it different labels.
    """
    # Same approach as PT01: keep original, append back button
    if original_mx03_smnu[-8:] == struct.pack("<ii", -1, -1):
        panel_body = original_mx03_smnu[:-8]
    else:
        panel_body = original_mx03_smnu[:-8]

    # Back button → router
    back_button = build_nav_button(
        x=170, y=223, w=25, h=20,
        tooltip_str=23,         # "Return to Research menu"
        label_str=24,           # "<- Back"
        tile_idx=1005,
        target_index=PANEL_INDEX_MX03_ROUTER,
        action_code=8013,
    )

    return panel_body + back_button + build_panel_eof()


def build_pt02_strt(original_mx03_strt):
    """
    Build PT02 STRT: replace the research item names with equipment names.
    Keep the same string indices structure so the SMNU widget refs still work.

    Original MX03 string indices (from the decode):
      0 = "Magic Bazaar" (panel title / header)
      1 = "Tonic of Speed" (item 1 name)
      2 = Tonic description
      3 = "Fire Balm" (item 2 name)
      4 = Fire Balm description
      5 = "Dirgo Strength" (item 3 name)
      6 = description
      7 = section label? ("Research Potions")
      8 = "Shapeshift" (item 4 name)
      9 = description
      10 = "Regeneration" (item 5 name)
      11 = description
      12 = "Invisibility" (item 6 name)
      13 = description
      ...rest are cost labels, tooltips, etc.

    We'll rebuild with equipment-themed names in the same slots.
    """
    original_strings = parse_strt(original_mx03_strt)

    # Replace item names/descriptions with equipment-themed alternatives
    modified = list(original_strings)
    if len(modified) > 0:
        modified[0] = "Magic Bazaar - Equipment"
    if len(modified) > 1:
        modified[1] = "Enchanted Sword"
    if len(modified) > 2:
        modified[2] = "A magically sharpened blade. +5 damage."
    if len(modified) > 3:
        modified[3] = "Shield of Valor"
    if len(modified) > 4:
        modified[4] = "Absorbs partial damage from attacks."
    if len(modified) > 5:
        modified[5] = "Ring of Power"
    if len(modified) > 6:
        modified[6] = "Increases spell damage by 25%."
    if len(modified) > 8:
        modified[8] = "Boots of Speed"
    if len(modified) > 9:
        modified[9] = "Increases movement speed by 50%."
    if len(modified) > 10:
        modified[10] = "Amulet of Life"
    if len(modified) > 11:
        modified[11] = "Regenerates health over time."
    if len(modified) > 12:
        modified[12] = "Cloak of Shadows"
    if len(modified) > 13:
        modified[13] = "Grants brief invisibility when hit."

    # Add Back button strings
    modified.append("Return to Research menu")  # index 23
    modified.append("<- Back")                  # index 24

    return build_strt(modified)


# --------------------------------------------------------------------------
# Main: Build the complete textdata.cam
# --------------------------------------------------------------------------

def main():
    print("=" * 70)
    print("Building Panel Navigation Test — Multi-Page Router")
    print("=" * 70)

    # Load original MX03 from expansion textdata as template
    mx_cam_path = workspace_root / 'DataMX' / 'mx_textdata.cam'
    mx_data = open(mx_cam_path, 'rb').read()
    mx_secs = read_cam(mx_data)

    # Find MX03 SMNU and STRT in the expansion data
    mx03_smnu = None
    mx03_strt = None

    for f in mx_secs[0].files:  # SMNU section (first section)
        if f.display_name == 'MX03':
            mx03_smnu = mx_data[f.data_off:f.data_off + f.data_size]

    for f in mx_secs[1].files:  # STRT section (second section)
        if f.display_name == 'MX03':
            mx03_strt = mx_data[f.data_off:f.data_off + f.data_size]

    if not mx03_smnu:
        print("ERROR: Could not find MX03 in SMNU section of mx_textdata.cam")
        sys.exit(1)
    if not mx03_strt:
        print("ERROR: Could not find MX03 in STRT section of mx_textdata.cam")
        sys.exit(1)

    print(f"Original MX03 SMNU: {len(mx03_smnu)} bytes")
    print(f"Original MX03 STRT: {len(mx03_strt)} bytes")
    print()

    # Count panels in the expansion file for index reference
    print(f"Expansion SMNU panel count: {len(mx_secs[0].files)}")
    for i, f in enumerate(mx_secs[0].files):
        if f.display_name == 'MX03':
            print(f"  MX03 is at index {i} in expansion file")
    print()

    # Build our three panels
    print("Building router panel (MX03 override)...")
    router_smnu = build_router_panel_smnu()
    router_strt = build_router_panel_strt()
    print(f"  SMNU: {len(router_smnu)} bytes")
    print(f"  STRT: {len(router_strt)} bytes")

    print("Building PT01 panel (Potions — clone of MX03 + back button)...")
    pt01_smnu = build_pt01_smnu(mx03_smnu)
    pt01_strt = build_pt01_strt(mx03_strt)
    print(f"  SMNU: {len(pt01_smnu)} bytes")
    print(f"  STRT: {len(pt01_strt)} bytes")

    print("Building PT02 panel (Equipment — modified MX03 + back button)...")
    pt02_smnu = build_pt02_smnu(mx03_smnu)
    pt02_strt = build_pt02_strt(mx03_strt)
    print(f"  SMNU: {len(pt02_smnu)} bytes")
    print(f"  STRT: {len(pt02_strt)} bytes")

    # Assemble CAM file with all three panels
    # IMPORTANT: MX03 must be named "MX03" to override the expansion's MX03
    sections = [
        ("SMNU", [
            ("MX03", router_smnu),
            ("PT01", pt01_smnu),
            ("PT02", pt02_smnu),
        ]),
        ("STRT", [
            ("MX03", router_strt),
            ("PT01", pt01_strt),
            ("PT02", pt02_strt),
        ]),
    ]

    cam_bytes = build_cam(sections)

    # Write output
    output_dir = Path(__file__).parent / 'Data'
    output_dir.mkdir(exist_ok=True)
    output = output_dir / 'Quest_textdata.cam'
    output.write_bytes(cam_bytes)
    print(f"\nWrote: {output} ({len(cam_bytes)} bytes)")

    # Verify by reading back
    print("\n" + "=" * 70)
    print("Verification:")
    print("=" * 70)
    verify_secs = read_cam(cam_bytes)
    for sec in verify_secs:
        print(f"  Section {sec.extension}: {len(sec.files)} files")
        for f in sec.files:
            print(f"    {f.display_name}: offset=0x{f.data_off:X}, size={f.data_size}")

    # Print panel index info for debugging
    print("\n" + "=" * 70)
    print("Panel Index Notes (for in-game debugging):")
    print("=" * 70)
    print(f"  MX03 (router) target index for nav buttons: {PANEL_INDEX_MX03_ROUTER}")
    print(f"  PT01 (potions) target index: {PANEL_INDEX_PT01}")
    print(f"  PT02 (equipment) target index: {PANEL_INDEX_PT02}")
    print()
    print("  If Potions/Equipment buttons don't work, try changing indices.")
    print("  The expansion has 35 SMNU panels (indices 0-34).")
    print("  If override replaces MX03 at index 7, PT01/PT02 are 35/36.")
    print("  If quest CAM appends ALL, MX03=35, PT01=36, PT02=37.")
    print()
    print("  The Return to Main button (target=9, code=8013) should always work")
    print("  regardless of index — it's hardcoded engine behavior.")


if __name__ == '__main__':
    main()
