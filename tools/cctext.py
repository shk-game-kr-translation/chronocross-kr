"""Reader/writer for Chrono Cross (RDE) text tables in data/lang.dat.

Two shapes, both tab separated, parsed so that dump(parse(x)) == x byte for byte:
  table  (*.txt, btmes/…): UTF-16LE+BOM or UTF-8(+BOM), header row of column names (#/id, Text, JP, EN, …),
         fields may be "quoted" (CSV style, may contain CR/LF, "" = literal quote).
  csv    (en.csv, jp.csv, btel_*.csv, Ex_*.csv): UTF-8+BOM, no header, rows "<group>\t<index>\t<text>[\t...]".
         Line breaks inside text are the two characters '\\n'.
"""


def _decode(raw: bytes):
    if raw[:2] == b"\xff\xfe":
        return "utf-16le", b"\xff\xfe", raw[2:].decode("utf-16le")
    if raw[:3] == b"\xef\xbb\xbf":
        return "utf-8", b"\xef\xbb\xbf", raw[3:].decode("utf-8")
    return "utf-8", b"", raw.decode("utf-8")


def _rows(s, quoting=True):
    """Split into rows of fields, keeping quoting flags and row terminators."""
    rows, i, n = [], 0, len(s)
    while i < n:
        fields, quoted = [], []
        while True:
            if quoting and i < n and s[i] == '"':
                i += 1
                buf = []
                while True:
                    k = s.index('"', i)
                    buf.append(s[i:k])
                    if k + 1 < n and s[k + 1] == '"':
                        buf.append('"')
                        i = k + 2
                        continue
                    i = k + 1
                    break
                fields.append("".join(buf))
                quoted.append(True)
            else:
                k = i
                while k < n and s[k] not in "\t\r\n":
                    k += 1
                fields.append(s[i:k])
                quoted.append(False)
                i = k
            if i < n and s[i] == "\t":
                i += 1
                continue
            break
        term = ""
        if i < n and s[i] == "\r":
            term += "\r"
            i += 1
        if i < n and s[i] == "\n":
            term += "\n"
            i += 1
        rows.append({"f": fields, "q": quoted, "t": term})
    return rows


def parse(raw: bytes, header=True, quoting=True):
    enc, bom, s = _decode(raw)
    rows = _rows(s, quoting)
    doc = {"enc": enc, "bom": bom, "rows": rows, "cols": None}
    if header and rows:
        doc["cols"] = rows[0]["f"]
    return doc


def _field(text, quoted):
    if quoted:
        return '"' + text.replace('"', '""') + '"'
    assert not any(c in text for c in "\t\r\n"), text[:80]
    return text


def dump(doc) -> bytes:
    out = []
    for r in doc["rows"]:
        out.append("\t".join(_field(t, q) for t, q in zip(r["f"], r["q"])) + r["t"])
    return doc["bom"] + "".join(out).encode(doc["enc"])


def needs_quote(text):
    return any(c in text for c in '\t\r\n"')
