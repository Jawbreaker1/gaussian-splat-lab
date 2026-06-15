# Stable Pipeline Build Plan

Verified: 2026-06-15

Goal: build the first robust golden path from local video to browser-visible Gaussian Splat on the Windows RTX 5090 workstation.

This plan is intentionally narrower than the long-term roadmap. The next implementation work should make one stage real at a time, validate it, and only then let the next stage depend on its output.

## Current Foundation

Already in place:

- dependency-free local UI for job planning
- manifest-driven pipeline skeleton
- dependency/license preflight gate
- commercial compliance gate
- preflight and media pipeline gate manifest
- RTX 5090 visibility from WSL via `nvidia-smi`
- COLMAP install/version validation
- FFmpeg/ffprobe install/version validation
- video intake stage with explicit missing-file and metadata stop conditions
- frame sampling stage with FFmpeg extraction, SHA256 frame manifest and contact sheet
- SfM stage boundary with COLMAP CPU feature extraction, matching, mapper and model analyzer
- minimal gsplat training orchestration with checkpoint/PLY/sample-render validation once the gsplat CUDA extension is available
- low-load stage gates for packaging, viewer validation and quality reporting
- placeholder capture and viewer asset manifests
- capture readiness reporting for local file/provenance status before intake

Not yet real:

- gsplat CUDA rasterization on this WSL environment, because Python 3.12 development headers are not installed yet; CUDA Toolkit `nvcc` is now visible
- a clean commercially reusable capture; the current imported phone video is local-test-only evidence
- actual packaging/export conversion beyond the training-produced PLY handoff
- real splat viewer load and screenshot validation

## Current Environment Result

As of 2026-06-15, the repo-local `.venv` and workstation validate:

- RTX 5090 visible through `nvidia-smi`
- PyTorch CUDA smoke passes with torch 2.11.0+cu128
- gsplat 1.5.3 imports successfully; CUDA Toolkit `nvcc` is visible at `/usr/local/cuda-12.8/bin/nvcc`, but extension build preflight reports `setup_gap` because `/usr/include/python3.12/Python.h` is missing
- COLMAP 3.9.1 is on PATH at `/usr/bin/colmap`
- installed COLMAP package reports `without CUDA`, so first SfM validation should assume CPU COLMAP
- FFmpeg/ffprobe 6.1.1-3ubuntu5 are on PATH at `/usr/bin/ffmpeg` and `/usr/bin/ffprobe`
- the installed Ubuntu FFmpeg build includes `--enable-gpl`; keep it as a lab-only system tool until redistribution/build flags are reviewed
- frame sampling passed a synthetic CLI smoke test; evidence is recorded in `docs/validation/phase-1-frame-sampling-smoke.md`
- SfM has a runnable COLMAP stage wrapper; the first post-PSU test produced a passing sparse reconstruction from local frame input
- `splat_training` now has a minimal gsplat trainer wrapper and correctly stops at `setup_gap` when the gsplat CUDA extension cannot load

## Workload Safety

Heavy stages remain guarded even after the PSU replacement. `sfm`, `splat_training` and `viewer` must not run accidentally. The CLI writes `blocked_workload` unless a heavy stage is explicitly run with `--allow-heavy`.

The UI intentionally sends `allowHeavy=false`; use CLI approval only after confirming the machine can sustain the load.

## Next Build Step

Install Python 3.12 development headers, then rerun the guarded `splat_training` stage.

Current setup note: PyTorch CUDA works on the RTX 5090, gsplat 1.5.3 imports, `CUDA_HOME` resolves to `/usr/local/cuda-12.8`, and `nvcc` is visible. The current `setup_gap` is `/usr/include/python3.12/Python.h` missing, which gsplat needs while building its CUDA extension. The official gsplat wheel index checked during validation did not provide a compatible prebuilt wheel for Python 3.12 + torch 2.11/cu128.

Why next:

- intake, frame sampling and SfM now pass on a local-test-only capture
- the training wrapper exists and reaches the exact gsplat CUDA-extension boundary
- without `Python.h`, gsplat cannot compile its CUDA extension even though `nvcc` is now available
- once this setup gap is closed, the same `splat_training --allow-heavy` command should run the first real GPU training smoke

Expected output after the setup gap is closed:

```text
outputs/jobs/<job_id>/reports/splat_training.json
outputs/jobs/<job_id>/splats/<run_timestamp>/checkpoint.pt
outputs/jobs/<job_id>/splats/<run_timestamp>/trained_splats.ply
outputs/jobs/<job_id>/splats/<run_timestamp>/sample_render.png
```

Stop condition:

- no packaging or viewer stage may run until `splat_training` writes a `pass` or explicitly accepted `warning` report with an exported artifact path
- do not install or redistribute NVIDIA CUDA Toolkit components without recording the exact install source and terms in the installation ledger

