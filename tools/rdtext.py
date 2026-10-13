"""Reader/writer for Radical Dreamers translate.txt.

Format (as shipped): UTF-16LE with BOM, tab-separated, CSV-style quoting.
Header: Address<TAB>JP<TAB>EN<TAB>FR<TAB>IT<TAB>DE<TAB>ES
Rows:   0xXXXXXX<TAB>field<TAB>field...<row terminator>
        A field is either "quoted" (may contain LF/CRLF; a literal quote is "") or bare (no tab/CR/LF/quote).
The parser keeps per-field quoting and per-row terminators so dump(parse(x)) == x byte-for-byte
(checked by tools/survey_rdtext.py and enforced in the product build).
"""
import hashlib

COLS = ["JP", "EN", "FR", "IT", "DE", "ES"]


def text_hash(text: str) -> str:
    """Sheet fingerprint of an original field (sheets store this instead of the game text)."""
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]


def parse(raw: bytes):
    assert raw[:2] == b"\xff\xfe"
    s = raw[2:].decode("utf-16le")
    header, sep, body = s.partition("\r\n")
    assert header.split("\t") == ["Address"] + COLS, header
    rows, i, n = [], 0, len(body)
    while i < n:
        j = body.index("\t", i)
        addr = body[i:j]
        i = j + 1
        fields, quoted = [], []
        while True:
            if i < n and body[i] == '"':
                i += 1
                buf = []
                while True:
                    k = body.index('"', i)
                    buf.append(body[i:k])
                    if k + 1 < n and body[k + 1] == '"':
                        buf.append('"')
                        i = k + 2
                        continue
                    i = k + 1
                    break
                fields.append("".join(buf))
                quoted.append(True)
            else:
                k = i
                while k < n and body[k] not in "\t\r\n":
                    k += 1
                assert '"' not in body[i:k], (addr, body[i:k])
                fields.append(body[i:k])
                quoted.append(False)
                i = k
            if i < n and body[i] == "\t":
                i += 1
                continue
            break
        term = ""
        while i < n and body[i] in "\r\n":
            term += body[i]
            i += 1
        rows.append({"addr": addr, "text": dict(zip(COLS, fields)), "quoted": quoted, "term": term})
    return {"header": header, "sep": sep, "rows": rows}


def _field(text, quoted):
    if quoted:
        return '"' + text.replace('"', '""') + '"'
    assert not any(c in text for c in '\t\r\n"'), text
    return text


def dump(doc) -> bytes:
    out = [doc["header"], doc["sep"]]
    for r in doc["rows"]:
        fs = [_field(r["text"][c], q) for c, q in zip(COLS, r["quoted"])]
        out.append(r["addr"] + "\t" + "\t".join(fs) + r["term"])
    return b"\xff\xfe" + "".join(out).encode("utf-16le")
