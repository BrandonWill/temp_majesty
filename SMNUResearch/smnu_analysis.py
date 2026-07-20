"""
smnu_analysis.py - SMNU binary format analysis tool
====================================================
Tools for analyzing and comparing SMNU panel definitions to decode
the widget/button format, particularly navigation buttons.

Usage:
    python SMNUResearch/smnu_analysis.py dump AP20
    python SMNUResearch/smnu_analysis.py compare AP20 MX03
    python SMNUResearch/smnu_analysis.py find-nav AP20
"""
import sys, struct, argparse
from pathlib import Path

workspace_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(workspace_root))
from cam_reader import read_cam


def load_panels():
    """Load all SMNU and STRT panels from both base and expansion."""
    panels = {}  # name -> {smnu: bytes, strt: bytes, source: str, index: int}
    
    # Base game
    data = open(workspace_root / 'Data/textdata.cam', 'rb').read()
    secs = read_cam(data)
    for i, f in enumerate(secs[0].files):  # SMNU
        name = f.display_name
        panels[name] = {
            'smnu': data[f.data_off:f.data_off + f.data_size],
            'strt': None,
            'source': 'Data/textdata.cam',
            'index': i
        }
    for f in secs[1].files:  # STRT
        name = f.display_name
        if name in panels:
            panels[name]['strt'] = data[f.data_off:f.data_off + f.data_size]
    
    # Expansion
    data2 = open(workspace_root / 'DataMX/mx_textdata.cam', 'rb').read()
    secs2 = read_cam(data2)
    base_count = len(secs[0].files)
    for i, f in enumerate(secs2[0].files):  # SMNU
        name = f.display_name
        panels[f'MX:{name}'] = {
            'smnu': data2[f.data_off:f.data_off + f.data_size],
            'strt': None,
            'source': 'DataMX/mx_textdata.cam',
            'index': base_count + i  # Expansion panels are loaded after base
        }
    for f in secs2[1].files:  # STRT
        name = f.display_name
        key = f'MX:{name}'
        if key in panels:
            panels[key]['strt'] = data2[f.data_off:f.data_off + f.data_size]
    
    return panels


def get_strt_strings(strt_blob):
    """Extract readable strings from a STRT entry."""
    if not strt_blob:
        return []
    text = strt_blob.decode('latin-1')
    # STRT format: [header bytes][null-terminated strings]
    # Split on nulls and filter to readable
    parts = text.split('\x00')
    strings = []
    for p in parts:
        if p and len(p) > 1:
            clean = ''.join(c if 32 <= ord(c) < 127 else f'[{ord(c):02X}]' for c in p)
            strings.append(clean)
    return strings


def dump_panel(name, panel):
    """Full hex dump of a panel's SMNU with annotations."""
    blob = panel['smnu']
    print(f"\n{'='*70}")
    print(f"Panel: {name} ({len(blob)} bytes) - index {panel['index']}")
    print(f"Source: {panel['source']}")
    print(f"{'='*70}")
    
    # STRT strings
    if panel['strt']:
        strings = get_strt_strings(panel['strt'])
        print(f"\nSTRT strings ({len(strings)}):")
        for i, s in enumerate(strings):
            print(f"  [{i:2d}] {s[:80]}")
    
    # SMNU hex dump
    print(f"\nSMNU hex dump:")
    for row in range(0, len(blob), 16):
        chunk = blob[row:row+16]
        hex_str = ' '.join(f'{b:02x}' for b in chunk)
        ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
        # u32 interpretation
        u32s = []
        for i in range(0, len(chunk)-3, 4):
            u32s.append(struct.unpack_from("<I", chunk, i)[0])
        print(f"  {row:4d}: {hex_str:<48s} | {ascii_str:<16s} | {u32s}")


def find_nav_refs(name, panel, all_panels):
    """Find potential navigation references (panel indices) in SMNU data."""
    blob = panel['smnu']
    # Build set of all known panel indices
    known_indices = {p['index']: n for n, p in all_panels.items()}
    
    print(f"\n{'='*70}")
    print(f"Navigation analysis: {name} (index {panel['index']})")
    print(f"{'='*70}")
    
    # Scan for u32 values that match known panel indices
    found = []
    for i in range(0, len(blob)-3, 4):
        val = struct.unpack_from("<I", blob, i)[0]
        if val in known_indices and val != panel['index']:
            # Skip common small values that are probably not panel refs
            # (0, 1, 2, 3 could be anything; panel indices start at reasonable numbers)
            if val > 5:
                target_name = known_indices[val]
                found.append((i, val, target_name))
    
    if found:
        print(f"\nPotential navigation targets found:")
        for offset, idx, target in found:
            # Show context
            ctx_start = max(0, offset - 16)
            ctx_end = min(len(blob), offset + 20)
            ctx = blob[ctx_start:ctx_end]
            ctx_u32 = [struct.unpack_from("<I", blob, j)[0] 
                       for j in range(ctx_start, min(len(blob)-3, ctx_end), 4)]
            print(f"  Offset {offset}: -> panel {idx} ({target})")
            print(f"    Context u32: {ctx_u32}")
    else:
        print(f"\n  No obvious panel index references found.")
        print(f"  (Navigation may use built-in action codes instead)")
    
    return found


def main():
    parser = argparse.ArgumentParser(description='SMNU panel analysis')
    parser.add_argument('command', choices=['dump', 'find-nav', 'compare', 'list'])
    parser.add_argument('panels', nargs='*', help='Panel names to analyze')
    args = parser.parse_args()
    
    all_panels = load_panels()
    
    if args.command == 'list':
        print(f"{'Index':<6} {'Name':<10} {'SMNU':<8} {'STRT':<8} {'Source'}")
        print('-' * 60)
        for name in sorted(all_panels.keys(), key=lambda x: all_panels[x]['index']):
            p = all_panels[name]
            smnu_size = len(p['smnu']) if p['smnu'] else 0
            strt_size = len(p['strt']) if p['strt'] else 0
            print(f"{p['index']:<6} {name:<10} {smnu_size:<8} {strt_size:<8} {p['source']}")
    
    elif args.command == 'dump':
        for name in args.panels:
            if name in all_panels:
                dump_panel(name, all_panels[name])
            elif f'MX:{name}' in all_panels:
                dump_panel(f'MX:{name}', all_panels[f'MX:{name}'])
            else:
                print(f"Panel '{name}' not found. Use 'list' to see available panels.")
    
    elif args.command == 'find-nav':
        for name in args.panels:
            if name in all_panels:
                find_nav_refs(name, all_panels[name], all_panels)
            elif f'MX:{name}' in all_panels:
                find_nav_refs(f'MX:{name}', all_panels[f'MX:{name}'], all_panels)
            else:
                print(f"Panel '{name}' not found.")
    
    elif args.command == 'compare':
        if len(args.panels) < 2:
            print("Need at least 2 panel names to compare")
            return
        for name in args.panels:
            key = name if name in all_panels else f'MX:{name}'
            if key in all_panels:
                find_nav_refs(key, all_panels[key], all_panels)


if __name__ == '__main__':
    main()
