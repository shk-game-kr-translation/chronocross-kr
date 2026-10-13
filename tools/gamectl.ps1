<#
Runtime control for CHRONO CROSS: THE RADICAL DREAMERS EDITION (test install).
Never steals focus: keys/clicks are posted to the game window (PostMessage), screenshots use PrintWindow.
  gamectl.ps1 start [launcher|rd|cc]   start the launcher or an exe directly (starts minimized-to-background is not possible; it opens once)
  gamectl.ps1 stop                      kill all game processes
  gamectl.ps1 shot <name>               capture the game window to 90_test/shots/<name>.png (window must not be minimized)
  gamectl.ps1 key <key> [count]         post a key press to the game window
  gamectl.ps1 fkey <key> [count]        REAL key press: game window to front, keybd_event, previous window restored (steals focus briefly)
  gamectl.ps1 click <x,y>               post a left click at 1280x720-reference client coordinates
  gamectl.ps1 status                    list game processes and window titles
  gamectl.ps1 seq "op:arg;wait:s;..."   run several steps in one invocation
Keys: up down left right enter esc space z x c a s q w d e f r v backspace tab f1..f12
#>
param([string]$cmd = "status", [string]$arg1 = "", [int]$count = 1, [int]$holdMs = 60, [int]$gapMs = 250)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$game = Join-Path $root "CHRONO CROSS  THE RADICAL DREAMERS EDITION"
$shots = Join-Path $root "90_test\shots"
$procs = "CHRONOCROSS_LAUNCHER", "CHRONOCROSS", "RADICALDREAMERS"

Add-Type -AssemblyName System.Drawing
Add-Type @"
using System;
using System.Runtime.InteropServices;
public static class W {
  [StructLayout(LayoutKind.Sequential)] public struct RECT { public int L, T, R, B; }
  [StructLayout(LayoutKind.Sequential)] public struct POINT { public int X, Y; }
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
  [DllImport("user32.dll")] public static extern bool GetClientRect(IntPtr h, out RECT r);
  [DllImport("user32.dll")] public static extern bool ClientToScreen(IntPtr h, ref POINT p);
  [DllImport("user32.dll")] public static extern bool IsIconic(IntPtr h);
  [DllImport("user32.dll")] public static extern uint MapVirtualKey(uint code, uint type);
  [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr h, IntPtr hdc, uint flags);
  [DllImport("user32.dll")] public static extern bool PostMessage(IntPtr h, uint msg, IntPtr w, IntPtr l);
  [DllImport("user32.dll")] public static extern IntPtr SendMessage(IntPtr h, uint msg, IntPtr w, IntPtr l);
  [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int cmd);
  [DllImport("user32.dll")] public static extern void keybd_event(byte vk, byte scan, uint flags, UIntPtr extra);
}
"@

function Get-GameWindow {
  foreach ($n in "RADICALDREAMERS", "CHRONOCROSS", "CHRONOCROSS_LAUNCHER") {
    $p = Get-Process -Name $n -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowHandle -ne 0 } | Select-Object -First 1
    if ($p) { return $p }
  }
  return $null
}

function Fake-Activate($h) {
  # Tell the window it is active without touching the real foreground window (WM_ACTIVATE / WM_SETFOCUS).
  [W]::SendMessage($h, 0x0006, [IntPtr]1, [IntPtr]::Zero) | Out-Null
  [W]::SendMessage($h, 0x0007, [IntPtr]::Zero, [IntPtr]::Zero) | Out-Null
}

$vk = @{ up = 0x26; down = 0x28; left = 0x25; right = 0x27; enter = 0x0D; esc = 0x1B; space = 0x20; backspace = 0x08; tab = 0x09
  z = 0x5A; x = 0x58; c = 0x43; a = 0x41; s = 0x53; q = 0x51; w = 0x57; d = 0x44; e = 0x45; f = 0x46; v = 0x56; r = 0x52
  shift = 0x10; f1 = 0x70; f2 = 0x71; f3 = 0x72; f4 = 0x73; f5 = 0x74; f6 = 0x75; f7 = 0x76; f8 = 0x77; f9 = 0x78; f10 = 0x79; f11 = 0x7A; f12 = 0x7B }

