# OpenCross Korean patch for the CHRONO CROSS Korean fan translation (CCRDE KR).
# Replaces OpenCross's built-in English battle words with Korean and fixes the post-battle heal window,
# which never registers its characters with the text atlas (only glyphs shown elsewhere appeared).
# Usage: put this file and OpenCross_한글패치.bat next to opencross.exe and run the .bat.
param([string]$Dir = $PSScriptRoot)
$ErrorActionPreference = "Stop"
Add-Type -TypeDefinition @"
using System;
using System.Collections.Generic;
using System.Text;
public static class OcKr {
    static readonly string[,] Words = new string[,] {
            {"Attack", "\uacf5\uaca9"},
            {"Element", "\uc5d8\ub9ac\uba58\ud0c8"},
            {"Defend", "\ubc29\uc5b4"},
            {"Run Away", "\ub3c4\ub9dd"},
            {"RunAway", "\ub3c4\ub9dd"},
            {"Poison", "\ub3c5"},
            {"Burns", "\ud654\uc0c1"},
            {"Cursed", "\uc800\uc8fc"},
            {"Confused", "\ud63c\ub780"},
            {"Asleep", "\uc218\uba74"},
            {"Darkness", "\uc554\ud751"},
            {"Afraid", "\uac81\uba39\uc74c"},
            {"Fatigued", "\uacfc\ub85c"},
            {"Sprain", "\uc5fc\uc88c"},
            {"Flu", "\uac10\uae30"},
            {"Dizzy", "\ud604\uae30\uc99d"},
            {"Frozen", "\ub3d9\uacb0"},
            {"INNATE:", "\uc18d\uc131:"},
            {"HIT%", "\uba85\uc911\ub960"},
            {"All Allies", "\uc544\uad70 \uc804\uccb4"},
            {"All Enemies", "\uc801 \uc804\uccb4"},
            {"All Enemies/Allies", "\uc801/\uc544\uad70 \uc804\uccb4"},
            {"New Game", "\uc0c8 \uac8c\uc784"},
            {"Continue", "\uc774\uc5b4\ud558\uae30"},
            {"New Game +", "\uc0c8 \uac8c\uc784 +"},
            {"Continue +", "\uc774\uc5b4\ud558\uae30 +"},
            {"Settings", "\uc124\uc815"},
            {"Press any button", "\uc544\ubb34 \ubc84\ud2bc\uc774\ub098 \ub204\ub974\uc138\uc694"},
            {"Quit", "\uc885\ub8cc"},
            {"Off", "\ub054"},
            {"Please enter a name...", "\uc774\ub984\uc744 \uc785\ub825\ud574 \uc8fc\uc138\uc694..."},
            {"Change Name", "\uc774\ub984 \ubcc0\uacbd"},
            {"Default", "\uae30\ubcf8\uac12"},
            {"Confirm", "\ud655\uc778"},
            {"Choose a slot (cancel: done)", "\uc2ac\ub86f\uc744 \uc120\ud0dd\ud558\uc138\uc694 (\ucde8\uc18c: \uc644\ub8cc)"},
            {"Current Party", "\ud604\uc7ac \ud30c\ud2f0"},
            {"Choose a character", "\uce90\ub9ad\ud130\ub97c \uc120\ud0dd\ud558\uc138\uc694"},
            {"Vibration Function", "\uc9c4\ub3d9 \uae30\ub2a5"},
            {"No save data in OpenCross.", "OpenCross \uc138\uc774\ube0c \ub370\uc774\ud130\uac00 \uc5c6\uc2b5\ub2c8\ub2e4."}
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
"@
$exe = Join-Path $Dir "opencross.exe"
if (-not (Test-Path $exe)) { Write-Host ((-join (0x6f,0x70,0x65,0x6e,0x63,0x72,0x6f,0x73,0x73,0x2e,0x65,0x78,0x65,0xb97c,0x20,0xcc3e,0xc9c0,0x20,0xbabb,0xd588,0xc2b5,0xb2c8,0xb2e4,0x2e,0x20,0xc774,0x20,0xd30c,0xc77c,0xb4e4,0xc744,0x20,0x6f,0x70,0x65,0x6e,0x63,0x72,0x6f,0x73,0x73,0x2e,0x65,0x78,0x65,0xc640,0x20,0xac19,0xc740,0x20,0xd3f4,0xb354,0xc5d0,0x20,0xb123,0xc5b4,0x20,0xc8fc,0xc138,0xc694,0x3a | % { [char]$_ })) + " $exe"); exit 1 }
$bytes = [IO.File]::ReadAllBytes($exe)
$changed = 0
$report = [OcKr]::Patch($bytes, [ref]$changed)
$w = ($report -split "`n" | ? { $_ -like "WORDS*" }) -split " "
$h = (($report -split "`n" | ? { $_ -like "HEAL*" }) -split " ")[1].Trim()
if ($changed -eq 0) {
  Write-Host (-join (0xc774,0xbbf8,0x20,0xc801,0xc6a9,0xb418,0xc5b4,0x20,0xc788,0xc2b5,0xb2c8,0xb2e4,0x2e,0x20,0xbc14,0xafc0,0x20,0xac83,0xc774,0x20,0xc5c6,0xc2b5,0xb2c8,0xb2e4,0x2e | % { [char]$_ }))
  exit 0
} else {
  $bak = "$exe.orig"
  $hookState = (($report -split "`n" | ? { $_ -like "HOOK*" }) -split " ")[1].Trim()
  try {
    # back up only an untouched exe (fresh install or after an OpenCross update), never a patched one
    if ($hookState -eq "OK" -or -not (Test-Path $bak)) { Copy-Item $exe $bak -Force }
    [IO.File]::WriteAllBytes($exe, $bytes)
  } catch { Write-Host (-join (0x6f,0x70,0x65,0x6e,0x63,0x72,0x6f,0x73,0x73,0x2e,0x65,0x78,0x65,0xc5d0,0x20,0xc4f8,0x20,0xc218,0x20,0xc5c6,0xc2b5,0xb2c8,0xb2e4,0x2e,0x20,0x4f,0x70,0x65,0x6e,0x43,0x72,0x6f,0x73,0x73,0xb97c,0x20,0xb044,0xace0,0x20,0xb2e4,0xc2dc,0x20,0xc2e4,0xd589,0xd574,0x20,0xc8fc,0xc138,0xc694,0x2e | % { [char]$_ })); exit 1 }
  Write-Host ((-join (0xc801,0xc6a9,0x20,0xc644,0xb8cc,0x2e,0x20,0xc6d0,0xbcf8,0x20,0xbc31,0xc5c5,0x3a | % { [char]$_ })) + " $bak")
}
$k = (($report -split "`n" | ? { $_ -like "HOOK*" }) -split " ")[1].Trim()
Write-Host ((-join (0xc601,0xc5b4,0x20,0xbb38,0xad6c,0x20,0xd55c,0xae00,0xd654,0x3a | % { [char]$_ })) + " " + $w[1] + "/39")
if ([int]$w[2] -gt 0) { Write-Host ((-join (0xc774,0x20,0xbc84,0xc804,0xc5d0,0xc11c,0x20,0xcc3e,0xc9c0,0x20,0xbabb,0xd55c,0x20,0xb2e8,0xc5b4,0x20,0xc218,0x3a | % { [char]$_ })) + " " + $w[2]) }
switch ($h) { "OK" { Write-Host (-join (0xacb0,0xacfc,0xcc3d,0x20,0xd68c,0xbcf5,0x20,0xba54,0xb274,0x20,0xae00,0xc790,0x20,0xc218,0xc815,0x3a,0x20,0xc801,0xc6a9,0xb428 | % { [char]$_ })) } "ALREADY" { Write-Host (-join (0xacb0,0xacfc,0xcc3d,0x20,0xd68c,0xbcf5,0x20,0xba54,0xb274,0x20,0xae00,0xc790,0x20,0xc218,0xc815,0x3a,0x20,0xc801,0xc6a9,0xb428 | % { [char]$_ })) } default { Write-Host (-join (0xacb0,0xacfc,0xcc3d,0x20,0xd68c,0xbcf5,0x20,0xba54,0xb274,0x20,0xae00,0xc790,0x20,0xc218,0xc815,0x3a,0x20,0xc774,0x20,0x4f,0x70,0x65,0x6e,0x43,0x72,0x6f,0x73,0x73,0x20,0xbc84,0xc804,0xc5d0,0xc11c,0xb294,0x20,0xc704,0xce58,0xb97c,0x20,0xcc3e,0xc9c0,0x20,0xbabb,0xd574,0x20,0xac74,0xb108,0xb700 | % { [char]$_ })) } }
switch ($k) { "OK" { Write-Host (-join (0xd55c,0xae00,0x20,0xae00,0xc790,0x20,0xbe60,0xc9d0,0x20,0xc218,0xc815,0x3a,0x20,0xc801,0xc6a9,0xb428 | % { [char]$_ })) } "ALREADY" { Write-Host (-join (0xd55c,0xae00,0x20,0xae00,0xc790,0x20,0xbe60,0xc9d0,0x20,0xc218,0xc815,0x3a,0x20,0xc801,0xc6a9,0xb428 | % { [char]$_ })) } default { Write-Host (-join (0xd55c,0xae00,0x20,0xae00,0xc790,0x20,0xbe60,0xc9d0,0x20,0xc218,0xc815,0x3a,0x20,0xc774,0x20,0x4f,0x70,0x65,0x6e,0x43,0x72,0x6f,0x73,0x73,0x20,0xbc84,0xc804,0xc5d0,0xc11c,0xb294,0x20,0xc704,0xce58,0xb97c,0x20,0xcc3e,0xc9c0,0x20,0xbabb,0xd574,0x20,0xac74,0xb108,0xb700 | % { [char]$_ })) } }
