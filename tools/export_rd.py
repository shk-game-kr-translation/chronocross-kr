"""Export translate.txt into translation sheets 20_source/trans/rd/rd_NNN.json (250 rows each).

Each row: {"i": row index, "addr": "0x...", "jh": hash of JP, "eh": hash of EN, "ko": "", "status": "todo", "note": ""}
The sheets carry no game text: JP/EN are read from the user's own radicaldreamers.dat at build time and matched by
hash (rdtext.text_hash), so the repository can be published.
Existing sheets are never overwritten (pass --force to regenerate empty ones; filled ko text is preserved).
"""
import json
import sys

from paths import EXTRACTED, TRANS_RD
import rdtext

CHUNK = 250


def main():
    force = "--force" in sys.argv
    rows = rdtext.parse((EXTRACTED / "rd" / "translate.txt").read_bytes())["rows"]
    TRANS_RD.mkdir(parents=True, exist_ok=True)
    made = kept = 0
    for c in range(0, len(rows), CHUNK):
        p = TRANS_RD / f"rd_{c // CHUNK:03d}.json"
        old = {}
        if p.exists():
            if not force:
                kept += 1
                continue
            old = {r["addr"]: r for r in json.loads(p.read_text(encoding="utf-8"))}
        sheet = []
        for i in range(c, min(c + CHUNK, len(rows))):
            r = rows[i]
            o = old.get(r["addr"], {})
            sheet.append({"i": i, "addr": r["addr"], "jh": rdtext.text_hash(r["text"]["JP"]),
                          "eh": rdtext.text_hash(r["text"]["EN"]),
                          "ko": o.get("ko", ""), "status": o.get("status", "todo"), "note": o.get("note", "")})
        p.write_text(json.dumps(sheet, ensure_ascii=False, indent=1), encoding="utf-8")
        made += 1
    print(f"sheets written {made}, kept {kept}, rows {len(rows)} -> {TRANS_RD}")


if __name__ == "__main__":
    main()
