param (
  [Parameter(Mandatory=$true)]
  [string]$InstallDir, 
  [switch]$Force
)

if (Test-Path $InstallDir -PathType Leaf) {
  Write-Error "InstallDir is a file"
  exit
}

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

$GitConfigInf = @"
[Setup]
Lang=default
Group=Git
NoIcons=0
SetupType=default
Components=gitlfs,assoc,assoc_sh,windowsterminal,scalar
Tasks=
EditorOption=VIM
CustomEditorPath=
DefaultBranchOption=main
PathOption=CmdTools
SSHOption=OpenSSH
TortoiseOption=false
CURLOption=WinSSL
CRLFOption=LFOnly
BashTerminalOption=MinTTY
GitPullBehaviorOption=Rebase
UseCredentialManager=Enabled
PerformanceTweaksFSCache=Enabled
EnableSymlinks=Enabled
EnablePseudoConsoleSupport=Disabled
EnableFSMonitor=Disabled
"@

function Get-VersionTag() {
  $releaseInfo = `
    Invoke-WebRequest -UseBasicParsing "https://api.github.com/repos/git-for-windows/git/releases/latest" |
    ConvertFrom-Json
  return $releaseInfo.tag_name
}

function Get-DownloadUrl($Version) {
  if ($Version -match "^v(\d+\.\d+\.\d+)\.windows.*$") {
    $versionNumber = $Matches[1]
    if ($Version -like '*.2') {
      $versionNumber += '.2'
    }
    $arch = (Get-CimInstance Win32_OperatingSystem).OSArchitecture
    return "https://github.com/git-for-windows/git/releases/download/$Version/Git-$versionNumber-$arch.exe"
  } else {
    Write-Host "FATAL: couldn't parse version number from tag"
    exit 1
  }
}

if (Test-Path -Path $InstallDir -PathType Container) {
  Write-Host 'INFO: already installed'
} else {
  Write-Host 'INFO: getting version from github'
  $version = Get-VersionTag
  $url = Get-DownloadUrl $version

  Write-Host 'INFO: downloading Git for Windows'
  $tmp = New-TemporaryFile
  Move-Item $tmp "$tmp.exe"
  $tmp = "$tmp.exe"
  Invoke-WebRequest -UseBasicParsing -OutFile "$tmp" "$url"

  New-Item "$InstallDir" -Type Directory -Force | Out-Null
  $configFile = New-TemporaryFile
  Set-Content -Value $GitConfigInf -Path "$configFile"

  Write-Host 'INFO: installing Git for Windows'
  Start-Process -Wait -FilePath "$tmp" -ArgumentList @(
    '/SILENT',
    '/NORESTART', 
    '/CURRENTUSER',
    "/DIR=`"$InstallDir`"",
    "/LOADINF=`"$configFile`""
    '/COMPONENTS="icons,ext\reg\shellhere,assoc,assoc_sh"'
  )
  $status = $?

  Remove-Item "$configFile" -Force
  Remove-Item "$tmp" -Force

  if (-not $status) {
    exit $status
  }
}

$binaryDirectories = @("bin", "usr\bin")
if ((Test-Path ($binaryDirectories | ForEach-Object { "$InstallDir\$_" })) -contains $false) {
  Write-Host 'WARN: not all expected binary dirs exist'
}
return $binaryDirectories
