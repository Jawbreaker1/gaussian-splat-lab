# Installation and Revert Ledger

Verified: 2026-06-07

Purpose: every package, binary, driver, toolchain or environment change made for this lab must be documented so it can be reviewed and reverted deliberately.

## Rule

Do not install or upgrade dependencies silently. Before or during an install, record:

- timestamp
- operator
- reason
- exact command
- working directory
- package/source/version
- files or environment expected to change
- validation command after install
- revert command or manual rollback plan
- whether the dependency is allowed, conditional or blocked in `framework-evaluation.json`

Generated install logs can live under ignored `logs/`, but curated decisions and reproducible setup notes should be copied here or into `docs/validation/`.

## Current Session

No packages, binaries, Python wheels, npm packages, CUDA components, COLMAP builds or gsplat/Nerfstudio packages were installed by Codex in this session.

The environment stage implemented in this session only detects installed tools and writes `setup_gap` when something is missing.

## Entry Template

```text
Date:
Operator:
Machine:
Purpose:
Dependency:
Commercial decision:
Command:
Working directory:
Expected changes:
Validation:
Revert plan:
Result:
Notes:
```

## Revert Guidance

Prefer isolated environments:

- Python: project `.venv` or documented conda environment
- Node: project-local `node_modules/` only after npm stack is approved
- System binaries: record apt/choco/winget/manual installer source and uninstall command
- CUDA/NVIDIA: record driver/toolkit versions and rollback path before changing them

If a dependency is installed into a shared system environment, document that explicitly and treat rollback as a manual machine-level operation.

## Entry: 2026-06-07 PyTorch CUDA venv bootstrap

Date: 2026-06-07
Operator: Codex
Machine: Windows RTX 5090 workstation / WSL2
Purpose: Create an isolated Python environment for GPU pipeline validation without modifying system Python.
Dependency: Python venv, pip, PyTorch CUDA 12.8 wheels
Commercial decision: PyTorch is `accepted` / `allowed_with_notice` in `framework-evaluation.json`; local venv use only at this stage.
Commands:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128
.venv/bin/python -c "import torch; print(torch.__version__); print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0)); print((torch.tensor([1.0, 2.0], device='cuda') * 2).cpu().tolist())"
```

Working directory: `/home/engwall/projects/gaussian-splat-lab`
Expected changes: create ignored `.venv/` directory only.
Validation: `python3 scripts/lab-pipeline.py run-stage environment --job <job.json>` should move `pytorch_cuda` from `setup_gap` to `pass` if CUDA wheel supports the RTX 5090 runtime.
Revert plan: stop processes using `.venv`, then delete `.venv/`; no system package should be changed.
Result: venv bootstrap failed because `ensurepip` is unavailable; no package installed by this entry yet.
Notes: System Python currently has no pip module. The failed `python3 -m venv .venv` left a partial ignored `.venv/`; recreate it with `--clear` after `python3.12-venv` is installed.

## Entry: 2026-06-07 Install python3.12-venv

Date: 2026-06-07
Operator: Codex
Machine: Windows RTX 5090 workstation / WSL2
Purpose: Enable Python's built-in venv/ensurepip so the GPU toolchain can be installed into a repo-local `.venv` instead of system Python.
Dependency: Ubuntu package `python3.12-venv` version candidate `3.12.3-1ubuntu0.13`
Commercial decision: OS packaging utility, not a runtime Gaussian Splat dependency; used only to create isolated local environment.
Command:

```bash
sudo apt-get install -y python3.12-venv
```

Working directory: `/home/engwall/projects/gaussian-splat-lab`
Expected changes: install Ubuntu package `python3.12-venv` and apt-managed dependencies if required.
Validation: `python3 -m venv --clear .venv` followed by `.venv/bin/python -m pip --version`.
Revert plan: remove the package with `sudo apt-get remove python3.12-venv`; delete repo-local `.venv/` if created.
Result: not installed; `sudo apt-get install -y python3.12-venv` failed because sudo requires an interactive password/TTY.
Notes: `apt-cache policy python3.12-venv` reports installed `(none)` and candidate `3.12.3-1ubuntu0.13`.

## Entry: 2026-06-07 Bootstrap pip inside partial .venv with get-pip.py

Date: 2026-06-07
Operator: Codex
Machine: Windows RTX 5090 workstation / WSL2
Purpose: Add pip inside the repo-local `.venv` after Ubuntu `ensurepip` was unavailable and sudo install of `python3.12-venv` was blocked.
Dependency: PyPA `get-pip.py`, pip/setuptools/wheel installed into `.venv` only
Commercial decision: Python packaging bootstrap tool; not a runtime Gaussian Splat dependency. Used only to enable isolated local dependency installation.
Commands:

```bash
mkdir -p logs/install
curl -fsSL https://bootstrap.pypa.io/get-pip.py -o logs/install/get-pip-20260607.py
.venv/bin/python logs/install/get-pip-20260607.py
.venv/bin/python -m pip --version
```

Working directory: `/home/engwall/projects/gaussian-splat-lab`
Expected changes: install pip tooling inside ignored `.venv/`; store downloaded bootstrap script under ignored `logs/install/`.
Validation: `.venv/bin/python -m pip --version`.
Revert plan: delete `.venv/` and `logs/install/get-pip-20260607.py`.
Result: pass; installed pip 26.1.2 inside `.venv` only. Downloaded `get-pip.py` size 2226848 bytes, sha256 `a341e1a43e38001c551a1508a73ff23636a11970b61d901d9a1cad2a18f57055`.
Notes: Official pip installation docs list `https://bootstrap.pypa.io/get-pip.py` as the bootstrap script when needed.

