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

If we build or unpack a CUDA-capable COLMAP later, place it in a separate path, for example:

```text
/opt/colmap-cuda/bin/colmap
```

or another clearly documented external-tools directory. Then test it explicitly:

```bash
GSL_COLMAP_BIN=/opt/colmap-cuda/bin/colmap \
  python3 -c "import os, subprocess; print(subprocess.run([os.environ['GSL_COLMAP_BIN'], '--help'], text=True, capture_output=True).stdout[:300])"
```

Run the pipeline with that binary only when you choose to:

```bash
GSL_COLMAP_BIN=/opt/colmap-cuda/bin/colmap \
  python3 scripts/lab-ui-server.py --host 127.0.0.1 --port 8769
```

or for a one-off CLI stage:

```bash
GSL_COLMAP_BIN=/opt/colmap-cuda/bin/colmap \
  .venv/bin/python scripts/lab-pipeline.py run-stage sfm \
    --job outputs/jobs/<job-id>/job.json \
    --accept-warning \
    --allow-heavy
```

Revert is simply unsetting the variable:

```bash
unset GSL_COLMAP_BIN
```

If the CUDA build was installed outside the repo, remove that separate directory according to the install note for that build. Do not remove `/usr/bin/colmap` unless you intentionally want to remove the CPU fallback.

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
