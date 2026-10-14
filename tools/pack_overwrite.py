"""Overwrite package: the built data files in a zip that users just copy over the game folder (no patcher).

  pack_overwrite.py <version>     -> 40_release/CCRDE_KR_v<version>_overwrite.zip
Run after build_rd.py --release and build_cc.py --release. Attach the zip to the GitHub release (never commit it).
"""
import hashlib
import sys
import zipfile

from paths import BUILD, FONTS_SRC, PATCH_KIT, RD_DAT, RELEASE

DATA = ["lang.dat", "font.dat", "ui.dat", RD_DAT]


def main():
    ver = sys.argv[1]
    top = f"CCRDE_한글패치_v{ver}"
    readme = (PATCH_KIT / "덮어쓰기_설명.txt").read_text(encoding="utf-8").replace("{ver}", ver)
    RELEASE.mkdir(exist_ok=True)
    out = RELEASE / f"CCRDE_KR_v{ver}_overwrite.zip"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        z.writestr(f"{top}/설치방법.txt", "﻿" + readme.replace("\n", "\r\n"))
        z.write(FONTS_SRC / "neodgm" / "LICENSE.txt", f"{top}/LICENSE_neodgm.txt")
        z.write(FONTS_SRC / "nanummyeongjo" / "OFL.txt", f"{top}/OFL_Nanum.txt")
        missing = [n for n in DATA if not (BUILD / "data" / n).exists()]
        if missing:
            sys.exit(f"not built: {missing}")
        for name in DATA:
            z.write(BUILD / "data" / name, f"{top}/data/{name}", compress_type=zipfile.ZIP_STORED)  # already zips
    print(f"{out} {out.stat().st_size} bytes sha256={hashlib.sha256(out.read_bytes()).hexdigest()}")


if __name__ == "__main__":
    main()
