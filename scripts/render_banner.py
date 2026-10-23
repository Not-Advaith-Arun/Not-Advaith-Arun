"""Render a deterministic, seamless ASCII banner. Requires Pillow.

Run from any directory: python scripts/render_banner.py
All motion uses integer harmonics of one phase, including the grain. The
endpoint equals the first frame and is omitted to avoid a pause at the seam.
"""

from pathlib import Path
import math
import os

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
WIDTH, HEIGHT = 960, 300
FRAME_COUNT, DURATION_MS = 160, 80
TAU = math.tau
FONT_PATH = os.environ.get(
    "BANNER_FONT", "/usr/share/fonts/google-noto/NotoSansMono-Regular.ttf"
)


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


def frame(phase):
    image = Image.new("RGB", (WIDTH, HEIGHT), (13, 17, 23))
    draw = ImageDraw.Draw(image)
    # A restrained full-width field, swelling into an orbital sculpture at right.
    ramp = " .,:;+=xX#%@"
    glyph_font = font(12)
    for row in range(23):
        for col in range(116):
            px, py = 20 + col * 8, 14 + row * 12
            x, y = (px - 724) / 146, (py - 148) / 112
            radius = math.hypot(x, y)
            angle = math.atan2(y, x)
            boundary = 1.05 + 0.14 * math.sin(3 * angle + phase)
            envelope = max(0.0, min(1.0, (boundary - radius) * 4))
            noise = field(x, y, phase)
            density = max(0.0, min(1.0, 0.49 + noise * 0.48))
            ring = 0.5 + 0.5 * math.sin(radius * 11 - phase * 2 + noise)
            intensity = envelope * (0.20 + 0.80 * density) * (0.6 + 0.4 * ring)
            # Keep the left area quiet around the name.
            background = 0.022 * (0.5 + 0.5 * noise)
            brightness = max(background, intensity)
            index = min(len(ramp) - 1, int(density * (len(ramp) - 1)))
            if index == 0:
                continue
            color = tuple(int(a + (b - a) * brightness) for a, b in
                          zip((13, 17, 23), (203, 191, 230)))
            draw.text((px, py), ramp[index], font=glyph_font, fill=color)
    # Fixed scanlines keep the texture subtle and do not flicker.
    for y in range(0, HEIGHT, 4):
        draw.line((0, y, WIDTH, y), fill=(13, 17, 23), width=1)
    draw.text((40, 48), "ADVAITH ARUN", font=font(30), fill=(235, 237, 243))
    draw.text((42, 100), "Full-stack engineer", font=font(16), fill=(181, 172, 204))
    draw.line((42, 145, 84, 145), fill=(159, 143, 190), width=2)
    draw.text((42, 171), "interfaces / systems / intelligence", font=font(12), fill=(139, 148, 162))
    draw.text((42, 244), "NOT-ADVAITH-ARUN", font=font(10), fill=(101, 111, 127))
    draw.line((42, 279, 918, 279), fill=(37, 42, 53))
    return image


def main():
    assets = ROOT / "assets"
    assets.mkdir(exist_ok=True)
    # Shared palette avoids color shimmer between frames and keeps the GIF small.
    palette = Image.new("P", (1, 1))
    colors = [tuple(int(a + (b - a) * i / 239) for a, b in
                    zip((13, 17, 23), (203, 191, 230))) for i in range(240)]
    colors += [(235, 237, 243), (181, 172, 204), (159, 143, 190),
               (139, 148, 162), (101, 111, 127), (37, 42, 53)]
    colors += [(13, 17, 23)] * (256 - len(colors))
    palette.putpalette([component for color in colors for component in color])
    frames = []
    for index in range(FRAME_COUNT):
        rgb = frame(TAU * index / FRAME_COUNT)
        if index == 0:
            rgb.save(assets / "ascii-banner.png")
        frames.append(rgb.quantize(palette=palette, dither=Image.Dither.NONE))
    frames[0].save(assets / "ascii-banner.gif", save_all=True,
                   append_images=frames[1:], duration=DURATION_MS,
                   loop=0, optimize=True, disposal=1)
    print(f"Rendered {FRAME_COUNT} frames, {FRAME_COUNT * DURATION_MS / 1000}s loop")


if __name__ == "__main__":
    main()
