"""Render a deterministic, seamless ASCII banner. Requires Pillow.

Run from any directory: python scripts/render_banner.py
All motion uses integer harmonics of one phase, including the grain. The
endpoint equals the first frame and is omitted to avoid a pause at the seam.
"""

from pathlib import Path
import math
import os
import colorsys
from functools import lru_cache

from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
WIDTH, HEIGHT = 960, 360
FRAME_COUNT, DURATION_MS = 160, 80
TAU = math.tau
FONT_PATH = os.environ.get(
    "BANNER_FONT", "/usr/share/fonts/google-noto/NotoSansMono-Regular.ttf"
)


@lru_cache
def font(size):
    return ImageFont.truetype(FONT_PATH, size)


def field(x, y, phase):
    """Periodic domain warping, interference, and fine grain."""
    u = x + 0.30 * math.sin(y * 2.4 + phase)
    v = y + 0.26 * math.cos(x * 2.0 - phase)
    return (
        0.53 * math.sin(u * 3.1 + math.cos(v * 2.7 + phase))
        + 0.28 * math.cos(v * 4.2 - phase + math.sin(u * 2.0))
        + 0.14 * math.sin(u * 8.0 + v * 5.0 + phase * 2)
        + 0.05 * math.cos(x * 79 + y * 113 + phase * 3)
    )


RAMP = " .,:;+=xX#%@"
BACKGROUND = (13, 17, 23)


@lru_cache
def glyph(character):
    mask = Image.new("L", (8, 12))
    ImageDraw.Draw(mask).text((0, -2), character, font=font(13), fill=255)
    return mask


def frame(phase):
    image = Image.new("RGB", (WIDTH, HEIGHT), BACKGROUND)
    # An elliptical, breathing noise sculpture occupies the entire panel.
    for row in range(29):
        for col in range(119):
            px, py = 4 + col * 8, 6 + row * 12
            x, y = (px - 480) / 425, (py - 180) / 145
            radius, angle = math.hypot(x, y), math.atan2(y, x)
            noise = field(x * 1.35, y * 1.1, phase)
            edge = 1.04 + 0.09 * math.sin(3 * angle + phase)
            envelope = max(0.0, min(1.0, (edge - radius) * 7))
            # Integer harmonics give circulating bands and expanding ripples
            # without a reset or a random discontinuity at the GIF seam.
            spiral = 0.5 + 0.5 * math.sin(radius * 15 - phase * 2 + angle * 2 + noise * 2)
            ripple = max(0.0, math.cos(radius * 21 - phase * 3 + noise * 0.8)) ** 9
            density = max(0.0, min(1.0, 0.46 + noise * 0.36 + spiral * 0.18))
            brightness = envelope * (0.52 + density * 0.46 + spiral * 0.15 + ripple * 0.22)
            # Cyan, blue, violet, pink and warm coral flow slowly through the field.
            hue = (0.64 + angle / math.tau * 0.23 + 0.13 * math.sin(x * 2 + phase)
                   + 0.08 * noise) % 1.0
            tint = colorsys.hsv_to_rgb(hue, 0.48, 1.0)
            color = tuple(min(255, int(base + (255 * channel - base) * min(1, brightness)))
                          for base, channel in zip(BACKGROUND, tint))
            index = min(len(RAMP) - 1, int(density * (len(RAMP) - 1)))
            if envelope and index:
                image.paste(color, (px, py, px + 8, py + 12), glyph(RAMP[index]))
    # Soft phosphor bloom adds depth while preserving sharp individual glyphs.
    bloom = image.filter(ImageFilter.GaussianBlur(3))
    image = Image.blend(image, bloom, 0.09)
    draw = ImageDraw.Draw(image)
    name = "ADVAITH ARUN"
    name_font = font(38)
    box = draw.textbbox((0, 0), name, font=name_font)
    width = box[2] - box[0]
    position = ((WIDTH - width) // 2, (HEIGHT - 44) // 2 - box[1])
    # Local shadow, rather than a solid label, lets the sculpture remain full-bleed.
    shadow = Image.new("RGBA", image.size)
    sd = ImageDraw.Draw(shadow)
    sd.rounded_rectangle((position[0] - 24, 145, position[0] + width + 24, 212),
                         radius=26, fill=(13, 17, 23, 222))
    image = Image.alpha_composite(image.convert("RGBA"), shadow.filter(ImageFilter.GaussianBlur(16)))
    ImageDraw.Draw(image).text(position, name, font=name_font, fill=(246, 245, 255),
                               stroke_width=1, stroke_fill=(246, 245, 255))
    return image.convert("RGB")


def main():
    assets = ROOT / "assets"
    assets.mkdir(exist_ok=True)
    # Shared palette avoids color shimmer between frames and keeps the GIF small.
    palette = Image.new("P", (1, 1))
    colors = [BACKGROUND]
    # Shared multicolor palette prevents per-frame palette flashes.
    for hue_index in range(28):
        tint = colorsys.hsv_to_rgb(0.40 + hue_index * 0.54 / 27, 0.48, 1)
        for level in range(1, 10):
            colors.append(tuple(int(base + (255 * channel - base) * level / 9)
                                for base, channel in zip(BACKGROUND, tint)))
    colors += [(246, 245, 255), (190, 190, 205), (224, 223, 237)]
    palette.putpalette([component for color in colors for component in color])
    frames = []
    for index in range(FRAME_COUNT):
        rgb = frame(TAU * index / FRAME_COUNT)
        if index == 0:
            rgb.save(assets / "ascii-ripple-v2.png")
        frames.append(rgb.quantize(palette=palette, dither=Image.Dither.NONE))
    frames[0].save(assets / "ascii-ripple-v2.gif", save_all=True,
                   append_images=frames[1:], duration=DURATION_MS,
                   loop=0, optimize=True, disposal=1)
    print(f"Rendered {FRAME_COUNT} frames, {FRAME_COUNT * DURATION_MS / 1000}s loop")


if __name__ == "__main__":
    main()
