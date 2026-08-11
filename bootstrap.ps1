# Windows PowerShell wrapper for bootstrap.sh. If bash is not install, bootstraps bash 
# via Git for Windows, then passes execution to bootstrap.sh.

# DEV NOTE: this hasn't really been tested, because im on linux right now...

$ErrorActionPreference = 'Stop'

if (-not $env:VULPIX_REPO) { $env:VULPIX_REPO = 'gord0nf/vulpix' }
if (-not $env:VULPIX_BRANCH) { $env:VULPIX_BRANCH = 'main' }
$VULPIX_REPO_RAW = "https://raw.githubusercontent.com/$env:VULPIX_REPO/refs/heads/$env:VULPIX_BRANCH"

if ($PSVersionTable.PSEdition -ne 'Desktop') {
  Write-Error 'Only for execution by Windows PowerShell on a Windows machine'
  exit 1
}

function Test-Admin() {
  ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()). `
    IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

# IMPORTANT: Define MANUAL_ROOT, which SHOULD BE THE SAME as defined in `library/managers/manual.sh`
if (Test-Admin) {
  $MANUAL_ROOT = "$env:ProgramData/vulpix/manual"
} else {
  $MANUAL_ROOT = "$env:LOCALAPPDATA/vulpix/manual"
}

function Bootstrap-Package($Package) {
  Write-Host "INFO: downloading '$Package' bootstrap script"
  $script = Invoke-WebRequest -UseBasicParsing `
    -Uri "$VULPIX_REPO_RAW/library/packages/$Package/manual.bootstrap.ps1"
  $installDir = "$MANUAL_ROOT\packages\$Package"

  $binDirs = & ([scriptblock]::Create($script.Content)) -InstallDir "$installDir"
  if (-not ($? -and $binDirs -and ($binDirs -is [array]))) {
    Write-Host "FATAL: $Package bootstrap failed"
    exit 1
  }

  # add to PATH (only for the powershell session, but that's all that's needed)
  $binDirs | ForEach-Object { $env:PATH += ";$installDir\$_" }
}

if (-not (Get-Command 'bash' -ErrorAction SilentlyContinue)) {
  Write-Host 'INFO: bash not installed'
  Write-Host 'INFO: bootstrapping Git for Windows (for Git Bash)'
  Bootstrap-Package 'git'

  if (-not (Get-Command 'bash' -ErrorAction SilentlyContinue)) {
    Write-Host "FATAL: Git for Windows bootstrap suppossedly succeeded, but bash isn't available"
    exit 1
  }
}

Write-Host 'INFO: downloading bootstrap.sh'
$bootstrapScript = New-TemporaryFile | Rename-Item -NewName { $_.Name -replace '\.tmp$', '.sh' } -PassThru   
Invoke-WebRequest -UseBasicParsing -OutFile $bootstrapScript "$VULPIX_REPO_RAW/bootstrap.sh" 

Write-Host 'INFO: passing execution to bootstrap.sh'
bash "$bootstrapScript"
$status = $?

Remove-Item -Force $bootstrapScript
return $status
