"""
ice_overlay_generator.py - Generate ice/frozen overlay sprite frames
====================================================================
Produces TILE-format binary files representing an ice crystalline
animation loop using colors from an existing SPLT palette.

The overlay renders ice crystals around the unit's bounding area,
with a shimmer/pulse effect across frames.

Usage:
    python ice_overlay_generator.py --cam Data/maindata.cam --palette-id 423 --output IceSpell/sprites/
    python ice_overlay_generator.py --cam Data/maindata.cam --palette-id 423 --output IceSpell/sprites/ --thaw

Requirements:
    pip install numpy
"""

import argparse
import math
import struct
import numpy as np
from pathlib import Path

from cam_reader import read_cam
from sprite_extractor import load_splt_palette, is_transparent_color
from sprite_injector import encode_tile


# Frame dimensions for the overlay (covers a standard unit sprite area)
FRAME_WIDTH = 48
FRAME_HEIGHT = 64


def get_ice_palette_indices(palette):
    """
    Extract usable ice color indices from a palette, sorted dark to light.
    Returns list of palette indices suitable for ice drawing.
    """
    ice_indices = []
    for i, (r, g, b) in enumerate(palette):
        if i == 0:
            continue
        if is_transparent_color(r, g, b):
            continue
        # Blue-dominant or white
        if (b > 100 and b > r + 20) or (r > 200 and g > 200 and b > 200):
            ice_indices.append(i)
    
    # Sort by brightness (dark to light)
    ice_indices.sort(key=lambda i: sum(palette[i]))
    return ice_indices


def generate_ice_crystal_points(frame_idx, num_frames):
    """
    Generate crystal point positions for a given frame.
    Points form an icy border around the unit with shimmer variation.
    """
    points = []
    phase = (frame_idx / num_frames) * 2 * math.pi
    
    # Ice crystals along left and right edges
    for y in range(8, FRAME_HEIGHT - 8, 3):
        # Left edge crystals
        x_offset = int(3 * math.sin(y * 0.15 + phase))
        lx = 4 + x_offset
        if 0 <= lx < FRAME_WIDTH:
            points.append((lx, y, 0.7 + 0.3 * math.sin(y * 0.2 + phase)))
        
        # Right edge crystals
        x_offset = int(3 * math.sin(y * 0.15 + phase + 1.5))
        rx = FRAME_WIDTH - 6 + x_offset
        if 0 <= rx < FRAME_WIDTH:
            points.append((rx, y, 0.7 + 0.3 * math.sin(y * 0.2 + phase + 1.0)))
    
    # Top crystals (icicle-like hanging down)
    for x in range(6, FRAME_WIDTH - 6, 4):
        length = int(5 + 3 * math.sin(x * 0.3 + phase))
        for dy in range(length):
            y = 3 + dy
            brightness = 1.0 - (dy / length) * 0.5
            brightness *= (0.8 + 0.2 * math.sin(x * 0.5 + phase + dy * 0.3))
            if 0 <= y < FRAME_HEIGHT:
                points.append((x, y, brightness))
    
    # Bottom frost crystals (growing up)
    for x in range(8, FRAME_WIDTH - 8, 5):
        length = int(3 + 2 * math.sin(x * 0.4 + phase + 2.0))
        for dy in range(length):
            y = FRAME_HEIGHT - 5 - dy
            brightness = 0.8 - (dy / max(length, 1)) * 0.3
            brightness *= (0.7 + 0.3 * math.cos(x * 0.3 + phase))
            if 0 <= y < FRAME_HEIGHT:
                points.append((x, y, brightness))
    
    # Scattered sparkle points (shimmer effect)
    np.random.seed(frame_idx * 7 + 42)
    for _ in range(12):
        sx = np.random.randint(6, FRAME_WIDTH - 6)
        sy = np.random.randint(6, FRAME_HEIGHT - 6)
        # Only sparkle near edges
        if 8 < sx < FRAME_WIDTH - 8 and 10 < sy < FRAME_HEIGHT - 10:
            continue
        brightness = 0.9 + 0.1 * math.sin(phase + sx + sy)
        points.append((sx, sy, brightness))
    
    return points