## Golden Path Implementation Sequence

### 0. Preflight Checks

Preflight checks protect project and workstation assumptions before the media pipeline starts.

Inputs:

- framework evaluation manifest
- job manifest
- local machine runtime

Components:

- Python stdlib
- `nvidia-smi`
- PyTorch when installed
- COLMAP when installed
- gsplat when installed

Outputs:

- `FrameworkDecisionReport`
- `EnvironmentReport`

Validation:

- runtime dependencies are accepted, conditional or blocked explicitly
- RTX 5090 visible
- PyTorch CUDA smoke passes
- COLMAP version recorded or setup gap recorded
- gsplat smoke passes or setup gap recorded

### 1. Video Intake

Inputs:

- `CaptureInput`
- environment report with `pass` or accepted `warning`

Components:

- system `ffprobe`

Output:

- `CaptureMetadata`

Validation:

- file exists
- provenance/license present
- duration, resolution, fps, codec and bitrate recorded
- video falls inside MVP limits

### 2. Frame Sampling

Inputs:

- `CaptureMetadata`

Components:

- system `ffmpeg`

Output:

- `FrameManifest`
- sampled frames under ignored job/artifact path
- contact sheet

Validation:

- frame count matches plan
- timestamps are monotonic
- files exist
- hashes recorded

### 3. SfM / Camera Solve

Inputs:

- `FrameManifest`

Components:

- COLMAP command line

Output:

- `CameraSolveReport`
- COLMAP database/model under ignored job/artifact path

Validation:

- registered-frame percentage recorded
- sparse point count nonzero
- reprojection metrics recorded
- if COLMAP emits multiple sparse models, the report selects the model with the most registered images
- failure boundary is clear if solve fails

### 4. Splat Training

Inputs:

- `CameraSolveReport`

Components:

- minimal repo-local `gsplat` trainer first
- Nerfstudio/Splatfacto remains a later alternative once dependency impact is justified

Output:

- `TrainingRunReport`
- checkpoint/export under ignored job/artifact path

Validation:

- training command and versions recorded
- gsplat CUDA extension availability checked before training
- export exists
- loss samples and wall time recorded
- sample render evidence saved where practical

### 5. Packaging

Inputs:

- `TrainingRunReport`

Components:

- selected export/conversion path

Output:

- `SplatArtifact`

Validation:

- artifact exists
- format, byte size and hash recorded
- selected viewer supports the format

### 6. Viewer Validation

Inputs:

- `SplatArtifact`

Components:

- Spark + Three.js first, subject to dependency gate when introduced
- Playwright or browser automation when available

Output:

- `ViewerValidationReport`

Validation:

- canvas is nonblank
- orbit, pan, zoom and reset work
- screenshot evidence saved

### 7. Quality Report

Inputs:

- all stage reports

Output:

- `CaptureQualityReport`

Validation:

- result classified as `usable`, `weak` or `failed`
- failure boundary identified
- enough evidence preserved for rerun/diagnosis

## What Not To Do Yet

Do not start with:

- arbitrary user-uploaded videos
- input-quality degradation experiments
- preflight scoring as a blocker
- polished React/Vite app
- cloud services
- main-project integration

Those are valuable later, after one known-good capture works end to end.

## Current Concrete Implementation Ticket

Import one known-good local capture through the provenance-aware CLI, then make `intake` and `frame_sampling` pass before any heavy stage is considered.

- download or self-record a static-scene orbit video outside git
- run `import-video` so the file lands at the manifest target path with a local hash/provenance report
- run `list-captures` and confirm the source file check changes from `setup_gap` to `pass`
- create a job for that capture
- run preflight checks (`framework_license`, `environment`), then media stages (`intake`, `frame_sampling`)
- stop before `sfm`, training or viewer validation unless heavy workload is explicitly approved in that turn

Acceptance:

```bash
./scripts/validate-architecture-contracts.sh
./scripts/validate-phase-1-contracts.sh
./scripts/validate-ui-contracts.sh
.venv/bin/python scripts/lab-pipeline.py list-captures --capture-manifest data/manifests/captures.example.json
.venv/bin/python scripts/lab-pipeline.py import-video --capture-id <capture-id> --input <local-video> --accept-warning --overwrite
.venv/bin/python scripts/lab-pipeline.py init-job --capture-id <capture-id>
.venv/bin/python scripts/lab-pipeline.py run-stage framework_license --job outputs/jobs/<job_id>/job.json
.venv/bin/python scripts/lab-pipeline.py run-stage environment --job outputs/jobs/<job_id>/job.json
.venv/bin/python scripts/lab-pipeline.py run-stage intake --job outputs/jobs/<job_id>/job.json
.venv/bin/python scripts/lab-pipeline.py run-stage frame_sampling --job outputs/jobs/<job_id>/job.json --accept-warning
```
