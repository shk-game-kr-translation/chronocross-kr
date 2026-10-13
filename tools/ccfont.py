"""Chrono Cross (RDE) DirectXTK spritefont reader/writer + Korean glyph generator.

File (MakeSpriteFont binary): "DXTKfont", u32 n, n x Glyph{u32 ch; RECT l,t,r,b (u32); f32 xoff, yoff, xadv},
f32 lineSpacing, u32 defaultChar, u32 w, h, DXGI format (115 = B4G4R4A4), u32 stride, u32 rows, pixels.
Pen advance = xoff + (r - l) + xadv (xadv is negative: it trims the outline/shadow padding).

Pixels are layer masks, recoloured by the game: R = fill, G = fill+outline, B = fill+outline+shadow, A = coverage.
  small_*  pixel font (16 px design grid upscaled x4.375), outline 1 grid px, shadow = outline shifted (+1,+1) px
  large_*  smooth font, outline ~5 px, shadow offset ~5 px
"""
import struct

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

SCALE_SMALL = 4.375


class SpriteFont:
    def __init__(self, data: bytes):
        assert data[:8] == b"DXTKfont"
        n = struct.unpack_from("<I", data, 8)[0]
        self.glyphs = {}
        for k in range(n):
            c, l, t, r, b = struct.unpack_from("<5I", data, 12 + 32 * k)
            xo, yo, xa = struct.unpack_from("<3f", data, 12 + 32 * k + 20)
            self.glyphs[c] = [l, t, r, b, xo, yo, xa]
        o = 12 + 32 * n
        self.line, self.default, w, h, self.fmt, stride, rows = struct.unpack_from("<fI5I", data, o)
        assert self.fmt == 115 and stride == w * 2 and rows == h
        o += 28
        self.tex = np.frombuffer(data, dtype="<u2", count=w * h, offset=o).reshape(h, w).copy()

    def dump(self) -> bytes:
        h, w = self.tex.shape
        out = [b"DXTKfont", struct.pack("<I", len(self.glyphs))]
        for c in sorted(self.glyphs):
            l, t, r, b, xo, yo, xa = self.glyphs[c]
            out.append(struct.pack("<5I3f", c, l, t, r, b, xo, yo, xa))
        out.append(struct.pack("<fI5I", self.line, self.default, w, h, self.fmt, w * 2, h))
        out.append(self.tex.astype("<u2").tobytes())
        return b"".join(out)

    def add(self, items, pad=1):
        """items: [(ch, layers uint16 array, xoff, yoff, xadv)] -> appended in shelf rows below the texture."""
        h, w = self.tex.shape
        rows, x, y, rowh = [], 0, h + pad, 0
        place = []
        for ch, img, xo, yo, xa in items:
            gh, gw = img.shape
            if x + gw + pad > w:
                x, y, rowh = 0, y + rowh + pad, 0
            place.append((ch, img, x, y, xo, yo, xa))
            x += gw + pad
            rowh = max(rowh, gh)
        newh = y + rowh + pad
        assert newh <= 16384, f"texture too tall ({newh}); widen it"
        tex = np.zeros((newh, w), dtype=np.uint16)
        tex[:h] = self.tex
        for ch, img, x, y, xo, yo, xa in place:
            gh, gw = img.shape
            tex[y:y + gh, x:x + gw] = img
            self.glyphs[ch] = [x, y, x + gw, y + gh, xo, yo, xa]
        self.tex = tex


def pack_layers(fill, outline, shadow):
    """float masks 0..1 (same shape) -> B4G4R4A4 uint16."""
    R = fill
    G = np.maximum(R, outline)
    B = np.maximum(G, shadow)
    A = B
    q = lambda m: np.clip(np.rint(m * 15), 0, 15).astype(np.uint16)
    return (q(A) << 12) | (q(R) << 8) | (q(G) << 4) | q(B)


def _dilate(m, r):
    """grayscale dilation with a disk of radius r (pixels)."""
    out = m.copy()
    ri = int(np.ceil(r))
    h, w = m.shape
    for dy in range(-ri, ri + 1):
        for dx in range(-ri, ri + 1):
            if dx * dx + dy * dy > r * r + 0.25:
                continue
            sh = np.zeros_like(m)
            ys, yd = (slice(0, h - dy), slice(dy, h)) if dy >= 0 else (slice(-dy, h), slice(0, h + dy))
            xs, xd = (slice(0, w - dx), slice(dx, w)) if dx >= 0 else (slice(-dx, w), slice(0, w + dx))
            sh[yd, xd] = m[ys, xs]
            np.maximum(out, sh, out=out)
    return out


