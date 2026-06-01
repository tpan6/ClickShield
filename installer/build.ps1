# ClickShield build script
# Run from the project root: .\installer\build.ps1

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot

Set-Location $root

Write-Host "==> Installing/updating dependencies..." -ForegroundColor Cyan
pip install -e ".[build]" -q

Write-Host "==> Cleaning previous build..." -ForegroundColor Cyan
if (Test-Path "dist") { Remove-Item -Recurse -Force "dist" }
if (Test-Path "build") { Remove-Item -Recurse -Force "build" }

Write-Host "==> Running PyInstaller..." -ForegroundColor Cyan
pyinstaller installer/clickshield.spec --noconfirm

if (-not (Test-Path "dist\ClickShield\ClickShield.exe")) {
    Write-Host "PyInstaller failed — ClickShield.exe not found." -ForegroundColor Red
    exit 1
}

# Check if Inno Setup is installed
$inno = "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if (-not (Test-Path $inno)) {
    $inno = "C:\Program Files\Inno Setup 6\ISCC.exe"
}

if (Test-Path $inno) {
    Write-Host "==> Building installer with Inno Setup..." -ForegroundColor Cyan
    & $inno installer/setup.iss
    Write-Host ""
    Write-Host "Build complete!" -ForegroundColor Green
    Write-Host "Installer: dist\ClickShield-Setup-0.1.0.exe" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "Inno Setup not found. Skipping installer creation." -ForegroundColor Yellow
    Write-Host "Portable build available at: dist\ClickShield\" -ForegroundColor Yellow
    Write-Host "Download Inno Setup from https://jrsoftware.org/isinfo.php" -ForegroundColor Yellow
}
