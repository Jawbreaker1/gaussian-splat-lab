# Phase 0 RTX Workstation WSL Smoke Output

Generated: 2026-06-07

## Topology

The primary Gaussian Splat lab host is now the local Windows workstation with an installed RTX 5090. The reconstruction pipeline is intended to run locally on this machine, using WSL2/Linux-first tooling where practical.

## WSL/Linux Smoke

```text
repo_root=/home/engwall/projects/gaussian-splat-lab
machine=Linux SpelDatorn 5.15.167.4-microsoft-standard-WSL2 #1 SMP Tue Nov 5 00:21:55 UTC 2024 x86_64 x86_64 x86_64 GNU/Linux
git=git version 2.43.0
python3=Python 3.12.3
node=v18.19.1
stage0_mac_smoke=ok
```

Result: pass

## NVIDIA Visibility From WSL

```text
NVIDIA-SMI 610.43.02
KMD Version: 610.47
CUDA UMD Version: 13.3
GPU 0: NVIDIA GeForce RTX 5090
Memory: 32607 MiB
```

Result: pass

## Contract Validation

```text
architecture_contract_validation=passed
phase1_contract_validation=passed
```

Result: pass

## Remaining GPU Gates

This proves the RTX 5090 is visible from WSL. Later environment gates must still validate:

- CUDA-compatible PyTorch install
- `torch.cuda.is_available()` and device name
- minimal CUDA tensor operation
- gsplat import/build/runtime smoke
- COLMAP availability and version
