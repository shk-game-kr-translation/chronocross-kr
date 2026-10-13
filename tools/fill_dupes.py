"""Write a batch that copies existing Korean onto untranslated msg rows that duplicate a translated row.

  fill_dupes.py <out_batch.json> [--jp] [sheet ...]
Default: match by the (jh, eh) hash pair (exact JP+EN duplicates).
--jp:    also match rows whose JP is identical and whose EN has the same control-tag sequence
         (EN only reworded; the Korean follows JP anyway).
Review/apply the batch with apply_cc.py like any other batch.
"""
import json
import re
import sys

import export_cc
from paths import TRANS_CC

TAG = re.compile(r"\{[^{}]*\}")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    by_jp = "--jp" in sys.argv
    out, only = args[0], set(args[1:])
    sheets = {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in sorted(TRANS_CC.glob("msg_*.json"))}
    en = {k: e for k, _, e in export_cc.msg_rows(export_cc.lang())} if by_jp else {}
    known, known_jp = {}, {}
    for rows in sheets.values():
        for r in rows:
            if r["ko"]:
                known.setdefault((r["jh"], r["eh"]), r["ko"])
                if by_jp:
                    known_jp.setdefault((r["jh"], tuple(TAG.findall(en[r["k"]]))), r["ko"])
    batch, n = {}, 0
    for name, rows in sheets.items():
        if only and name not in only:
            continue
        for r in rows:
            if r["ko"]:
                continue
            ko = known.get((r["jh"], r["eh"]))
            if ko is None and by_jp:
                ko = known_jp.get((r["jh"], tuple(TAG.findall(en[r["k"]]))))
            if ko is not None:
                batch.setdefault(name, {})[r["k"]] = ko
                n += 1
    with open(out, "w", encoding="utf-8") as f:
        json.dump(batch, f, ensure_ascii=False, indent=0)
    print(f"{n} duplicate rows -> {out}")


if __name__ == "__main__":
    main()
