"""Radical Dreamers *.DAT font container cipher.

RADICALDREAMERS.exe (Steam build 8116082) loads data\\radicaldreamers\\<NAME>.DAT through 0x41b4e3:
  seed (16 bytes @ .rdata 0x5ea5e0) -> 0x409070 makes a GUID-style string from a running XOR of the
  eight LE u16 words -> 0x408d30 SHA-256(string) -> key = digest[:16], IV = digest[16:]
  -> 0x408ed0 BCrypt AES-128-CBC decrypt, PKCS#7 padding.
The plaintext is a TrueType (ENFONT*) or CFF OpenType (JPFONT) file handed to the embedded FreeType.
"""
import hashlib
import struct

from Crypto.Cipher import AES

FONT_SEED = bytes.fromhex("48db6d9b2d5f3b10f1e689250fe9b84d")


def _password(seed: bytes) -> str:
    w = struct.unpack("<8H", seed)
    a = [w[0] ^ w[7]]
    for k in range(1, 7):
        a.append(a[-1] ^ w[k])
    a.append(w[7] ^ a[6])
    return "%04x%04x-%04x-%04x-%04x-%04x%04x%04x" % tuple(a)


def _key_iv(seed: bytes = FONT_SEED):
    h = hashlib.sha256(_password(seed).encode("ascii")).digest()
    return h[:16], h[16:]


def decrypt(data: bytes, seed: bytes = FONT_SEED) -> bytes:
    key, iv = _key_iv(seed)
    p = AES.new(key, AES.MODE_CBC, iv).decrypt(data)
    n = p[-1]
    if not 1 <= n <= 16 or p[-n:] != bytes([n]) * n:
        raise ValueError("bad PKCS#7 padding (wrong key or not a font container)")
    return p[:-n]


def encrypt(data: bytes, seed: bytes = FONT_SEED) -> bytes:
    key, iv = _key_iv(seed)
    n = 16 - len(data) % 16
    return AES.new(key, AES.MODE_CBC, iv).encrypt(data + bytes([n]) * n)
