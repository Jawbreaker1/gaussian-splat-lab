# Installation

This document describes the current RTX workstation setup for Gaussian Splat Lab. It is written for the Windows + WSL2 machine with the RTX 5090, because that is the supported local reconstruction host right now.

The short version: install the system tools first, then create the isolated Python environments, then install the browser viewer dependencies, then run the validation checks.

## 1. Host Machine

Required host:

- Windows workstation with an NVIDIA RTX GPU
- current NVIDIA Windows driver with WSL CUDA support
- WSL2 with Ubuntu 24.04
- enough free disk space for generated frames, SfM databases, checkpoints and PLY exports

The Mac can open the web UI over the LAN, but it is not the reconstruction runtime because the training path depends on NVIDIA CUDA.

Check WSL and GPU visibility from Ubuntu:

```bash
nvidia-smi
python3 --version
```

Expected local baseline:

- Python `3.12`
- GPU visible as `NVIDIA GeForce RTX 5090`
- CUDA Toolkit `nvcc` available at `/usr/local/cuda-12.8/bin/nvcc`

## 2. System Packages In WSL

Install the general WSL packages:

```bash
sudo apt-get update
sudo apt-get install -y git python3.12 python3.12-venv python3.12-dev nodejs npm ffmpeg colmap
```

Validate:

```bash
python3 --version
ffmpeg -version
ffprobe -version
colmap --help
node --version
npm --version
```

Notes:

- The Ubuntu COLMAP package currently reports `without CUDA`; in this lab it is accepted as a CPU SfM tool.
- Keep the Ubuntu COLMAP package installed as the known-good CPU fallback even if a CUDA build is added later.
- The Ubuntu FFmpeg build may include GPL flags. Use it as a local system tool only until redistribution is reviewed.

## 3. CUDA Toolkit Boundary

PyTorch uses the Windows NVIDIA driver through WSL. The `gsplat` CUDA extension also needs a Linux CUDA Toolkit with `nvcc`.

Install a WSL toolkit-only path, not a Linux driver metapackage. On this machine the intended package is:

```bash
sudo apt-get install -y cuda-nvcc-12-8
```

Do not install the broad `cuda`, `cuda-12-x` or `cuda-drivers` metapackages in WSL unless that decision is documented first.

Validate:

```bash
/usr/local/cuda-12.8/bin/nvcc --version
test -f /usr/include/python3.12/Python.h
```

## 4. Clone And Enter The Repo

```bash
cd ~/projects
git clone git@github.com:Jawbreaker1/gaussian-splat-lab.git
cd gaussian-splat-lab
```

If the repo already exists:

```bash
cd ~/projects/gaussian-splat-lab
git status --short --branch
```

## 5. Main Python Environment

This environment runs the lab pipeline, the local mini `gsplat` trainer, diagnostics and validation scripts.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128
.venv/bin/python -m pip install -r requirements/gpu-cu128.txt --extra-index-url https://download.pytorch.org/whl/cu128
```

Validate CUDA:

```bash
.venv/bin/python -c "import torch; print(torch.__version__); print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0))"
```

## 6. Nerfstudio / Splatfacto Environment

This environment is separate on purpose. Nerfstudio brings a larger dependency tree, and keeping it isolated makes rollback easier.

```bash
.venv/bin/python -m pip install --target /tmp/gsl-virtualenv virtualenv
PYTHONPATH=/tmp/gsl-virtualenv .venv/bin/python -m virtualenv .venv-nerfstudio-py312
.venv-nerfstudio-py312/bin/python -m pip install "nerfstudio==1.1.5"
```

The pipeline supplies the runtime environment when it launches Splatfacto:

```text
MPLCONFIGDIR=/tmp/gsl-mpl
WANDB_MODE=disabled
TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD=1
CUDA_HOME=/usr/local/cuda-12.8
PATH=.venv-nerfstudio-py312/bin:/usr/local/cuda-12.8/bin:$PATH
TORCH_CUDA_ARCH_LIST=12.0
```

Validate:

```bash
.venv-nerfstudio-py312/bin/python -m pip show nerfstudio gsplat torch
.venv-nerfstudio-py312/bin/ns-train --help
.venv-nerfstudio-py312/bin/ns-process-data record3d --help
```

## 7. Browser Viewer Dependencies

The UI is dependency-light and uses the approved local viewer stack from `package-lock.json`.

```bash
npm ci
npm run check:js
```

Approved viewer packages:

- `@sparkjsdev/spark`
- `three`
- transitive `fflate`

Do not add a new UI framework, CDN dependency or npm package without updating the framework/commercial gate first.

## 8. Validate The Repo

Run the lightweight checks:

```bash
./scripts/validate-architecture-contracts.sh
./scripts/validate-phase-1-contracts.sh
./scripts/validate-ui-contracts.sh
python3 scripts/lab-ui-server.py --check
npm run check:js
```

Validate that the pipeline can see the workstation tools:

```bash
.venv/bin/python scripts/lab-pipeline.py list-captures --capture-manifest data/manifests/captures.example.json
```

Heavy SfM/training validation should be launched deliberately from the UI or with `--allow-heavy`.

## 9. Optional Side-By-Side CUDA COLMAP

Do not replace `/usr/bin/colmap`. The apt package is the fallback that keeps the pipeline recoverable.

The repo contains a sidecar build script for a CUDA-capable, headless COLMAP CLI:

```bash
./scripts/build-colmap-cuda-sidecar.sh
```

By default it clones COLMAP `4.0.4`, builds under ignored `outputs/build/colmap-cuda/`, and installs into ignored `outputs/tools/colmap-cuda/`. Override knobs:

```bash
COLMAP_REF=4.0.4
GSL_COLMAP_BUILD_ROOT="$(pwd)/outputs/build/colmap-cuda"
GSL_COLMAP_PREFIX="$(pwd)/outputs/tools/colmap-cuda"
CUDA_HOME=/usr/local/cuda-12.8
COLMAP_CUDA_ARCHITECTURES=native
GSL_COLMAP_BUILD_JOBS="$(nproc)"
```

The script does not install system packages. Install the current headless build prerequisites first:

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

This is intentionally smaller than COLMAP's full GUI-oriented Ubuntu dependency list because the sidecar build uses `GUI_ENABLED=OFF`, `OPENGL_ENABLED=OFF` and `CGAL_ENABLED=OFF`. If CMake asks for extra packages, record them in `docs/installation-and-revert-ledger.md` before installing them.

The build can take tens of minutes or more and will keep many CPU cores busy. It is compilation, not Gaussian Splat training.

After the build, test both the fallback and the sidecar explicitly:

```bash
python3 scripts/validate-colmap-binary.py --binary /usr/bin/colmap

