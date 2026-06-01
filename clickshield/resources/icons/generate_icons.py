"""
Generates tray icon PNGs from shield_source.png (black outline on white bg).
Run once: python clickshield/resources/icons/generate_icons.py
"""
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw


def _make_icon_from_source(source: Image.Image, size: int, fill_rgb: tuple[int, int, int]) -> Image.Image:
    scale = 4
    big = size * scale

    src = source.resize((big, big), Image.LANCZOS).convert("RGBA")
    data = np.array(src, dtype=np.float32)

    # Per-pixel darkness: 0 = pure white, 1 = pure black
    darkness = 1.0 - (data[:, :, 0] + data[:, :, 1] + data[:, :, 2]) / (3.0 * 255.0)

    # Flood-fill from top-left corner to identify exterior white pixels
    gray = src.convert("L")
    binary = gray.point(lambda x: 255 if x > 128 else 0).convert("RGB")
    ImageDraw.floodfill(binary, (0, 0), (255, 0, 0), thresh=50)
    bd = np.array(binary)
    exterior_mask = (bd[:, :, 0] > 200) & (bd[:, :, 1] == 0)  # flood-fill sentinel
    border_mask = (darkness > 0.25) & ~exterior_mask
    interior_mask = ~exterior_mask & ~border_mask

    r, g, b = fill_rgb
    dr, dg, db = max(0, r - 60), max(0, g - 60), max(0, b - 60)

    out = np.zeros((big, big, 4), dtype=np.uint8)
    out[interior_mask] = [r, g, b, 255]
    out[border_mask, 0] = dr
    out[border_mask, 1] = dg
    out[border_mask, 2] = db
    out[border_mask, 3] = np.clip(darkness[border_mask] * 255, 0, 255).astype(np.uint8)
    # exterior stays transparent (zeros)

    return Image.fromarray(out, "RGBA").resize((size, size), Image.LANCZOS)


VARIANTS = {
    "tray_normal.png":   (0x2E, 0x7D, 0x32),  # green  — clean
    "tray_scanning.png": (0x15, 0x65, 0xC0),  # blue   — scanning
    "tray_warning.png":  (0xE6, 0x51, 0x00),  # deep orange — warning
    "tray_danger.png":   (0xB7, 0x1C, 0x1C),  # red    — danger
}

out_dir = Path(__file__).parent
source_path = out_dir / "shield_source.png"

if not source_path.exists():
    raise FileNotFoundError(
        f"Missing {source_path}\n"
        "Save the shield image (black outline on white background) as shield_source.png "
        "in the icons directory, then re-run this script."
    )

source = Image.open(source_path)

for filename, fill_rgb in VARIANTS.items():
    icon = _make_icon_from_source(source, 64, fill_rgb)
    icon.save(out_dir / filename)
    print(f"  {filename}")

# Multi-resolution .ico
sizes = [16, 24, 32, 48, 64, 128, 256]
frames = [_make_icon_from_source(source, s, (0x2E, 0x7D, 0x32)) for s in sizes]
frames[0].save(
    out_dir / "clickshield.ico",
    format="ICO",
    append_images=frames[1:],
    sizes=[(s, s) for s in sizes],
)
print("  clickshield.ico")
print("Done.")
