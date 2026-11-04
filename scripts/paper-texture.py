#!/usr/bin/env python3
# Бесшовная текстура бумаги для стиля Paper: textures/paper.png (512×512, RGBA).
# Рисует только зерно и волокна — тёмные и светлые крапинки с альфой на прозрачном фоне,
# поэтому ложится поверх любого цвета панели (светлая тема — бумага, тёмная — крафт).
# Бесшовность: шум тайлится 3×3, размывается и вырезается центр.
#
#   python3 scripts/paper-texture.py [out.png] [seed]
import os
import random
import sys

from PIL import Image, ImageChops, ImageDraw, ImageFilter

SIZE = 512


def tiled_blur(img, radius):
    big = Image.new(img.mode, (SIZE * 3, SIZE * 3))
    for i in range(3):
        for j in range(3):
            big.paste(img, (i * SIZE, j * SIZE))
    big = big.filter(ImageFilter.GaussianBlur(radius))
    return big.crop((SIZE, SIZE, SIZE * 2, SIZE * 2))


def noise(rng, radius):
    img = Image.frombytes("L", (SIZE, SIZE), bytes(rng.randrange(256) for _ in range(SIZE * SIZE)))
    return tiled_blur(img, radius)


def fibers(rng, count):
    # Волокна: короткие изогнутые штрихи, рисуются с переносом через край.
    img = Image.new("L", (SIZE, SIZE), 0)
    d = ImageDraw.Draw(img)
    for _ in range(count):
        x, y = rng.uniform(0, SIZE), rng.uniform(0, SIZE)
        dx, dy = rng.uniform(-1, 1), rng.uniform(-1, 1)
        pts = []
        for _ in range(rng.randint(6, 18)):
            pts.append((x, y))
            dx += rng.uniform(-0.35, 0.35)
            dy += rng.uniform(-0.35, 0.35)
            x += dx * 3
            y += dy * 3
        shade = rng.randint(18, 45)
        for ox in (-SIZE, 0, SIZE):
            for oy in (-SIZE, 0, SIZE):
                d.line([(px + ox, py + oy) for px, py in pts], fill=shade, width=1)
    return tiled_blur(img, 0.6)


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "..", "textures", "paper.png")
    rng = random.Random(int(sys.argv[2]) if len(sys.argv) > 2 else 7)

    # Мягкие пятна (неравномерная плотность бумаги) + мелкое зерно.
    blotch = noise(rng, 22).point(lambda v: max(0, (v - 122) * 4))
    grain = noise(rng, 0.7).point(lambda v: max(0, (v - 165) * 2))
    dark = ImageChops.add(ImageChops.add(blotch.point(lambda v: v // 4), grain.point(lambda v: v // 3)), fibers(rng, 90))
    light = noise(rng, 0.8).point(lambda v: max(0, (v - 175) * 2))

    # paper.png — для светлых панелей: тёмные чернила зерна и волокон + редкие светлые блики.
    # paper-dark.png — для тёмных: те же маски светлыми чернилами (крафт / грифельная бумага).
    def build(ink, ink_k, glint, glint_k):
        tex = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
        tex.paste(Image.new("RGBA", (SIZE, SIZE), ink + (255,)), (0, 0), dark.point(lambda v: min(255, int(v * ink_k))))
        tex.alpha_composite(Image.merge("RGBA", tuple(Image.new("L", (SIZE, SIZE), c) for c in glint)
                                        + (light.point(lambda v: int(v * glint_k)),)))
        return tex

    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    build((40, 30, 20), 1.0, (255, 255, 255), 0.25).save(out, optimize=True)
    dark_out = out[:-4] + "-dark.png"
    build((235, 225, 205), 3.2, (0, 0, 0), 0.6).save(dark_out, optimize=True)
    print(out, dark_out)


if __name__ == "__main__":
    main()
