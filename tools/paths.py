"""Project path constants. Every tool resolves paths through this module."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GAME = ROOT / "CHRONO CROSS  THE RADICAL DREAMERS EDITION"   # test install (patched in place by tools/install.py)
GAME_DATA = GAME / "data"

ORIGINAL = ROOT / "00_original"          # pristine copies of every file the patch replaces (never edited)
EXTRACTED = ROOT / "10_extracted"        # decrypted / unpacked analysis artifacts (regenerable)
SOURCE = ROOT / "20_source"              # git-tracked inputs: translations, glossary, font config
TRANS_RD = SOURCE / "trans" / "rd"       # Radical Dreamers translation sheets
TRANS_CC = SOURCE / "trans" / "cc"       # Chrono Cross main-game translation sheets
FONTS_SRC = SOURCE / "fonts"             # third-party Korean fonts (with licenses)
BUILD = ROOT / "30_build"                # product build outputs (regenerable)
RELEASE = ROOT / "40_release"            # versioned release zips
PATCH = ROOT / "50_patch"                # generated patch recipe (50_patch/patch/rd.ops + rd.bin)
PATCH_KIT = ROOT / "patch_kit"           # patcher sources shipped in the release zip (apply.ps1, .bat, README.txt)
DOCS = ROOT / "docs"

RD_DAT = "radicaldreamers.dat"
