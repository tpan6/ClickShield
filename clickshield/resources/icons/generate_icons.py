"""
Generates tray icon PNGs using a proper shield shape.
Run once: python clickshield/resources/icons/generate_icons.py
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter


def _bezier3(t, p0, p1, p2):
    return (
        (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t ** 2 * p2[0],
        (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t ** 2 * p2[1],
    )


def _bezier4(t, p0, p1, p2, p3):
    return (
        (1 - t) ** 3 * p0[0] + 3 * (1 - t) ** 2 * t * p1[0] + 3 * (1 - t) * t ** 2 * p2[0] + t ** 3 * p3[0],
        (1 - t) ** 3 * p0[1] + 3 * (1 - t) ** 2 * t * p1[1] + 3 * (1 - t) * t ** 2 * p2[1] + t ** 3 * p3[1],
    )


def _shield_polygon(size: int, inset: float = 0.0) -> list[tuple[float, float]]:
    """
    Returns smooth polygon points for a heraldic shield at `size` x `size`.
    `inset` shrinks the shield inward (0.0 = full size, 0.12 = inner detail line).
    """
    pad = 0.08 + inset
    w = size * (1 - 2 * pad)
    h = size * (1 - 2 * pad)
    ox = size * pad
    oy = size * pad

    def pt(nx: float, ny: float) -> tuple[float, float]:
        return (ox + nx * w, oy + ny * h)

    steps = 48
    points: list[tuple[float, float]] = []

    # Top arch: left shoulder → slight peak at centre → right shoulder
    for i in range(steps + 1):
        t = i / steps
        points.append(_bezier3(t, pt(0.02, 0.22), pt(0.50, -0.04), pt(0.98, 0.22)))

    # Right side: shoulder → outward bow → bottom point
    for i in range(1, steps + 1):
        t = i / steps
        points.append(_bezier4(t, pt(0.98, 0.22), pt(1.05, 0.38), pt(0.82, 0.72), pt(0.50, 1.00)))

    # Left side: bottom point → outward bow → left shoulder
    for i in range(1, steps + 1):
        t = i / steps
        points.append(_bezier4(t, pt(0.50, 1.00), pt(0.18, 0.72), pt(-0.05, 0.38), pt(0.02, 0.22)))

    return points


def _make_icon(size: int, fill_rgb: tuple[int, int, int]) -> Image.Image:
    """Draws a shield icon at `size`×`size` with the given fill colour."""
    # Render at 4× for antialiasing then scale down
    scale = 4
    big = size * scale
    img = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    outer = _shield_polygon(big, inset=0.0)
    inner = _shield_polygon(big, inset=0.10)

    # Shadow / depth — slightly darker version offset down-right
    dark = tuple(max(0, c - 40) for c in fill_rgb)
    shadow_pts = [(x + big * 0.025, y + big * 0.025) for x, y in outer]
    draw.polygon(shadow_pts, fill=(*dark, 140))

    # Main fill
    draw.polygon(outer, fill=(*fill_rgb, 255))

    # Inner border line (white at ~40 % opacity for the "outline" detail)
    draw.polygon(inner, outline=(255, 255, 255, 100), width=max(2, big // 32))

    # Slight vignette gradient by drawing a semi-transparent dark top arc
    vignette = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    vd = ImageDraw.Draw(vignette)
    for i in range(big // 10):
        alpha = int(60 * (1 - i / (big / 10)))
        vd.polygon(_shield_polygon(big, inset=i / big), outline=(0, 0, 0, alpha), width=1)
    img = Image.alpha_composite(img, vignette)

    # Scale down with LANCZOS for crisp edges
    return img.resize((size, size), Image.LANCZOS)


VARIANTS = {
    "tray_normal.png":   (0x2E7D32,),   # green  — clean
    "tray_scanning.png": (0x1565C0,),   # blue   — scanning
    "tray_warning.png":  (0xE65100,),   # deep orange — low/medium
    "tray_danger.png":   (0xB71C1C,),   # red    — high / danger
}

out = Path(__file__).parent

for filename, (hex_color,) in VARIANTS.items():
    r = (hex_color >> 16) & 0xFF
    g = (hex_color >> 8) & 0xFF
    b = hex_color & 0xFF
    icon = _make_icon(64, (r, g, b))
    icon.save(out / filename)
    print(f"  {filename}")

# Also write a multi-resolution .ico for the app window / installer
sizes = [16, 24, 32, 48, 64, 128, 256]
frames = [_make_icon(s, (0x2E, 0x7D, 0x32)) for s in sizes]
frames[0].save(
    out / "clickshield.ico",
    format="ICO",
    append_images=frames[1:],
    sizes=[(s, s) for s in sizes],
)
print("  clickshield.ico")
print("Done.")
