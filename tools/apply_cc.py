"""Merge translated batches into the CC sheets.

  apply_cc.py <batch.json> [...]
Batch format: {"<sheet>": {"<k>": "한국어", ...}, ...}   (k as in the sheet: "12:3" for msg_*, row number for tbl_*)
"""
import json
import sys

from paths import TRANS_CC


def main():
    n = 0
    for b in sys.argv[1:]:
        batch = json.loads(open(b, encoding="utf-8").read())
        for sheet, items in batch.items():
            p = TRANS_CC / f"{sheet}.json"
            rows = json.loads(p.read_text(encoding="utf-8"))
            idx = {r["k"]: r for r in rows}
            for k, v in items.items():
                if k not in idx:
                    sys.exit(f"{b}: {sheet} has no row {k}")
                if isinstance(v, str):
                    v = {"ko": v}
                idx[k]["ko"] = v["ko"]
                idx[k]["status"] = v.get("status", "draft")
                if "note" in v:
                    idx[k]["note"] = v["note"]
                n += 1
            p.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    done = total = 0
    for p in TRANS_CC.glob("*.json"):
        rows = json.loads(p.read_text(encoding="utf-8"))
        total += len(rows)
        done += sum(1 for r in rows if r["ko"])
    print(f"applied {n} rows; progress {done}/{total}")


if __name__ == "__main__":
    main()
