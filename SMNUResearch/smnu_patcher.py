"""
smnu_patcher.py - Surgical SMNU panel modification tool
========================================================
Modifies navigation target panel indices in SMNU binary data within
textdata.cam files. Used to test panel-to-panel navigation hypothesis.

Usage:
    # List all nav buttons in a panel
    python SMNUResearch/smnu_patcher.py list-nav DataMX/mx_textdata.cam MX03

    # Patch a nav button's target
    python SMNUResearch/smnu_patcher.py patch DataMX/mx_textdata.cam MX03 \
        --offset 2024 --new-target 7 --output patched_mx_textdata.cam

    # Generate the proof-of-concept test patch
    python SMNUResearch/smnu_patcher.py poc --output SMNUResearch/test/
"""
import sys
import struct
import shutil
import argparse
from pathlib import Path

workspace_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(workspace_root))
from cam_reader import read_cam


def find_nav_buttons_in_smnu(smnu_blob):
    """Find all navigation buttons in an SMNU blob.
    
    We look for two patterns:
    A) Simple nav: [..., 1024, 5, TARGET, 6, CODE, ...] where CODE >= 8000
       (used in MX03 Return button, offset 2016-2024)
    B) Full nav: [..., 1024, 3, 8, 5, TARGET, 6, CODE, 258, ...] 
       (used in hero panels)
    """
    results = []
    
    for i in range(0, len(smnu_blob) - 12, 4):
        val = struct.unpack_from("<I", smnu_blob, i)[0]
        
        if val == 1024:  # ACTION_BLOCK marker
            # Check pattern A: [1024, 5, TARGET, 6, CODE]
            if i + 20 <= len(smnu_blob):
                next_val = struct.unpack_from("<I", smnu_blob, i + 4)[0]
                if next_val == 5:
                    target = struct.unpack_from("<I", smnu_blob, i + 8)[0]
                    marker6 = struct.unpack_from("<I", smnu_blob, i + 12)[0]
                    code = struct.unpack_from("<I", smnu_blob, i + 16)[0]
                    if marker6 == 6 and code >= 5000:
                        results.append({
                            'type': 'A' if code >= 8000 else 'research',
                            'offset': i,
                            'target_offset': i + 8,
                            'target': target,
                            'code': code,
                            'pattern': 'simple [1024, 5, TARGET, 6, CODE]'
                        })
            
            # Check pattern B: [1024, 3, 8, 5, TARGET, 6, CODE, 258, ...]
            if i + 28 <= len(smnu_blob):
                v1 = struct.unpack_from("<I", smnu_blob, i + 4)[0]
                v2 = struct.unpack_from("<I", smnu_blob, i + 8)[0]
                v3 = struct.unpack_from("<I", smnu_blob, i + 12)[0]
                if v1 == 3 and v2 == 8 and v3 == 5:
                    target = struct.unpack_from("<I", smnu_blob, i + 16)[0]
                    marker6 = struct.unpack_from("<I", smnu_blob, i + 20)[0]
                    code = struct.unpack_from("<I", smnu_blob, i + 24)[0]
                    if marker6 == 6:
                        results.append({
                            'type': 'B',
                            'offset': i,
                            'target_offset': i + 16,
                            'target': target,
                            'code': code,
                            'pattern': 'full [1024, 3, 8, 5, TARGET, 6, CODE, 258, ...]'
                        })
    
    return results


def load_cam_panels(cam_path):
    """Load all SMNU panels from a CAM file. Returns (raw_data, sections)."""
    with open(cam_path, 'rb') as f:
        raw = f.read()
    sections = read_cam(raw)
    return raw, sections


def get_panel_smnu(raw_data, sections, panel_name):
    """Get the SMNU blob for a named panel."""
    smnu_sec = sections[0]  # SMNU is always first section
    for f in smnu_sec.files:
        if f.display_name == panel_name:
            return raw_data[f.data_off:f.data_off + f.data_size], f.data_off, f.data_size
    return None, None, None


def patch_cam_bytes(raw_data, offset, new_value_u32):
    """Patch a u32 value at a specific offset in the raw CAM data."""
    patched = bytearray(raw_data)
    struct.pack_into("<I", patched, offset, new_value_u32)
    return bytes(patched)


