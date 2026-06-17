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

## Entry: 2026-06-15 CUDA nvcc setup gap

Date: 2026-06-15
Operator: Codex
Machine: Windows RTX 5090 workstation / WSL2
Purpose: Identify the narrow CUDA Toolkit component needed for gsplat JIT compilation after `splat_training` reached the CUDA extension boundary.
Dependency: NVIDIA CUDA WSL-Ubuntu repo keyring and `cuda-nvcc-12-8`
Commercial decision: Covered by the existing `nvidia-cuda` conditional decision in `framework-evaluation.json`; local workstation use only unless NVIDIA redistribution terms are reviewed.
Command considered:

```bash
sudo dpkg -i /tmp/cuda-keyring_1.1-1_all.deb
sudo apt-get update
sudo apt-get install -y cuda-nvcc-12-8
```

Working directory: `/home/engwall/projects/gaussian-splat-lab`
Expected changes: register NVIDIA's WSL-Ubuntu CUDA apt repository and install the CUDA 12.8 nvcc/compiler packages under `/usr/local/cuda-12.8/`, including `/usr/local/cuda-12.8/bin/nvcc`.
Validation: `/usr/local/cuda-12.8/bin/nvcc --version`, `torch.utils.cpp_extension.CUDA_HOME`, and `.venv/bin/python scripts/lab-pipeline.py run-stage splat_training --job <job.json> --allow-heavy`.
Revert plan: remove installed CUDA packages with `sudo apt-get remove cuda-nvcc-12-8` and remove the CUDA keyring/repo package with `sudo apt-get remove cuda-keyring` if no longer needed; verify `nvcc` is absent or no longer on PATH.
Result: pass for CUDA/nvcc after the user installed the documented packages locally. `/usr/local/cuda-12.8/bin/nvcc --version` reports CUDA compilation tools release 12.8, V12.8.93. Installed package snapshot includes `cuda-keyring 1.1-1`, `cuda-nvcc-12-8 12.8.93-1`, `cuda-cudart-dev-12-8 12.8.90-1`, `cuda-nvvm-12-8 12.8.93-1`, and `cuda-crt-12-8 12.8.93-1`.
Notes: Do not install `cuda`, `cuda-12-x`, `cuda-drivers`, or Ubuntu `nvidia-cuda-toolkit` for this WSL setup. NVIDIA's WSL guidance warns not to install a Linux display driver inside WSL; use toolkit-only packages. The remaining gsplat setup gap is Python development headers for Python 3.12.

## Entry: 2026-06-15 Python 3.12 development headers setup gap

Date: 2026-06-15
Operator: Codex
Machine: Windows RTX 5090 workstation / WSL2
Purpose: Provide `Python.h` for gsplat's CUDA extension build after CUDA Toolkit `nvcc` became visible.
Dependency: Ubuntu package `python3.12-dev`
Commercial decision: System build dependency for local workstation compilation; do not redistribute system packages without OS/package license review.
Command considered:

```bash
sudo apt-get install -y python3.12-dev
```

Working directory: `/home/engwall/projects/gaussian-splat-lab`
Expected changes: install Python 3.12 C headers and related development files under system include/lib paths, including `/usr/include/python3.12/Python.h`.
Validation: `test -f /usr/include/python3.12/Python.h` and `.venv/bin/python scripts/lab-pipeline.py run-stage splat_training --job outputs/jobs/static-room-orbit-001-20260614T100535Z/job.json --allow-heavy`.
Revert plan: remove with `sudo apt-get remove python3.12-dev` if no longer needed; run `sudo apt-get autoremove` only after reviewing packages apt proposes to remove.
Result: pass after the user installed `python3.12-dev 3.12.3-1ubuntu0.13`. `/usr/include/python3.12/Python.h` exists, `splat_training --allow-heavy` passed, and gsplat produced checkpoint/PLY/sample-render artifacts on the RTX 5090.
Notes: `python3-dev` is also available in apt, but the exact missing header path belongs to Python 3.12, so the narrow package is `python3.12-dev`. The remaining quality warning is capture/commercial provenance, not a Python/CUDA setup gap.

## Entry: 2026-06-16 Install bubblewrap for Codex sandbox support

Date: 2026-06-16
Operator: User
Machine: Windows RTX 5090 workstation / WSL2
Purpose: Restore the local Codex sandbox helper after image inspection and patch application failed with missing `bwrap`.
Dependency: Ubuntu package `bubblewrap 0.9.0-1ubuntu0.1`
Commercial decision: Developer/sandbox support tool only; not a Gaussian Splat runtime dependency and not intended for redistribution with product artifacts.
Command recorded:

```bash
sudo apt-get install -y bubblewrap
```

Working directory: system package install, outside repo
Expected changes: apt-managed `/usr/bin/bwrap` and package metadata for `bubblewrap`.
Validation:

```bash
command -v bwrap
bwrap --version
dpkg-query -W -f='${Package} ${Version}\n' bubblewrap
```

Revert plan: remove with `sudo apt-get remove bubblewrap` if Codex sandbox support is no longer needed; review apt's proposed autoremove list before accepting any additional removals.
Result: pass; `/usr/bin/bwrap` exists, `bwrap --version` reports `bubblewrap 0.9.0`, dpkg reports `bubblewrap 0.9.0-1ubuntu0.1`, `view_image` successfully opened the render-review contact sheet, and `apply_patch` successfully edited tracked files after install.
Notes: This fixes the local Codex tooling issue only. It does not affect the video-to-splat runtime pipeline or commercial framework decision surface.

## Entry: 2026-06-17 Install local Spark/Three.js viewer dependencies