## Entry: 2026-06-07 Install PyTorch CUDA 12.8 into .venv

Date: 2026-06-07
Operator: Codex
Machine: Windows RTX 5090 workstation / WSL2
Purpose: Enable PyTorch CUDA smoke validation for the Gaussian Splat pipeline environment gate.
Dependency: PyTorch `torch` and `torchvision` wheels from PyTorch CUDA 12.8 index
Commercial decision: PyTorch is `accepted` / `allowed_with_notice` in `framework-evaluation.json`; local venv use only at this stage.
Command:

```bash
.venv/bin/python -m pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cu128
```

Working directory: `/home/engwall/projects/gaussian-splat-lab`
Expected changes: install PyTorch packages and wheel dependencies inside ignored `.venv/` only; no pip cache retained by command.
Validation: `.venv/bin/python -c "import torch; print(torch.__version__); print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0)); print((torch.tensor([1.0, 2.0], device='cuda') * 2).cpu().tolist())"` and `.venv/bin/python scripts/lab-pipeline.py run-stage environment --job <job.json>`.
Revert plan: delete `.venv/`; no system package should be changed.
Result: pass; installed torch 2.11.0+cu128 and torchvision 0.26.0+cu128 into `.venv`; CUDA smoke passed on NVIDIA GeForce RTX 5090 with tensor result `[2.0, 4.0]`; `.venv` size after install: 6.8G. Exact package freeze recorded in `requirements/gpu-cu128.txt`.
Notes: Official PyTorch install selector lists CUDA 12.8 pip wheels. Command used `--no-cache-dir` to avoid retaining pip cache outside `.venv`.

## Entry: 2026-06-07 Install gsplat into .venv

Date: 2026-06-07
Operator: Codex
Machine: Windows RTX 5090 workstation / WSL2
Purpose: Enable the Gaussian splatting rasterization/training backend smoke for the environment gate.
Dependency: Python package `gsplat`
Commercial decision: `gsplat` is `accepted` / `allowed_with_notice` in `framework-evaluation.json`; local venv use only at this stage.
Command:

```bash
.venv/bin/python -m pip install --no-cache-dir gsplat
```

Working directory: `/home/engwall/projects/gaussian-splat-lab`
Expected changes: install gsplat and Python dependencies inside ignored `.venv/` only; no pip cache retained by command.
Validation: `.venv/bin/python -c "import gsplat; print(gsplat.__version__)"` and environment stage.
Revert plan: delete `.venv/` or uninstall with `.venv/bin/python -m pip uninstall gsplat`; full rollback remains deleting `.venv/`.
Result: pass; installed gsplat 1.5.3 into `.venv`; import smoke passed; environment stage now reports `gsplat=pass`. Updated exact package freeze in `requirements/gpu-cu128.txt`.
Notes: Official gsplat project is accepted in framework evaluation as Apache-2.0.

## Entry: 2026-06-07 COLMAP setup gap

Date: 2026-06-07
Operator: Codex
Machine: Windows RTX 5090 workstation / WSL2
Purpose: Identify the next SfM dependency required by the environment gate.
Dependency: COLMAP command-line tool
Commercial decision: COLMAP is `accepted` / `allowed_with_notice` in `framework-evaluation.json`, with dependency review required for the exact binary/build.
Command considered:

```bash
sudo apt-get install -y colmap
```

Working directory: `/home/engwall/projects/gaussian-splat-lab`
Expected changes: apt-managed COLMAP package and dependencies if installed.
Validation: `colmap --help` and environment stage.
Revert plan: `sudo apt-get remove colmap` if installed by apt.
Result: pass; user installed COLMAP manually after resetting/using sudo credentials. Installed apt package `colmap 3.9.1-2build2` at `/usr/bin/colmap`; `colmap --help` reports `COLMAP 3.9.1 -- Structure-from-Motion and Multi-View Stereo (Commit Unknown on Unknown without CUDA)`. Environment stage now reports `colmap=pass` and overall `environment_status=pass`.
Notes: `apt-cache policy colmap` now reports installed `3.9.1-2build2` from Ubuntu noble/universe. Setup notes recorded in `docs/rtx-workstation-setup.md`. This Ubuntu package is without CUDA; acceptable for first SfM validation, but performance expectations should reflect CPU COLMAP.

