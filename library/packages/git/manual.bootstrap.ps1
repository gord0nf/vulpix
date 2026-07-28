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
  Write-Host 'INFO: getting version from github'
  $releaseInfo = `
    Invoke-WebRequest -UseBasicParsing "https://api.github.com/repos/git-for-windows/git/releases/latest" |
    ConvertFrom-Json
  return $releaseInfo.tag_name
}

function Get-InstalledVersion() {
  $git = "$InstallDir/bin/git"
  if (Test-Path $git) {
    $currentVersion = & $git --version
    if ($currentVersion -match "(\d+\.\d+\.\d+)(\.windows.*)?") {
      $currentVersion = "v$($Matches[1])"
    }
  }
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

$Update = Test-Path -Path $InstallDir -PathType Container
$Install = -not $Update
$LatestVersion = Get-VersionTag

if ($Update) {
  $currentVersion = Get-InstalledVersion
  if ($currentVersion) {
    Write-Host "DEBUG: current version: $currentVersion"
    Write-Host "DEBUG: latest version: $LatestVersion"
    if ($currentVersion -eq $LatestVersion) {
      Write-Host 'INFO: up to date'
    } else {
      Write-Host 'INFO: reinstalling updated version'
      $Install = $true
    }
  } else {
    Write-Host 'INFO: broken installation, reinstalling latest'
    $Install = $true
  }
}

if ($Install) {
  Remove-Item -Force -Recursive $InstallDir
  $url = Get-DownloadUrl $LatestVersion

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
