from __future__ import annotations

import random
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
TARGETS = [
    (ROOT / "website" / "spiele" / "blockwelt-icon.png", 512),
    (ROOT / "website" / "spiele" / "blockwelt-icon-192.png", 192),
    (ROOT / "backend" / "app" / "static" / "blockwelt-icon.png", 256),
]

GRASS_LIGHT = (143, 208, 90)
GRASS_DARK = (95, 156, 56)
DIRT_LEFT = (109, 79, 52)
DIRT_RIGHT = (138, 101, 68)
GOLD = (212, 175, 55)
GOLD_LIGHT = (251, 234, 166)
GOLD_DARK = (138, 106, 28)
BG_TOP = (27, 36, 64)
BG_BOTTOM = (8, 10, 20)


def _blend(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def draw_icon(size: int) -> Image.Image:
    scale = 4
    px = size * scale
    img = Image.new("RGBA", (px, px), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    for y in range(px):
        draw.line([(0, y), (px, y)], fill=_blend(BG_TOP, BG_BOTTOM, y / max(1, px - 1)))

    mask = Image.new("L", (px, px), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, px - 1, px - 1], radius=int(px * 0.22), fill=255)
    img.putalpha(mask)

    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle(
        [int(px * 0.014), int(px * 0.014), px - int(px * 0.014), px - int(px * 0.014)],
        radius=int(px * 0.207),
        outline=GOLD + (220,),
        width=int(px * 0.028),
    )

    unit = px / 256.0
    side = 74 * unit
    cx, cy = px / 2, 150 * unit
    depth = side * 0.82

    top = [(cx, cy - side / 2), (cx + side, cy), (cx, cy + side / 2), (cx - side, cy)]
    left = [(cx - side, cy), (cx, cy + side / 2), (cx, cy + side / 2 + depth), (cx - side, cy + depth)]
    right = [(cx + side, cy), (cx, cy + side / 2), (cx, cy + side / 2 + depth), (cx + side, cy + depth)]

    draw.polygon(left, fill=DIRT_LEFT)
    draw.polygon(right, fill=DIRT_RIGHT)
    draw.polygon(top, fill=GRASS_DARK)

    gmask = Image.new("L", (px, px), 0)
    ImageDraw.Draw(gmask).polygon(top, fill=255)

    layer = Image.new("RGBA", (px, px), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer, "RGBA")
    steps = 320
    for i in range(steps + 1):
        t = i / steps
        a = (top[0][0] + (top[1][0] - top[0][0]) * t, top[0][1] + (top[1][1] - top[0][1]) * t)
        b = (top[3][0] + (top[2][0] - top[3][0]) * t, top[3][1] + (top[2][1] - top[3][1]) * t)
        ld.line([a, b], fill=_blend(GRASS_LIGHT, GRASS_DARK, t), width=max(2, int(unit * 4)))
    rng = random.Random(1337)
    for _ in range(90):
        u, v = rng.random(), rng.random()
        sx = cx + (u - v) * side * 0.94
        sy = cy + (u + v - 1) * side / 2 * 0.94
        tone = (63, 111, 38, 70) if rng.random() < 0.5 else (176, 226, 124, 70)
        ld.rectangle([sx, sy, sx + unit * 4, sy + unit * 3], fill=tone)
    layer.putalpha(ImageChops.multiply(layer.getchannel("A"), gmask))
    img = Image.alpha_composite(img, layer)

    draw = ImageDraw.Draw(img, "RGBA")
    draw.polygon(
        [(cx - side, cy), (cx, cy + side / 2), (cx, cy + side / 2 + 11 * unit), (cx - side, cy + 11 * unit)],
        fill=(120, 190, 80, 190),
    )
    draw.polygon(
        [(cx + side, cy), (cx, cy + side / 2), (cx, cy + side / 2 + 11 * unit), (cx + side, cy + 11 * unit)],
        fill=(140, 205, 95, 150),
    )
    edge = (0, 0, 0, 110)
    width = max(1, int(unit * 3))
    draw.line([(cx, cy + side / 2), (cx, cy + side / 2 + depth)], fill=edge, width=width)
    draw.line([(cx - side, cy), (cx, cy + side / 2)], fill=edge, width=width)
    draw.line([(cx + side, cy), (cx, cy + side / 2)], fill=edge, width=width)

    gy = cy - side / 2 - 42 * unit
    gem = [(cx, gy - 26 * unit), (cx + 21 * unit, gy), (cx, gy + 26 * unit), (cx - 21 * unit, gy)]
    draw.polygon(gem, fill=GOLD)
    draw.polygon([(cx, gy - 26 * unit), (cx + 21 * unit, gy), (cx, gy)], fill=GOLD_DARK)
    draw.polygon(
        [(cx, gy - 26 * unit), (cx + 9 * unit, gy - 8 * unit), (cx, gy + 2 * unit), (cx - 9 * unit, gy - 8 * unit)],
        fill=GOLD_LIGHT + (210,),
    )

    return img.resize((size, size), Image.LANCZOS)


def main() -> int:
    for path, size in TARGETS:
        path.parent.mkdir(parents=True, exist_ok=True)
        draw_icon(size).save(path, "PNG", optimize=True)
        print(f"{path.relative_to(ROOT)}  {size}x{size}  {path.stat().st_size} Bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
