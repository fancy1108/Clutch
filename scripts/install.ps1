# Install Clutch from GitHub Releases (Windows x64 NSIS).
# Usage (PowerShell):
#   irm https://raw.githubusercontent.com/fancy1108/Clutch/main/scripts/install.ps1 | iex
#   $env:CLUTCH_VERSION = 'v1.0.2'; .\scripts\install.ps1
#
# Env:
#   CLUTCH_VERSION  Release tag (default: latest)
#   CLUTCH_REPO     owner/repo (default: fancy1108/Clutch)

$ErrorActionPreference = 'Stop'
$Repo = if ($env:CLUTCH_REPO) { $env:CLUTCH_REPO } else { 'fancy1108/Clutch' }
$Api = "https://api.github.com/repos/$Repo"

function Get-ReleaseTag {
    if ($env:CLUTCH_VERSION) {
        return $env:CLUTCH_VERSION.TrimStart('v')
    }
    $latest = Invoke-RestMethod -Uri "$Api/releases/latest"
    return $latest.tag_name.TrimStart('v')
}

function Get-SetupAsset($Version) {
    $release = Invoke-RestMethod -Uri "$Api/releases/tags/v$Version"
    $asset = $release.assets | Where-Object { $_.name -like 'Clutch_*_x64-setup.exe' } | Select-Object -First 1
    if (-not $asset) { throw "No x64-setup.exe in v$Version" }
    return $asset
}

if ($PSVersionTable.PSVersion.Major -lt 5) {
    throw 'PowerShell 5+ required'
}

Write-Host '==> WARNING: Windows installers are NOT yet verified on physical hardware (see Issue #23).' -ForegroundColor Yellow

$version = Get-ReleaseTag
$asset = Get-SetupAsset $version
$dest = Join-Path $env:TEMP $asset.name

Write-Host "==> Clutch v$version · $($asset.name)"
Write-Host '==> Downloading…'
Invoke-WebRequest -Uri $asset.browser_download_url -OutFile $dest -UseBasicParsing

Write-Host '==> Launching installer (follow the wizard)…'
Start-Process -FilePath $dest -Wait

Write-Host ''
Write-Host "==> Done. Start Clutch from the Start menu."
Write-Host '    Feedback welcome: https://github.com/fancy1108/Clutch/issues/new/choose'
