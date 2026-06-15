# Phase 2 Splat Training Setup Gap

Verified: 2026-06-15

Goal: validate the next boundary after a passing COLMAP SfM report: minimal gsplat training on the RTX workstation.

## Input

- Job: `/home/engwall/projects/gaussian-splat-lab/outputs/jobs/static-room-orbit-001-20260614T100535Z/job.json`
- Upstream SfM report: `outputs/jobs/static-room-orbit-001-20260614T100535Z/reports/sfm.json`
- SfM status: `pass`
- Selected sparse model: `outputs/jobs/static-room-orbit-001-20260614T100535Z/sfm/20260614T114234Z/sparse/1`
- Registered frames: `42/60`
- Sparse points: `2423`

## Command

```bash
.venv/bin/python scripts/lab-pipeline.py run-stage splat_training --job outputs/jobs/static-room-orbit-001-20260614T100535Z/job.json --allow-heavy
```

## Result

- Stage status: `setup_gap`
- PyTorch CUDA: `pass` on NVIDIA GeForce RTX 5090
- gsplat import: `pass` with gsplat 1.5.3
- CUDA Toolkit: `pass`; `nvcc` visible at `/usr/local/cuda-12.8/bin/nvcc`
- Blocking check: `python_dev_headers`
- Required next setup: `python3.12-dev` so `/usr/include/python3.12/Python.h` exists

The pipeline now stops before starting gsplat's extension build because Python development headers are missing. This is a setup boundary, not a training-code failure.

## Dependency Notes

- `packaging 26.2` was installed into `.venv` because gsplat/torch extension loading required it. This is recorded in `docs/installation-and-revert-ledger.md` and `requirements/gpu-cu128.txt`.
- `nvidia-cuda-nvcc-cu12==12.8.93` was tested as a repo-local narrow alternative, but it did not provide a `bin/nvcc` executable and was immediately uninstalled. This attempt and revert are recorded in `docs/installation-and-revert-ledger.md`.
- The user installed NVIDIA CUDA `cuda-nvcc-12-8`; `/usr/local/cuda-12.8/bin/nvcc --version` reports CUDA compilation tools release 12.8, V12.8.93.
- The official gsplat wheel index checked at `https://docs.gsplat.studio/whl/gsplat/` did not list a compatible wheel for Python 3.12 + torch 2.11 + CUDA 12.8. Listed wheels were for Python 3.10 and older torch/CUDA combinations.

## Current Boundary

The video-to-splat pipeline is validated through:

```text
video -> intake -> frame_sampling -> COLMAP SfM -> minimal gsplat trainer setup boundary
```

The next required action is environment setup, not pipeline code: install `python3.12-dev`, verify `/usr/include/python3.12/Python.h`, then rerun the same guarded training command.
