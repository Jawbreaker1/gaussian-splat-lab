# RTX Workstation Setup

Verified: 2026-06-16

This document records the local workstation setup needed for the Gaussian Splat golden path.

## Current Environment

Host: Windows RTX 5090 workstation / WSL2
Python: 3.12.3
GPU: NVIDIA GeForce RTX 5090, driver 610.47, 32607 MiB VRAM

Repo-local Python environment:

```text
.venv/
```

Validated in `.venv`:

- pip 26.1.2
- torch 2.11.0+cu128
- torchvision 0.26.0+cu128
- gsplat 1.5.3
- packaging 26.2
- PyTorch CUDA smoke: pass on NVIDIA GeForce RTX 5090
- gsplat CUDA extension/training smoke: pass on NVIDIA GeForce RTX 5090 after CUDA Toolkit `nvcc` and Python 3.12 development headers were installed

Exact package freeze:

```text
requirements/gpu-cu128.txt
```

## CUDA Toolkit / Python Header Boundary

PyTorch CUDA works with the installed Windows driver/runtime. gsplat 1.5.3 JIT-loads a CUDA extension and needs both a CUDA Toolkit with `nvcc` and Python development headers for the active Python 3.12 environment. Current checks:

```text
CUDA_HOME = /usr/local/cuda-12.8
nvcc = /usr/local/cuda-12.8/bin/nvcc
nvcc version = CUDA compilation tools, release 12.8, V12.8.93
Python.h = present at /usr/include/python3.12/Python.h
python3.12-dev = 3.12.3-1ubuntu0.13
```

The user installed NVIDIA's WSL-Ubuntu CUDA repo/keyring path plus `cuda-nvcc-12-8` after Codex documented the narrow setup, then installed `python3.12-dev`. The pipeline prepends `.venv/bin` and `/usr/local/cuda-12.8/bin` for the trainer so `ninja` and `nvcc` are visible without requiring users to hand-prefix every command.

A repo-local `nvidia-cuda-nvcc-cu12==12.8.93` wheel was tested and reverted because it did not provide a `bin/nvcc` executable. The official gsplat wheel index checked on 2026-06-15 did not list a compatible prebuilt wheel for Python 3.12 + torch 2.11 + CUDA 12.8.

NVIDIA's WSL guidance says the Windows NVIDIA driver should remain the GPU driver, and WSL should use a CUDA Toolkit package that does not install or overwrite a Linux NVIDIA driver. Avoid the `cuda`, `cuda-12-x`, and `cuda-drivers` metapackages under WSL; use a toolkit-only package/path.

Validation now passing:

```bash
test -f /usr/include/python3.12/Python.h
.venv/bin/python scripts/lab-pipeline.py run-stage splat_training --job outputs/jobs/static-room-orbit-001-20260614T100535Z/job.json --allow-heavy
```

## COLMAP

COLMAP is installed on PATH:

```text
/usr/bin/colmap
colmap 3.9.1-2build2 from Ubuntu noble/universe
COLMAP 3.9.1 -- Structure-from-Motion and Multi-View Stereo
Commit Unknown on Unknown without CUDA
```

Validation:

```bash
colmap --help
.venv/bin/python scripts/lab-pipeline.py run-stage environment --job <job.json>
```

Revert if installed with apt:

```bash
sudo apt-get remove colmap
```

Notes:

- The installed Ubuntu package reports `without CUDA`. This is acceptable for the first golden-path SfM validation, but performance may be CPU-bound.
- If we later choose another COLMAP path, such as CUDA-enabled source build, local extracted binary, Docker, or Python bindings, record it in `framework-evaluation.json` and the installation ledger before installing.

## FFmpeg / ffprobe

FFmpeg and ffprobe are installed on PATH:

```text
/usr/bin/ffmpeg
/usr/bin/ffprobe
ffmpeg 7:6.1.1-3ubuntu5 from Ubuntu noble/universe
ffmpeg/ffprobe version 6.1.1-3ubuntu5
configuration includes --enable-gpl
```

Validation:

```bash
ffprobe -version
ffmpeg -version
```

Revert if installed with apt:

```bash
sudo apt-get remove ffmpeg
```

Notes:

- FFmpeg is conditional in the framework/commercial gate. Use it as a system external tool in this lab.
- The installed Ubuntu build includes `--enable-gpl`; do not bundle or redistribute this binary without LGPL/GPL/build-flag review.
- Record `ffmpeg -version` output and configure flags in stage reports before relying on it for product evaluation.
