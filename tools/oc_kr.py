"""oc_kr.py <opencross.exe> [--dry]: replace OpenCross's hardcoded English battle words (UTF-32LE, NUL-terminated)
with the Korean used in our cmnmes.txt. Each string must be found whole (NUL before and after) and the Korean must
not be longer; the rest is NUL-padded. The original is kept as opencross.exe.orig (rename works on a running exe)."""
import shutil
import sys
from pathlib import Path

KO = {
    "Attack": "공격", "Element": "엘리멘탈", "Defend": "방어", "Run Away": "도망", "RunAway": "도망",
    "Poison": "독", "Burns": "화상", "Cursed": "저주", "Confused": "혼란", "Asleep": "수면", "Darkness": "암흑",
    "Afraid": "겁먹음", "Fatigued": "과로", "Sprain": "염좌", "Flu": "감기", "Dizzy": "현기증", "Frozen": "동결",
    "INNATE:": "속성:", "HIT%": "명중률",
    "All Allies": "아군 전체", "All Enemies": "적 전체", "All Enemies/Allies": "적/아군 전체",
    # OpenCross title / name entry / party / options (not in the game's own tables)
    "New Game": "새 게임", "Continue": "이어하기", "New Game +": "새 게임 +", "Continue +": "이어하기 +",
    "Settings": "설정", "Press any button": "아무 버튼이나 누르세요", "Quit": "종료", "Off": "끔",
    "Please enter a name...": "이름을 입력해 주세요...", "Change Name": "이름 변경", "Default": "기본값",
    "Confirm": "확인", "Choose a slot (cancel: done)": "슬롯을 선택하세요 (취소: 완료)",
    "Current Party": "현재 파티", "Choose a character": "캐릭터를 선택하세요", "Vibration Function": "진동 기능",
    "No save data in OpenCross.": "OpenCross 세이브 데이터가 없습니다.",
}


def u32(s):
    return s.encode("utf-32-le")


def patch(b: bytearray):
    report = []
    for en, ko in KO.items():
        assert len(ko) <= len(en), en
        # a whole string: aligned, and not the tail of another word (e.g. JP "強くてNew Game"); long phrases exempt
        hits = []
        pat = u32(en) + b"\0\0\0\0"
        i = b.find(pat)
        while i >= 0:
            prev = int.from_bytes(b[i - 4:i], "little")
            if i % 4 == 0 and (prev == 0 or not (0x20 <= prev < 0x10000 and chr(prev).isalpha()) or len(en) >= 12):
                hits.append(i)
            i = b.find(pat, i + 1)
        for h in hits:
            b[h:h + 4 * len(en)] = u32(ko) + b"\0" * (4 * (len(en) - len(ko)))
        report.append((en, ko, [hex(h) for h in hits]))
    return report


import re  # noqa: E402

# Heal window after battle (btlexit rows 18/21/23/25) is drawn by a function that measures and draws each line but never
# registers its characters with the text atlas, so only glyphs some other screen already registered show up (ASCII is
# always there, Hangul is not). Its measure result is unused, so retarget that call to FontSet's register function, which
# takes the same arguments (rcx=FontSet, edx=font id, r8=&u32string_view).
SITE = re.compile(re.escape(bytes.fromhex("49 8d 8d 40 07 00 00")) + b"\xe8(....)" +
                  re.escape(bytes.fromhex("c7 44 24 50 cf c5 c5 ff")), re.S)
REQUEST = bytes.fromhex("48 89 5c 24 08 48 89 74 24 10 57 48 83 ec 30 49 8b f0 8b da")
MEASURE = bytes.fromhex("48 89 5c 24 20 41 56 48 83 ec 30 49 8b d8")


