"""Survey translate.txt: round trip, row/field counts, tokens, line shapes, charset."""
import collections
import re

from paths import EXTRACTED
import rdtext

raw = (EXTRACTED / "rd" / "translate.txt").read_bytes()
doc = rdtext.parse(raw)
rows = doc["rows"]
print("round trip identical:", rdtext.dump(doc) == raw)
print("rows:", len(rows), "nfields:", collections.Counter(len(r["quoted"]) for r in rows), "unquoted:", sum(not q for r in rows for q in r["quoted"]),
      "terms:", collections.Counter(repr(r["term"]) for r in rows).most_common(5))
addrs = [int(r["addr"], 16) for r in rows]
print("addr range", hex(min(addrs)), hex(max(addrs)), "sorted:", addrs == sorted(addrs), "unique:", len(set(addrs)))
for c in rdtext.COLS:
    txt = [r["text"][c] for r in rows]
    empty = sum(1 for t in txt if not t.strip())
    chars = sum(len(t) for t in txt)
    lines = collections.Counter(t.count("\n") for t in txt)
    maxw = max(len(l) for t in txt for l in t.split("\n"))
    print(f"{c}: empty={empty} chars={chars} unique={len(set(txt))} newlines={sorted(lines.items())[:8]} maxline={maxw}")
en = [r["text"]["EN"] for r in rows]
tok = collections.Counter(m for t in en for m in re.findall(r"\[[^\]]*\]|\{|\}|<[^>]*>|[^\x20-\x7e\n]", t))
print("EN tokens/nonascii:", tok.most_common(60))
jtok = collections.Counter(m for r in rows for m in re.findall(r"\[[^\]]*\]|<[^>]*>|[{}]", r["text"]["JP"]))
print("JP tokens:", jtok.most_common(20))
# leading-space convention
print("EN lead:", collections.Counter(re.match(r"^[ 　»]*", t).group() for t in en).most_common(8))
ws = collections.Counter(len(l) for t in en for l in t.split("\n"))
print("EN line len hist (>=40):", sorted((k, v) for k, v in ws.items() if k >= 40))
for r in rows[1000:1012]:
    print(r["addr"], repr(r["text"]["JP"]), "|", repr(r["text"]["EN"]))
