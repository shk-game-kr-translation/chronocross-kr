"""gen_ocpatch.py: write patch_kit/opencross/{OpenCross_한글패치.bat, opencross_kr.ps1} (Windows PowerShell 5.1, no Python).
Same logic as tools/opencross_kr.py: Korean battle words in place of OpenCross's hardcoded English, plus the heal-window
glyph registration fix. Korean is written as \\u escapes so the script's own encoding cannot break it."""
from pathlib import Path

ROOT = Path(r"D:\Game\kr_translate\CHRONO-CROSS-THE-RADICAL-DREAMERS-EDITION")
OUT = ROOT / "patch_kit" / "opencross"
import ast  # noqa: E402

_src = (Path(__file__).parent / "oc_kr.py").read_text(encoding="utf-8")
KO = next(ast.literal_eval(n.value) for n in ast.parse(_src).body
          if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == "KO")


def esc(s):
    return "".join(c if 32 <= ord(c) < 127 and c not in '"\\' else f"\\u{ord(c):04x}" for c in s)


words = ",\n            ".join(f'{{"{esc(k)}", "{esc(v)}"}}' for k, v in KO.items())


def msg(s):  # Korean console text for PowerShell, built from code points
    return "(-join (" + ",".join(f"0x{ord(c):x}" for c in s) + " | % { [char]$_ }))"