def code_patch(b: bytearray):
    import struct
    pe = struct.unpack_from("<I", b, 0x3C)[0]
    so = pe + 24 + struct.unpack_from("<H", b, pe + 20)[0]
    secs = []
    for i in range(struct.unpack_from("<H", b, pe + 6)[0]):
        o = so + 40 * i
        vs, va, rs, ra = struct.unpack_from("<IIII", b, o + 8)
        secs.append((va, rs, ra))

    def rva(off):
        for va, rs, ra in secs:
            if ra <= off < ra + rs:
                return va + off - ra

    def off(r):
        for va, rs, ra in secs:
            if va <= r < va + rs:
                return ra + r - va

    sites = list(SITE.finditer(b))
    req = [m.start() for m in re.finditer(re.escape(REQUEST), b)]
    if len(sites) != 1 or len(req) != 1:
        return f"heal-window fix skipped: {len(sites)} call site(s), {len(req)} register function(s) found"
    m = sites[0]
    call = m.start() + 7
    rel = struct.unpack_from("<i", b, call + 1)[0]
    tgt_rva = rva(call) + 5 + rel
    req_rva = rva(req[0])
    if tgt_rva == req_rva:
        return "heal-window fix already applied"
    if b[off(tgt_rva):off(tgt_rva) + len(MEASURE)] != MEASURE:
        return "heal-window fix skipped: call target is not the measure function"
    struct.pack_into("<i", b, call + 1, req_rva - (rva(call) + 5))
    return f"heal-window fix applied at file offset {call:#x}"


DRAW = bytes.fromhex("48 89 4c 24 08 56 57 41 56 41 57 48 81 ec 28 01 00 00")


def draw_hook(b: bytearray):
    """Every FontSet draw first registers its text (same args: rcx=FontSet, edx=font id, r8=&view), so no screen can
    show a glyph that was never registered. Code goes into the zero slack at the end of .text."""
    import struct
    pe = struct.unpack_from("<I", b, 0x3C)[0]
    so = pe + 24 + struct.unpack_from("<H", b, pe + 20)[0]
    text = None
    secs = []
    for i in range(struct.unpack_from("<H", b, pe + 6)[0]):
        o = so + 40 * i
        vs, va, rs, ra = struct.unpack_from("<IIII", b, o + 8)
        secs.append((va, rs, ra))
        if b[o:o + 6] == b".text\0":
            text = (o, vs, va, rs, ra)
    so_, vs, va, rs, ra = text

    def rva(off):
        for v, r, a in secs:
            if a <= off < a + r:
                return v + off - a

    draws = [m.start() for m in re.finditer(re.escape(DRAW), b)]
    reqs = [m.start() for m in re.finditer(re.escape(REQUEST), b)]
    cave_off = ra + ((vs + 15) & ~15)
    if len(reqs) != 1:
        return "draw hook skipped: register function not found"
    if not draws:
        if b[cave_off:cave_off + 4] == bytes.fromhex("51 52 41 50"):
            return "draw hook already applied"
        return "draw hook skipped: draw function not found"
    if len(draws) != 1:
        return "draw hook skipped: draw function ambiguous"
    if cave_off + 64 > ra + rs or any(b[cave_off:cave_off + 64]):
        return "draw hook skipped: no room at the end of .text"
    cave, req, draw = rva(cave_off), rva(reqs[0]), rva(draws[0])
    c = bytearray(bytes.fromhex("51 52 41 50 41 51 48 83 ec 48 f3 0f 7f 54 24 20 f3 0f 7f 5c 24 30"))
    c += b"\xe8" + struct.pack("<i", req - (cave + len(c) + 5))
    c += bytes.fromhex("f3 0f 6f 54 24 20 f3 0f 6f 5c 24 30 48 83 c4 48 41 59 41 58 5a 59 48 89 4c 24 08")
    c += b"\xe9" + struct.pack("<i", draw + 5 - (cave + len(c) + 5))
    b[cave_off:cave_off + len(c)] = c
    b[draws[0]:draws[0] + 5] = b"\xe9" + struct.pack("<i", cave - (draw + 5))
    struct.pack_into("<I", b, so_ + 8, max(vs, (cave_off - ra) + len(c)))  # VirtualSize covers the cave
    return f"draw hook applied (cave rva {cave:#x})"


def main():
    exe = Path(sys.argv[1])
    dry = "--dry" in sys.argv
    orig = exe.with_name(exe.name + ".orig")
    src = orig if orig.exists() else exe
    b = bytearray(src.read_bytes())
    rep = patch(b)
    for r in rep:
        print(r)
    miss = [r[0] for r in rep if not r[2]]
    print("missing:", miss)
    print(code_patch(b))
    print(draw_hook(b))
    if dry:
        return
    if not orig.exists():
        exe.rename(orig)
    tmp = exe.with_name(exe.name + ".new")
    tmp.write_bytes(b)
    if exe.exists():  # a running exe cannot be deleted but can be renamed
        old = exe.with_name(exe.name + f".old{int(__import__('time').time())}")
        exe.rename(old)
    tmp.rename(exe)
    print("patched", exe, "from", src)


main()
