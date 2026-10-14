"""Product build for Radical Dreamers: 00_original radicaldreamers.dat -> 30_build/data/radicaldreamers.dat

- EN column of translate.txt is replaced by the Korean text of every sheet row with non-empty "ko"
  (rows with empty ko keep English; --release refuses any untranslated row).
- ENFONT/ENFONTI/ENFONTN.DAT are replaced with 30_build/rd/fonts/*.DAT (tools/build_rdfont.py).
Checks (fail the build): source dat hash, translate.txt round trip, row/addr alignment with sheets,
[NAME] token count, {} balance, trailing newline shape, every character present in ENFONT cmap.
Sheets keep [NAME]; the build writes it as the fixed Korean hero name HERO.
"""
import hashlib
import json
import re
import sys
import zipfile

from fontTools.ttLib import TTFont

from paths import BUILD, ORIGINAL, RD_DAT, TRANS_RD
import rdtext

FONTS = ["ENFONT", "ENFONTI", "ENFONTN"]
HERO = "세르쥬"


def load_sheets():
    rows = {}
    for p in sorted(TRANS_RD.glob("rd_*.json")):
        for r in json.loads(p.read_text(encoding="utf-8")):
            rows[r["addr"]] = r
    return rows


def check_row(r, en, jp, ko, cmap, errors):
    tag = f"{r['addr']} (row {r['i']})"
    if ko.count("[NAME]") not in (en.count("[NAME]"), jp.count("[NAME]")):
        errors.append(f"{tag}: [NAME] count {ko.count('[NAME]')} vs en {en.count('[NAME]')}")
    if ko.count("{") != ko.count("}"):
        errors.append(f"{tag}: unbalanced braces")
    if en.endswith("\n") != ko.endswith("\n"):
        errors.append(f"{tag}: trailing newline differs from EN")
    for ch in set(re.sub(r"\[NAME\]", HERO, ko)):
        # chars the original EN row already uses (e.g. the ★ chapter marker) are handled by the game itself
        if ch not in "\n" and ord(ch) not in cmap and ch not in en:
            errors.append(f"{tag}: U+{ord(ch):04X} {ch!r} missing from ENFONT")


def main():
    release = "--release" in sys.argv
    src = ORIGINAL / "data" / RD_DAT
    man = json.loads((ORIGINAL / "manifest.json").read_text(encoding="utf-8"))
    if hashlib.sha256(src.read_bytes()).hexdigest() != man["data/" + RD_DAT]["sha256"]:
        sys.exit("00_original radicaldreamers.dat hash mismatch")
    zin = zipfile.ZipFile(src)
    raw = zin.read("translate.txt")
    doc = rdtext.parse(raw)
    assert rdtext.dump(doc) == raw, "translate.txt round trip"

    sheets = load_sheets()
    font_dir = BUILD / "rd" / "fonts"
    cmap = TTFont(font_dir / "ENFONT.ttf").getBestCmap()
    errors, done, todo = [], 0, 0
    for i, row in enumerate(doc["rows"]):
        s = sheets.get(row["addr"])
        en, jp = row["text"]["EN"], row["text"]["JP"]
        if s is None or s["i"] != i or s["eh"] != rdtext.text_hash(en) or s["jh"] != rdtext.text_hash(jp):
            errors.append(f"{row['addr']}: sheet missing or out of sync with translate.txt")
            continue
        ko = s["ko"]
        if not ko and not en.strip():
            done += 1  # blank EN rows (e.g. 0x0196CA) need no translation; keep them as is
            continue
        if not ko:
            todo += 1
            continue
        check_row(s, en, jp, ko, cmap, errors)
        # the exe fills [NAME] with its built-in English default "Serge" (not in any data file), so the
        # hero name is fixed in Korean; a custom name typed at the name entry is not shown (user decision)
        row["text"]["EN"] = ko.replace("[NAME]", HERO)
        row["quoted"][1] = True
        done += 1
    if release and todo:
        errors.append(f"{todo} rows untranslated (release build requires all)")
    if errors:
        print("\n".join(errors[:80]))
        sys.exit(f"BUILD FAILED: {len(errors)} errors")

    out = BUILD / "data" / RD_DAT
    out.parent.mkdir(parents=True, exist_ok=True)
    repl = {"translate.txt": rdtext.dump(doc)}
    for f in FONTS:
        repl[f + ".DAT"] = (font_dir / (f + ".DAT")).read_bytes()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zout:
        for info in zin.infolist():
            data = repl.pop(info.filename, None)
            if data is None:
                data = zin.read(info)
            zi = zipfile.ZipInfo(info.filename, info.date_time)
            zi.compress_type = info.compress_type
            zi.external_attr = info.external_attr
            zout.writestr(zi, data)
    assert not repl, repl
    # verify the written archive reads back exactly what was planned
    zchk = zipfile.ZipFile(out)
    assert zchk.namelist() == zin.namelist()
    assert zchk.read("translate.txt") == rdtext.dump(doc)
    print(f"translated {done}/{done + todo} rows -> {out} ({out.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