def cmd_list_nav(cam_path, panel_name):
    """List all navigation buttons in a panel."""
    raw, sections = load_cam_panels(cam_path)
    blob, abs_offset, size = get_panel_smnu(raw, sections, panel_name)
    
    if blob is None:
        print(f"Panel '{panel_name}' not found in {cam_path}")
        return
    
    print(f"Panel: {panel_name} ({size} bytes, starts at file offset 0x{abs_offset:08X})")
    print()
    
    buttons = find_nav_buttons_in_smnu(blob)
    
    nav_buttons = [b for b in buttons if b['type'] in ('A', 'B')]
    research_buttons = [b for b in buttons if b['type'] == 'research']
    
    if nav_buttons:
        print(f"Navigation buttons ({len(nav_buttons)}):")
        for btn in nav_buttons:
            file_offset = abs_offset + btn['target_offset']
            print(f"  SMNU offset {btn['target_offset']:5d} (file 0x{file_offset:08X}): "
                  f"target={btn['target']} code={btn['code']} [{btn['pattern']}]")
    
    if research_buttons:
        print(f"\nResearch/action buttons ({len(research_buttons)}):")
        for btn in research_buttons:
            file_offset = abs_offset + btn['target_offset']
            print(f"  SMNU offset {btn['target_offset']:5d} (file 0x{file_offset:08X}): "
                  f"action_id={btn['target']} code={btn['code']}")


def cmd_patch(cam_path, panel_name, smnu_offset, new_target, output_path):
    """Patch a nav button's target panel index."""
    raw, sections = load_cam_panels(cam_path)
    blob, abs_offset, size = get_panel_smnu(raw, sections, panel_name)
    
    if blob is None:
        print(f"Panel '{panel_name}' not found in {cam_path}")
        return
    
    # Verify the offset is within bounds
    if smnu_offset >= size:
        print(f"Offset {smnu_offset} is beyond panel size {size}")
        return
    
    old_value = struct.unpack_from("<I", blob, smnu_offset)[0]
    file_offset = abs_offset + smnu_offset
    
    print(f"Patching {cam_path} -> {panel_name}")
    print(f"  SMNU offset: {smnu_offset}")
    print(f"  File offset: 0x{file_offset:08X}")
    print(f"  Old value: {old_value}")
    print(f"  New value: {new_target}")
    
    patched = patch_cam_bytes(raw, file_offset, new_target)
    
    with open(output_path, 'wb') as f:
        f.write(patched)
    
    print(f"\nWrote: {output_path} ({len(patched)} bytes)")
    print(f"To test: replace {cam_path} with this file in your game install.")


