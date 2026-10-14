"""Merge an export of the review page (make_review.py -> "JSON 내보내기") into the CC and RD sheets.

  apply_review.py <export.json> [...]

Export format: {"format": "ccrde-review", "ver": ..., "edits": {"cc:<sheet>" | "rd:<sheet>": {"<key>": "한국어"}}}
Dialogue sheets (msg_*, btel) get their real newlines turned back into the literal \\n of lang.dat. Edited rows get
status "reviewed". Unknown sheets/keys and unbalanced {} fail before anything is written.
"""
import json
import sys

from paths import TRANS_CC, TRANS_RD


def main():
    sheets, plan = {}, []
    for b in sys.argv[1:]:
        doc = json.loads(open(b, encoding="utf-8").read())
        if doc.get("format") != "ccrde-review":
            sys.exit(f"{b}: not a review-page export")
        for sid, items in doc["edits"].items():
            kind, name = sid.split(":", 1)
            if kind not in ("cc", "rd"):
                sys.exit(f"{b}: unknown sheet {sid}")
            p = (TRANS_CC if kind == "cc" else TRANS_RD) / f"{name}.json"
            if not p.exists():
                sys.exit(f"{b}: unknown sheet {sid}")
            if p not in sheets:
                sheets[p] = json.loads(p.read_text(encoding="utf-8"))
            idx = {r["k" if kind == "cc" else "addr"]: r for r in sheets[p]}
            dialogue = kind == "cc" and (name.startswith("msg_") or name == "btel")
            for k, ko in items.items():
                if k not in idx:
                    sys.exit(f"{b}: {sid} has no row {k}")
                if ko.count("{") != ko.count("}"):
                    sys.exit(f"{b}: {sid} {k}: unbalanced braces: {ko}")
                plan.append((p, idx[k], ko.replace("\n", "\\n") if dialogue else ko))
    changed, n = set(), 0
    for p, r, ko in plan:
        if r["ko"] != ko:
            print(f"{p.stem} {r.get('k', r.get('addr'))}\n  - {r['ko']!r}\n  + {ko!r}")
            r["ko"] = ko
            r["status"] = "reviewed"
            changed.add(p)
            n += 1
    for p in changed:
        p.write_text(json.dumps(sheets[p], ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(plan)} entries, {n} rows changed in {len(changed)} sheets")


if __name__ == "__main__":
    main()
