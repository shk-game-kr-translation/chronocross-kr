"""Inspect the decrypted RD fonts: pixel grid, advance widths, outline style, cmap blocks."""
import collections
import sys

from fontTools.ttLib import TTFont
from fontTools.pens.boundsPen import BoundsPen

from paths import EXTRACTED

for name in sys.argv[1:] or ["ENFONT.ttf", "ENFONTI.ttf", "ENFONTN.ttf", "JPFONT.otf"]:
    p = EXTRACTED / "rd" / "fonts" / name
    if not p.exists():
        p = __import__("pathlib").Path(name)
    f = TTFont(p)
    cmap = f.getBestCmap()
    gs = f.getGlyphSet()
    hm = f["hmtx"].metrics
    print("==", p.name, f["name"].getDebugName(1), "/", f["name"].getDebugName(2), "upem", f["head"].unitsPerEm,
          "tables", sorted(f.keys()))
    os2 = f["OS/2"]
    print("  OS2 typoAsc", os2.sTypoAscender, "typoDesc", os2.sTypoDescender, "winAsc", os2.usWinAscent,
          "winDesc", os2.usWinDescent, "lineGap", f["hhea"].lineGap)
    for ch in "AMgi .,あ漢가":
        g = cmap.get(ord(ch))
        if g is None:
            continue
        bp = BoundsPen(gs)
        gs[g].draw(bp)
        print(f"  {ch!r} {g} adv={hm[g][0]} bounds={bp.bounds}")
    if "glyf" in f:
        xs = collections.Counter()
        for g in [cmap[ord(c)] for c in "ABCabc" if ord(c) in cmap]:
            gl = f["glyf"][g]
            if gl.numberOfContours > 0:
                for x, y in gl.getCoordinates(f["glyf"])[0]:
                    xs[x % 256] += 1
        print("  coord mod 256:", xs.most_common(5))
    blocks = collections.Counter()
    for c in cmap:
        blocks[c >> 8] += 1
    print("  cmap blocks:", sorted((hex(k << 8), v) for k, v in blocks.items())[:40])
    advs = collections.Counter(hm[cmap[c]][0] for c in cmap)
    print("  advances:", advs.most_common(8))
