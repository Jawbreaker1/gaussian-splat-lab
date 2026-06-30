# Input Intake Roadmap

## Decision

Gaussian Splat Lab will support multiple input lanes side by side.

Plain `mp4`/`mov` video remains a first-class path. Structured reference datasets and RGB-D captures are added to give us reliable quality baselines and richer capture data, not to replace ordinary user video.

## Why

Plain video is the easiest user input, but it is a weak reconstruction source. It usually lacks camera poses, intrinsics, tracking confidence, depth and capture coverage information. That makes COLMAP/SfM work harder and makes floaters, holes and weak plain surfaces more likely.

Reference datasets let us test the trainer and viewer when camera data is already good. RGB-D and ARKit-style bundles let us explore the next product path: smarter capture, depth-aware validation and scene completion before presentation.

## Input Lanes

| Lane | Source shape | Frame sampling | SfM/COLMAP | Training input | Purpose |
| --- | --- | --- | --- | --- | --- |
| Plain video | `mp4` / `mov` | Run FFmpeg keyframe selection | Run COLMAP | COLMAP images + sparse model | Default user path and regression baseline |
| COLMAP dataset | `images/` + `sparse/0` | Skip | Skip | Existing COLMAP model | Use externally solved cameras directly |
| Nerfstudio dataset | `transforms.json` + images, optional depth | Skip | Usually skip | Nerfstudio dataparser data | Reference datasets and camera-known captures |
| RGB-D capture bundle | images + depth + confidence + poses/intrinsics | Convert or validate | Skip when poses exist | Pose-aware Nerfstudio dataparser data first; depth-aware training later | LiDAR/Record3D/ARKit-style capture experiments |

All lanes must converge to the same downstream artifact contract:

- trained or exported Gaussian Splat PLY
- `viewer-manifest.json`
- gallery entry
- reference camera views where available
- render/debug viewer support
- quality report

## Non-Negotiable Regression Rule

The plain-video lane must keep working whenever a new dataset lane is added.

Every intake change should preserve or add validation for:

- a small plain-video smoke run
- a best-quality plain-video run when heavy work is explicitly approved
- at least one structured reference dataset
- gallery loading and export for all produced scene types

## First Reference Targets

Start with datasets that Nerfstudio can already download or read:

- `ns-download-data nerfstudio --capture-name poster` or `kitchen`
- `ns-download-data record3d --capture-name bear`
- existing COLMAP-style reference scenes when available locally

These are reference media for technical validation. Their license and use terms still need to be recorded before any commercial showcase or redistribution.

## Implementation Shape

Introduce an explicit input kind in job/capture manifests:

```json
{
  "input": {
    "kind": "plain_video",
    "path": "data/videos/example.mp4"
  }
}
```

Expected kinds:

- `plain_video`
- `colmap_dataset`
- `nerfstudio_dataset`
- `rgbd_capture_bundle`

Each stage should report whether it ran or was skipped because upstream data already exists. Skips are only valid when the stage can point to validated replacement data.

Examples:

- `frame_sampling`: `skipped_precomputed_images`
- `sfm`: `skipped_precomputed_cameras`
- `splat_training`: records which dataparser/input lane was used

## Current Build Status

Implemented now:

- `plain_video`: unchanged default path through FFmpeg, COLMAP, Splatfacto/gsplat, packaging and viewer.
- `nerfstudio_dataset`: local `transforms.json` datasets now pass intake, frame-manifest creation, SfM skip, Splatfacto training through Nerfstudio's `nerfstudio-data` dataparser, PLY export, viewer packaging and reference camera export.
- `colmap_dataset`: local `images/` plus `sparse/0` datasets now pass intake, frame-manifest creation, SfM skip, Splatfacto training through Nerfstudio's `colmap` dataparser, PLY export, viewer packaging and reference camera export.
- `rgbd_capture_bundle` with `format: record3d`: raw Record3D `rgb/` + `metadata.json` exports now pass intake, are converted with `ns-process-data record3d`, skip COLMAP via Record3D poses/intrinsics, and train through Splatfacto's `nerfstudio-data` parser. Depth files are counted and reported but are not yet consumed by training.
- ARKitScenes raw sequences can be converted with `scripts/convert-arkitscenes-to-nerfstudio.py` into the `nerfstudio_dataset` lane. The converter supports selectable RGB streams such as `lowres_wide` and `vga_wide`, links RGB/depth/confidence frames, writes ARKit camera transforms and keeps Apple license provenance in the manifest.
- The web UI can queue selected manifest sources from the Advanced panel, so local reference datasets and ordinary uploaded videos now use the same render queue.

Not implemented yet:

- Generic ARKit app exports and Polycam bundle handling beyond Record3D/ARKitScenes conversion.
- Depth-aware training, depth-guided cleanup and confidence-map use.

Smoke evidence from 2026-06-29:

- A local three-frame `nerfstudio_dataset` fixture passed the full light pipeline through Splatfacto, export, packaging and viewer validation.
- The local Mip-NeRF 360 `flowers` COLMAP dataset passed the full light pipeline through Splatfacto preview, export, packaging and viewer validation as `mipnerf360-flowers-colmap-reference-20260629T181131Z`.
- The same `flowers` COLMAP dataset passed full `splatfacto_reference` and `splatfacto_big_quality` runs. The best-quality run improved eval metrics to PSNR `20.4715`, SSIM `0.5701`, LPIPS `0.2974`; packaging keeps the `4784784`-splat full export and defaults the browser to a `2000000`-splat interactive PLY.
- TUM RGB-D `freiburg1_xyz` and ARKitScenes `42444511` both passed the known-pose RGB-D lane into gallery on 2026-06-30. TUM is a stable smoke sample; ARKitScenes VGA is the better iPhone/LiDAR-style proof, with `790806` packaged splats in the `splatfacto_reference` run.
- The quality report stayed at `warning` because the fixture is `local-test-only` and framework/license review has warnings, which is expected for a smoke fixture.

## Later Product Direction

Richer inputs should feed later scene-completion work:

- depth-aware scene bounds
- floater and empty-space detection
- missing-surface scanning
- generated surface patches with provenance
- presentation scenes labeled as captured, inferred or AI-completed