def generate_thaw_points(frame_idx, num_frames):
    """
    Generate shattering ice fragment positions for thaw animation.
    Fragments disperse outward and fade over frames.
    """
    points = []
    progress = frame_idx / (num_frames - 1)  # 0.0 = start, 1.0 = fully thawed
    
    np.random.seed(123)  # Consistent fragment positions
    num_fragments = int(30 * (1.0 - progress * 0.7))
    
    for i in range(num_fragments):
        # Start position (centered around unit)
        base_x = np.random.randint(8, FRAME_WIDTH - 8)
        base_y = np.random.randint(8, FRAME_HEIGHT - 8)
        
        # Fragment flies outward as animation progresses
        angle = np.random.uniform(0, 2 * math.pi)
        distance = progress * (10 + np.random.uniform(0, 15))
        
        fx = int(base_x + math.cos(angle) * distance)
        fy = int(base_y + math.sin(angle) * distance + progress * 3)  # gravity
        
        if not (0 <= fx < FRAME_WIDTH and 0 <= fy < FRAME_HEIGHT):
            continue
        
        # Brightness fades over time
        brightness = max(0.2, 1.0 - progress * 0.8)
        
        # Each fragment is a small cluster (1-3 pixels)
        frag_size = max(1, int(3 * (1.0 - progress)))
        for dx in range(frag_size):
            for dy in range(frag_size):
                px = fx + dx
                py = fy + dy
                if 0 <= px < FRAME_WIDTH and 0 <= py < FRAME_HEIGHT:
                    points.append((px, py, brightness * (1.0 - 0.2 * (dx + dy))))
    
    return points


def render_frame(points, ice_indices, palette):
    """
    Render a list of (x, y, brightness) points into a 2D pixel index array.
    brightness 0.0 = darkest ice color, 1.0 = brightest (white/light blue).
    """
    pixels = np.zeros((FRAME_HEIGHT, FRAME_WIDTH), dtype=np.uint8)
    
    num_colors = len(ice_indices)
    if num_colors == 0:
        return pixels
    
    for x, y, brightness in points:
        x, y = int(x), int(y)
        if not (0 <= x < FRAME_WIDTH and 0 <= y < FRAME_HEIGHT):
            continue
        
        # Map brightness to palette index (0.0 = dark, 1.0 = light)
        brightness = max(0.0, min(1.0, brightness))
        color_idx = int(brightness * (num_colors - 1))
        color_idx = max(0, min(num_colors - 1, color_idx))
        
        pal_index = ice_indices[color_idx]
        pixels[y, x] = pal_index
    
    return pixels


def generate_ice_frames(palette, palette_id, num_frames=6):
    """Generate ice overlay animation frames."""
    ice_indices = get_ice_palette_indices(palette)
    if len(ice_indices) < 3:
        raise ValueError(f"Palette has only {len(ice_indices)} ice colors (need >= 3)")
    
    print(f"  Using {len(ice_indices)} ice palette indices")
    
    frames = []
    for i in range(num_frames):
        points = generate_ice_crystal_points(i, num_frames)
        pixels = render_frame(points, ice_indices, palette)
        tile_data = encode_tile(pixels, palette_id)
        frames.append(tile_data)
        
        # Count non-transparent pixels
        opaque = np.count_nonzero(pixels)
        print(f"  Frame {i}: {opaque} opaque pixels, {len(tile_data)} bytes")
    
    return frames


def generate_thaw_frames(palette, palette_id, num_frames=5):
    """Generate thaw/shatter animation frames."""
    ice_indices = get_ice_palette_indices(palette)
    if len(ice_indices) < 3:
        raise ValueError(f"Palette has only {len(ice_indices)} ice colors (need >= 3)")
    
    print(f"  Using {len(ice_indices)} ice palette indices")
    
    frames = []
    for i in range(num_frames):
        points = generate_thaw_points(i, num_frames)
        pixels = render_frame(points, ice_indices, palette)
        tile_data = encode_tile(pixels, palette_id)
        frames.append(tile_data)
        
        opaque = np.count_nonzero(pixels)
        print(f"  Thaw frame {i}: {opaque} opaque pixels, {len(tile_data)} bytes")
    
    return frames


