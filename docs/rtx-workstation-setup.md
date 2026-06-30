# RTX Workstation Setup

Verified: 2026-06-16

This document records the local workstation setup needed for the Gaussian Splat reference pipeline.

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
- ninja 1.13.0
- PyTorch CUDA smoke: pass on NVIDIA GeForce RTX 5090
- gsplat CUDA extension/training smoke: pass on NVIDIA GeForce RTX 5090 after CUDA Toolkit `nvcc`, Python 3.12 development headers and repo-local `ninja` were available

Exact package freeze:

```text
requirements/gpu-cu128.txt
```

## CUDA Toolkit / Python Header Boundary

PyTorch CUDA works with the installed Windows driver/runtime. gsplat 1.5.3 JIT-loads a CUDA extension and needs a CUDA Toolkit with `nvcc`, Python development headers for the active Python 3.12 environment and `ninja` visible to PyTorch extension builds. Current checks:

```text
CUDA_HOME = /usr/local/cuda-12.8
nvcc = /usr/local/cuda-12.8/bin/nvcc
nvcc version = CUDA compilation tools, release 12.8, V12.8.93
Python.h = present at /usr/include/python3.12/Python.h
python3.12-dev = 3.12.3-1ubuntu0.13
ninja = /home/engwall/projects/gaussian-splat-lab/.venv/bin/ninja
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

- The installed Ubuntu package reports `without CUDA`. This is acceptable for the first reference SfM validation, but performance may be CPU-bound.
- If we later choose another COLMAP path, such as CUDA-enabled source build, local extracted binary, Docker, or Python bindings, record it in `framework-evaluation.json` and the installation ledger before installing.

### 2026-06-21 COLMAP GPU/CUDA Check

The RTX 5090 is visible from WSL outside the Codex sandbox:

```text
NVIDIA GeForce RTX 5090, driver 610.47, 32607 MiB VRAM
```

The installed `/usr/bin/colmap` is still the Ubuntu package:

```text
COLMAP 3.9.1 -- Structure-from-Motion and Multi-View Stereo
Commit Unknown on Unknown without CUDA
```

Runtime test result:

- `--SiftExtraction.use_gpu 0` succeeds on a tiny local image set.
- `--SiftExtraction.use_gpu 1` aborts in headless WSL while trying to create a Qt/OpenGL context.
- `QT_QPA_PLATFORM=offscreen` avoids the X display error but still fails at OpenGL context creation.

Pipeline status:

- `scripts/lab-pipeline.py` already supports `pipeline.sfm.useGpu`.
- The pipeline resolves COLMAP through `GSL_COLMAP_BIN` when set; otherwise it uses `colmap` from `PATH`.
- Keep `/usr/bin/colmap` installed as the CPU fallback. A CUDA COLMAP should be side-by-side, not a replacement.
- `scripts/validate-colmap-binary.py` validates a candidate COLMAP binary with synthetic images before it is used in the UI/pipeline.
- GUI jobs keep `useGpu: False` when the server uses `/usr/bin/colmap`.
- If the UI server is started with `GSL_COLMAP_BIN` pointing at the repo-local CUDA sidecar, new GUI uploads are planned with `pipeline.sfm.useGpu=True`.

Viable upgrade paths:

1. Build COLMAP from source in WSL with CUDA support and install it into a controlled prefix such as `/opt/colmap-cuda` or a repo-documented external tools directory.
2. Use COLMAP's CUDA Docker image if Docker + NVIDIA container runtime is available and path mapping is acceptable.
3. Use a Windows CUDA-capable COLMAP binary and add explicit WSL-to-Windows path translation in the pipeline.

Official COLMAP documentation notes that default Linux distribution packages do not come with CUDA support and require a manual source build for CUDA. It also documents CUDA/Docker options and GPU feature extraction/matching controls.

### 2026-06-21 CUDA COLMAP Sidecar Build

Chosen path: build COLMAP from source in WSL into a repo-local sidecar prefix, not over the Ubuntu package.

Target binary:

```text
outputs/tools/colmap-cuda/bin/colmap
```

Build script:

```bash
./scripts/build-colmap-cuda-sidecar.sh
```

Prerequisite inventory:

- present: `build-essential`, `git`, `g++`, `libssl-dev`, `/usr/local/cuda-12.8/bin/nvcc`
- missing from PATH before any install: `cmake`, `ninja`
- first CMake attempt also required `libopencv-dev` and `libcurand-dev-12-8`
- Docker not installed, so the Docker CUDA path is not the short-term route

The script defaults to COLMAP `4.0.4`, `CUDA_ENABLED=ON`, `GUI_ENABLED=OFF`, `OPENGL_ENABLED=OFF`, `CGAL_ENABLED=OFF`, and `CMAKE_CUDA_ARCHITECTURES=native`. It builds under `outputs/build/colmap-cuda/` and installs under `outputs/tools/colmap-cuda/`, both ignored by git.

Validated sidecar:

```text
outputs/tools/colmap-cuda/bin/colmap
COLMAP 4.0.4 -- Structure-from-Motion and Multi-View Stereo
(Commit 9c23f69 on 2026-04-27 with CUDA)
```

Validation sequence:

```bash
python3 scripts/validate-colmap-binary.py --binary /usr/bin/colmap
python3 scripts/validate-colmap-binary.py --binary "$(pwd)/outputs/tools/colmap-cuda/bin/colmap"
python3 scripts/validate-colmap-binary.py --binary "$(pwd)/outputs/tools/colmap-cuda/bin/colmap" --allow-gpu --qt-offscreen
```

Result: pass. The GPU smoke created a SIFT GPU feature extractor and GPU feature matcher on device `0`. The same GPU validation also passes without `QT_QPA_PLATFORM=offscreen`, so the UI start command only needs `GSL_COLMAP_BIN`.

Start the UI with the CUDA sidecar:

```bash
GSL_COLMAP_BIN="$(pwd)/outputs/tools/colmap-cuda/bin/colmap" \
  python3 scripts/lab-ui-server.py --host 0.0.0.0 --port 8769
```

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
