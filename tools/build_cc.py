"""Product build for Chrono Cross: 00_original lang.dat + font.dat + ui.dat -> 30_build/data/ (same names)

- en.csv rows and the EN column of the tables are replaced by the sheets' Korean text (rows without ko keep English;
  --release refuses untranslated rows).
- Every character used by the Korean text that a Latin font (gn, gn_italic, bn, ci, ch; ui.dat's gnb for the ESC
  menu) lacks is rendered into it
  (pixel small_*: NeoDunggeunmo, smooth: NanumSquareRound EB), see glyph_maker() and tools/ccfont.py; every font gets
  '?' as default character so a missing glyph can no longer crash the game.
Checks (fail): source hashes (jh/eh), {} balance, tags must be known (seen in the row's EN/JP or in ALLOWED),
the message must end with the same terminator tags as EN, choice rows keep EN's option count.
Report (warn): lines wider than the widest EN line of the same row (pixel width with the small gn font).
"""
import json
import re
import sys
import zipfile

import cctext
import export_cc
import ziputil
from ccfont import LargeGlyphs, SmallGlyphs, SpriteFont
from paths import BUILD, FONTS_SRC, ORIGINAL, TRANS_CC

TAG = re.compile(r"\{[^{}]*\}")
ALLOWED = re.compile(r"\{(wait|speed|color|wend|fwait|fset)\(\d+\)\}|\{(bpage|bwait|mend)\}|\{[A-Z0-9]+%\d?\}")
END = re.compile(r"(\{[^{}]*\})+$")
OPTION = "　　　"
HANGUL_ADV_SMALL, HANGUL_ADV_LARGE = 74, 72


def load_sheets():
    sheets = {}
    for p in sorted(TRANS_CC.glob("*.json")):
        sheets[p.stem] = json.loads(p.read_text(encoding="utf-8"))
    return sheets


def check_msg(tag, ko, en, jp, errors):
    if ko.count("{") != ko.count("}"):
        errors.append(f"{tag}: unbalanced braces")
        return
    known = set(TAG.findall(en)) | set(TAG.findall(jp))
    for t in TAG.findall(ko):
        if t not in known and not ALLOWED.fullmatch(t):
            errors.append(f"{tag}: unknown tag {t}")
    def ending(s):
        m = END.search(s)
        return re.sub(r"\{color\([^)]*\)\}", "", m.group()) if m else None  # colour resets are not terminators

    me, mk = END.search(en), END.search(ko)
    if me and ending(ko) != ending(en):
        errors.append(f"{tag}: ending {mk.group() if mk else None} != EN {me.group()}")
    lines_en = en.split("\\n")
    lines_ko = ko.split("\\n")
    n_en = sum(1 for l in lines_en if TAG.sub("", l).startswith(OPTION))
    n_ko = sum(1 for l in lines_ko if TAG.sub("", l).startswith(OPTION))
    if n_en >= 2 and n_en != n_ko:  # a single indented line (e.g. a tombstone) is layout, not a choice
        errors.append(f"{tag}: {n_ko} option lines vs EN {n_en}")


