"""Guard for the public repository: fail if game data or the original script slipped in.

usage: check_public.py <repo dir>     (exit 1 on any violation)
Checks every file except .git/ and the ignored work folders:
  - translation sheets must not carry 'jp' / 'en' text (only the hashes 'jh' / 'eh')
  - no game binaries (.dat, .rom, exe, images, zip ...) and no large files except the bundled Korean font
  - no file with a long run of Japanese text (short terms in the glossary are fine)
  - markdown: no bare '~' (GitHub renders ~text~ as strikethrough)
"""
import json
import os
import re
import sys

SKIP_DIRS = {".git", "00_original", "10_extracted", "30_build", "40_release", "50_patch", "90_test", "__pycache__",
             "CHRONO CROSS  THE RADICAL DREAMERS EDITION", "DirectX & Must Install", "batches", ".claude"}
FONT_DIR = os.path.join("20_source", "fonts")
BAD_EXT = {".dat", ".rom", ".exe", ".dll", ".zip", ".rar", ".7z", ".xdelta", ".png", ".jpg", ".bmp", ".otf"}
JP = re.compile(r"[぀-ヿ㐀-鿿]")
MAX_JP_CHARS = 2500
MAX_SIZE = 2 << 20


def md_tildes(rel, s):
    out, fence = [], False
    for n, ln in enumerate(s.splitlines(), 1):
        if ln.lstrip().startswith("```"):
            fence = not fence
            continue
        if fence:
            continue
        prose = re.sub(r"`[^`]*`", "", ln).replace("\~", "")
        if "~" in prose:
            out.append(f'{rel}:{n}: unescaped "~" (renders as strikethrough): {ln.strip()[:60]}')
    return out


def tracked(root):
    """git-tracked files when run inside a work tree (respects .gitignore), else every file."""
    try:
        import subprocess
        out = subprocess.run(["git", "-C", root, "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
                             capture_output=True, check=True).stdout
        return [f for f in out.decode("utf-8").split("\0") if f]
    except Exception:
        files = []
        for dp, dn, fn in os.walk(root):
            dn[:] = [d for d in dn if d not in SKIP_DIRS]
            files += [os.path.relpath(os.path.join(dp, f), root) for f in fn]
        return files


def main(root):
    bad, report = [], []
    for rel in tracked(root):
        rel = os.path.normpath(rel)
        if any(part in SKIP_DIRS for part in rel.split(os.sep)):
            bad.append(f"{rel}: inside a work folder that must not be published")
            continue
        p = os.path.join(root, rel)
        ext = os.path.splitext(rel)[1].lower()
        size = os.path.getsize(p)
        in_fonts = rel.startswith(FONT_DIR)
        if ext in BAD_EXT:
            bad.append(f"{rel}: file type not allowed")
            continue
        if size > MAX_SIZE and not in_fonts:
            bad.append(f"{rel}: {size} bytes (large files are not allowed)")
            continue
        if in_fonts:
            continue
        try:
            s = open(p, encoding="utf-8-sig").read()
        except UnicodeDecodeError:
            bad.append(f"{rel}: binary file")
            continue
        if rel.startswith(os.path.join("20_source", "trans")) and ext == ".json":
            n = sum(1 for e in json.loads(s) if "jp" in e or "en" in e)
            if n:
                bad.append(f"{rel}: {n} entries carry original text (jp/en)")
        if ext == ".md":
            bad += md_tildes(rel, s)
        j = len(JP.findall(s))
        if j:
            report.append((j, rel))
        if j > MAX_JP_CHARS:
            bad.append(f"{rel}: {j} Japanese characters")
    report.sort(reverse=True)
    print("Japanese characters per file (top 8):")
    for j, rel in report[:8]:
        print(f"  {j:6d}  {rel}")
    if bad:
        print("FAIL")
        for b in bad:
            print("  " + b)
        sys.exit(1)
    print("OK: no game data found")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else ".")
