$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Resolve-Path (Join-Path $ScriptDir "..")
$ReportPath = Join-Path $RepoRoot "docs\validation\phase-0-rtx-worker-output.md"

function Add-ReportLine {
  param([string]$Line)
  Add-Content -Path $ReportPath -Value $Line
}

function Run-Check {
  param(
    [string]$Name,
    [scriptblock]$Command,
    [bool]$Required = $true
  )

  Add-ReportLine "## $Name"
  Add-ReportLine ""
  Add-ReportLine '```text'

  try {
    $output = & $Command 2>&1
    if ($LASTEXITCODE -ne $null -and $LASTEXITCODE -ne 0) {
      throw "command exited with code $LASTEXITCODE"
    }
    if ($output) {
      $output | ForEach-Object { Add-ReportLine "$_" }
    } else {
      Add-ReportLine "ok"
    }
    Add-ReportLine '```'
    Add-ReportLine ""
    Add-ReportLine "Result: pass"
    Add-ReportLine ""
    return $true
  } catch {
    Add-ReportLine "$_"
    Add-ReportLine '```'
    Add-ReportLine ""
    if ($Required) {
      Add-ReportLine "Result: fail"
    } else {
      Add-ReportLine "Result: setup_gap"
    }
    Add-ReportLine ""
    return (-not $Required)
  }
}

New-Item -ItemType Directory -Force -Path (Split-Path -Parent $ReportPath) | Out-Null
Set-Content -Path $ReportPath -Value "# Phase 0 RTX Worker Smoke Output"
Add-ReportLine ""
Add-ReportLine "Generated: $(Get-Date -Format o)"
Add-ReportLine "Computer: $env:COMPUTERNAME"
Add-ReportLine "User: $env:USERNAME"
Add-ReportLine "Repo root: $RepoRoot"
Add-ReportLine ""

$allPassed = $true

$allPassed = (Run-Check "PowerShell" { $PSVersionTable | Out-String }) -and $allPassed
$allPassed = (Run-Check "Git" { git --version }) -and $allPassed
$allPassed = (Run-Check "Repository" {
  git -C $RepoRoot rev-parse --show-toplevel
  git -C $RepoRoot status --short
}) -and $allPassed
$allPassed = (Run-Check "NVIDIA Driver / nvidia-smi" { nvidia-smi } $false) -and $allPassed
$allPassed = (Run-Check "WSL" { wsl --status } $false) -and $allPassed

Add-ReportLine "## Summary"
Add-ReportLine ""
if ($allPassed) {
  Add-ReportLine "phase0_rtx_worker_validation=passed_or_setup_gaps_recorded"
  Write-Output "phase0_rtx_worker_validation=passed_or_setup_gaps_recorded"
} else {
  Add-ReportLine "phase0_rtx_worker_validation=failed"
  Write-Output "phase0_rtx_worker_validation=failed"
  exit 1
}

Write-Output "report=$ReportPath"
