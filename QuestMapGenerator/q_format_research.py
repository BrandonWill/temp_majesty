"""
Deep analysis of .q file format across multiple quest files.
Goal: Crack the coordinate encoding for placed objects.

Strategy:
1. Parse all .q files to build a corpus of object entries
2. Compare coordinate values across files with different map sizes
3. Look for patterns: float encoding, fixed-point, packed x,y, etc.
"""
import struct, os, sys
from pathlib import Path

def u8(d, o): return d[o]
def u16(d, o): return struct.unpack_from("<H", d, o)[0]
def u32(d, o): return struct.unpack_from("<I", d, o)[0]
def i32(d, o): return struct.unpack_from("<i", d, o)[0]
def f32(d, o): return struct.unpack_from("<f", d, o)[0]
def read_cstr(d, o):
    end = d.find(b'\x00', o)
    if end == -1: return d[o:].decode('ascii', errors='replace'), len(d)
    return d[o:end].decode('ascii', errors='replace'), end + 1

def parse_q_file(filepath):
    """Parse a .q file and return structured data."""
    data = Path(filepath).read_bytes()
    result = {
        'path': str(filepath),
        'size': len(data),
        'magic1': data[0:4].decode('ascii', errors='replace'),
        'magic2': data[8:12].decode('ascii', errors='replace'),
    }
    
    # Header strings
    pos = 0x10
    quest_name, pos = read_cstr(data, pos)
    pattern_name, pos = read_cstr(data, pos)
    result['quest_name'] = quest_name
    result['pattern_name'] = pattern_name
    result['strings_end'] = pos
    
    # Parameters after strings
    params = []
    for i in range(10):
        if pos + 4 <= len(data):
            params.append(u32(data, pos))
            pos += 4
    result['params'] = params
    
    # Find all object IDs and their contexts
    objects = []
    for i in range(len(data) - 4):
        c = data[i:i+4]
        try:
            s = c.decode('ascii')
            if len(s) == 4 and s[0:2] in ('BV', 'BB', 'AB', 'AV', 'AC', 'AA', 'BA') and s[2:4].replace(' ', '').isalnum():
                # Get context around the ID
                pre_bytes = data[max(0, i-8):i]
                post_bytes = data[i+4:min(len(data), i+40)]
                
                # Try to read description string after ID + u32
                desc = ""
                desc_off = i + 8
                if desc_off < len(data):
                    desc, _ = read_cstr(data, desc_off)
                    if not desc.isprintable() or len(desc) > 50:
                        desc = ""
                
                obj = {
                    'offset': i,
                    'id': s,
                    'prefix': s[0:2],
                    'u32_after': u32(data, i+4) if i+4+4 <= len(data) else None,
                    'desc': desc,
                    'pre_4bytes': data[i-4:i] if i >= 4 else b'',
                    'pre_u32': u32(data, i-4) if i >= 4 else 0,
                    'pre_as_float': f32(data, i-4) if i >= 4 else 0.0,
                    'pre_8_as_2floats': (f32(data, i-8), f32(data, i-4)) if i >= 8 else (0.0, 0.0),
                }
                objects.append(obj)
        except:
            continue
    
    result['objects'] = objects
    return result, data

def analyze_coordinate_candidates(parsed_files):
    """Look at the u32 values before long entries (BB* lairs) and try different interpretations."""
    print("\n" + "="*80)
    print("COORDINATE ANALYSIS: Long entries (lairs/buildings)")
    print("="*80)
    
    for pf in parsed_files:
        lairs = [o for o in pf['objects'] if o['prefix'] in ('BB', 'AB')]
        if not lairs:
            continue
        print(f"\n--- {pf['quest_name']} (map params: {pf['params'][:4]}) ---")
        for lair in lairs:
            pre_u32 = lair['pre_u32']
            pre_float = lair['pre_as_float']
            pre_2f = lair['pre_8_as_2floats']
            
            # Try interpreting pre_u32 as packed coordinates
            # Possibility 1: two u16 packed (x, y)
            if lair['pre_4bytes']:
                lo16 = struct.unpack_from("<H", lair['pre_4bytes'], 0)[0]
                hi16 = struct.unpack_from("<H", lair['pre_4bytes'], 2)[0]
            else:
                lo16 = hi16 = 0
            
            # Possibility 2: float coordinate
            # Possibility 3: fixed-point (e.g., 16.16)
            fixed_x = (pre_u32 >> 16) & 0xFFFF
            fixed_frac = pre_u32 & 0xFFFF
            
            print(f"  @0x{lair['offset']:04X} {lair['id']} {lair['desc']!r:20s} | "
                  f"pre_u32={pre_u32:>12d} (0x{pre_u32:08X}) | "
                  f"as_float={pre_float:12.4f} | "
                  f"packed_u16=({lo16},{hi16}) | "
                  f"fixed16.16=({fixed_x}.{fixed_frac})")
            
            # Also show the 8 bytes before the ID as two separate u32s
            if lair['offset'] >= 8:
                pass  # pre_2f already covers this

