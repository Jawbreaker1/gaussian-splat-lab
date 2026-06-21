# COLMAP CUDA Sidecar Build Plan

Verified: 2026-06-21

Purpose: prepare a CUDA-capable COLMAP candidate without replacing the working Ubuntu CPU fallback at `/usr/bin/colmap`.

## Decision

Build COLMAP from source into ignored repo-local paths:

```text
outputs/build/colmap-cuda/
outputs/tools/colmap-cuda/
```

The pipeline only uses this binary when `GSL_COLMAP_BIN` is explicitly set.

## Current Machine Inventory

Present:

- `build-essential`
- `git`
- `g++`
- `libssl-dev`
- `/usr/local/cuda-12.8/bin/nvcc`

Missing before installation:

- `cmake`
- `ninja`

Docker was not present, so the Docker CUDA image path is not the current shortcut.

## Planned System Packages

The sidecar script is configured as a headless CLI build, so it starts with this package list:

```bash
sudo apt-get install -y \
  cmake \
  ninja-build \
  libboost-program-options-dev \
  libboost-graph-dev \
  libboost-system-dev \
  libeigen3-dev \
  libopencv-dev \
  libopenimageio-dev \
  openimageio-tools \
  libmetis-dev \
  libgoogle-glog-dev \
  libgtest-dev \
  libgmock-dev \
  libsqlite3-dev \
  libglew-dev \
  libceres-dev \
  libsuitesparse-dev \
  libcurl4-openssl-dev \
  libssl-dev \
  libcurand-dev-12-8 \
  libgl-dev \
  libglx-dev \
  libopengl-dev
```

A dry-run on 2026-06-21 reported `148` new packages, `0` upgraded, `0` removed, and `27` not upgraded. No packages were installed by that dry-run.

First CMake attempt after the initial prerequisite install found two missing pieces:

- `libopencv-dev`: OpenImageIO's CMake target referenced `/usr/include/opencv4`.
- `libcurand-dev-12-8`: COLMAP CUDA targets require `CUDA::curand`.

The documented package list now includes both.

If CMake asks for additional dependencies, add a new ledger note before installing them.

## Build Command

```bash
./scripts/build-colmap-cuda-sidecar.sh
```

Defaults:

- `COLMAP_REF=4.0.4`
- `GSL_COLMAP_BUILD_ROOT=outputs/build/colmap-cuda`
- `GSL_COLMAP_PREFIX=outputs/tools/colmap-cuda`
- `CUDA_HOME=/usr/local/cuda-12.8`
- `COLMAP_CUDA_ARCHITECTURES=native`

This is a source compilation step and can keep many CPU cores busy for tens of minutes or longer.

Result on 2026-06-21:

- build pass
- installed binary: `outputs/tools/colmap-cuda/bin/colmap`
- version: `COLMAP 4.0.4`, commit `9c23f69`, `with CUDA`
- build log: `logs/build/colmap-cuda-sidecar-foreground.log`

## Validation

Keep the fallback validated:

```bash
python3 scripts/validate-colmap-binary.py --binary /usr/bin/colmap
```

Then validate the sidecar:

```bash
python3 scripts/validate-colmap-binary.py --binary "$(pwd)/outputs/tools/colmap-cuda/bin/colmap"
python3 scripts/validate-colmap-binary.py --binary "$(pwd)/outputs/tools/colmap-cuda/bin/colmap" --allow-gpu --qt-offscreen
```

Only after both sidecar checks pass should the UI or CLI be launched with:

```bash
GSL_COLMAP_BIN="$(pwd)/outputs/tools/colmap-cuda/bin/colmap"
```

Result on 2026-06-21: pass. The GPU smoke logged `Creating SIFT GPU feature extractor`, `Bind FeatureMatcherWorker to GPU device 0`, and `Creating SIFT GPU feature matcher`.

## Rollback

Unset the override:

```bash
unset GSL_COLMAP_BIN
```

Remove build artifacts:

```bash
rm -rf outputs/build/colmap-cuda outputs/tools/colmap-cuda
```

The Ubuntu fallback remains available at `/usr/bin/colmap`.
