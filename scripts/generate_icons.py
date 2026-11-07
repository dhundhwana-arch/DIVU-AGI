#!/usr/bin/env python3
"""Generate the DIVU AI PWA icon set.

Deterministic, dependency-light (Pillow only) so the icons can be regenerated at any time:

    python scripts/generate_icons.py

Outputs PNG files into ``frontend/public/icons/`` at the sizes required by the web app
manifest, iOS home screen and Windows tiles.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "frontend" / "public" / "icons"

BRAND_START = (47, 155, 255)  # #2f9bff
BRAND_END = (139, 92, 246)  # #8b5cf6
BACKGROUND = (5, 6, 10)  # #05060a

SIZES = {
    "icon-192.png": 192,
    "icon-256.png": 256,
    "icon-384.png": 384,
    "icon-512.png": 512,
    "maskable-512.png": 512,
    "apple-touch-icon.png": 180,
}


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
        "/Library/Fonts/Arial Bold.ttf",
    ]
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _vertical_gradient(size: int, top: tuple[int, int, int], bottom: tuple[int, int, int]) -> Image.Image:
    gradient = Image.new("RGB", (1, size))
    draw = ImageDraw.Draw(gradient)
    for y in range(size):
        ratio = y / max(1, size - 1)
        draw.point(
            (0, y),
            fill=(
                int(top[0] + (bottom[0] - top[0]) * ratio),
                int(top[1] + (bottom[1] - top[1]) * ratio),
                int(top[2] + (bottom[2] - top[2]) * ratio),
            ),
        )
    return gradient.resize((size, size))


def _rounded_square(size: int, radius_ratio: float = 0.22) -> Image.Image:
    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle(
        [(0, 0), (size - 1, size - 1)], radius=int(size * radius_ratio), fill=255
    )
    return mask


def make_icon(size: int, *, maskable: bool = False) -> Image.Image:
    """Draw the DIVU AI mark: a gradient rounded square with a bold 'D'."""
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    pad_ratio = 0.16 if maskable else 0.0  # safe zone for Android adaptive masks
    padding = int(size * pad_ratio)
    inner = size - padding * 2

    gradient = _vertical_gradient(inner, BRAND_START, BRAND_END).convert("RGBA")
    if maskable:
        # Maskable icons must fill the full canvas; the gradient covers everything.
        gradient = _vertical_gradient(size, BRAND_START, BRAND_END).convert("RGBA")
        canvas.paste(gradient, (0, 0))
        canvas.putalpha(_rounded_square(size, radius_ratio=0.5))
    else:
        mask = _rounded_square(inner)
        tile = Image.new("RGBA", (inner, inner), (0, 0, 0, 0))
        tile.paste(gradient, (0, 0), mask)
        canvas.alpha_composite(tile, (padding, padding))

    # Subtle inner highlight for depth.
    glow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    glow_draw.ellipse(
        [-size * 0.25, -size * 0.45, size * 0.85, size * 0.35],
        fill=(255, 255, 255, 46),
    )
    glow = glow.filter(ImageFilter.GaussianBlur(size * 0.06))
    canvas.alpha_composite(glow)

    letter_size = int(size * (0.46 if maskable else 0.58))
    font = _load_font(letter_size)
    draw = ImageDraw.Draw(canvas)

    # Optical centring of the glyph inside the tile.
    box = draw.textbbox((0, 0), "D", font=font)
    text_width = box[2] - box[0]
    text_height = box[3] - box[1]
    x = (size - text_width) / 2 - box[0]
    y = (size - text_height) / 2 - box[1] - size * 0.02
    draw.text((x, y), "D", font=font, fill=(255, 255, 255, 255))
    return canvas


def make_favicon(size: int = 64) -> Image.Image:
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    gradient = _vertical_gradient(size, BRAND_START, BRAND_END).convert("RGBA")
    canvas.paste(gradient, (0, 0), _rounded_square(size))
    draw = ImageDraw.Draw(canvas)
    font = _load_font(int(size * 0.62))
    box = draw.textbbox((0, 0), "D", font=font)
    draw.text(
        ((size - (box[2] - box[0])) / 2 - box[0], (size - (box[3] - box[1])) / 2 - box[1]),
        "D",
        font=font,
        fill=(255, 255, 255, 255),
    )
    return canvas


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, size in SIZES.items():
        icon = make_icon(size, maskable=name.startswith("maskable"))
        icon.save(OUT_DIR / name, "PNG", optimize=True)
        print(f"wrote {OUT_DIR / name} ({size}x{size})")

    favicon = make_favicon(64)
    favicon.save(ROOT / "frontend" / "public" / "favicon.png", "PNG", optimize=True)
    favicon.save(
        ROOT / "frontend" / "public" / "favicon.ico",
        "ICO",
        sizes=[(16, 16), (32, 32), (48, 48), (64, 64)],
    )
    print("wrote favicon.png and favicon.ico")

    # A wide marketing card used for social sharing / install previews.
    card = Image.new("RGB", (1200, 630), BACKGROUND)
    draw = ImageDraw.Draw(card)
    gradient = _vertical_gradient(630, BRAND_START, BRAND_END).resize((1200, 630))
    overlay = Image.new("RGB", (1200, 630), (0, 0, 0))
    card = Image.blend(card, gradient, 0.35)
    card = Image.blend(card, overlay, 0.45)
    draw = ImageDraw.Draw(card)
    title_font = _load_font(96)
    sub_font = _load_font(40)
    mark = make_icon(180)
    card.paste(mark, (96, 150), mark)
    draw.text((320, 210), "DIVU AI", font=title_font, fill=(255, 255, 255))
    draw.text(
        (324, 330), "Beyond Conversations. Towards Intelligence.", font=sub_font, fill=(200, 220, 255)
    )
    draw.text((324, 400), "DIVYESH BAMBHANIYA — Founder & Creator", font=sub_font, fill=(160, 180, 210))
    card.save(ROOT / "frontend" / "public" / "og-cover.png", "PNG", optimize=True)
    print("wrote og-cover.png")


if __name__ == "__main__":
    main()