def analyze_entry_structure(parsed_files):
    """Determine the exact byte layout of entries by analyzing gaps and patterns."""
    print("\n" + "="*80)
    print("ENTRY STRUCTURE ANALYSIS")
    print("="*80)
    
    for pf in parsed_files:
        objects = pf['objects']
        if len(objects) < 2:
            continue
        
        print(f"\n--- {pf['quest_name']} ({len(objects)} objects, file size={pf['size']}) ---")
        
        # Group by type
        by_prefix = {}
        for o in objects:
            by_prefix.setdefault(o['prefix'], []).append(o)
        
        for prefix, entries in sorted(by_prefix.items()):
            offsets = [e['offset'] for e in entries]
            if len(offsets) >= 2:
                spacings = [offsets[i+1] - offsets[i] for i in range(len(offsets)-1)]
                print(f"  {prefix}: {len(entries)} entries, spacings={spacings[:15]}")

def deep_hex_dump(filepath, start, length=128):
    """Hex dump a region of a file."""
    data = Path(filepath).read_bytes()
    chunk = data[start:start+length]
    lines = []
    for i in range(0, len(chunk), 16):
        hex_part = ' '.join(f'{b:02X}' for b in chunk[i:i+16])
        ascii_part = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk[i:i+16])
        lines.append(f"  {start+i:04X}: {hex_part:<48s} {ascii_part}")
    return '\n'.join(lines)

def full_structure_parse(filepath):
    """Attempt a complete sequential parse of a .q file."""
    data = Path(filepath).read_bytes()
    fname = Path(filepath).name
    print(f"\n{'='*80}")
    print(f"FULL SEQUENTIAL PARSE: {fname} ({len(data)} bytes)")
    print(f"{'='*80}")
    
    pos = 0
    # Header
    magic1 = data[0:4].decode('ascii', errors='replace')
    magic2 = data[8:12].decode('ascii', errors='replace')
    print(f"  Header: magic={magic1!r}/{magic2!r}")
    pos = 0x10
    
    # Strings
    quest_name, pos = read_cstr(data, pos)
    pattern_name, pos = read_cstr(data, pos)
    print(f"  Quest: {quest_name!r}, Pattern: {pattern_name!r}")
    print(f"  After strings: 0x{pos:04X}")
    
    # Hex dump the next 64 bytes to see the parameter block
    print(f"\n  Parameter block (0x{pos:04X} - 0x{pos+64:04X}):")
    print(deep_hex_dump(filepath, pos, 64))
    
    # Try to identify the "NONE" markers
    none_pos = data.find(b'NONE', pos)
    if none_pos >= 0:
        print(f"\n  'NONE' marker at 0x{none_pos:04X}")
        print(f"  Bytes between params start and NONE: {none_pos - pos}")
        # Dump the NONE area
        print(f"  Around NONE:")
        print(deep_hex_dump(filepath, none_pos - 4, 32))
        
        # After NONE there's typically "none\0" then some data
        pos2 = none_pos
        m1, pos2 = read_cstr(data, pos2)
        m2, pos2 = read_cstr(data, pos2)
        print(f"  Markers: {m1!r}, {m2!r}, then pos=0x{pos2:04X}")
        
        # Dump what follows
        print(f"\n  After NONE markers (0x{pos2:04X}):")
        print(deep_hex_dump(filepath, pos2, min(128, len(data) - pos2)))
    
    # Find first object and dump area before it
    for i in range(len(data) - 4):
        c = data[i:i+4]
        try:
            s = c.decode('ascii')
            if s[0:2] in ('BV', 'BB', 'AB') and s[2:4].isalnum():
                print(f"\n  First object ID '{s}' at 0x{i:04X}")
                print(f"  Context (20 bytes before to 40 after):")
                print(deep_hex_dump(filepath, max(0, i-20), 64))
                break
        except:
            continue

def compare_wrathofkrolm_and_myquest():
    """Compare WrathOfKrolm (known complex) with MyQuest (known simple) to understand structure."""
    files = [
        "MyQuest/Quest.q",
        "Quests/Krolm.q",
        "Quests/Brashnard.q",
        "Quests/fertile_plain.q",
        "Quests/barren_waste.q",
    ]
    
    parsed_files = []
    for f in files:
        fp = Path(f)
        if fp.exists():
            pf, raw = parse_q_file(fp)
            parsed_files.append(pf)
            print(f"\n{'─'*60}")
            print(f"File: {f} ({len(raw)} bytes)")
            print(f"  Magic: {pf['magic1']}, Quest: {pf['quest_name']}, Pattern: {pf['pattern_name']}")
            print(f"  Params: {pf['params']}")
            print(f"  Objects: {len(pf['objects'])} IDs found")
            by_type = {}
            for o in pf['objects']:
                by_type.setdefault(o['prefix'], []).append(o)
            for prefix, entries in sorted(by_type.items()):
                ids = [e['id'] for e in entries]
                print(f"    {prefix}: {len(entries)} — {ids[:8]}")
    
    return parsed_files

if __name__ == "__main__":
    os.chdir(Path(__file__).parent.parent)
    
    print("="*80)
    print("Q FILE FORMAT RESEARCH — Coordinate Cracking")
    print("="*80)
    
    # Phase 1: Overview of multiple files
    parsed_files = compare_wrathofkrolm_and_myquest()
    
    # Phase 2: Full sequential parse of key files
    for f in ["MyQuest/Quest.q", "Quests/Krolm.q", "Quests/fertile_plain.q"]:
        if Path(f).exists():
            full_structure_parse(f)
    
    # Phase 3: Coordinate analysis
    analyze_coordinate_candidates(parsed_files)
    
    # Phase 4: Entry structure analysis (spacings between objects)
    analyze_entry_structure(parsed_files)