def glyph_maker(name, neodgm, nanum, nanum_r):
    """Korean glyph generator matching one game font (metrics scaled from the font's own 'A'), None = leave as is.
    small_* gn/bn/ci are pixel fonts (NeoDunggeunmo), everything else is smooth (NanumSquareRound EB)."""
    fam = name.split("_font_")[1].rsplit(".", 1)[0]
    italic = 10 if "italic" in fam or fam == "ci_70" else 0
    # ui.dat (ESC menu, key bindings ...): ui_font_gnb = large gn at ~95%, ui_font_gnb_small = small gn
    if fam == "gnb_small":
        return SmallGlyphs(neodgm, top=19.5, advance=HANGUL_ADV_SMALL)
    if fam == "gnb":
        return LargeGlyphs(nanum, size=71, top=11, advance=70)
    # the exe draws the ESC menu / key bindings (ui_configmenu.txt) with large kb_70 (Japanese, thin rounded gothic)
    # whatever the language: Hangul centred on its kanji (漢: 97x99 at yoff 21) and a little larger, because the
    # menu's Latin is large next to it; advance 90 (kanji 93 looks letter-spaced in Korean)
    if name == "large_font_kb_70.spritefont":
        return LargeGlyphs(nanum_r, size=92, top=22, advance=90, left=4)
    if name.startswith("small_") and fam in ("gn_70", "gn_italic_70", "bn_70", "ci_70"):
        top = {"gn_70": 19.5, "gn_italic_70": 19.5, "bn_70": 32.5, "ci_70": 23.5}[fam]
        return SmallGlyphs(neodgm, top=top, advance=HANGUL_ADV_SMALL, italic=italic)
    # size (px), top, advance per family: gn is the reference (A: 87 px tall, yoff 13)
    smooth = {"gn_70": (74, 10, HANGUL_ADV_LARGE), "gn_italic_70": (74, 10, HANGUL_ADV_LARGE),
              "bn_70": (66, 17, 64), "ci_70": (69, 15, 66), "ch_100": (78, 21, 76)}
    if fam not in smooth:
        return None
    size, top, adv = smooth[fam]
    return LargeGlyphs(nanum, size=size, top=top, advance=adv, italic=italic)


def width(sf, line, hangul_adv):
    w = 0.0
    for ch in TAG.sub("", line):
        g = sf.glyphs.get(ord(ch))
        if g:
            w += g[4] + (g[2] - g[0]) + g[6]
        else:
            w += hangul_adv
    return w


