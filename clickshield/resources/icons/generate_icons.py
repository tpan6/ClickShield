"""Run this script once to generate placeholder tray icons."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ICONS = {
    "tray_normal.png":   (0x2E7D32, "S"),   # green
    "tray_scanning.png": (0x1565C0, "S"),   # blue
    "tray_warning.png":  (0xF57F17, "S"),   # amber
    "tray_danger.png":   (0xB71C1C, "!"),   # red
}

out = Path(__file__).parent

for filename, (bg_color, letter) in ICONS.items():
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Draw shield shape (simplified as rounded rectangle)
    r, g, b = (bg_color >> 16) & 0xFF, (bg_color >> 8) & 0xFF, bg_color & 0xFF
    draw.rounded_rectangle([4, 4, 60, 60], radius=8, fill=(r, g, b, 255))
    # Letter
    draw.text((32, 32), letter, fill=(255, 255, 255, 255), anchor="mm")
    img = img.resize((32, 32), Image.LANCZOS)
    img.save(out / filename)
    print(f"Generated {filename}")

print("Done.")