Date: 2026-06-17
Operator: Codex
Machine: Windows RTX 5090 workstation / WSL2
Purpose: Add a production-style browser Gaussian Splat viewer while keeping the existing PLY point-debug viewer available as a fallback/debug mode.
Dependency: npm packages `@sparkjsdev/spark 2.1.0`, `three 0.180.0`, and transitive `fflate 0.8.3`
Commercial decision: `sparkjsdev-spark` is `preferred` / `allowed_with_notice`; `threejs` and `fflate` are `accepted` / `allowed_with_notice` in `framework-evaluation.json`.
Command:

```bash
npm install
```

Working directory: `/home/engwall/projects/gaussian-splat-lab`
Expected changes: create ignored `node_modules/`, create/update tracked `package-lock.json`, and leave exact package versions reproducible from `package.json`/lockfile.
Validation: `npm ls --depth=0`, `npm run check:js`, `./scripts/validate-ui-contracts.sh`, browser screenshot/visual QA of Spark viewer mode.
Revert plan: remove tracked `package.json`/`package-lock.json` changes if abandoning the Spark viewer, delete ignored `node_modules/`, and remove any UI/server routes that serve local npm modules.
Result: pass. `npm ls --depth=0` reports `@sparkjsdev/spark 2.1.0` and `three 0.180.0`; lockfile records transitive `fflate 0.8.3`. `npm run check:js`, `./scripts/validate-ui-contracts.sh`, `./scripts/validate-architecture-contracts.sh` and `./scripts/validate-phase-1-contracts.sh` passed. PowerShell/Chrome visual QA reached `spark|reference inspect|` and wrote `C:\Users\engwa\AppData\Local\Temp\gslab-spark-cdp-capped.png`.
Notes: The app does not import CDN resources; browser imports resolve to local project `node_modules` through the local UI server. Initial `lod: "quality"` caused Spark to load the 22 MB PLY to 100% but not finish initialization in QA, so the first stable renderer path uses `lod: false`. The viewer render loop is capped to 24 fps and pauses when hidden to avoid unnecessary RTX load while the UI is idle.

## Entry: 2026-06-17 Install gdown dataset helper and Mip-NeRF 360 flowers reference

Date: 2026-06-17
Operator: Codex
Machine: Windows RTX 5090 workstation / WSL2
Purpose: Attempt Nerfstudio `dozer` dataset download, then use a reproducible Mip-NeRF 360 reference capture when Google Drive access was unavailable.
Dependency: Python package `gdown 6.1.0` with transitive packages `beautifulsoup4 4.15.0`, `certifi 2026.6.17`, `charset_normalizer 3.4.7`, `idna 3.18`, `PySocks 1.7.1`, `requests 2.34.2`, `soupsieve 2.8.4`, `tqdm 4.68.3`, `urllib3 2.7.0`
Commercial decision: `gdown` is MIT licensed and accepted as a repo-local dataset download helper only. Downloaded datasets are separate inputs and remain technical-validation-only until exact dataset license evidence is reviewed.
Commands:

```bash
.venv/bin/python -m pip install --disable-pip-version-check gdown
.venv/bin/gdown 1jQJPz5PhzTH--LOcCxvfzV_SDLEp1de3 -O data/datasets/nerfstudio/dozer.zip
curl -L -C - --fail https://storage.googleapis.com/gresearch/refraw360/360_extra_scenes.zip -o data/datasets/mipnerf360/360_extra_scenes.zip
ffmpeg -y -framerate 3 -start_number 9040 -i data/datasets/mipnerf360/flowers/images_4/_DSC%04d.JPG -c:v libx264 -preset medium -crf 16 -pix_fmt yuv420p data/videos/mipnerf360-flowers-reference.mp4
```

Working directory: `/home/engwall/projects/gaussian-splat-lab`
Expected changes: install ignored venv packages; write ignored dataset/video artifacts under `data/datasets/mipnerf360/` and `data/videos/`; update tracked manifests/docs separately.
Validation: `.venv/bin/python -m pip show gdown`, `sha256sum data/datasets/mipnerf360/360_extra_scenes.zip data/videos/mipnerf360-flowers-reference.mp4`, pipeline run `mipnerf360-flowers-reference-20260617T142004Z`, and PowerShell/Chrome visual QA reaching `spark|reference inspect|`.
Revert plan: remove `gdown` and its transitive packages from the venv if they are not needed by other tooling; delete ignored local artifacts `data/datasets/mipnerf360/`, `data/videos/mipnerf360-flowers-reference.mp4`, `data/videos/.provenance/mipnerf360-flowers-reference.mp4.derived.json`, and `outputs/jobs/mipnerf360-flowers-reference-20260617T142004Z/`; revert tracked manifest/docs changes if abandoning this reference.
Result: partial pass. Nerfstudio `dozer` failed through `gdown` because Google Drive did not expose a retrievable public file URL to CLI automation. Mip-NeRF 360 `360_extra_scenes.zip` downloaded from Google Cloud Storage and extracted `flowers`; derived MP4 SHA-256 is `adabc37325e0182770f104a7222af6b8d74e12bc27ba57ce96dea8b617e80153`, archive SHA-256 is `f8d42b372d7cc589928c3d22849f958c1e2ae948c21e89c6a32c904cefba2fa4`.
Notes: The active technical run passed frame sampling, SfM, `rtx_reference` training, packaging and viewer validation. SfM registered 173/173 frames with 43,287 sparse points and mean reprojection error 0.477 px. `rtx_reference` used RTX 5090, 9,000 iterations, 64 images, 400,000 gaussians, 67.7 seconds wall time and produced a 22.4 MB binary PLY. Visual review shows a recognizable but still soft scene; this is a pipeline-quality baseline, not commercial showcase material.
