"""Render a text line with a (patched) spritefont the way DirectXTK SpriteFont does, for visual checks.

  ccfont_preview.py <font.spritefont> <out.png> "<text>"
Colours: fill white, outline dark blue, shadow black (approximation of the game's text window).
"""
import sys

import numpy as np
from PIL import Image

from ccfont import SpriteFont


def render(sf, text, scale=1.0):
    lines = text.split("\n")
    W = int(max(len(l) for l in lines) * 110 + 100)
    H = int(sf.line * len(lines) + 120)
    canvas = np.zeros((H, W, 3), dtype=np.float32)
    canvas[:] = (0.15, 0.2, 0.45)
    for li, line in enumerate(lines):
        x, y = 20.0, 20.0 + li * sf.line
        for ch in line:
            g = sf.glyphs.get(ord(ch)) or sf.glyphs.get(sf.default)
            l, t, r, b, xo, yo, xa = g
            sub = sf.tex[t:b, l:r]
            R = ((sub >> 8) & 15) / 15
            G = ((sub >> 4) & 15) / 15
            B = (sub & 15) / 15
            px, py = int(round(x + xo)), int(round(y + yo))
            reg = canvas[py:py + sub.shape[0], px:px + sub.shape[1]]
            hh, ww = reg.shape[:2]
            R, G, B = R[:hh, :ww], G[:hh, :ww], B[:hh, :ww]
            sh = B - G
            ol = G - R
            for c, col in enumerate(((0, 0, 0), (0.05, 0.05, 0.2), (1, 1, 1))):
                pass
            reg[:] = reg * (1 - B[..., None]) + (np.array((0, 0, 0)) * sh[..., None]) + \
                (np.array((0.08, 0.08, 0.25)) * ol[..., None]) + (np.array((1, 1, 1)) * R[..., None])
            x += xo + (r - l) + xa
    return Image.fromarray((np.clip(canvas, 0, 1) * 255).astype(np.uint8))


if __name__ == "__main__":
    sf = SpriteFont(open(sys.argv[1], "rb").read())
    render(sf, sys.argv[3].replace("\\n", "\n")).save(sys.argv[2])