def cmd_poc(output_dir):
    """Generate proof-of-concept test patch.
    
    Test 1: Modify MX03 "Return to Main" button to navigate to MX07 
    (Sorcerer's Abode spell list) instead of back to MX02.
    
    If this works in-game:
    - Clicking "Return" in Magic Bazaar research goes to Sorcerer spell list
    - Proves cross-panel navigation works with arbitrary targets
    - Validates our entire multi-page approach
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    cam_path = workspace_root / 'DataMX' / 'mx_textdata.cam'
    raw, sections = load_cam_panels(cam_path)
    
    # Find MX03's "Return to Main" nav button
    blob, abs_offset, size = get_panel_smnu(raw, sections, 'MX03')
    if blob is None:
        print("ERROR: MX03 not found!")
        return
    
    buttons = find_nav_buttons_in_smnu(blob)
    nav_buttons = [b for b in buttons if b['type'] == 'A']
    
    print("MX03 navigation buttons:")
    for btn in nav_buttons:
        print(f"  offset {btn['target_offset']}: target={btn['target']} code={btn['code']}")
    
    if not nav_buttons:
        print("ERROR: No nav buttons found in MX03!")
        return
    
    # The "Return to Main" button has code 8013 and target 9
    return_btn = None
    for btn in nav_buttons:
        if btn['code'] >= 8000:
            return_btn = btn
            break
    
    if return_btn is None:
        print("ERROR: Could not identify Return button!")
        return
    
    print(f"\nReturn button found: target={return_btn['target']}, code={return_btn['code']}")
    
    # Find index of MX07 (Sorcerer spells panel) in the expansion file
    smnu_sec = sections[0]
    mx07_idx = None
    for i, f in enumerate(smnu_sec.files):
        if f.display_name == 'MX07':
            mx07_idx = i
            break
    
    if mx07_idx is None:
        print("ERROR: MX07 not found in expansion panels!")
        # Fall back: use a known base game panel that we know exists
        # Let's just redirect to MX01 (Hall of Champions monster list) instead
        for i, f in enumerate(smnu_sec.files):
            if f.display_name == 'MX01':
                mx07_idx = i
                print(f"Using MX01 (index {mx07_idx}) as fallback target")
                break
    
    # IMPORTANT: expansion panels are loaded AFTER base game panels.
    # The panel index in-game = base_panel_count + expansion_index
    # We need to determine the base panel count.
    base_raw, base_sections = load_cam_panels(workspace_root / 'Data' / 'textdata.cam')
    base_panel_count = len(base_sections[0].files)
    
    print(f"\nBase game has {base_panel_count} panels")
    print(f"MX07 is expansion index {mx07_idx}")
    
    # The target index in SMNU seems to be LOCAL to the expansion
    # (since MX03 uses target=9 for "Return to Main" which would be MX02's local index)
    # Let's check: MX02 should be at expansion index ~3
    for i, f in enumerate(smnu_sec.files):
        if f.display_name == 'MX02':
            print(f"MX02 (Magic Bazaar main) = expansion index {i}")
        if f.display_name == 'MX03':
            print(f"MX03 (Magic Bazaar research) = expansion index {i}")
        if f.display_name == 'MX07':
            print(f"MX07 (Sorcerer spells) = expansion index {i}")
    
    # Wait — the current target is 9. Let's check what's at base index 9:
    # From base game: index 9 = AP07. But MX03 is an expansion panel,
    # so target=9 might use a COMBINED index (base+expansion) or the
    # building's DialogID maps to a specific panel.
    # 
    # Actually, looking back at MX02 building def: DialogID="MX02"
    # The return target 9 might be referring to the MX panel list where
    # MX02 is index 3 (0-based)... but 9 doesn't match.
    #
    # OR: the target is the building's SMNU entry index within its own CAM file.
    # Expansion SMNU has: AP03(0), AP30(1), AP41(2), APMK(3), MX00(4), MX01(5),
    # MX02(6), MX03(7), MX04(8), MX05(9)...
    # Wait, MX02 is at index 6, not 9.
    #
    # Let me just check: the base game AP31 (Marketplace) has DialogID="AP31"
    # and textdata index 32. Its research panel APa3 at index 93 is reached
    # without embedding 93 in the SMNU. So building main is found by DialogID.
    # 
    # For "Return to Main", target=9 might be a SPECIAL CODE meaning
    # "go back to the building that opened this panel" rather than a literal index.
    # That would explain why all return buttons would use the same small value.
    #
    # BUT in the hero panel, targets 22/23/69 ARE literal panel indices.
    # So the system might be: 
    #   - Small values (< some threshold) = special actions
    #   - Larger values = literal panel indices
    #
    # Let's just try it: patch target from 9 to mx07_idx and see what happens.
    
    # For the POC, let's generate TWO test files:
    # Test A: Change target to 5 (MX01 = Hall of Champions monster list)
    # Test B: Change target to 7 (MX07 = Sorcerer spells list)  
    # If both navigate to those panels, we know it's a literal local index.
    # If they crash or do nothing, target 9 might be a special "back" code.
    
    target_offset_in_file = abs_offset + return_btn['target_offset']
    
    # Test A
    patched_a = patch_cam_bytes(raw, target_offset_in_file, 5)
    out_a = output_dir / 'mx_textdata_test_A_target5.cam'
    with open(out_a, 'wb') as f:
        f.write(patched_a)
    print(f"\nTest A: target=5 (MX01 Hall of Champions list)")
    print(f"  Wrote: {out_a}")
    
    # Test B
    patched_b = patch_cam_bytes(raw, target_offset_in_file, 7)
    out_b = output_dir / 'mx_textdata_test_B_target7.cam'
    with open(out_b, 'wb') as f:
        f.write(patched_b)
    print(f"\nTest B: target=7 (MX07 Sorcerer spells)")
    print(f"  Wrote: {out_b}")
    
    # Also keep the original for reference
    orig = output_dir / 'mx_textdata_ORIGINAL.cam'
    shutil.copy2(cam_path, orig)
    print(f"\nOriginal: {orig}")
    
    # Write test instructions
    instructions = output_dir / 'TEST_INSTRUCTIONS.md'
    instructions.write_text(f"""# SMNU Navigation Test - Instructions

