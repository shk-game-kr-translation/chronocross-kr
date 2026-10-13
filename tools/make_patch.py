"""Make the distributable patch for radicaldreamers.dat (run after tools/build_rd.py --release).

The patched dat is rebuilt from the original by splicing at the raw ZIP level:
  - unchanged members: local header + compressed data copied byte-for-byte from the original
  - translate.txt: written STORED; its bytes are mostly copied from the original's decompressed translate.txt
    (every column except EN is untouched), only the Korean EN fields come from the payload
  - ENFONT/ENFONTI/ENFONTN.DAT: written STORED; the plain TTF is diffed against the original font (decrypted from the
    user's dat), so the payload holds only the added Hangul data; the patcher AES-encrypts the assembled TTF
  - local header fields / central directory patched for the new method, CRC, sizes and offsets
So the patch ships no game data except a few header bytes, and the output is byte-deterministic:
the patcher checks the final SHA-256.

Recipe (50_patch/patch/rd.ops, one op per line), output = concatenation of:
  O <off> <len>   bytes of the original radicaldreamers.dat
  T <off> <len>   bytes of the original translate.txt after inflate
  P <off> <len>   bytes of rd.bin
  F<k> <off> <len>  bytes of original font k (FONTS[k]) after AES decrypt (only inside [ ])
  [  ...  ]       the ops in between build a buffer that is AES-128-CBC/PKCS#7 encrypted (font container cipher)
Header lines: "#key value" (source/target size+sha256, translate.txt / font raw-data offsets, AES key/iv).

Outputs: 50_patch/patch/rd.ops + rd.bin, and 30_build/data/radicaldreamers.dat = the patcher's exact result
(so tools/install.py tests what players get).
"""
import hashlib
import struct
import sys
import zipfile
import zlib

from paths import BUILD, ORIGINAL, PATCH, RD_DAT
import rdcrypt
import rdtext

FONTS = ["ENFONT", "ENFONTI", "ENFONTN"]
LFH, CDH, EOCD = b"PK\x03\x04", b"PK\x01\x02", b"PK\x05\x06"


def raw_offset(orig, info):
    o = info.header_offset
    nlen, xlen = struct.unpack_from("<HH", orig, o + 26)
    return o + 30 + nlen + xlen


class Recipe:
    def __init__(self):
        self.ops, self.payload = [], bytearray()

    def add(self, src, off, n):
        if n == 0:
            return
        last = self.ops[-1] if self.ops else None
        if last and last[0] == src and src not in "[]" and last[1] + last[2] == off:
            last[2] += n
        else:
            self.ops.append([src, off, n])

    def lit(self, data):
        self.add("P", len(self.payload), len(data))
        self.payload += data

    def font(self, k, src, data, minlen=8):
        """Greedy block match of data against src: copy runs from original font k, literal the rest."""
        index = {}
        for i in range(len(src) - minlen + 1):
            index.setdefault(src[i:i + minlen], i)
        self.ops.append(["[", 0, 0])
        p, lit = 0, 0
        while p < len(data):
            j = index.get(data[p:p + minlen]) if p + minlen <= len(data) else None
            if j is None:
                p += 1
                continue
            n = minlen
            while p + n < len(data) and j + n < len(src) and data[p + n] == src[j + n]:
                n += 1
            self.lit(data[lit:p])
            self.add(f"F{k}", j, n)
            p += n
            lit = p
        self.lit(data[lit:])
        self.ops.append(["]", 0, 0])


def apply(recipe_ops, orig, tt, fonts, payload):
    """Reference implementation of the patcher (50_patch/apply.ps1 must do exactly this)."""
    out = top = bytearray()
    for src, off, n in recipe_ops:
        if src == "[":
            out = bytearray()
        elif src == "]":
            top += rdcrypt.encrypt(bytes(out))
            out = top
        elif src == "O":
            out += orig[off:off + n]
        elif src == "T":
            out += tt[off:off + n]
        elif src == "P":
            out += payload[off:off + n]
        else:
            out += fonts[int(src[1:])][off:off + n]
    return bytes(top)


def translate_ops(rc, orig_doc, new_doc):
    """translate.txt bytes = header + rows; per row copy common prefix/suffix from the original."""
    head = (orig_doc["header"] + orig_doc["sep"]).encode("utf-16le")
    assert new_doc["header"] == orig_doc["header"]
    pos = 2 + len(head)  # BOM + header
    rc.add("T", 0, pos)

    def row_bytes(doc, r):
        one = {"header": "", "sep": "", "rows": [r]}
        return rdtext.dump(one)[2:]

    for ro, rn in zip(orig_doc["rows"], new_doc["rows"], strict=True):
        a, b = row_bytes(orig_doc, ro), row_bytes(new_doc, rn)
        p = 0
        while p < min(len(a), len(b)) and a[p] == b[p]:
            p += 1
        p -= p % 2
        s = 0
        while s < min(len(a), len(b)) - p and a[len(a) - 1 - s] == b[len(b) - 1 - s]:
            s += 1
        s -= s % 2
        rc.add("T", pos, p)
        rc.lit(b[p:len(b) - s])
        rc.add("T", pos + len(a) - s, s)
        pos += len(a)


