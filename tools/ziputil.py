"""Raw-level ZIP rebuild for the game's data/*.dat archives.

rebuild(src_bytes, repl) -> bytes
  Unchanged members are copied byte-for-byte (local header + compressed data); members in `repl` are written
  STORED (or DEFLATED when deflate=True) with patched local header fields; the central directory is rebuilt from
  the original entries (extra fields / timestamps kept) with new offsets, sizes and CRCs.
Also returns a layout list so tools/make_patch.py-style recipes can reference original byte ranges.
"""
import struct
import zipfile
import zlib
import io

LFH, CDH, EOCD = b"PK\x03\x04", b"PK\x01\x02", b"PK\x05\x06"


def raw_offset(orig, info):
    o = info.header_offset
    nlen, xlen = struct.unpack_from("<HH", orig, o + 26)
    return o + 30 + nlen + xlen


def rebuild(orig: bytes, repl: dict, deflate=False):
    """Return (new_bytes, layout). layout = list of ("O", off, len) | ("N", name, hdr_bytes, data_bytes) | ("C", bytes)."""
    zin = zipfile.ZipFile(io.BytesIO(orig))
    infos = zin.infolist()
    out = bytearray()
    layout, cd_new = [], []
    repl = dict(repl)
    for info in infos:
        o = info.header_offset
        assert orig[o:o + 4] == LFH
        hdr_len = raw_offset(orig, info) - o
        new_off = len(out)
        if info.filename in repl:
            plain = repl.pop(info.filename)
            if deflate:
                c = zlib.compressobj(9, zlib.DEFLATED, -15)
                data, method, ver = c.compress(plain) + c.flush(), 8, 20
            else:
                data, method, ver = plain, 0, 10
            crc = zlib.crc32(plain)
            hdr = bytearray(orig[o:o + hdr_len])
            struct.pack_into("<H", hdr, 4, ver)
            struct.pack_into("<H", hdr, 6, struct.unpack_from("<H", hdr, 6)[0] & ~0x8)  # no data descriptor
            struct.pack_into("<H", hdr, 8, method)
            struct.pack_into("<III", hdr, 14, crc, len(data), len(plain))
            out += hdr
            out += data
            layout.append(("N", info.filename, bytes(hdr), data))
            cd_new.append((info, new_off, (ver, method, crc, len(data), len(plain))))
        else:
            assert not info.flag_bits & 0x8, f"{info.filename}: data descriptor not supported"
            n = hdr_len + info.compress_size
            out += orig[o:o + n]
            layout.append(("O", o, n))
            cd_new.append((info, new_off, None))
    assert not repl, f"members not in archive: {list(repl)}"
    cd_start = len(out)
    p = zin.start_dir
    cd = bytearray()
    for info, new_off, r in cd_new:
        assert orig[p:p + 4] == CDH
        nlen, xlen, clen = struct.unpack_from("<HHH", orig, p + 28)
        ent = bytearray(orig[p:p + 46 + nlen + xlen + clen])
        struct.pack_into("<I", ent, 42, new_off)
        if r:
            ver, method, crc, cs, us = r
            struct.pack_into("<H", ent, 6, ver)
            struct.pack_into("<H", ent, 8, struct.unpack_from("<H", ent, 8)[0] & ~0x8)
            struct.pack_into("<H", ent, 10, method)
            struct.pack_into("<III", ent, 16, crc, cs, us)
        cd += ent
        p += len(ent)
    eocd_off = len(orig) - 22
    assert orig[eocd_off:eocd_off + 4] == EOCD and p == eocd_off, "zip comment / zip64 not supported"
    eocd = bytearray(orig[eocd_off:])
    struct.pack_into("<II", eocd, 12, len(cd), cd_start)
    tail = bytes(cd) + bytes(eocd)
    out += tail
    layout.append(("C", tail))
    return bytes(out), layout