def verify_roundtrip(tile_data, frame_name):
    """Verify a generated TILE frame round-trips correctly."""
    from sprite_extractor import decode_tile
    
    decoded = decode_tile(tile_data)
    if decoded is None:
        print(f"  ✗ {frame_name}: Failed to decode!")
        return False
    
    # Re-encode from decoded pixels
    h, w = decoded["height"], decoded["width"]
    pixels = np.zeros((h, w), dtype=np.uint8)
    for y, segments in enumerate(decoded["rows"]):
        for x_start, px_list in segments:
            for dx, idx in enumerate(px_list):
                pixels[y, x_start + dx] = idx
    
    reencoded = encode_tile(pixels, decoded["palette_id"])
    
    if reencoded == tile_data:
        print(f"  ✓ {frame_name}: perfect round-trip")
        return True
    else:
        # Check if pixels match even if bytes differ
        decoded2 = decode_tile(reencoded)
        if decoded2 is None:
            print(f"  ✗ {frame_name}: re-encoded data failed to decode")
            return False
        
        pixels2 = np.zeros((decoded2["height"], decoded2["width"]), dtype=np.uint8)
        for y, segments in enumerate(decoded2["rows"]):
            for x_start, px_list in segments:
                for dx, idx in enumerate(px_list):
                    pixels2[y, x_start + dx] = idx
        
        if np.array_equal(pixels[:min(h, pixels2.shape[0]), :min(w, pixels2.shape[1])],
                         pixels2[:min(h, pixels2.shape[0]), :min(w, pixels2.shape[1])]):
            print(f"  ✓ {frame_name}: pixel-identical round-trip (different encoding)")
            return True
        else:
            print(f"  ✗ {frame_name}: pixel mismatch after round-trip!")
            return False


def main():
    parser = argparse.ArgumentParser(description="Generate ice overlay sprites")
    parser.add_argument("--cam", default="Data/maindata.cam", help="Path to maindata.cam")
    parser.add_argument("--palette-id", type=int, default=423,
                        help="SPLT palette index (default: 423, the ice/water palette)")
    parser.add_argument("--output", default="IceSpell/sprites",
                        help="Output directory for TILE files")
    parser.add_argument("--ice-frames", type=int, default=6,
                        help="Number of ice loop frames (4-8)")
    parser.add_argument("--thaw-frames", type=int, default=5,
                        help="Number of thaw frames (4-6)")
    parser.add_argument("--thaw", action="store_true",
                        help="Generate thaw animation instead of ice loop")
    parser.add_argument("--both", action="store_true",
                        help="Generate both ice loop and thaw animation")
    parser.add_argument("--verify", action="store_true", default=True,
                        help="Verify round-trip (default: on)")
    args = parser.parse_args()

    print(f"Loading {args.cam}...")
    with open(args.cam, "rb") as f:
        cam_data = f.read()

    sections = read_cam(cam_data)
    splt_section = sections[2]

    palette = load_splt_palette(cam_data, splt_section, args.palette_id)
    if palette is None:
        print(f"ERROR: Failed to load palette {args.palette_id}")
        return

    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    do_ice = not args.thaw or args.both
    do_thaw = args.thaw or args.both

    all_ok = True

    if do_ice:
        print(f"\nGenerating {args.ice_frames} ice overlay frames (palette {args.palette_id})...")
        ice_frames = generate_ice_frames(palette, args.palette_id, args.ice_frames)
        
        for i, frame_data in enumerate(ice_frames):
            path = out_dir / f"ice_frame_{i:02d}.tile"
            with open(path, "wb") as f:
                f.write(frame_data)
            
            if args.verify:
                if not verify_roundtrip(frame_data, f"ice_frame_{i:02d}"):
                    all_ok = False
        
        print(f"\n  Saved {len(ice_frames)} ice frames to {out_dir}/")

    if do_thaw:
        print(f"\nGenerating {args.thaw_frames} thaw/shatter frames (palette {args.palette_id})...")
        thaw_frames = generate_thaw_frames(palette, args.palette_id, args.thaw_frames)
        
        for i, frame_data in enumerate(thaw_frames):
            path = out_dir / f"thaw_frame_{i:02d}.tile"
            with open(path, "wb") as f:
                f.write(frame_data)
            
            if args.verify:
                if not verify_roundtrip(frame_data, f"thaw_frame_{i:02d}"):
                    all_ok = False
        
        print(f"\n  Saved {len(thaw_frames)} thaw frames to {out_dir}/")

    if all_ok:
        print("\n✓ All frames generated and verified successfully!")
    else:
        print("\n✗ Some frames failed round-trip verification!")


if __name__ == "__main__":
    main()
