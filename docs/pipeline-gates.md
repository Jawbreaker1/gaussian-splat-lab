# Pipeline Gates

Verified: 2026-06-15

The media pipeline must be stage-based and self-validating. Preflight gates use the same report/status mechanics, but they are project and workstation readiness checks rather than media-processing stages. A downstream stage may only read an upstream output after that output has a passing validation report.

## Core Rule

Each stage has:

- one explicit input contract
- one explicit output contract
- one local validation command or validation function
- one report file with pass/fail/setup_gap status
- clear stop conditions

Generated artifacts stay out of git. Only manifests, small reports, docs and reproducible configuration belong in git.

## Preflight Gates

These checks run before or alongside a job, but they are not part of the media-processing pipeline.

| Order | Gate | Input Contract | Output Contract | Validation Before Media Pipeline |
| --- | --- | --- | --- | --- |
| 0 | Dependency review | `FrameworkEvaluation` | `FrameworkDecisionReport` | All runtime dependencies are accepted or conditional with documented conditions; blocked dependencies are absent. |
| 1 | Workstation check | machine runtime | `EnvironmentReport` | Required tools visible; versions recorded; RTX workstation has `nvidia-smi`, Python, CUDA-compatible PyTorch and gsplat smoke when training starts. |

## Media Pipeline Gates

This is the actual video-to-splat chain.

| Order | Stage | Input Contract | Output Contract | Validation Before Next Stage |
| --- | --- | --- | --- | --- |
| 1 | Capture intake | `CaptureInput` | `CaptureMetadata` | Video exists locally, provenance/license recorded, `ffprobe` metadata parsed, duration/resolution/frame rate within configured limits. |
| 2 | Frame sampling | `CaptureMetadata` | `FrameManifest` | Frame count matches plan, timestamps are monotonic, files exist, hashes recorded, contact sheet generated. |
| 3 | SfM/camera solve | `FrameManifest` | `CameraSolveReport` | COLMAP exits cleanly, sparse model exists, enough frames are registered, sparse point count and reprojection error are recorded. |
| 4 | Splat training | `CameraSolveReport` | `TrainingRunReport` | Training completes or checkpoints cleanly, nonzero splats exported, loss trend and sample renders recorded. |
| 5 | Packaging | `TrainingRunReport` | `SplatArtifact` | Artifact file exists, format is declared, byte size/hash recorded, viewer loader can parse it. |
| 6 | Viewer | `SplatArtifact` | `ViewerValidationReport` | Browser opens, canvas is nonblank, orbit/pan/zoom/reset work, screenshot evidence saved. |
| 7 | Quality report | all stage reports | `CaptureQualityReport` | Result classified as `usable`, `weak` or `failed` with failure boundary identified. |

## Validation Status Values

- `pass`: next stage may proceed.
- `warning`: next stage may proceed only when explicitly accepted and recorded in the job report.
- `setup_gap`: stop for environment/setup work; not a capture or algorithm failure.
- `fail`: stop; downstream stages must not run.
- `blocked_license`: stop; dependency or input license is incompatible or unknown.
- `blocked_workload`: stop; the stage may place sustained load on CPU/GPU and needs explicit operator approval.

## Job Folder Layout

A job folder under `outputs/jobs/<job_id>/` should use this shape:

```text
job.json
reports/
  framework_license.json
  environment.json
  intake.json
  frame_sampling.json
  sfm.json
  splat_training.json
  packaging.json
  viewer.json
  quality_report.json
frames/
  <run_timestamp>/
    frame_manifest.json
    frame_000001.jpg
    contact_sheet.jpg
sfm/
checkpoints/
splats/
viewer/
```

The folder is generated output and must remain ignored by git.

## Iteration Loop

Every stage follows the same loop:

1. Read only validated upstream manifests.
2. Run the smallest deterministic operation for this stage.
3. Write output manifest/report atomically.
4. Validate output locally.
5. Stop immediately on `fail`, `setup_gap`, `blocked_license` or `blocked_workload`.
6. Allow the next stage only on `pass` or explicit `warning`.

## MVP Gate Thresholds

Initial thresholds are intentionally conservative and can be tuned after known-good captures exist.

| Stage | Initial Threshold |
| --- | --- |
| Capture intake | local file exists; duration 10-120 seconds; resolution at least 720p; license/provenance non-empty |
| Frame sampling | 50-250 frames; no missing files; contact sheet generated |
| SfM | pass at 70% registered frames; warning at 50-70%; sparse points and reprojection error recorded |
| Training | gsplat CUDA extension available; exported splat exists; final report includes iterations, wall time and loss samples |
| Packaging | artifact hash and byte size recorded; selected viewer supports the format |
| Viewer | nonblank screenshot; camera reset returns to initial pose |

## Current Workload Guard

SfM, training and viewer validation remain guarded heavy stages. Training now has a minimal gsplat orchestration behind `--allow-heavy`; on the RTX workstation it produces a checkpoint, binary PLY and sample render. Packaging writes a viewer manifest with hash, byte size and PLY header metadata. Viewer validation reads that manifest, verifies the artifact hash/header and checks that the local UI contains the binary PLY viewer hooks.

## Responsibility Boundaries

- Intake never trains or samples frames.
- Frame sampling never runs SfM.
- SfM never trains splats.
- Training never decides browser packaging format.
- Packaging never performs quality classification.
- Viewer validation never mutates reconstruction artifacts.

This keeps each stage replaceable: COLMAP can be swapped, training can move from Nerfstudio to custom gsplat, and viewer format can change without rewriting video intake.
