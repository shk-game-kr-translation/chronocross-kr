# CHRONO CROSS: THE RADICAL DREAMERS EDITION 한글 패치 적용/복구 스크립트
#   apply.ps1 [-GameDir <게임 폴더>] [-Restore]
# 원본 data\radicaldreamers.dat 를 검증한 뒤 patch\rd.ops 레시피대로 새 파일을 만들고 SHA-256 을 확인한다.
# 원본은 data\radicaldreamers.dat.kr_backup 으로 보관하며 -Restore 로 되돌린다.
param([string]$GameDir = "", [switch]$Restore)

$ErrorActionPreference = "Stop"
$Here = $PSScriptRoot
$DatName = "radicaldreamers.dat"
$GameFolder = "CHRONO CROSS  THE RADICAL DREAMERS EDITION"

function Say($msg) { Write-Host $msg }
function Fail($msg) { Write-Host ""; Write-Host "[오류] $msg" -ForegroundColor Red; exit 1 }

function Sha256File($path) {
    $s = [System.IO.File]::OpenRead($path)
    try { $h = [System.Security.Cryptography.SHA256]::Create().ComputeHash($s) } finally { $s.Dispose() }
    return ([System.BitConverter]::ToString($h) -replace "-", "").ToLower()
}
function Sha256Bytes([byte[]]$b) {
    $h = [System.Security.Cryptography.SHA256]::Create().ComputeHash($b)
    return ([System.BitConverter]::ToString($h) -replace "-", "").ToLower()
}
function HexBytes([string]$hex) {
    $b = New-Object byte[] ($hex.Length / 2)
    for ($i = 0; $i -lt $b.Length; $i++) { $b[$i] = [Convert]::ToByte($hex.Substring($i * 2, 2), 16) }
    return ,$b
}

function Find-SteamGameDirs {
    $dirs = @()
    $steam = $null
    foreach ($k in "HKCU:\Software\Valve\Steam", "HKLM:\SOFTWARE\WOW6432Node\Valve\Steam", "HKLM:\SOFTWARE\Valve\Steam") {
        try {
            $p = Get-ItemProperty -Path $k -ErrorAction Stop
            if ($p.SteamPath) { $steam = $p.SteamPath } elseif ($p.InstallPath) { $steam = $p.InstallPath }
            if ($steam) { break }
        } catch {}
    }
    if (-not $steam) { return $dirs }
    $libs = @($steam)
    $vdf = Join-Path $steam "steamapps\libraryfolders.vdf"
    if (Test-Path -LiteralPath $vdf) {
        foreach ($m in [regex]::Matches((Get-Content -LiteralPath $vdf -Raw), '"path"\s+"([^"]+)"')) {
            $libs += $m.Groups[1].Value -replace "\\\\", "\"
        }
    }
    foreach ($l in $libs) { $dirs += (Join-Path $l "steamapps\common\$GameFolder") }
    return $dirs
}

function Resolve-GameDir {
    $cands = @()
    if ($GameDir) { $cands += $GameDir }
    $cands += $Here, (Split-Path -Parent $Here)
    $cands += Find-SteamGameDirs
    foreach ($d in $cands) {
        if ($d -and (Test-Path -LiteralPath (Join-Path $d "data\$DatName")) -and (Test-Path -LiteralPath (Join-Path $d "RADICALDREAMERS.exe"))) {
            return (Resolve-Path -LiteralPath $d).Path
        }
    }
    if ($GameDir) { Fail "지정한 폴더에서 게임을 찾지 못했습니다: $GameDir" }
    Fail "게임 폴더를 찾지 못했습니다. 패치 폴더를 게임 폴더(RADICALDREAMERS.exe 가 있는 곳) 안에 넣고 다시 실행하거나, 게임 폴더를 인자로 지정해 주세요."
}

# --- 레시피 읽기 ---
$opsPath = Join-Path $Here "patch\rd.ops"
$binPath = Join-Path $Here "patch\rd.bin"
if (-not (Test-Path -LiteralPath $opsPath) -or -not (Test-Path -LiteralPath $binPath)) { Fail "patch 폴더(rd.ops, rd.bin)가 없습니다. 압축을 모두 풀었는지 확인해 주세요." }
$meta = @{}
$ops = New-Object System.Collections.Generic.List[string]
foreach ($line in [System.IO.File]::ReadAllLines($opsPath)) {
    if ($line.StartsWith("#")) { $kv = $line.Substring(1).Split(" ", 2); $meta[$kv[0]] = $kv[1] }
    elseif ($line) { $ops.Add($line) }
}

$game = Resolve-GameDir
$dat = Join-Path $game "data\$DatName"
$bak = "$dat.kr_backup"
Say "게임 폴더: $game"

$running = Get-Process -Name "RADICALDREAMERS", "CHRONOCROSS", "CHRONOCROSS_LAUNCHER" -ErrorAction SilentlyContinue
if ($running) { Fail "게임이 실행 중입니다. 게임을 종료한 뒤 다시 실행해 주세요." }

$cur = Sha256File $dat

