# Stable Pipeline Build Plan

Verified: 2026-06-08

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
- low-load stage gates for splat training, packaging, viewer validation and quality reporting
- placeholder capture and viewer asset manifests
- capture readiness reporting for local file/provenance status before intake

Not yet real:

- a known-good capture video that passes intake, frame sampling and SfM
- actual splat training implementation
- actual packaging/export conversion
- real splat viewer load and screenshot validation

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

Heavy stages are currently guarded because the workstation has a known power-supply/load stability concern. `sfm`, `splat_training` and `viewer` must not run accidentally. The CLI writes `blocked_workload` unless a heavy stage is explicitly run with `--allow-heavy`.

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
- failure boundary is clear if solve fails

### 4. Splat Training

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