def main():
    release = "--release" in sys.argv
    sheets = load_sheets()
    zl = export_cc.lang()
    errors, warns, done, todo = [], [], 0, 0
    used = set()

    zf = zipfile.ZipFile(ORIGINAL / "data" / "font.dat")
    small = SpriteFont(zf.read("small_font_gn_70.spritefont"))

    # dialogue (en.csv) and battle event lines (btel_en.csv)
    src = {k: (jp, en) for k, jp, en in export_cc.msg_rows(zl)}
    src_btel = {k: (jp, en) for k, jp, en in export_cc.btel_rows(zl)}
    ko_msg, ko_btel = {}, {}
    for name, rows in sheets.items():
        if name == "btel":
            src_of, out_of = src_btel, ko_btel
        elif name.startswith("msg_"):
            src_of, out_of = src, ko_msg
        else:
            continue
        for r in rows:
            jp, en = src_of[r["k"]]
            if r["jh"] != export_cc.text_hash(jp) or r["eh"] != export_cc.text_hash(en):
                errors.append(f"{name} {r['k']}: sheet out of sync with lang.dat")
                continue
            if not r["ko"]:
                todo += 1
                continue
            check_msg(f"{name} {r['k']}", r["ko"], en, jp, errors)
            budget = max(width(small, l, HANGUL_ADV_SMALL) for l in en.split("\\n"))
            for l in r["ko"].split("\\n"):
                w = width(small, l, HANGUL_ADV_SMALL)
                if w > max(budget, 1250) + 1:
                    warns.append(f"{name} {r['k']}: line {w:.0f}px > EN {budget:.0f}px: {TAG.sub('', l)}")
            out_of[r["k"]] = r["ko"]
            used |= set(TAG.sub("", r["ko"]).replace("\\n", ""))
            done += 1

    en_doc = cctext.parse(zl.read("en.csv"), header=False, quoting=False)
    for row in en_doc["rows"]:
        k = f"{row['f'][0]}:{row['f'][1]}"
        if k in ko_msg:
            row["f"] = row["f"][:2] + [ko_msg[k]]
            row["q"] = row["q"][:3]
    repl_lang = {"en.csv": cctext.dump(en_doc)}
    if ko_btel:
        bt_doc = cctext.parse(zl.read("btel_en.csv"), header=False, quoting=False)
        for row in bt_doc["rows"]:
            k = f"{row['f'][0]}:{row['f'][1]}"
            if k in ko_btel:
                row["f"] = row["f"][:2] + [ko_btel[k]]
                row["q"] = row["q"][:3]
        repl_lang["btel_en.csv"] = cctext.dump(bt_doc)

    # tables
    for name in export_cc.TABLES:
        rows = sheets.get("tbl_" + name.split(".")[0], [])
        doc = cctext.parse(zl.read(name))
        cols = doc["cols"]
        ie, ij = cols.index("EN"), cols.index("JP")
        changed = False
        for r in rows:
            row = doc["rows"][int(r["k"])]
            f = row["f"]
            if r["jh"] != export_cc.text_hash(f[ij]) or r["eh"] != export_cc.text_hash(f[ie]):
                errors.append(f"tbl {name} {r['k']}: sheet out of sync")
                continue
            if not r["ko"]:
                todo += 1
                continue
            f[ie] = r["ko"]
            if cctext.needs_quote(r["ko"]):
                row["q"][ie] = True
            used |= set(TAG.sub("", r["ko"]))
            changed = True
            done += 1
        if changed:
            repl_lang[name] = cctext.dump(doc)

    if release and todo:
        errors.append(f"{todo} rows untranslated (release build requires all)")
    if errors:
        print("\n".join(errors[:80]))
        sys.exit(f"BUILD FAILED: {len(errors)} errors")

    # fonts: add every used char each Latin font lacks. The game's fonts have no default character, so a missing
    # glyph throws inside SpriteFont and the game quits (e.g. the title menu uses ci_70) -> every font also gets '?'
    # as default character. large kb_70 gets Hangul too (ESC menu); the other
    # Japanese fonts (kt, small kb) only get the default character.
    # U+3000 is laid out by the game itself (EN choice indents use it although gn has no glyph)
    need = sorted(c for c in used if ord(c) not in small.glyphs and not c.isspace())
    neodgm = str(FONTS_SRC / "neodgm" / "neodgm.ttf")
    nanum = str(FONTS_SRC / "nanumsquareround" / "NanumSquareRoundEB.ttf")
    nanum_r = str(FONTS_SRC / "nanumsquareround" / "NanumSquareRoundR.ttf")
    missing = set()

    def fonts_of(z):
        repl = {}
        for name in sorted(n for n in z.namelist() if n.endswith(".spritefont")):
            sf = SpriteFont(z.read(name))
            g = glyph_maker(name, neodgm, nanum, nanum_r)
            if g is not None:
                items = []
                for c in sorted(used):
                    if ord(c) in sf.glyphs or c.isspace():
                        continue
                    r = g.make(c)
                    if r is None:
                        missing.add(c)
                        continue
                    items.append((ord(c),) + tuple(r))
                if items:
                    sf.add(items)
            if ord("?") in sf.glyphs:
                sf.default = ord("?")
            repl[name] = sf.dump()
        return repl

    repl_font = fonts_of(zf)
    repl_ui = fonts_of(zipfile.ZipFile(ORIGINAL / "data" / "ui.dat"))  # ESC menu / key binding screens
    if missing:
        sys.exit("characters no font can render: " + " ".join(f"U+{ord(c):04X}" for c in sorted(missing)))

    out = BUILD / "data"
    out.mkdir(parents=True, exist_ok=True)
    data, _ = ziputil.rebuild((ORIGINAL / "data" / "lang.dat").read_bytes(), repl_lang, deflate=True)
    (out / "lang.dat").write_bytes(data)
    data, _ = ziputil.rebuild((ORIGINAL / "data" / "font.dat").read_bytes(), repl_font, deflate=True)
    (out / "font.dat").write_bytes(data)
    data, _ = ziputil.rebuild((ORIGINAL / "data" / "ui.dat").read_bytes(), repl_ui, deflate=True)
    (out / "ui.dat").write_bytes(data)
    if warns:
        (BUILD / "cc_width_warnings.txt").write_text("\n".join(warns), encoding="utf-8")
    print(f"translated {done}/{done + todo} rows, {len(need)} new glyphs, {len(warns)} width warnings -> {out}")


if __name__ == "__main__":
    main()
