$ErrorActionPreference = "Stop"

Write-Output "stage0_rtx_worker_smoke=start"

if (Get-Command git -ErrorAction SilentlyContinue) {
  git --version
} else {
  throw "missing git"
}

if (Get-Command nvidia-smi -ErrorAction SilentlyContinue) {
  nvidia-smi
} else {
  Write-Output "nvidia-smi=not found in current shell; later stages must validate NVIDIA driver/CUDA on the RTX worker"
}

if (Get-Command wsl -ErrorAction SilentlyContinue) {
  wsl --status
} else {
  Write-Output "wsl=not found; install/configure WSL2 before Linux-first reconstruction work"
}

Write-Output "stage0_rtx_worker_smoke=ok"