python3 scripts/validate-colmap-binary.py \
  --binary "$(pwd)/outputs/tools/colmap-cuda/bin/colmap" \
  --allow-gpu \
  --qt-offscreen
```

The first command confirms that the CPU fallback still works. The second command is the smoke test a CUDA candidate must pass before we point the UI or pipeline at it.

Run the pipeline with that binary only when you choose to:

```bash
GSL_COLMAP_BIN="$(pwd)/outputs/tools/colmap-cuda/bin/colmap" \
  python3 scripts/lab-ui-server.py --host 0.0.0.0 --port 8769
```

When the UI server is started this way, newly uploaded GUI jobs are planned with `pipeline.sfm.useGpu=True`. Without `GSL_COLMAP_BIN`, GUI jobs keep the apt CPU fallback.

or for a one-off CLI stage:

```bash
GSL_COLMAP_BIN="$(pwd)/outputs/tools/colmap-cuda/bin/colmap" \
  .venv/bin/python scripts/lab-pipeline.py run-stage sfm \
    --job outputs/jobs/<job-id>/job.json \
    --accept-warning \
    --allow-heavy
```

Revert is simply unsetting the variable:

```bash
unset GSL_COLMAP_BIN
```

Remove the sidecar build artifacts if you want the repo-local disk space back:

```bash
rm -rf outputs/build/colmap-cuda outputs/tools/colmap-cuda
```

Do not remove `/usr/bin/colmap` unless you intentionally want to remove the CPU fallback.

## 10. Start The Local UI

Local-only:

```bash
python3 scripts/lab-ui-server.py --host 127.0.0.1 --port 8769
```

Open:

```text
http://127.0.0.1:8769/
```

LAN access from another computer:

```bash
python3 scripts/lab-ui-server.py --host 0.0.0.0 --port 8769
```

Then run this from elevated Windows PowerShell:

```powershell
powershell.exe -ExecutionPolicy Bypass -File "\\wsl.localhost\Ubuntu-24.04\home\engwall\projects\gaussian-splat-lab\scripts\expose-ui-lan.ps1" -Port 8769
```

The script prints the LAN URL. Use the actual LAN address from that output on the Mac.

## 11. Revert / Cleanup

Remove repo-local environments:

```bash
rm -rf .venv .venv-nerfstudio-py312 node_modules
rm -rf /tmp/gsl-virtualenv /tmp/gsl-mpl
```

Remove generated reconstruction data while keeping packaged gallery exports:

```bash
python3 scripts/cleanup-generated-data.py --all-safe --write-report
python3 scripts/cleanup-generated-data.py --all-safe --apply --write-report
```

Remove WSL system packages only if they were installed for this project and no other local work depends on them:

```bash
sudo apt-get remove colmap ffmpeg python3.12-venv python3.12-dev cuda-nvcc-12-8
```

Every install, upgrade or manual machine-level change should be recorded in `docs/installation-and-revert-ledger.md`.
