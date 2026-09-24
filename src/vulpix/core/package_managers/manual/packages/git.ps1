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
  [Console]::Error.WriteLine('INFO: getting version from github')
  $releaseInfo = `
    Invoke-WebRequest -UseBasicParsing "https://api.github.com/repos/git-for-windows/git/releases/latest" |
    ConvertFrom-Json
  return $releaseInfo.tag_name
}

function Get-InstalledVersion() {
  $git = "$InstallDir/bin/git.exe"
  if (Test-Path $git) {
    $currentVersion = & $git --version
    if ($currentVersion -match ".*(\d+\.\d+\.\d+)(\.windows)?(\.\d+)?.*") {
      $currentVersion = "v$($Matches[1])"
      if ($Matches.Count -gt 2) {
        $currentVersion = "$currentVersion$($Matches[2])"
      }
      if ($Matches.Count -gt 3) {
        $currentVersion = "$currentVersion$($Matches[3])"
      }
      return $currentVersion
    }
  }
}

function Get-DownloadUrl($Version) {
  if ($Version -match "^v(\d+\.\d+\.\d+)\.windows(\.\d+)?$") {
    $versionNumber = $Matches[1]
    if ($Matches.Count -gt 2) {
      $versionNumber = "$versionNumber$($Matches[2])"
    }
    $arch = (Get-CimInstance Win32_OperatingSystem).OSArchitecture
    return "https://github.com/git-for-windows/git/releases/download/$Version/Git-$versionNumber-$arch.exe"
  } else {
    [Console]::Error.WriteLine("FATAL: couldn't parse version number from tag")
    exit 1
  }
}

$Update = Test-Path -Path $InstallDir -PathType Container
$Install = -not $Update
$LatestVersion = Get-VersionTag
[Console]::Error.WriteLine("DEBUG: latest version: $LatestVersion")

if ($Update) {
  $currentVersion = Get-InstalledVersion
  if ($currentVersion) {
    [Console]::Error.WriteLine("DEBUG: current version: $currentVersion")
    if ($currentVersion -eq $LatestVersion) {
      [Console]::Error.WriteLine('INFO: up to date')
    } else {
      [Console]::Error.WriteLine('INFO: reinstalling updated version')
      $Install = $true
    }
  } else {
    [Console]::Error.WriteLine('INFO: broken installation, reinstalling latest')
    $Install = $true
  }
}

if ($Install) {
  $tmpInstallDir = "$InstallDir.tmp"
  $url = Get-DownloadUrl $LatestVersion
  [Console]::Error.WriteLine("DEBUG: url=$url")

  [Console]::Error.WriteLine('INFO: downloading')
  $tmp = New-TemporaryFile
  Move-Item $tmp "$tmp.exe"
  $tmp = "$tmp.exe"
  Invoke-WebRequest -UseBasicParsing -OutFile "$tmp" "$url"

  New-Item $tmpInstallDir -Type Directory -Force | Out-Null
  $configFile = New-TemporaryFile
  Set-Content -Value $GitConfigInf -Path "$configFile"

  [Console]::Error.WriteLine('INFO: installing')
  Start-Process -Wait -FilePath "$tmp" -ArgumentList @(
    '/SILENT',
    '/NORESTART', 
    '/CURRENTUSER',
    "/DIR=`"$tmpInstallDir`"",
    "/LOADINF=`"$configFile`""
    '/COMPONENTS="icons,ext\reg\shellhere,assoc,assoc_sh"'
  )
  $status = $?

  Remove-Item "$configFile" -Force
  Remove-Item "$tmp" -Force

  if ($status) {
    Remove-Item -Force -Recurse $InstallDir -ErrorAction SilentlyContinue
    Move-Item -Path $tmpInstallDir -Destination $InstallDir
  } else {
    exit $status
  }
}

$binaryDirectories = @("bin", "usr\bin")
if ((Test-Path ($binaryDirectories | ForEach-Object { "$InstallDir\$_" })) -contains $false) {
  [Console]::Error.WriteLine('WARN: not all expected binary dirs exist')
}
[Console]::Out.WriteLine(($binaryDirectories -join "`n"))