def main():
    src = ORIGINAL / "data" / RD_DAT
    orig = src.read_bytes()
    built = zipfile.ZipFile(BUILD / "data" / RD_DAT)
    zin = zipfile.ZipFile(src)
    tt_orig = zin.read("translate.txt")
    tt_new = built.read("translate.txt")
    fonts_plain = {}
    for f in FONTS:
        ttf = (BUILD / "rd" / "fonts" / (f + ".ttf")).read_bytes()
        assert rdcrypt.encrypt(ttf) == built.read(f + ".DAT"), f"{f}: .ttf and built .DAT disagree"
        fonts_plain[f + ".DAT"] = ttf

    fonts_orig = [rdcrypt.decrypt(zin.read(f + ".DAT")) for f in FONTS]
    rc = Recipe()
    infos = zin.infolist()
    cd_new, tt_raw_off = [], None
    out_len = 0

    def emit_len(n):
        nonlocal out_len
        out_len += n

    for info in infos:
        o = info.header_offset
        assert orig[o:o + 4] == LFH
        nlen, xlen = struct.unpack_from("<HH", orig, o + 26)
        hdr_len = 30 + nlen + xlen
        name = info.filename
        new_off = out_len
        if name == "translate.txt" or name in fonts_plain:
            data_plain = tt_new if name == "translate.txt" else fonts_plain[name]
            data = data_plain if name == "translate.txt" else rdcrypt.encrypt(data_plain)
            crc, size = zlib.crc32(data), len(data)
            hdr = bytearray(orig[o:o + hdr_len])
            struct.pack_into("<H", hdr, 8, 0)                  # method: stored
            struct.pack_into("<III", hdr, 14, crc, size, size)  # crc, csize, usize
            struct.pack_into("<H", hdr, 4, 10)                  # version needed for stored
            rc.lit(bytes(hdr))
            if name == "translate.txt":
                tt_raw_off = o + hdr_len
                translate_ops(rc, rdtext.parse(tt_orig), rdtext.parse(tt_new))
            else:
                k = FONTS.index(name[:-4])
                rc.font(k, fonts_orig[k], data_plain)
            emit_len(hdr_len + size)
            cd_new.append((info, new_off, (0, crc, size, size, 10)))
        else:
            n = hdr_len + info.compress_size
            rc.add("O", o, n)
            emit_len(n)
            cd_new.append((info, new_off, None))

    # central directory: copy each original entry, patch offset (+ method/crc/sizes for replaced members)
    cd_start = out_len
    p = zin.start_dir
    cd = bytearray()
    for info, new_off, repl in cd_new:
        assert orig[p:p + 4] == CDH
        nlen, xlen, clen = struct.unpack_from("<HHH", orig, p + 28)
        ent = bytearray(orig[p:p + 46 + nlen + xlen + clen])
        assert ent[46:46 + nlen].decode("cp437") == info.filename
        assert xlen == 36 and ent[46 + nlen:48 + nlen] == b"\x0a\x00", "expected NTFS extra only (no zip64)"
        struct.pack_into("<I", ent, 42, new_off)
        if repl:
            method, crc, cs, us, ver = repl
            struct.pack_into("<H", ent, 6, ver)
            struct.pack_into("<H", ent, 10, method)
            struct.pack_into("<III", ent, 16, crc, cs, us)
        cd += ent
        p += len(ent)
    eocd_off = len(orig) - 22
    assert orig[eocd_off:eocd_off + 4] == EOCD and p == eocd_off
    eocd = bytearray(orig[eocd_off:])
    struct.pack_into("<II", eocd, 12, len(cd), cd_start)
    rc.lit(bytes(cd) + bytes(eocd))

    # reference apply + verification
    target = apply(rc.ops, orig, tt_orig, fonts_orig, rc.payload)
    for k, f in enumerate(FONTS):
        info = zin.getinfo(f + ".DAT")
        assert info.compress_type == 0
        o = raw_offset(orig, info)
        assert rdcrypt.decrypt(orig[o:o + info.compress_size]) == fonts_orig[k]
    zt = zipfile.ZipFile(__import__("io").BytesIO(target))
    assert zt.testzip() is None
    assert zt.namelist() == built.namelist()
    for n in built.namelist():
        assert zt.read(n) == built.read(n), n
    assert zipfile.ZipFile(src).read("translate.txt")[:2] == b"\xff\xfe"
    assert zlib.decompress(orig[tt_raw_off:tt_raw_off + zin.getinfo("translate.txt").compress_size], -15) == tt_orig

    key, iv = rdcrypt._key_iv()
    sha = lambda b: hashlib.sha256(b).hexdigest()
    out_dir = PATCH / "patch"
    out_dir.mkdir(parents=True, exist_ok=True)
    lines = [
        f"#source_size {len(orig)}", f"#source_sha256 {sha(orig)}",
        f"#target_size {len(target)}", f"#target_sha256 {sha(target)}",
        f"#tt_offset {tt_raw_off}", f"#tt_csize {zin.getinfo('translate.txt').compress_size}",
        f"#tt_size {len(tt_orig)}", f"#tt_sha256 {sha(tt_orig)}",
    ] + [
        f"#font{k} {raw_offset(orig, zin.getinfo(f + '.DAT'))} {zin.getinfo(f + '.DAT').compress_size} {sha(fonts_orig[k])}"
        for k, f in enumerate(FONTS)
    ] + [
        f"#payload_size {len(rc.payload)}", f"#payload_sha256 {sha(rc.payload)}",
        f"#aes_key {key.hex()}", f"#aes_iv {iv.hex()}",
    ] + [f"{s} {o} {n}" if s not in "[]" else s for s, o, n in rc.ops]
    (out_dir / "rd.ops").write_text("\n".join(lines) + "\n", encoding="ascii", newline="\n")
    (out_dir / "rd.bin").write_bytes(rc.payload)
    (BUILD / "data" / RD_DAT).write_bytes(target)
    print(f"ops={len(rc.ops)} payload={len(rc.payload)} target={len(target)} sha256={sha(target)[:16]}")


if __name__ == "__main__":
    sys.exit(main())