if ($Restore) {
    if ($cur -eq $meta["source_sha256"]) { Say "이미 원본 상태입니다."; exit 0 }
    if (-not (Test-Path -LiteralPath $bak)) { Fail "백업($DatName.kr_backup)이 없습니다. Steam에서 '게임 파일 무결성 검사'로 복구해 주세요." }
    if ((Sha256File $bak) -ne $meta["source_sha256"]) { Fail "백업 파일이 원본과 다릅니다. Steam에서 '게임 파일 무결성 검사'로 복구해 주세요." }
    Copy-Item -LiteralPath $bak -Destination $dat -Force
    Remove-Item -LiteralPath $bak -Force
    Say "원본으로 복구했습니다."
    exit 0
}

if ($cur -eq $meta["target_sha256"]) { Say "이미 한글 패치가 적용되어 있습니다."; exit 0 }
$src = $dat
if ($cur -ne $meta["source_sha256"]) {
    # 이전 버전 패치가 적용된 경우 백업에서 다시 만든다
    if ((Test-Path -LiteralPath $bak) -and (Sha256File $bak) -eq $meta["source_sha256"]) { $src = $bak }
    else { Fail "$DatName 이 이 패치가 지원하는 원본과 다릅니다(게임 업데이트 또는 다른 버전). Steam에서 '게임 파일 무결성 검사'를 한 뒤 다시 시도해 주세요." }
}

Say "패치 데이터를 만드는 중..."
$orig = [System.IO.File]::ReadAllBytes($src)
$payload = [System.IO.File]::ReadAllBytes($binPath)
if ((Sha256Bytes $payload) -ne $meta["payload_sha256"]) { Fail "patch\rd.bin 이 손상되었습니다. 패치를 다시 받아 주세요." }

# 원본 translate.txt 압축 해제
$ms = New-Object System.IO.MemoryStream($orig, [int]$meta["tt_offset"], [int]$meta["tt_csize"], $false)
$ds = New-Object System.IO.Compression.DeflateStream($ms, [System.IO.Compression.CompressionMode]::Decompress)
$tt = New-Object byte[] ([int]$meta["tt_size"])
$got = 0
while ($got -lt $tt.Length) {
    $n = $ds.Read($tt, $got, $tt.Length - $got)
    if ($n -le 0) { break }
    $got += $n
}
$ds.Dispose()
if ((Sha256Bytes $tt) -ne $meta["tt_sha256"]) { Fail "원본 translate.txt 를 읽지 못했습니다." }

$aes = [System.Security.Cryptography.Aes]::Create()
$aes.Mode = [System.Security.Cryptography.CipherMode]::CBC
$aes.Padding = [System.Security.Cryptography.PaddingMode]::PKCS7
$aes.Key = HexBytes $meta["aes_key"]
$aes.IV = HexBytes $meta["aes_iv"]

# 원본 글꼴 복호화 (패치 데이터에는 한글 부분만 들어 있고 나머지는 원본 글꼴에서 가져온다)
$fonts = @()
for ($k = 0; $k -lt 3; $k++) {
    $fi = $meta["font$k"].Split(" ")
    $plain = $aes.CreateDecryptor().TransformFinalBlock($orig, [int]$fi[0], [int]$fi[1])
    if ((Sha256Bytes $plain) -ne $fi[2]) { Fail "원본 글꼴을 읽지 못했습니다." }
    $fonts += ,$plain
}

$top = New-Object System.IO.MemoryStream([int]$meta["target_size"])
$out = $top
foreach ($op in $ops) {
    if ($op -eq "[") { $out = New-Object System.IO.MemoryStream; continue }
    if ($op -eq "]") {
        $buf = $out.ToArray()
        $enc = $aes.CreateEncryptor().TransformFinalBlock($buf, 0, $buf.Length)
        $top.Write($enc, 0, $enc.Length)
        $out = $top
        continue
    }
    $f = $op.Split(" ")
    $off = [int]$f[1]; $len = [int]$f[2]
    switch ($f[0]) {
        "O" { $out.Write($orig, $off, $len) }
        "T" { $out.Write($tt, $off, $len) }
        "P" { $out.Write($payload, $off, $len) }
        "F0" { $out.Write($fonts[0], $off, $len) }
        "F1" { $out.Write($fonts[1], $off, $len) }
        "F2" { $out.Write($fonts[2], $off, $len) }
        default { Fail "레시피 형식 오류: $op" }
    }
}
$out = $top
$result = $out.ToArray()
if ((Sha256Bytes $result) -ne $meta["target_sha256"]) { Fail "결과 검증에 실패했습니다. 게임 파일은 변경하지 않았습니다." }

if ($src -eq $dat) { Copy-Item -LiteralPath $dat -Destination $bak -Force }
$tmp = "$dat.kr_tmp"
[System.IO.File]::WriteAllBytes($tmp, $result)
Move-Item -LiteralPath $tmp -Destination $dat -Force
Say "한글 패치를 적용했습니다. (원본 백업: data\$DatName.kr_backup)"
