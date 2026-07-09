"""
ice_palette_analyzer.py - Find palettes with suitable ice/blue colors
=====================================================================
Scans all SPLT palettes in maindata.cam and ranks them by the number
of blue/cyan/white color entries available for ice sprite generation.

Usage:
    python ice_palette_analyzer.py [--cam Data/maindata.cam] [--top 10]
"""

import argparse
from pathlib import Path
from cam_reader import read_cam
from sprite_extractor import load_splt_palette, is_transparent_color


def classify_ice_color(r, g, b, white_threshold=200, sat_threshold=60):
    """
    Classify a palette color as ice-suitable.
    
    Ice colors are:
    - Blue-dominant: B > R and B > 100
    - Cyan: B > 100 and G > 100 and R < G
    - White/light: all channels > white_threshold
    
    Returns category string or None.
    """
    # Skip transparent/magic pink
    if is_transparent_color(r, g, b):
        return None
    # Skip black/very dark
    if r < 30 and g < 30 and b < 30:
        return None
    
    # White/near-white
    if r >= white_threshold and g >= white_threshold and b >= white_threshold:
        return "white"
    
    # Pure blue dominant (B significantly > R, B > G)
    if b > 100 and b > r + 30 and b >= g:
        return "blue"
    
    # Cyan (G and B high, R low)
    if b > 100 and g > 100 and r < g and b >= r + 30:
        return "cyan"
    
    # Light blue (high B, moderate G, lower R)
    if b > 150 and g > 80 and r < b - 30:
        return "light_blue"
    
    return None


def analyze_palette(palette):
    """
    Analyze a single palette for ice-suitable colors.
    Returns dict with counts and index lists per category.
    """
    results = {
        "blue": [],
        "cyan": [],
        "white": [],
        "light_blue": [],
    }
    
    for i, (r, g, b) in enumerate(palette):
        if i == 0:  # skip index 0 (transparent)
            continue
        cat = classify_ice_color(r, g, b)
        if cat:
            results[cat].append((i, r, g, b))
    
    return results


def main():
    parser = argparse.ArgumentParser(description="Find ice-suitable palettes in maindata.cam")
    parser.add_argument("--cam", default="Data/maindata.cam", help="Path to maindata.cam")
    parser.add_argument("--top", type=int, default=10, help="Show top N palettes")
    parser.add_argument("--detail", type=int, default=None,
                        help="Show full detail for a specific palette index")
    args = parser.parse_args()

    print(f"Loading {args.cam}...")
    with open(args.cam, "rb") as f:
        cam_data = f.read()

    sections = read_cam(cam_data)
    splt_section = sections[2]  # SPLT is section index 2
    total_palettes = len(splt_section.files)
    print(f"Found {total_palettes} SPLT palettes\n")

    if args.detail is not None:
        # Detailed view of one palette
        palette = load_splt_palette(cam_data, splt_section, args.detail)
        if palette is None:
            print(f"Failed to load palette {args.detail}")
            return
        
        results = analyze_palette(palette)
        total = sum(len(v) for v in results.values())
        print(f"Palette {args.detail}: {total} ice-suitable colors")
        for cat, entries in results.items():
            if entries:
                print(f"  {cat} ({len(entries)}):")
                for idx, r, g, b in entries:
                    print(f"    [{idx:3d}] RGB({r:3d}, {g:3d}, {b:3d})")
        return

    # Scan all palettes and rank
    rankings = []
    for pal_id in range(total_palettes):
        palette = load_splt_palette(cam_data, splt_section, pal_id)
        if palette is None:
            continue
        
        results = analyze_palette(palette)
        total_ice = sum(len(v) for v in results.values())
        n_blue = len(results["blue"])
        n_cyan = len(results["cyan"])
        n_white = len(results["white"])
        n_light = len(results["light_blue"])
        
        # Need at least 3 colors to be useful
        if total_ice >= 3:
            rankings.append((total_ice, pal_id, n_blue, n_cyan, n_white, n_light))

    rankings.sort(reverse=True)

    if not rankings:
        print("ERROR: No palette contains at least 3 ice-suitable colors!")
        return

    print(f"Top {args.top} palettes for ice sprites:\n")
    print(f"{'Rank':<5} {'PalID':<7} {'Total':<7} {'Blue':<6} {'Cyan':<6} {'White':<7} {'LightB':<7}")
    print("-" * 50)
    for rank, (total, pal_id, n_blue, n_cyan, n_white, n_light) in enumerate(rankings[:args.top], 1):
        print(f"{rank:<5} {pal_id:<7} {total:<7} {n_blue:<6} {n_cyan:<6} {n_white:<7} {n_light:<7}")

    print(f"\nUse --detail <pal_id> to see specific palette indices.")
    print(f"Example: python ice_palette_analyzer.py --detail {rankings[0][1]}")


if __name__ == "__main__":
    main()
