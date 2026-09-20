param (
  [Parameter(Mandatory=$true)]
  [string]$InstallDir
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

$PythonUrl = 'https://www.python.org/ftp/python'
$binary = 'python.exe'

if (Test-Path $InstallDir -PathType Leaf) {
  Write-Error "InstallDir is a file"
}
$InstallDir = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($InstallDir)

# https://stackoverflow.com/a/65316146
function Get-LatestVersion() {
  $html = (Invoke-WebRequest $PythonUrl -UseBasicParsing).Content
  $versions = $html -split "`n" | ForEach-Object {
    if ($_ -match "([0-9]+\.[0-9]+\.[0-9]+)") { $Matches[1] }
  }
  $versions = $versions | Sort-Object { [version]$_ } -Descending 
  foreach ($version in $versions) {
    $filename = "Python-$version.tar.xz"
    # Versions which only have alpha, beta, or rc releases will fail here.
    # Stop when we find one with a final release.
    try {
      $status = (
        Invoke-WebRequest -Uri "$PythonUrl/$version/$filename" `
          -Method Head -UseBasicParsing -ErrorAction Stop
      ).StatusCode
      if ($status -ne 200) {
        continue
      }
      return $version
    } catch {
      continue
    }
  }
}

function Get-InstalledVersion() {
  if (Test-Path "$InstallDir/$binary") {
    $currentVersion = & "$InstallDir/$binary" --version
    if ($currentVersion -match '^.*([0-9]+(\.[0-9]+){2}).*$') {
      return $Matches[1]
    }
  }
  return $null
}

function Get-DownloadUrl($Version) {
  switch ([System.Runtime.InteropServices.RuntimeInformation]::OSArchitecture) {
    "X64" { $arch = 'amd64' }
    "Arm64" { $arch = 'arm64' }
    default { Write-Error 'invalid architecture' }
  }
  return "$PythonUrl/$Version/python-$Version-$arch.zip"
}

$Update = Test-Path -Path $InstallDir -PathType Container
$Install = -not $Update
$LatestVersion = Get-LatestVersion
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
  Remove-Item $InstallDir -Force -Recurse -ErrorAction SilentlyContinue
  $url = Get-DownloadUrl $LatestVersion
  [Console]::Error.WriteLine("DEBUG: url=$url")

  [Console]::Error.WriteLine('INFO: downloading')
  $tmp = New-TemporaryFile
  Move-Item $tmp "$tmp.zip"
  $tmp = "$tmp.zip"
  Invoke-WebRequest -UseBasicParsing -OutFile "$tmp" "$url"

  [Console]::Error.WriteLine('INFO: extracting')
  New-Item $InstallDir -Type Directory -Force -ErrorAction SilentlyContinue | Out-Null
  Add-Type -Assembly "System.IO.Compression.Filesystem"
  [System.IO.Compression.ZipFile]::ExtractToDirectory($tmp, $InstallDir)

  #while ($true) {
    #$topLevelItems = Get-ChildItem -Path $InstallDir
    #if (($topLevelItems.Count -eq 1) -and ($topLevelItems[0].PSIsContainer)) {
      ##Get-ChildItem -Path $topLevelItems[0].FullName | Move-Item -Destination $InstallDir -Force
      #Remove-Item -Path $topLevelItems[0] -Force
    #} else {
      #break
    #}
  #}

  Remove-Item "$tmp" -Force
}

if ((Test-Path ($Binaries | ForEach-Object { "$InstallDir\$_" })) -contains $false) {
  [Console]::Error.WriteLine('WARN: not all expected binary dirs exist')
}
[Console]::Out.WriteLine('.') # return the relative bin dir