## What We're Testing

Can we redirect a panel's "Return to Main" button to navigate to an arbitrary
different panel? If yes, multi-page research panels are possible.

## Setup

1. Back up your game's `DataMX/mx_textdata.cam`
2. Copy one of the test files to replace it:
   - `mx_textdata_test_A_target5.cam` -> rename to `mx_textdata.cam`
   - `mx_textdata_test_B_target7.cam` -> rename to `mx_textdata.cam`

## Test Procedure

1. Start the game in **Expansion mode** (any quest that has Magic Bazaar buildable)
2. Build a **Magic Bazaar**
3. Click on the Magic Bazaar
4. Click **"Research"** to open the research panel (MX03)
5. Click the **"Return to Main"** button (bottom of panel)

## Expected Results

### Test A (target=5):
- Clicking "Return" should navigate to the **Hall of Champions known monsters list**
- This would appear as a list of known monster types instead of the Bazaar main panel

### Test B (target=7):
- Clicking "Return" should navigate to the **Sorcerer's Abode spell list**
- This would show spells like "Change of Heart", "Frost Field", etc.

### If target is a special code (not literal index):
- Button might do nothing
- Button might crash the game
- Button might still go back to Bazaar main (engine ignores the value)

## What Success Means

If EITHER test redirects to the expected panel, we've proven:
- Panel navigation targets are data-driven (literal indices in SMNU binary)
- We can create "Page 2 ->" and "<- Page 1" buttons between custom panels
- Multi-page building research is achievable without engine modification

## Restoring Original

Copy `mx_textdata_ORIGINAL.cam` back to `DataMX/mx_textdata.cam`.

## Technical Details

- Modified offset in MX03 SMNU: {return_btn['target_offset']} (within panel)
- Absolute file offset: 0x{target_offset_in_file:08X}
- Original value: {return_btn['target']} (navigates to building main)
- Test A value: 5 (MX01 in expansion panel list)
- Test B value: 7 (MX07 in expansion panel list)
- Original code byte: {return_btn['code']} (unchanged in tests)
""")
    print(f"\nInstructions: {instructions}")
    print("\n=== POC generation complete ===")


def main():
    parser = argparse.ArgumentParser(description='SMNU Panel Patcher')
    sub = parser.add_subparsers(dest='command')
    
    # list-nav
    p_list = sub.add_parser('list-nav', help='List nav buttons in a panel')
    p_list.add_argument('cam', help='Path to textdata CAM file')
    p_list.add_argument('panel', help='Panel name (e.g., MX03)')
    
    # patch
    p_patch = sub.add_parser('patch', help='Patch a nav button target')
    p_patch.add_argument('cam', help='Path to textdata CAM file')
    p_patch.add_argument('panel', help='Panel name')
    p_patch.add_argument('--offset', type=int, required=True, help='SMNU offset of target value')
    p_patch.add_argument('--new-target', type=int, required=True, help='New panel index')
    p_patch.add_argument('--output', required=True, help='Output file path')
    
    # poc
    p_poc = sub.add_parser('poc', help='Generate proof-of-concept test files')
    p_poc.add_argument('--output', default='SMNUResearch/test/', help='Output directory')
    
    args = parser.parse_args()
    
    if args.command == 'list-nav':
        cmd_list_nav(args.cam, args.panel)
    elif args.command == 'patch':
        cmd_patch(args.cam, args.panel, args.offset, args.new_target, args.output)
    elif args.command == 'poc':
        cmd_poc(args.output)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
