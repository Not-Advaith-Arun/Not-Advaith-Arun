"""Render a monochrome, seamless geometric-noise banner with Pillow.

Inspired by the desktop wallpaper's layered, cell-quantized noise and symbol
atlas. Shapes are drawn here from primitives; no wallpaper assets are bundled.
Run: python scripts/render_banner.py
"""

from functools import lru_cache
from pathlib import Path
import math

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
CELL = 16
WIDTH, HEIGHT = 960, 352
FRAME_COUNT, DURATION_MS = 300, 60
ASSET_NAME = "mono-flow-v4"


def fade(t):
    return t * t * t * (t * (t * 6 - 15) + 10)


@lru_cache(maxsize=None)
def lattice(x, y, z, w):
    h = (x * 374761393 + y * 668265263 + z * 2147483647 + w * 1274126177) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((h ^ (h >> 16)) & 0xFFFFFFFF) / 0xFFFFFFFF


def noise(x, y, z, w):
    coords = (x, y, z, w)
    origins = tuple(math.floor(v) for v in coords)
    fractions = tuple(fade(v - origin) for v, origin in zip(coords, origins))
    result = 0.0
    for corner in range(16):
        offsets = tuple((corner >> axis) & 1 for axis in range(4))
        weight = math.prod(f if offset else 1 - f for f, offset in zip(fractions, offsets))
        result += lattice(*(origin + offset for origin, offset in zip(origins, offsets))) * weight
    return result


@lru_cache(maxsize=None)
def symbol(index):
    # Supersampling keeps small geometric strokes clean at profile width.
    scale = 3
    mask = Image.new("L", (CELL * scale, CELL * scale))
    d = ImageDraw.Draw(mask)
    def line(points, width=1.1):
        d.line([(round(x * scale), round(y * scale)) for x, y in points],
               fill=255, width=max(1, round(width * scale)))
    def ellipse(box, fill=None, width=1.1):
        d.ellipse(tuple(round(v * scale) for v in box), fill=fill,
                  outline=255 if fill is None else None, width=round(width * scale))
    if index == 1:
        ellipse((7, 7, 8.5, 8.5), fill=255)
    elif index == 2:
        line(((6, 10), (10, 6)))
    elif index == 3:
        line(((5, 5), (11, 11))); line(((11, 5), (5, 11)))
    elif index == 4:
        line(((8, 4), (8, 12))); line(((4, 8), (12, 8)))
    elif index == 5:
        for x, y in ((4, 4), (10, 4), (4, 10), (10, 10)):
            ellipse((x, y, x + 1.6, y + 1.6), fill=255)
    elif index == 6:
        ellipse((3.5, 3.5, 12.5, 12.5)); ellipse((7, 7, 9, 9), fill=255)
    elif index == 7:
        line(((8, 2.5), (12.8, 5.2), (12.8, 10.8), (8, 13.5), (3.2, 10.8),
              (3.2, 5.2), (8, 2.5)))
        ellipse((5.5, 5.5, 10.5, 10.5))
    elif index == 8:
        for x, y in ((5, 5), (11, 5), (5, 11), (11, 11)):
            line(((x - 1.6, y), (x + 1.6, y)))
            line(((x, y - 1.6), (x, y + 1.6)))
    elif index == 9:
        ellipse((2.5, 2.5, 13.5, 13.5)); ellipse((5.5, 5.5, 10.5, 10.5))
    elif index == 10:
        for box in ((3, 3, 8, 8), (8, 3, 13, 8), (3, 8, 8, 13), (8, 8, 13, 13)):
            ellipse(box, fill=255)
    elif index == 11:
        d.rounded_rectangle((8, 8, 40, 40), radius=4, fill=255)
        d.ellipse((17, 17, 31, 31), fill=0)
    return mask.resize((CELL, CELL), Image.Resampling.LANCZOS)


@lru_cache(maxsize=384)
def transition(index, step):
    # Cross-fade shapes instead of snapping between discrete noise buckets.
    return Image.blend(symbol(index), symbol(min(11, index + 1)), step / 24)


def frame(phase):
    phase %= math.tau
    mask = Image.new("L", (WIDTH, HEIGHT), 0)
    # A circular path through four-dimensional noise has no temporal reset or
    # synchronized zero-velocity time slices. The spatial drift also never stops.
    z, w = 2.2 + 1.4 * math.cos(phase), 2.2 + 1.4 * math.sin(phase)
    drift_x, drift_y = 0.65 * math.sin(phase), 0.65 * math.cos(phase)
    samples = {}
    for row in range(HEIGHT // CELL):
        for col in range(WIDTH // CELL):
            value = 0.0
            for layer in range(4):
                span = 2 ** layer
                x = (math.floor(col / span) + 0.5) * span / 6.5 + drift_x
                y = (math.floor(row / span) + 0.5) * span / 6.5 + drift_y
                if (x, y) not in samples:
                    samples[x, y] = noise(x, y, z, w)
                value += samples[x, y] / 4
            value = max(0.0, min(1.0, (value - 0.5) * 1.85 + 0.5)) * 11
            index = min(11, int(value))
            step = round((value - index) * 24)
            mask.paste(transition(index, step), (col * CELL, row * CELL))
    rgba = Image.new("RGBA", mask.size, (210, 210, 210, 0))
    rgba.putalpha(mask)
    return rgba


def gif_frame(rgba):
    # GIF has binary alpha: use one neutral ink and a transparent index. This
    # avoids a black matte or dark antialiasing halo on the profile background.
    alpha = rgba.getchannel("A")
    indexed = alpha.point(lambda a: 0 if a < 96 else 1)
    output = Image.new("P", rgba.size)
    output.putdata(indexed.get_flattened_data())
    output.putpalette([0, 0, 0, 210, 210, 210] + [0] * 762)
    output.info["transparency"] = 0
    return output


def main():
    assets = ROOT / "assets"
    assets.mkdir(exist_ok=True)
    frames = []
    for index in range(FRAME_COUNT):
        rendered = frame(math.tau * index / FRAME_COUNT)
        if index == 0:
            rendered.save(assets / f"{ASSET_NAME}.png")
        frames.append(gif_frame(rendered))
    frames[0].save(assets / f"{ASSET_NAME}.gif", save_all=True,
                   append_images=frames[1:], duration=DURATION_MS,
                   loop=0, optimize=False, disposal=2, transparency=0)
    print(f"Rendered {FRAME_COUNT} frames, {FRAME_COUNT * DURATION_MS / 1000}s loop")


if __name__ == "__main__":
    main()
