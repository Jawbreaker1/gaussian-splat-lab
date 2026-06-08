# Stable Pipeline Build Plan

Verified: 2026-06-08

Goal: build the first robust golden path from local video to browser-visible Gaussian Splat on the Windows RTX 5090 workstation.

This plan is intentionally narrower than the long-term roadmap. The next implementation work should make one stage real at a time, validate it, and only then let the next stage depend on its output.

## Current Foundation

Already in place:

- dependency-free local UI for job planning
- manifest-driven pipeline skeleton
- framework/license evaluation gate
- commercial compliance gate
- pipeline gate manifest
- RTX 5090 visibility from WSL via `nvidia-smi`
- COLMAP install/version validation
- FFmpeg/ffprobe install/version validation
- video intake stage with explicit missing-file and metadata stop conditions
- frame sampling stage with FFmpeg extraction, SHA256 frame manifest and contact sheet
- SfM stage boundary with COLMAP CPU feature extraction, matching, mapper and model analyzer
- placeholder capture and viewer asset manifests

Not yet real:

- a known-good capture video that passes intake, frame sampling and SfM
- splat training
- real splat viewer load

## Current Environment Result

As of 2026-06-08, the repo-local `.venv` and workstation validate:

- RTX 5090 visible through `nvidia-smi`
- PyTorch CUDA smoke passes with torch 2.11.0+cu128
- gsplat 1.5.3 imports successfully
- COLMAP 3.9.1 is on PATH at `/usr/bin/colmap`
- installed COLMAP package reports `without CUDA`, so first SfM validation should assume CPU COLMAP
- FFmpeg/ffprobe 6.1.1-3ubuntu5 are on PATH at `/usr/bin/ffmpeg` and `/usr/bin/ffprobe`
- the installed Ubuntu FFmpeg build includes `--enable-gpl`; keep it as a lab-only system tool until redistribution/build flags are reviewed
- frame sampling passed a synthetic CLI smoke test; evidence is recorded in `docs/validation/phase-1-frame-sampling-smoke.md`
- SfM now has a runnable COLMAP stage wrapper; successful reconstruction awaits real frame input

## Workload Safety

Heavy stages are currently guarded because the workstation has a known power-supply/load stability concern. `sfm`, future training and viewer/render validation must not run accidentally. The CLI writes `blocked_workload` unless a heavy stage is explicitly run with `--allow-heavy`.

The UI intentionally sends `allowHeavy=false`; use CLI approval only after confirming the machine can sustain the load.

## Next Build Step

Provide a known-good local capture and make the video intake stage pass.

Current setup note: FFmpeg/ffprobe is installed and now recorded by the environment report. The current placeholder capture points at `data/videos/static-room-orbit-001.mp4`, which does not exist yet, so intake correctly writes a `fail` report and frame sampling refuses to run on top of it.

Why next:

- the environment gate now passes on the RTX workstation
- intake is the first stage that touches real capture input
- it gives frame sampling and SfM a validated metadata contract instead of ad hoc file paths
- the frame sampling command is already implemented and will produce `FrameManifest` once intake passes
- the SfM command is already implemented and will refuse to run until `FrameManifest` is valid

Expected output:

```text
outputs/jobs/<job_id>/reports/intake.json
```

Minimum intake report fields:

- source video path
- source/provenance/license fields from the capture manifest
- `ffprobe` availability/version or `setup_gap`
- duration, resolution, frame rate, codec, bitrate and stream summary
- pass/warning/fail classification against MVP limits

Stop condition:

- no frame sampling may run until intake report is `pass` or an explicitly accepted `warning`
- missing video file or missing/unclear source rights must stop the pipeline

## Golden Path Implementation Sequence

### 1. Environment Gate

Inputs:

- job manifest
- framework evaluation manifest
- local machine runtime

Components:

- Python stdlib
- `nvidia-smi`
- PyTorch when installed
- COLMAP when installed
- gsplat when installed

Output:

- `EnvironmentReport`

Validation:

- RTX 5090 visible
- PyTorch CUDA smoke passes
- COLMAP version recorded or setup gap recorded
- gsplat smoke passes or setup gap recorded

### 2. Video Intake

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

### 3. Frame Sampling

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

### 4. SfM / Camera Solve

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
- failure boundary is clear if solve fails

### 5. Splat Training

Inputs:

- `CameraSolveReport`

Components:

- Nerfstudio/Splatfacto first
- `gsplat` backend

Output:

- `TrainingRunReport`
- checkpoint/export under ignored job/artifact path

Validation:

- training command and versions recorded
- export exists
- loss samples and wall time recorded
- sample render evidence saved where practical

### 6. Packaging

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

### 7. Viewer Validation

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

### 8. Quality Report

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

## First Concrete Implementation Ticket

Build `environment` stage support into `scripts/lab-pipeline.py`:

- add a `run-stage environment` command
- write `outputs/jobs/<job_id>/reports/environment.json`
- record `nvidia-smi`
- record Python version
- if PyTorch is installed, run a minimal CUDA tensor test
- if PyTorch is missing, write `setup_gap` with install guidance
- if COLMAP/gsplat are missing, write `setup_gap` entries without pretending reconstruction failed
- make the UI show the environment report status for the active job

Acceptance:

```bash
./scripts/validate-architecture-contracts.sh
./scripts/validate-phase-1-contracts.sh
./scripts/validate-ui-contracts.sh
python3 scripts/lab-pipeline.py init-job --capture-id static-room-orbit-001
python3 scripts/lab-pipeline.py run-stage environment --job outputs/jobs/<job_id>/job.json
```
