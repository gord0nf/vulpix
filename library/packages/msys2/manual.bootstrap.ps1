param (
  [Parameter(Mandatory=$true)]
  [string]$InstallDir,
  [string]$Repo = 'msys2/msys2-installer',
  [switch]$Force
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

$InstallDir = [System.IO.Path]::GetFullPath("$InstallDir")
$BINS = @('.', 'usr\bin', 'ucrt64\bin', 'mingw64\bin', 'clang64\bin')
$INIT_PACKAGES = @('unzip')

function Test-ValidInstall() {
  -not (Test-Path ($BINS | ForEach-Object { "$InstallDir\$_" })) -contains $false
}

function Get-DownloadUrl($Version) {
  $arch = [System.Runtime.InteropServices.RuntimeInformation]::OSArchitecture
  if ($arch -eq 'Arm64') {
    $arch = 'arm64'
  } else {
    $arch = 'x86_64'
  }
  return "https://github.com/$Repo/releases/latest/download/msys2-$arch-latest.exe"
}

function Start-InitPackages() {
  $pacman = Join-Path $InstallDir 'usr\bin\pacman.exe'
  if (-not (Test-Path $pacman)) {
    return $false
  }
  & $pacman -S --noconfirm $INIT_PACKAGES
}

if ((-not $Force) -and (Test-Path $InstallDir) -and (Test-ValidInstall)) {
  Write-Host "WARN: InstallDir already exists (this script is not for updating!)"
  Write-Host "INFO: nothing to do"
  return $BINS
}
if (Test-Path $InstallDir) {
  Remove-Item -Force -Recurse $InstallDir 
}

Write-Host 'INFO: downloading msys2-installer'
$tmp = New-TemporaryFile
Move-Item $tmp "$tmp.exe"
$tmp = "$tmp.exe"
$url = Get-DownloadUrl 
Invoke-WebRequest -UseBasicParsing -OutFile "$tmp" "$url"

Write-Host 'INFO: running msys2-installer'
New-Item "$InstallDir" -Type Directory -Force | Out-Null
Start-Process -Wait -FilePath "$tmp" -ArgumentList @(
  'in', '--root', "$InstallDir",
  '--confirm-command', '--accept-messages'
)
$status = $?
Remove-Item "$tmp" -Force

if (-not $status) {
  exit $status
}

if (-not (Test-ValidInstall)) {
  Write-Host 'WARN: not all expected binary dirs exist'
}
if (-not (Start-InitPackages)) {
  Write-Host 'WARN: could not install base pacman packages'
}

return $BINS
