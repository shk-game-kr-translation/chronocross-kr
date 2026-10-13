"""Install the built data files into the test game folder, or restore the originals.

  install.py          copy 30_build/data/* over the game's data/ (only files the patch owns)
  install.py restore  copy 00_original/data/* back
"""
import hashlib
import shutil
import sys

from paths import BUILD, GAME_DATA, ORIGINAL


def main():
    src = ORIGINAL / "data" if len(sys.argv) > 1 and sys.argv[1] == "restore" else BUILD / "data"
    for p in sorted(src.iterdir()):
        dst = GAME_DATA / p.name
        if not (ORIGINAL / "data" / p.name).exists():
            sys.exit(f"{p.name}: no pristine backup in 00_original; refusing to overwrite")
        shutil.copy2(p, dst)
        print(f"{p.name} -> {dst} sha256={hashlib.sha256(dst.read_bytes()).hexdigest()[:16]}")


if __name__ == "__main__":
    main()
