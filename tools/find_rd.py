"""Find translate.txt rows: find_rd.py <regex> [column=EN] [limit=20]"""
import re
import sys

from paths import EXTRACTED
import rdtext

pat = re.compile(sys.argv[1])
col = sys.argv[2] if len(sys.argv) > 2 else "EN"
lim = int(sys.argv[3]) if len(sys.argv) > 3 else 20
rows = rdtext.parse((EXTRACTED / "rd" / "translate.txt").read_bytes())["rows"]
n = 0
for i, r in enumerate(rows):
    if pat.search(r["text"][col]):
        print(i, r["addr"], "JP:", repr(r["text"]["JP"]), "\n   EN:", repr(r["text"]["EN"]))
        n += 1
        if n >= lim:
            break