## Entry: 2026-06-08 FFmpeg / ffprobe setup gap

Date: 2026-06-08
Operator: Codex
Machine: Windows RTX 5090 workstation / WSL2
Purpose: Identify the next video intake dependency required for metadata extraction and frame sampling.
Dependency: FFmpeg / ffprobe command-line tools
Commercial decision: FFmpeg is `conditional` / `conditional_external_tool_only` in `framework-evaluation.json`; use as system external tool for lab only, with build flags and redistribution reviewed before product packaging.
Command considered:

```bash
sudo apt-get install -y ffmpeg
```

Working directory: `/home/engwall/projects/gaussian-splat-lab`
Expected changes: apt-managed FFmpeg package and dependencies if installed.
Validation: `ffprobe -version`, `ffmpeg -version`, and future intake/frame-sampling stages.
Revert plan: `sudo apt-get remove ffmpeg` if installed by apt.
Result: pass; user installed FFmpeg manually. Installed apt package `ffmpeg 7:6.1.1-3ubuntu5` at `/usr/bin/ffmpeg` and `/usr/bin/ffprobe`; both report version `6.1.1-3ubuntu5`.
Notes: The Ubuntu build configuration includes `--enable-gpl`, so this remains conditional for commercial/product use. It is acceptable as a system external tool in this lab, but must not be bundled or redistributed without LGPL/GPL/build-flag review.

## Entry: 2026-06-15 Install packaging into .venv

Date: 2026-06-15
Operator: Codex
Machine: Windows RTX 5090 workstation / WSL2
Purpose: Provide the Python packaging utility required by the local torch/gsplat training runtime path.
Dependency: Python package `packaging`
Commercial decision: `packaging` is `accepted` / `allowed_with_notice` in `framework-evaluation.json`; package metadata reports `Apache-2.0 OR BSD-2-Clause`.
Command:

```bash
.venv/bin/python -m pip install --no-cache-dir packaging
```

Working directory: `/home/engwall/projects/gaussian-splat-lab`
Expected changes: install `packaging` inside ignored `.venv/` only and update `requirements/gpu-cu128.txt` with the exact version.
Validation: `.venv/bin/python -c "import packaging; print(packaging.__version__)"` and the `splat_training` stage.
Revert plan: uninstall with `.venv/bin/python -m pip uninstall packaging`; full rollback remains deleting `.venv/`.
Result: pass; installed `packaging 26.2` into `.venv`; exact package freeze updated in `requirements/gpu-cu128.txt`.
Notes: This was discovered by the first gsplat training smoke attempt, which failed before sustained GPU load with `No module named 'packaging'`.

## Entry: 2026-06-15 Attempt nvidia-cuda-nvcc-cu12 wheel, then revert

Date: 2026-06-15
Operator: Codex
Machine: Windows RTX 5090 workstation / WSL2
Purpose: Test whether a repo-local CUDA 12.8 nvcc wheel could satisfy gsplat JIT compilation without a system CUDA Toolkit install.
Dependency: Python package `nvidia-cuda-nvcc-cu12`
Commercial decision: Covered by the existing `nvidia-cuda` conditional decision in `framework-evaluation.json`; package metadata reports NVIDIA Proprietary Software.
Command:

```bash
.venv/bin/python -m pip install --no-cache-dir nvidia-cuda-nvcc-cu12==12.8.93
```

Working directory: `/home/engwall/projects/gaussian-splat-lab`
Expected changes: install NVIDIA CUDA compiler-related files inside ignored `.venv/` only.
Validation: inspect wheel contents for `nvcc`, run `torch.utils.cpp_extension.CUDA_HOME`, and re-run `splat_training`.
Revert plan: uninstall with `.venv/bin/python -m pip uninstall nvidia-cuda-nvcc-cu12`; full rollback remains deleting `.venv/`.
Result: reverted; the wheel installed successfully but did not provide a `bin/nvcc` executable, so it did not satisfy gsplat's CUDA toolkit check. It was removed with:

```bash
.venv/bin/python -m pip uninstall -y nvidia-cuda-nvcc-cu12
```

Notes: After revert, `requirements/gpu-cu128.txt` no longer contains `nvidia-cuda-nvcc-cu12`. The remaining setup gap is a CUDA Toolkit with `nvcc` visible to WSL or a compatible prebuilt gsplat wheel.