if ($cmd -eq "seq") {
  foreach ($step in $arg1.Split(";")) {
    $s = $step.Trim(); if (-not $s) { continue }
    $op, $val = $s.Split(":", 2)
    if ($op -eq "wait") { Start-Sleep -Milliseconds ([int]([double]$val * 1000)); continue }
    $n = 1
    if ($val -and $val.Contains("*")) { $val, $nn = $val.Split("*"); $n = [int]$nn }
    & $PSCommandPath $op $val $n
  }
  return
}

switch ($cmd) {
  "start" {
    $exe = switch ($arg1) { "rd" { "RADICALDREAMERS.exe" } "cc" { "CHRONOCROSS.exe" } default { "CHRONOCROSS_LAUNCHER.exe" } }
    Start-Process -FilePath (Join-Path $game $exe) -WorkingDirectory $game
    Write-Output "started $exe"
  }
  "stop" {
    foreach ($n in $procs) {
      Get-Process -Name $n -ErrorAction SilentlyContinue | ForEach-Object {
        Start-Process -FilePath taskkill.exe -ArgumentList "/F /T /PID $($_.Id)" -NoNewWindow -Wait -RedirectStandardOutput "NUL"
      }
    }
    Start-Sleep -Milliseconds 800
    $left = foreach ($n in $procs) { Get-Process -Name $n -ErrorAction SilentlyContinue }
    if ($left) { Write-Output ("still running: " + ($left | ForEach-Object { "$($_.Name)/$($_.Id)" }) -join ",") } else { Write-Output "stopped" }
  }
  "status" {
    foreach ($n in $procs) {
      Get-Process -Name $n -ErrorAction SilentlyContinue | ForEach-Object {
        Write-Output ("{0} pid={1} hwnd={2} title='{3}' minimized={4}" -f $_.Name, $_.Id, $_.MainWindowHandle, $_.MainWindowTitle, ($_.MainWindowHandle -ne 0 -and [W]::IsIconic($_.MainWindowHandle)))
      }
    }
  }
  "shot" {
    $p = Get-GameWindow
    if (-not $p) { throw "no game window" }
    $h0 = $p.MainWindowHandle
    if ([W]::IsIconic($h0)) { Write-Output "window is minimized; shot skipped (restore it to capture)"; return }
    $wr = New-Object W+RECT; [W]::GetWindowRect($h0, [ref]$wr) | Out-Null
    $r = New-Object W+RECT; [W]::GetClientRect($h0, [ref]$r) | Out-Null
    $pt = New-Object W+POINT; [W]::ClientToScreen($h0, [ref]$pt) | Out-Null
    $w = $r.R - $r.L; $h = $r.B - $r.T
    New-Item -ItemType Directory -Force $shots | Out-Null
    $full = New-Object System.Drawing.Bitmap ($wr.R - $wr.L), ($wr.B - $wr.T)
    $g = [System.Drawing.Graphics]::FromImage($full)
    $hdc = $g.GetHdc()
    [W]::PrintWindow($h0, $hdc, 2) | Out-Null   # PW_RENDERFULLCONTENT: works while covered, never raises the window
    $g.ReleaseHdc($hdc); $g.Dispose()
    $bmp = $full.Clone((New-Object System.Drawing.Rectangle ($pt.X - $wr.L), ($pt.Y - $wr.T), $w, $h), $full.PixelFormat)
    $out = Join-Path $shots ($arg1 + ".png")
    $bmp.Save($out, [System.Drawing.Imaging.ImageFormat]::Png)
    $view = Join-Path $root "90_test\viewdir.txt"
    if (Test-Path $view) { Copy-Item $out (Join-Path (Get-Content $view -TotalCount 1).Trim() ($arg1 + ".png")) -Force }
    $full.Dispose(); $bmp.Dispose()
    Write-Output ("{0} {1}x{2} from {3}" -f $out, $w, $h, $p.Name)
  }
  "click" {
    $p = Get-GameWindow
    if (-not $p) { throw "no game window" }
    $h0 = $p.MainWindowHandle
    $xy = $arg1.Split(",")
    $r = New-Object W+RECT; [W]::GetClientRect($h0, [ref]$r) | Out-Null
    $x = [int]([double]$xy[0] * ($r.R - $r.L) / 1280); $y = [int]([double]$xy[1] * ($r.B - $r.T) / 720)
    $lp = [IntPtr](($y -shl 16) -bor ($x -band 0xFFFF))
    Fake-Activate $h0
    [W]::PostMessage($h0, 0x0200, [IntPtr]::Zero, $lp) | Out-Null   # WM_MOUSEMOVE
    Start-Sleep -Milliseconds 120
    [W]::PostMessage($h0, 0x0201, [IntPtr]1, $lp) | Out-Null        # WM_LBUTTONDOWN
    Start-Sleep -Milliseconds 60
    [W]::PostMessage($h0, 0x0202, [IntPtr]::Zero, $lp) | Out-Null   # WM_LBUTTONUP
    Write-Output "posted click $x,$y to $($p.Name)"
  }
  "fkey" {
    $p = Get-GameWindow
    if (-not $p) { throw "no game window" }
    $h0 = $p.MainWindowHandle
    $prev = [W]::GetForegroundWindow()
    $code = [byte]$vk[$arg1.ToLower()]
    $scan = [byte][W]::MapVirtualKey($code, 0)
    $ext = if ($arg1 -in "up", "down", "left", "right") { 1 } else { 0 }
    [W]::keybd_event(0x12, 0, 0, [UIntPtr]::Zero); [W]::keybd_event(0x12, 0, 2, [UIntPtr]::Zero)  # ALT tap unlocks SetForegroundWindow
    if ([W]::IsIconic($h0)) { [W]::ShowWindow($h0, 9) | Out-Null; Start-Sleep -Milliseconds 500 }
    [W]::SetForegroundWindow($h0) | Out-Null
    Start-Sleep -Milliseconds 150
    for ($i = 0; $i -lt $count; $i++) {
      [W]::keybd_event($code, $scan, $ext, [UIntPtr]::Zero)
      Start-Sleep -Milliseconds $holdMs
      [W]::keybd_event($code, $scan, ($ext -bor 2), [UIntPtr]::Zero)
      Start-Sleep -Milliseconds $gapMs
    }
    # env GAMECTL_KEEP=1: leave the game in front (it minimizes itself when it loses focus, so shots need it in front)
    if ($env:GAMECTL_KEEP -ne "1" -and $prev -ne $h0 -and $prev -ne [IntPtr]::Zero) { [W]::SetForegroundWindow($prev) | Out-Null }
    Write-Output "sent $arg1 x$count to $($p.Name)"
  }
  "key" {
    $p = Get-GameWindow
    if (-not $p) { throw "no game window" }
    $h0 = $p.MainWindowHandle
    $code = [int]$vk[$arg1.ToLower()]
    $scan = [int][W]::MapVirtualKey($code, 0)
    $ext = if ($arg1 -in "up", "down", "left", "right") { 1 } else { 0 }
    $down = [IntPtr](1 -bor ($scan -shl 16) -bor ($ext -shl 24))
    $up = [IntPtr]([int64]1 -bor ($scan -shl 16) -bor ($ext -shl 24) -bor (3L -shl 30))
    Fake-Activate $h0
    for ($i = 0; $i -lt $count; $i++) {
      [W]::PostMessage($h0, 0x0100, [IntPtr]$code, $down) | Out-Null   # WM_KEYDOWN
      Start-Sleep -Milliseconds $holdMs
      [W]::PostMessage($h0, 0x0101, [IntPtr]$code, $up) | Out-Null     # WM_KEYUP
      Start-Sleep -Milliseconds $gapMs
    }
    Write-Output "posted $arg1 x$count to $($p.Name)"
  }
}
