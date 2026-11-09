#!/usr/bin/env python3
"""Rasterize web/icon.svg to the PNG sizes the manifest and index.html need.

No SVG library is available in this environment (no cairosvg, no ImageMagick,
no Inkscape), and the icon is just a handful of rectangles, so this redraws
the same shapes with Pillow instead of pulling in a renderer. If icon.svg's
shapes ever change, update RECTS/STROKE below to match.
"""
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).parent.parent
VIEWBOX = 512

BG = "#1E1320"
PANEL_FILL = "#2B1A2E"
PANEL_STROKE = "#46294A"
STROKE_WIDTH = 8
HEADER_FILL = "#FF2E88"
TEXT_FILL = "#F4EADF"
REWARD_FILL = "#F5B32E"

# (x, y, w, h) in the original 512x512 viewBox, drawn in this order.
RECTS = [
    (0, 0, 512, 512, BG, None),
    (48, 96, 416, 320, PANEL_FILL, PANEL_STROKE),
    (48, 96, 416, 34, HEADER_FILL, None),
    (88, 182, 264, 26, TEXT_FILL, None),
    (88, 232, 336, 26, TEXT_FILL, None),
    (88, 282, 208, 26, TEXT_FILL, None),
    (88, 340, 176, 26, REWARD_FILL, None),
]

SIZES = [192, 512, 180]


def render(size: int) -> Image.Image:
    scale = size / VIEWBOX
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    for x, y, w, h, fill, stroke in RECTS:
        box = [x * scale, y * scale, (x + w) * scale, (y + h) * scale]
        draw.rectangle(box, fill=fill)
        if stroke:
            sw = max(1, round(STROKE_WIDTH * scale))
            draw.rectangle(box, outline=stroke, width=sw)
    return img


def main() -> None:
    out_dir = ROOT / "web"
    for size in SIZES:
        img = render(size)
        path = out_dir / f"icon-{size}.png"
        img.save(path)
        print(f"wrote {path} ({size}x{size})")


if __name__ == "__main__":
    main()
