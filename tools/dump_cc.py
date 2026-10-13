"""Print sheet rows with their JP/EN source (read from the user's lang.dat) for translating.

  dump_cc.py <sheet name, e.g. msg_000 | tbl_sysmes> [start] [end] [--todo] [--out file]
"""
import json
import sys

import export_cc
from paths import TRANS_CC


def sources(sheet):
    z = export_cc.lang()
    if sheet.startswith("msg_"):
        return {k: (jp, en) for k, jp, en in export_cc.msg_rows(z)}
    if sheet == "btel":
        return {k: (jp, en) for k, jp, en in export_cc.btel_rows(z)}
    name = sheet[4:] + ".txt"
    return {n: (jp, en) for n, i, jp, en in export_cc.table_rows(z, name)}


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    sheet = args[0]
    rows = json.loads((TRANS_CC / f"{sheet}.json").read_text(encoding="utf-8"))
    a = int(args[1]) if len(args) > 1 else 0
    b = int(args[2]) if len(args) > 2 else len(rows)
    src = sources(sheet)
    out = []
    for n, r in enumerate(rows[a:b], a):
        if "--todo" in sys.argv and r["ko"]:
            continue
        jp, en = src[r["k"]]
        out.append(f"#{n} [{r['k']}]" + (f" id={r['id']}" if "id" in r else ""))
        out.append(f"JP: {jp}")
        out.append(f"EN: {en}")
        if r["ko"]:
            out.append(f"KO: {r['ko']}")
    text = "\n".join(out) + "\n"
    if "--out" in sys.argv:
        open(sys.argv[sys.argv.index("--out") + 1], "w", encoding="utf-8").write(text)
        print(f"{len(out) // 3} rows -> {sys.argv[sys.argv.index('--out') + 1]}")
    else:
        sys.stdout.write(text)


if __name__ == "__main__":
    main()
