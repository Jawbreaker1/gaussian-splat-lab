# RTX Workstation Setup

Verified: 2026-06-15

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
- gsplat CUDA extension: setup gap; `nvcc` / CUDA Toolkit is not visible in WSL

Exact package freeze:

```text
requirements/gpu-cu128.txt
```

## CUDA Toolkit Boundary

PyTorch CUDA works with the installed Windows driver/runtime, but gsplat 1.5.3 JIT-loads a CUDA extension and currently needs a CUDA Toolkit with `nvcc` visible inside WSL. Current checks:

```text
torch.utils.cpp_extension.CUDA_HOME = None
nvcc: not found
```

A repo-local `nvidia-cuda-nvcc-cu12==12.8.93` wheel was tested and reverted because it did not provide a `bin/nvcc` executable. The official gsplat wheel index checked on 2026-06-15 did not list a compatible prebuilt wheel for Python 3.12 + torch 2.11 + CUDA 12.8.

NVIDIA's WSL guidance says the Windows NVIDIA driver should remain the GPU driver, and WSL should use a CUDA Toolkit package that does not install or overwrite a Linux NVIDIA driver. Avoid the `cuda`, `cuda-12-x`, and `cuda-drivers` metapackages under WSL; use a toolkit-only package/path.

Next setup action: install or expose a CUDA Toolkit with `nvcc` inside WSL, preferably matching the CUDA 12.8 runtime line used by the current PyTorch wheel, and record the exact source, version and revert plan in `docs/installation-and-revert-ledger.md`.

The narrow candidate identified on 2026-06-15 is NVIDIA's WSL-Ubuntu repo keyring plus `cuda-nvcc-12-8`, not the broader `cuda`, `cuda-12-x`, `cuda-drivers`, or Ubuntu `nvidia-cuda-toolkit` packages. The inspected `cuda-nvcc-12-8_12.8.93-1_amd64.deb` contains `/usr/local/cuda-12.8/bin/nvcc` and depends on CUDA runtime/dev/compiler support packages, but not on a Linux display driver package.

Candidate commands, to run manually in WSL because sudo requires the local Linux password:

```bash
cd /home/engwall/projects/gaussian-splat-lab
sudo dpkg -i /tmp/cuda-keyring_1.1-1_all.deb
sudo apt-get update
sudo apt-get install -y cuda-nvcc-12-8
```

Validation after install:

```bash
/usr/local/cuda-12.8/bin/nvcc --version
CUDA_HOME=/usr/local/cuda-12.8 PATH=/usr/local/cuda-12.8/bin:$PATH .venv/bin/python -c "from gsplat.cuda import _backend; print(_backend._C is not None)"
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
