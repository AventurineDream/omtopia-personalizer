#!/usr/bin/env python3
# Dotify: renders an image as an LED dot matrix (NIHIL wallpapers).
#
# Based on theme/dotmatrix.py from NIHIL by Pol Iglesias (poligle), MIT —
# https://github.com/poligle/Nihil-Shell. See NOTICE.
#
#   dotify.py SOURCE OUT.png [--size 2880x1800] [--pitch 18] [--tint '#F2F2F2']
#   dotify.py --glyph '' OUT.png --font 'JetBrainsMono Nerd Font'   # a glyph/text in dots
#
# Without --size the picture is made for the largest monitor Hyprland reports, in
# physical pixels, and the pitch is multiplied by its scale — so every dot lands
# on exact pixels. Each cell gets:
#   - an "off" LED (dark grey), so the matrix texture is always visible;
#   - a lit LED whose radius and brightness grow with the cell luminance.
# The black point is raised so the sky stays off, and isolated peaks (stars)
# light their cell even when the cell average is dark.

import argparse
import json
import os
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont


def cover(img, width, height):
    scale = max(width / img.width, height / img.height)
    img = img.resize((round(img.width * scale), round(img.height * scale)), Image.LANCZOS)
    left = (img.width - width) // 2
    top = (img.height - height) // 2
    return img.crop((left, top, left + width, top + height))


def luminance(img, stretch=True):
    rgb = np.asarray(img.convert("RGB"), dtype=np.float32) / 255.0
    lum = 0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1] + 0.0722 * rgb[..., 2]
    if not stretch:
        return lum
    low, high = np.percentile(lum, [2.0, 99.7])
    return np.clip((lum - low) / max(high - low, 1e-6), 0.0, 1.0)


def render(lum, width, height, pitch, supersample=3, gamma=1.25,
           black=0.10, star=0.55, star_gain=0.9, off_level=0.07):
    cols, rows = width // pitch, height // pitch
    ox, oy = (width - cols * pitch) // 2, (height - rows * pitch) // 2
    cells = lum[oy:oy + rows * pitch, ox:ox + cols * pitch].reshape(rows, pitch, cols, pitch)

    level = np.clip((cells.mean(axis=(1, 3)) - black) / max(1.0 - black, 1e-6), 0.0, 1.0) ** gamma
    if star_gain > 0.0 and star < 1.0:
        stars = np.clip((cells.max(axis=(1, 3)) - star) / max(1.0 - star, 1e-6), 0.0, 1.0)
        level = np.maximum(level, star_gain * stars)

    s = supersample
    step = pitch * s
    canvas = Image.new("L", (width * s, height * s), 0)
    draw = ImageDraw.Draw(canvas)
    r_max, r_off = 0.44 * step, 0.16 * step
    off = round(255 * off_level)

    for j in range(rows):
        cy = oy * s + j * step + step / 2
        for i in range(cols):
            cx = ox * s + i * step + step / 2
            if off > 0:
                draw.ellipse((cx - r_off, cy - r_off, cx + r_off, cy + r_off), fill=off)
            v = float(level[j, i])
            if v <= 0.02:
                continue
            radius = r_max * (0.25 + 0.75 * np.sqrt(v))
            grey = round(30 + 206 * v)
            if grey > off:
                draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=grey)

    return canvas.resize((width, height), Image.LANCZOS)


def tinted(mask, tint, background):
    """Grey mask → RGB: 0 is the background, 255 the tint."""
    fg = Image.new("RGB", mask.size, tint)
    bg = Image.new("RGB", mask.size, background)
    return Image.composite(fg, bg, mask)


def glyph_image(text, font_name, width, height, fill=0.42):
    """White text centred on black, `fill` of the shorter side tall."""
    path = font_name
    if not os.path.isfile(path):
        try:
            path = subprocess.run(["fc-match", "-f", "%{file}", font_name],
                                  capture_output=True, text=True, check=True).stdout.strip()
        except (OSError, subprocess.CalledProcessError):
            path = ""
    size = round(min(width, height) * fill)
    font = ImageFont.truetype(path, size) if path else ImageFont.load_default(size)
    img = Image.new("L", (width, height), 0)
    draw = ImageDraw.Draw(img)
    box = draw.textbbox((0, 0), text, font=font)
    x = (width - (box[2] - box[0])) / 2 - box[0]
    y = (height - (box[3] - box[1])) / 2 - box[1]
    draw.text((x, y), text, font=font, fill=255)
    return img


def largest_monitor():
    try:
        out = subprocess.run(["hyprctl", "monitors", "-j"], capture_output=True, text=True, check=True).stdout
        mons = json.loads(out)
    except (OSError, subprocess.CalledProcessError, ValueError):
        return None
    if not mons:
        return None
    m = max(mons, key=lambda m: m["width"] * m["height"])
    w, h = m["width"], m["height"]
    if m.get("transform", 0) % 2 == 1:
        w, h = h, w
    return w, h, float(m.get("scale", 1.0))


def parse_color(value):
    value = value.strip().lstrip("#")
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


def main():
    p = argparse.ArgumentParser(description="Render an image (or a glyph) as an LED dot matrix")
    p.add_argument("source", nargs="?", help="image file (omit with --glyph)")
    p.add_argument("out", help="output .png")
    p.add_argument("--glyph", help="text/glyph to draw instead of an image, e.g. the Arch logo ")
    p.add_argument("--font", default="JetBrainsMono Nerd Font", help="font for --glyph (name or file)")
    p.add_argument("--size", help="WIDTHxHEIGHT in pixels (default: largest monitor)")
    p.add_argument("--pitch", type=float, default=9, help="dot pitch in logical px (× monitor scale), default 9")
    p.add_argument("--gamma", type=float, default=1.25, help="brightness curve gamma (lower = brighter), default 1.25")
    p.add_argument("--tint", default="#FFFFFF", help="colour of a fully lit LED, default white")
    p.add_argument("--background", default="#000000", help="colour between the LEDs, default black")
    p.add_argument("--off", type=float, default=0.07, help="brightness of switched-off LEDs 0…0.3, default 0.07")
    args = p.parse_args()

    if not args.glyph and not args.source:
        p.error("SOURCE or --glyph is required")

    scale = 1.0
    if args.size:
        width, height = (int(v) for v in args.size.lower().split("x"))
    else:
        mon = largest_monitor()
        if mon:
            width, height, scale = mon
        else:
            width, height = 1920, 1080
    pitch = max(3, round(args.pitch * scale))

    if args.glyph:
        lum = luminance(glyph_image(args.glyph, args.font, width, height), stretch=False)
        mask = render(lum, width, height, pitch, gamma=args.gamma, black=0.0, star=1.0, star_gain=0.0, off_level=args.off)
    else:
        source = Image.open(args.source)
        source.load()
        lum = luminance(cover(source, width, height))
        mask = render(lum, width, height, pitch, gamma=args.gamma, off_level=args.off)

    image = tinted(mask, parse_color(args.tint), parse_color(args.background))
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    image.save(args.out, optimize=True)
    print(args.out)


if __name__ == "__main__":
    sys.exit(main())
