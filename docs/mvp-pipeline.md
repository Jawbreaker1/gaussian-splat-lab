# MVP Pipeline

Goal: turn a local video capture into a browser-viewable Gaussian Splat artifact that a user can orbit, pan, zoom and reset.

This lab should first prove one known-good input end to end. The app can stay simple as long as every boundary is explicit and inspectable.

Dependency review and workstation checks are preflight gates. They protect commercial and runtime assumptions, but the media pipeline itself begins at video intake.

## User Flow

1. User selects or imports a local video capture.
2. The app creates a lab job with a stable job manifest.
3. The pipeline extracts metadata and samples frames.
4. SfM estimates cameras and produces a solve report.
5. A splat trainer produces a raw artifact and logs.
6. Packaging creates a browser-loadable splat asset.
7. The viewer opens the artifact through a small `ViewerAsset` manifest.

## Stage Boundaries

Each stage reads one manifest and writes a new manifest or report.

| Stage | Input | Output | Notes |
| --- | --- | --- | --- |
| Intake | `CaptureInput` | `CaptureMetadata` | Validate path, format, duration and provenance. |
| Frame sampling | `CaptureMetadata` | `FrameManifest` | Deterministic sampling settings; generated frames stay out of git. |
| SfM | `FrameManifest` | `CameraSolveReport` | COLMAP or equivalent runs behind this boundary. |
| Splat training | `CameraSolveReport` | `TrainingRunReport` | CUDA/PyTorch/gsplat stack runs only on the RTX workstation. |
| Packaging | `TrainingRunReport` | `SplatArtifact` | Convert/copy to a browser delivery format. |
| Viewer | `SplatArtifact` | `ViewerAsset` | Minimal browser contract for interaction. |

## Minimal App Shape

The first usable app should have three surfaces:

- import/status: create a job from a local video manifest and show stage state
- report: show stage outputs, errors and quality status
- viewer: open a packaged splat with orbit, pan, zoom and reset

The first checked-in interface is documented in [end-user-ui.md](end-user-ui.md) and intentionally uses no external frontend dependencies.

The app should not hide pipeline failures. If a stage fails, the job folder should preserve enough evidence to rerun or diagnose that stage without restarting from video import.

## MVP Definition

MVP is complete when:

- one known-good local video produces a packaged splat
- the packaged splat opens in an isolated browser viewer
- the viewer can orbit, pan, zoom and reset
- the job folder contains all intermediate manifests and reports
- generated videos, frames, SfM databases, checkpoints, splats and logs remain ignored by git

## Deferred Until After MVP

- input quality experiments for controlled video degradation, documented in [input-quality-experiments.md](input-quality-experiments.md)
- capture-quality preflight for arbitrary user videos
- product integration with `blender-ai-poc`
- cloud reconstruction services
- multi-user job orchestration
- polished capture UI