CS = r'''
using System;
using System.Collections.Generic;
using System.Text;
public static class OcKr {
    static readonly string[,] Words = new string[,] {
            @@WORDS@@
    };
    static byte[] U32(string s) { return new UTF32Encoding(false, false).GetBytes(s); }
    static int Find(byte[] b, byte[] p, int from) {
        for (int i = from; i <= b.Length - p.Length; i++) {
            if (b[i] != p[0]) continue;
            int k = 1; while (k < p.Length && b[i + k] == p[k]) k++;
            if (k == p.Length) return i;
        }
        return -1;
    }
    static List<int> FindAll(byte[] b, byte[] p) {
        var r = new List<int>(); int i = Find(b, p, 0);
        while (i >= 0) { r.Add(i); i = Find(b, p, i + 1); }
        return r;
    }
    static bool IsLetter(int v) { return v >= 0x20 && v < 0x10000 && char.IsLetter((char)v); }
    // returns lines of report; changed = number of modifications
    public static string Patch(byte[] b, out int changed) {
        var sb = new StringBuilder(); changed = 0; int done = 0, missing = 0;
        for (int w = 0; w < Words.GetLength(0); w++) {
            string en = Words[w, 0], ko = Words[w, 1];
            byte[] pe = U32(en), pk = U32(ko);
            var tail = new byte[pe.Length + 4]; Buffer.BlockCopy(pe, 0, tail, 0, pe.Length);
            // a whole string: aligned, and not the tail of another word (e.g. JP "強くてNew Game"); long phrases exempt
            var use = new List<int>();
            foreach (int i in FindAll(b, tail)) {
                if (i % 4 != 0 || i < 4) continue;
                int prev = BitConverter.ToInt32(b, i - 4);
                if (prev == 0 || !IsLetter(prev) || en.Length >= 12) use.Add(i);
            }
            int hits = 0;
            foreach (int i in use) {
                Array.Clear(b, i, pe.Length); Buffer.BlockCopy(pk, 0, b, i, pk.Length);
                hits++; changed++;
            }
            if (hits > 0) done++;
            else {
                var tk = new byte[pk.Length + 4]; Buffer.BlockCopy(pk, 0, tk, 0, pk.Length);
                if (FindAll(b, tk).Count == 0) missing++;
            }
        }
        sb.AppendLine("WORDS " + done + " " + missing);
        sb.AppendLine("HEAL " + HealFix(b, ref changed));
        sb.AppendLine("HOOK " + DrawHook(b, ref changed));
        return sb.ToString();
    }
    // Every FontSet draw first registers its text with the glyph atlas (same arguments as the register function).
    static string DrawHook(byte[] b, ref int changed) {
        byte[] draw = { 0x48, 0x89, 0x4c, 0x24, 0x08, 0x56, 0x57, 0x41, 0x56, 0x41, 0x57, 0x48, 0x81, 0xec, 0x28, 0x01, 0x00, 0x00 };
        byte[] req = { 0x48, 0x89, 0x5c, 0x24, 0x08, 0x48, 0x89, 0x74, 0x24, 0x10, 0x57, 0x48, 0x83, 0xec, 0x30, 0x49, 0x8b, 0xf0, 0x8b, 0xda };
        int pe = BitConverter.ToInt32(b, 0x3c);
        int n = BitConverter.ToUInt16(b, pe + 6);
        int so = pe + 24 + BitConverter.ToUInt16(b, pe + 20);
        int th = -1;
        for (int i = 0; i < n; i++) { int o = so + 40 * i; if (b[o] == 0x2e && b[o + 1] == 0x74 && b[o + 2] == 0x65 && b[o + 3] == 0x78 && b[o + 4] == 0x74 && b[o + 5] == 0) th = o; }
        if (th < 0) return "SKIP";
        int vs = BitConverter.ToInt32(b, th + 8), va = BitConverter.ToInt32(b, th + 12), rs = BitConverter.ToInt32(b, th + 16), ra = BitConverter.ToInt32(b, th + 20);
        int caveOff = ra + ((vs + 15) & ~15);
        var draws = FindAll(b, draw); var reqs = FindAll(b, req);
        if (reqs.Count != 1) return "SKIP";
        if (draws.Count == 0) return (b[caveOff] == 0x51 && b[caveOff + 1] == 0x52 && b[caveOff + 2] == 0x41 && b[caveOff + 3] == 0x50) ? "ALREADY" : "SKIP";
        if (draws.Count != 1 || caveOff + 64 > ra + rs) return "SKIP";
        for (int k = 0; k < 64; k++) if (b[caveOff + k] != 0) return "SKIP";
        long cave = Rva(b, caveOff), rq = Rva(b, reqs[0]), dr = Rva(b, draws[0]);
        var c = new List<byte>(new byte[] { 0x51, 0x52, 0x41, 0x50, 0x41, 0x51, 0x48, 0x83, 0xec, 0x48, 0xf3, 0x0f, 0x7f, 0x54, 0x24, 0x20, 0xf3, 0x0f, 0x7f, 0x5c, 0x24, 0x30 });
        c.Add(0xe8); c.AddRange(BitConverter.GetBytes((int)(rq - (cave + c.Count + 4))));
        c.AddRange(new byte[] { 0xf3, 0x0f, 0x6f, 0x54, 0x24, 0x20, 0xf3, 0x0f, 0x6f, 0x5c, 0x24, 0x30, 0x48, 0x83, 0xc4, 0x48, 0x41, 0x59, 0x41, 0x58, 0x5a, 0x59, 0x48, 0x89, 0x4c, 0x24, 0x08 });
        c.Add(0xe9); c.AddRange(BitConverter.GetBytes((int)(dr + 5 - (cave + c.Count + 4))));
        c.CopyTo(b, caveOff);
        b[draws[0]] = 0xe9; Buffer.BlockCopy(BitConverter.GetBytes((int)(cave - (dr + 5))), 0, b, draws[0] + 1, 4);
        int need = caveOff - ra + c.Count;
        if (need > vs) Buffer.BlockCopy(BitConverter.GetBytes(need), 0, b, th + 8, 4);
        changed++;
        return "OK";
    }
    static string HealFix(byte[] b, ref int changed) {
        byte[] pre = { 0x49, 0x8d, 0x8d, 0x40, 0x07, 0x00, 0x00, 0xe8 };
        byte[] post = { 0xc7, 0x44, 0x24, 0x50, 0xcf, 0xc5, 0xc5, 0xff };
        byte[] req = { 0x48, 0x89, 0x5c, 0x24, 0x08, 0x48, 0x89, 0x74, 0x24, 0x10, 0x57, 0x48, 0x83, 0xec, 0x30, 0x49, 0x8b, 0xf0, 0x8b, 0xda };
        byte[] mea = { 0x48, 0x89, 0x5c, 0x24, 0x20, 0x41, 0x56, 0x48, 0x83, 0xec, 0x30, 0x49, 0x8b, 0xd8 };
        var sites = new List<int>();
        foreach (int i in FindAll(b, pre)) {
            bool ok = true;
            for (int k = 0; k < post.Length; k++) if (b[i + 12 + k] != post[k]) { ok = false; break; }
            if (ok) sites.Add(i + 7);
        }
        var reqs = FindAll(b, req);
        if (sites.Count != 1 || reqs.Count != 1) return "SKIP";
        int call = sites[0];
        long callRva = Rva(b, call), reqRva = Rva(b, reqs[0]);
        if (callRva < 0 || reqRva < 0) return "SKIP";
        long tgt = callRva + 5 + BitConverter.ToInt32(b, call + 1);
        if (tgt == reqRva) return "ALREADY";
        int toff = Off(b, tgt);
        if (toff < 0) return "SKIP";
        for (int k = 0; k < mea.Length; k++) if (b[toff + k] != mea[k]) return "SKIP";
        byte[] rel = BitConverter.GetBytes((int)(reqRva - (callRva + 5)));
        Buffer.BlockCopy(rel, 0, b, call + 1, 4); changed++;
        return "OK";
    }
    static void Sections(byte[] b, Func<int, int, int, bool> f) {
        int pe = BitConverter.ToInt32(b, 0x3c);
        int n = BitConverter.ToUInt16(b, pe + 6);
        int so = pe + 24 + BitConverter.ToUInt16(b, pe + 20);
        for (int i = 0; i < n; i++) {
            int o = so + 40 * i;
            int va = BitConverter.ToInt32(b, o + 12), rs = BitConverter.ToInt32(b, o + 16), ra = BitConverter.ToInt32(b, o + 20);
            if (f(va, rs, ra)) return;
        }
    }
    static long Rva(byte[] b, int off) {
        long r = -1;
        Sections(b, (va, rs, ra) => { if (off >= ra && off < ra + rs) { r = (long)va + off - ra; return true; } return false; });
        return r;
    }
    static int Off(byte[] b, long rva) {
        int r = -1;
        Sections(b, (va, rs, ra) => { if (rva >= va && rva < va + rs) { r = (int)(ra + rva - va); return true; } return false; });
        return r;
    }
}
'''.replace("@@WORDS@@", words)

