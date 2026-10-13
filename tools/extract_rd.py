"""Back up the pristine Radical Dreamers archive and unpack it for analysis.

- 00_original/data/radicaldreamers.dat (+ SHA-256 manifest of the whole install, first run only)
- 10_extracted/rd/<entries>             raw zip entries
- 10_extracted/rd/fonts/<NAME>.ttf|otf  decrypted fonts (round-trip checked against the original ciphertext)
"""
import hashlib
import json
import shutil
import sys
import zipfile

from fontTools.ttLib import TTFont

from paths import EXTRACTED, GAME, GAME_DATA, ORIGINAL, RD_DAT
import rdcrypt


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def backup():
    ORIGINAL.mkdir(exist_ok=True)
    man = ORIGINAL / "manifest.json"
    if not man.exists():
        files = {}
        for p in sorted(GAME.rglob("*")):
            if p.is_file() and "_CommonRedist" not in p.parts:
                files[p.relative_to(GAME).as_posix()] = {"size": p.stat().st_size, "sha256": sha256(p)}
        man.write_text(json.dumps(files, indent=1), encoding="utf-8")
        print("manifest:", len(files), "files")
    dst = ORIGINAL / "data" / RD_DAT
    if not dst.exists():
        dst.parent.mkdir(exist_ok=True)
        shutil.copy2(GAME_DATA / RD_DAT, dst)
    want = json.loads(man.read_text(encoding="utf-8"))["data/" + RD_DAT]["sha256"]
    if sha256(dst) != want:
        sys.exit("00_original radicaldreamers.dat does not match manifest")
    return dst


def main():
    src = backup()
    out = EXTRACTED / "rd"
    (out / "fonts").mkdir(parents=True, exist_ok=True)
    z = zipfile.ZipFile(src)
    for info in z.infolist():
        data = z.read(info)
        (out / info.filename).write_bytes(data)
        if info.filename.upper().endswith("FONT.DAT") or info.filename.upper().startswith(("ENFONT", "JPFONT")):
            plain = rdcrypt.decrypt(data)
            assert rdcrypt.encrypt(plain) == data, info.filename + " cipher round trip failed"
            ext = ".otf" if plain[:4] == b"OTTO" else ".ttf"
            fp = out / "fonts" / (info.filename.rsplit(".", 1)[0] + ext)
            fp.write_bytes(plain)
            f = TTFont(fp)
            cmap = f.getBestCmap()
            hangul = sum(1 for c in cmap if 0xAC00 <= c <= 0xD7A3)
            name = f["name"].getDebugName(4)
            upem = f["head"].unitsPerEm
            print(f"{fp.name}: '{name}' glyphs={len(f.getGlyphOrder())} cmap={len(cmap)} hangul={hangul} upem={upem}"
                  f" asc={f['hhea'].ascent} desc={f['hhea'].descent}")
    print("entries:", len(z.infolist()), "->", out)


if __name__ == "__main__":
    main()