def _shift(m, dx, dy):
    out = np.zeros_like(m)
    h, w = m.shape
    out[dy:, dx:] = m[:h - dy, :w - dx]
    return out


class SmallGlyphs:
    """Pixel glyphs from a bitmap-style TTF (NeoDunggeunmo, 16 px grid), upscaled like the game's small_* fonts."""

    def __init__(self, path, px=16, top=19.5, advance=None, italic=0.0):
        self.font = ImageFont.truetype(path, px)
        self.px, self.top, self.advance, self.italic = px, top, advance, italic

    def make(self, ch):
        px = self.px
        im = Image.new("L", (px + 4, px + 4))
        ImageDraw.Draw(im).text((1, 1), ch, font=self.font, fill=255)
        src = (np.asarray(im) > 127).astype(np.float32)
        ys, xs = np.nonzero(src)
        if len(xs) == 0:
            return None
        x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
        g = src[y0:y1 + 1, x0:x1 + 1]
        g = np.pad(g, ((1, 2), (1, 2)))                      # room for outline (1) + shadow (1)
        outline = _dilate(g, 1.5)                             # 8-neighbourhood
        shadow = _shift(outline, 1, 1)
        # upscale by 4.375 with the game's uneven 4/5 px pattern
        edges = lambda n: np.floor(np.arange(n + 1) * SCALE_SMALL).astype(int)
        ey, ex = edges(g.shape[0]), edges(g.shape[1])
        iy = np.repeat(np.arange(g.shape[0]), np.diff(ey))
        ix = np.repeat(np.arange(g.shape[1]), np.diff(ex))
        up = lambda m: m[np.ix_(iy, ix)]
        F, O, S = up(g), up(outline), up(shadow)
        if self.italic:
            F, O, S = (_shear(m, self.italic) for m in (F, O, S))
        img = pack_layers(F, O, S)
        # pen-relative placement: grid cell (1,1) of the render = pen origin
        xoff = (x0 - 1 - 1) * SCALE_SMALL + 4.375
        yoff = self.top + (y0 - 1 - 1) * SCALE_SMALL
        adv = self.advance if self.advance is not None else (px - 1) * SCALE_SMALL + 4
        xadv = adv - xoff - img.shape[1]
        return img, xoff, yoff, xadv


class LargeGlyphs:
    """Smooth glyphs (NanumSquareRound) with outline + shadow like the game's large_* fonts."""

    def __init__(self, path, size=74, top=10.0, outline=5.0, shadow=5, advance=None, italic=0.0, ss=4):
        self.font = ImageFont.truetype(path, size * ss)
        self.size, self.top, self.outline, self.shadow = size, top, outline, shadow
        self.advance, self.italic, self.ss = advance, italic, ss
        asc, desc = self.font.getmetrics()
        self.asc = asc / ss

    def make(self, ch):
        ss, size = self.ss, self.size
        cell = int(size * 1.6)
        im = Image.new("L", (cell * ss, cell * ss))
        ImageDraw.Draw(im).text((size // 4 * ss, size // 4 * ss), ch, font=self.font, fill=255)
        im = im.resize((cell, cell), Image.LANCZOS)
        F = np.asarray(im).astype(np.float32) / 255
        ys, xs = np.nonzero(F > 0.02)
        if len(xs) == 0:
            return None
        p = int(np.ceil(self.outline)) + self.shadow + 1
        x0, x1, y0, y1 = xs.min() - p, xs.max() + p + 1, ys.min() - p, ys.max() + p + 1
        F = F[max(y0, 0):y1, max(x0, 0):x1]
        O = _dilate(F, self.outline)
        S = _shift(O, self.shadow, self.shadow)
        if self.italic:
            F, O, S = (_shear(m, self.italic) for m in (F, O, S))
        img = pack_layers(F, O, S)
        origin = size // 4
        xoff = (x0 - origin) - (-self.outline) + 0.0
        xoff = float(x0 - origin) + 4.0
        yoff = self.top + float(y0 - origin)
        adv = self.advance if self.advance is not None else size + 2
        xadv = adv - xoff - img.shape[1]
        return img, xoff, yoff, xadv


def _shear(m, deg):
    """italic: shift rows right proportionally to height above the bottom."""
    h, w = m.shape
    k = np.tan(np.radians(deg))
    extra = int(np.ceil(h * k))
    out = np.zeros((h, w + extra), dtype=m.dtype)
    for y in range(h):
        s = (h - 1 - y) * k
        i, f = int(s), s - int(s)
        out[y, i:i + w] += m[y] * (1 - f)
        out[y, i + 1:i + 1 + w] += m[y] * f
    return np.clip(out, 0, 1)