PS = r'''# OpenCross Korean patch for the CHRONO CROSS Korean fan translation (CCRDE KR).
# Replaces OpenCross's built-in English battle words with Korean and fixes the post-battle heal window,
# which never registers its characters with the text atlas (only glyphs shown elsewhere appeared).
# Usage: put this file and OpenCross_한글패치.bat next to opencross.exe and run the .bat.
param([string]$Dir = $PSScriptRoot)
$ErrorActionPreference = "Stop"
Add-Type -TypeDefinition @"
@@CS@@
"@
$exe = Join-Path $Dir "opencross.exe"
if (-not (Test-Path $exe)) { Write-Host (MSG_NOEXE + " $exe"); exit 1 }
$bytes = [IO.File]::ReadAllBytes($exe)
$changed = 0
$report = [OcKr]::Patch($bytes, [ref]$changed)
$w = ($report -split "`n" | ? { $_ -like "WORDS*" }) -split " "
$h = (($report -split "`n" | ? { $_ -like "HEAL*" }) -split " ")[1].Trim()
if ($changed -eq 0) {
  Write-Host MSG_NOCHANGE
  exit 0
} else {
  $bak = "$exe.orig"
  $hookState = (($report -split "`n" | ? { $_ -like "HOOK*" }) -split " ")[1].Trim()
  try {
    # back up only an untouched exe (fresh install or after an OpenCross update), never a patched one
    if ($hookState -eq "OK" -or -not (Test-Path $bak)) { Copy-Item $exe $bak -Force }
    [IO.File]::WriteAllBytes($exe, $bytes)
  } catch { Write-Host MSG_LOCKED; exit 1 }
  Write-Host (MSG_DONE + " $bak")
}
$k = (($report -split "`n" | ? { $_ -like "HOOK*" }) -split " ")[1].Trim()
Write-Host (MSG_WORDS + " " + $w[1] + "/@@NWORDS@@")
if ([int]$w[2] -gt 0) { Write-Host (MSG_WORDMISS + " " + $w[2]) }
switch ($h) { "OK" { Write-Host MSG_HEALOK } "ALREADY" { Write-Host MSG_HEALOK } default { Write-Host MSG_HEALSKIP } }
switch ($k) { "OK" { Write-Host MSG_HOOKOK } "ALREADY" { Write-Host MSG_HOOKOK } default { Write-Host MSG_HOOKSKIP } }
'''
PS = PS.replace("@@CS@@", CS.strip()).replace("@@NWORDS@@", str(len(KO)))
for k, s in {
    "MSG_NOEXE": "opencross.exe를 찾지 못했습니다. 이 파일들을 opencross.exe와 같은 폴더에 넣어 주세요:",
    "MSG_NOCHANGE": "이미 적용되어 있습니다. 바꿀 것이 없습니다.",
    "MSG_LOCKED": "opencross.exe에 쓸 수 없습니다. OpenCross를 끄고 다시 실행해 주세요.",
    "MSG_DONE": "적용 완료. 원본 백업:",
    "MSG_HOOKOK": "한글 글자 빠짐 수정: 적용됨",
    "MSG_HOOKSKIP": "한글 글자 빠짐 수정: 이 OpenCross 버전에서는 위치를 찾지 못해 건너뜀",
    "MSG_WORDS": "영어 문구 한글화:",
    "MSG_WORDMISS": "이 버전에서 찾지 못한 단어 수:",
    "MSG_HEALOK": "결과창 회복 메뉴 글자 수정: 적용됨",
    "MSG_HEALSKIP": "결과창 회복 메뉴 글자 수정: 이 OpenCross 버전에서는 위치를 찾지 못해 건너뜀",
}.items():
    PS = PS.replace(k, msg(s))

BAT = ('@echo off\r\n'
       'powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0opencross_kr.ps1" "%~dp0."\r\n'
       'pause\r\n')
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "opencross_kr.ps1").write_text(PS, encoding="utf-8-sig", newline="\r\n")
(OUT / "OpenCross_한글패치.bat").write_bytes(BAT.encode("ascii"))
print([(p.name, p.stat().st_size) for p in OUT.iterdir()])
