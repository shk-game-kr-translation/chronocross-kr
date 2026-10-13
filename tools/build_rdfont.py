"""Build Korean-capable Radical Dreamers fonts.

Each original font (decrypted from 10_extracted/rd/fonts) keeps its own Latin glyphs; Hangul glyphs are copied
from a donor TrueType font listed in 20_source/fonts/rdfont.json, scaled to the base unitsPerEm, optionally
sheared (italic) and shifted. Output: 30_build/rd/fonts/<NAME>.ttf (plain) and <NAME>.DAT (encrypted).

The repertoire is all 11,172 precomposed syllables + compatibility jamo + any extra code points from the profile,
so no translated character can be missing; tools/build_rd.py still checks every character against the cmap.
"""
import json
import math
import sys

from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont

from paths import BUILD, EXTRACTED, FONTS_SRC
import rdcrypt

REPERTOIRE = list(range(0xAC00, 0xD7A4)) + list(range(0x3131, 0x3164))


def merge(base_path, donor_path, prof):
    base = TTFont(base_path)
    donor = TTFont(donor_path)
    s = base["head"].unitsPerEm / donor["head"].unitsPerEm * prof.get("scale", 1.0)
    shear = math.tan(math.radians(prof.get("italic_deg", 0)))
    dx = prof.get("dx", 0) * base["head"].unitsPerEm
    dy = prof.get("dy", 0) * base["head"].unitsPerEm
    adv_scale = prof.get("advance", 1.0)
    dcmap = donor.getBestCmap()
    dgs = donor.getGlyphSet()
    dh = donor["hmtx"].metrics
    order = base.getGlyphOrder()
    glyf, hmtx = base["glyf"], base["hmtx"]
    cps = REPERTOIRE + [ord(c) for c in prof.get("extra", "")]
    added = {}
    bcmap = base.getBestCmap()
    for cp in cps:
        if cp in bcmap or cp in added:
            continue
        dname = dcmap.get(cp)
        if dname is None:
            sys.exit(f"donor lacks U+{cp:04X}")
        name = f"uni{cp:04X}"
        pen = TTGlyphPen(None)
        rec = DecomposingRecordingPen(dgs)  # donor composites are flattened into plain contours
        dgs[dname].draw(rec)
        # x' = s*x + shear*s*y + dx ; y' = s*y + dy
        rec.replay(TransformPen(pen, (s, 0, shear * s, s, dx, dy)))
        g = pen.glyph()
        glyf[name] = g
        adv = round(dh[dname][0] * s * adv_scale)
        g.recalcBounds(glyf)
        hmtx[name] = (adv, getattr(g, "xMin", 0))

        added[cp] = name
    order = glyf.glyphOrder  # glyf.__setitem__ appended the new names
    base.setGlyphOrder(order)
    for t in base["cmap"].tables:
        if t.isUnicode():
            if t.format == 4 and max(added) > 0xFFFF:
                continue
            t.cmap.update(added)
    # make sure a format-4 (BMP) unicode table exists so FreeType picks up the new code points
    base["maxp"].numGlyphs = len(order)
    if "post" in base:
        base["post"].formatType = 3.0  # drop glyph-name table (saves space, avoids name limits)
    return base, len(added)


def main():
    cfg = json.loads((FONTS_SRC / "rdfont.json").read_text(encoding="utf-8"))
    out = BUILD / "rd" / "fonts"
    out.mkdir(parents=True, exist_ok=True)
    for name, prof in cfg["fonts"].items():
        base = EXTRACTED / "rd" / "fonts" / (name + ".ttf")
        donor = FONTS_SRC / prof["donor"]
        f, n = merge(base, donor, prof)
        ttf = out / (name + ".ttf")
        f.save(ttf)
        data = ttf.read_bytes()
        enc = rdcrypt.encrypt(data)
        assert rdcrypt.decrypt(enc) == data
        (out / (name + ".DAT")).write_bytes(enc)
        chk = TTFont(ttf).getBestCmap()
        missing = [cp for cp in REPERTOIRE if cp not in chk]
        assert not missing, (name, len(missing))
        print(f"{name}: +{n} glyphs, {len(data)} bytes, donor {prof['donor']}")


if __name__ == "__main__":
    main()
