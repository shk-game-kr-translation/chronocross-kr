"""Export Chrono Cross text into translation sheets 20_source/trans/cc/ (no game text, hashes only).

  msg_NNN.json   en.csv dialogue rows whose EN text is real (not {ERROR}), 250 rows per sheet
                 row: {"k": "<group>:<index>", "jh", "eh", "ko", "status", "note"}
  btel.json      btel_en.csv battle event lines, same row shape as msg_*
  tbl_<name>.json  rows of the column tables (sysmes.txt, keyitem.txt, …) with non-empty EN
                 row: {"k": "<row number>", "id": first column, "jh", "eh", "ko", "status", "note"}
Existing sheets are kept (pass --force to regenerate; filled ko is preserved by key when hashes still match).
"""
import json
import sys
import zipfile

import cctext
from paths import ORIGINAL, TRANS_CC

CHUNK = 250
TABLES = ["sysmes.txt", "keyitem.txt", "btmes.txt", "cmnmes.txt", "menutest.txt", "shopmenu.txt", "waa_spec.txt",
          "ome.txt", "savetbl.txt", "ui_configmenu.txt", "ui_pausemenu.txt", "error.txt", "btlexit.txt", "memmenu.txt"]


def text_hash(t):
    import hashlib
    return hashlib.sha1(t.encode("utf-8")).hexdigest()[:12]


def lang():
    return zipfile.ZipFile(ORIGINAL / "data" / "lang.dat")


def msg_rows(z):
    """[(key, jp, en)] for en.csv rows with real EN text. Field 2.. joined (one EN row contains stray tabs)."""
    en = cctext.parse(z.read("en.csv"), header=False, quoting=False)["rows"]
    jp = cctext.parse(z.read("jp.csv"), header=False, quoting=False)["rows"]
    out = []
    for re_, rj in zip(en, jp, strict=True):
        assert re_["f"][:2] == rj["f"][:2]
        t = "\t".join(re_["f"][2:])
        if t != "{ERROR}":
            out.append((f"{re_['f'][0]}:{re_['f'][1]}", "\t".join(rj["f"][2:]), t))
    return out


def btel_rows(z):
    """[(key, jp, en)] for btel_en.csv (battle event lines), aligned 1:1 with btel_jp.csv."""
    en = cctext.parse(z.read("btel_en.csv"), header=False, quoting=False)["rows"]
    jp = cctext.parse(z.read("btel_jp.csv"), header=False, quoting=False)["rows"]
    out = []
    for re_, rj in zip(en, jp, strict=True):
        assert re_["f"][:2] == rj["f"][:2]
        out.append((f"{re_['f'][0]}:{re_['f'][1]}", "\t".join(rj["f"][2:]), "\t".join(re_["f"][2:])))
    return out


def table_rows(z, name):
    doc = cctext.parse(z.read(name))
    cols = doc["cols"]
    ie, ij = cols.index("EN"), cols.index("JP")
    out = []
    for n, r in enumerate(doc["rows"][1:], 1):
        f = r["f"]
        if len(f) > ie and f[ie].strip():
            out.append((str(n), f[0], f[ij], f[ie]))
    return out


def write(path, rows, force):
    if path.exists() and not force:
        return False
    old = {}
    if path.exists():
        old = {r["k"]: r for r in json.loads(path.read_text(encoding="utf-8"))}
    for r in rows:
        o = old.get(r["k"])
        if o and o["eh"] == r["eh"] and o["jh"] == r["jh"]:
            r.update(ko=o["ko"], status=o["status"], note=o["note"])
    path.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    return True


def main():
    force = "--force" in sys.argv
    TRANS_CC.mkdir(parents=True, exist_ok=True)
    z = lang()
    msgs = msg_rows(z)
    made = 0
    for c in range(0, len(msgs), CHUNK):
        rows = [{"k": k, "jh": text_hash(jp), "eh": text_hash(en), "ko": "", "status": "todo", "note": ""}
                for k, jp, en in msgs[c:c + CHUNK]]
        made += write(TRANS_CC / f"msg_{c // CHUNK:03d}.json", rows, force)
    rows = [{"k": k, "jh": text_hash(jp), "eh": text_hash(en), "ko": "", "status": "todo", "note": ""}
            for k, jp, en in btel_rows(z)]
    made += write(TRANS_CC / "btel.json", rows, force)
    for name in TABLES:
        rows = [{"k": n, "id": i, "jh": text_hash(jp), "eh": text_hash(en), "ko": "", "status": "todo", "note": ""}
                for n, i, jp, en in table_rows(z, name)]
        made += write(TRANS_CC / f"tbl_{name.split('.')[0]}.json", rows, force)
    print(f"dialogue rows {len(msgs)}, sheets written {made} -> {TRANS_CC}")


if __name__ == "__main__":
    main()
