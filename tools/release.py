"""Pack patch_kit/ + 50_patch/patch/ into 40_release/<name>.zip (run after build_rd.py --release and make_patch.py).

  release.py <version>     e.g. release.py 0.1.0
"""
import hashlib
import sys
import zipfile

from paths import FONTS_SRC, PATCH, PATCH_KIT, RELEASE

KIT = PATCH_KIT
# published name -> source
FILES = {
    "README.txt": KIT / "README.txt",
    "한글패치_적용.bat": KIT / "한글패치_적용.bat",
    "원본_복구.bat": KIT / "원본_복구.bat",
    "apply.ps1": KIT / "apply.ps1",
    "OFL_NanumMyeongjo.txt": FONTS_SRC / "nanummyeongjo" / "OFL.txt",
    "patch/rd.ops": PATCH / "patch" / "rd.ops",
    "patch/rd.bin": PATCH / "patch" / "rd.bin",
}


def main():
    ver = sys.argv[1]
    top = f"CCRDE_한글패치_v{ver}"
    readme = (KIT / "README.txt").read_text(encoding="utf-8-sig")
    if f"v{ver}" not in readme:
        sys.exit(f"README.txt does not mention v{ver}")
    RELEASE.mkdir(exist_ok=True)
    out = RELEASE / f"CCRDE_KR_v{ver}.zip"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for name, src in FILES.items():
            z.write(src, f"{top}/{name}")
    print(f"{out} {out.stat().st_size} bytes sha256={hashlib.sha256(out.read_bytes()).hexdigest()}")


if __name__ == "__main__":
    main()
