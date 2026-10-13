"""Merge translated batches into the RD sheets.

  apply_batch.py <batch.json> [...]
Batch format: {"0x000DDD": "한국어 …", ...}  or  {"0x000DDD": {"ko": "...", "status": "draft", "note": "..."}}
Rows keep their sheet order; unknown addresses fail. Default status for plain strings is "draft".
"""
import json
import sys

from paths import TRANS_RD


def main():
    sheets = {p: json.loads(p.read_text(encoding="utf-8")) for p in sorted(TRANS_RD.glob("rd_*.json"))}
    index = {r["addr"]: (p, r) for p, rows in sheets.items() for r in rows}
    touched, n = set(), 0
    for b in sys.argv[1:]:
        for addr, v in json.loads(open(b, encoding="utf-8").read()).items():
            if addr not in index:
                sys.exit(f"{b}: unknown address {addr}")
            p, r = index[addr]
            if isinstance(v, str):
                v = {"ko": v}
            r["ko"] = v["ko"]
            r["status"] = v.get("status", "draft")
            if "note" in v:
                r["note"] = v["note"]
            touched.add(p)
            n += 1
    for p in touched:
        p.write_text(json.dumps(sheets[p], ensure_ascii=False, indent=1), encoding="utf-8")
    total = sum(1 for rows in sheets.values() for r in rows)
    done = sum(1 for rows in sheets.values() for r in rows if r["ko"])
    print(f"applied {n} rows to {len(touched)} sheets; progress {done}/{total}")


if __name__ == "__main__":
    main()
