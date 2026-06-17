# Phase 2 Technical Golden Path Viewer Validation

Verified: 2026-06-16

Goal: prove that the local RTX workstation can run the lab pipeline from existing video-derived SfM output through gsplat training, artifact packaging and a browser-consumable viewer handoff.

## Input

- Job: `outputs/jobs/static-room-orbit-001-20260614T100535Z/job.json`
- Capture posture: `local-test-only`; not commercial showcase evidence
- Upstream SfM report: `outputs/jobs/static-room-orbit-001-20260614T100535Z/reports/sfm.json`
- Sparse points: `2423`
- Registered frames: `42/60`

## Commands

```bash
.venv/bin/python scripts/lab-pipeline.py run-stage splat_training --job outputs/jobs/static-room-orbit-001-20260614T100535Z/job.json --allow-heavy --training-profile rtx_reference
.venv/bin/python scripts/lab-pipeline.py run-stage packaging --job outputs/jobs/static-room-orbit-001-20260614T100535Z/job.json
.venv/bin/python scripts/lab-pipeline.py run-stage viewer --job outputs/jobs/static-room-orbit-001-20260614T100535Z/job.json --allow-heavy
.venv/bin/python scripts/lab-pipeline.py run-stage quality_report --job outputs/jobs/static-room-orbit-001-20260614T100535Z/job.json
```

## Result

- `splat_training`: `pass`
- `packaging`: `pass`
- `viewer`: `pass`
- `quality_report`: `warning`

The warning is expected for the current fixture because framework/commercial review and capture provenance are not product-ready. It is not a CUDA, gsplat, packaging or viewer setup gap.

## Produced Local Artifacts

```text
outputs/jobs/static-room-orbit-001-20260614T100535Z/splats/20260617T005232Z/checkpoint.pt
outputs/jobs/static-room-orbit-001-20260614T100535Z/splats/20260617T005232Z/trained_splats.ply
outputs/jobs/static-room-orbit-001-20260614T100535Z/splats/20260617T005232Z/sample_render.png
outputs/jobs/static-room-orbit-001-20260614T100535Z/splats/20260617T005232Z/sample_target.png
outputs/jobs/static-room-orbit-001-20260614T100535Z/splats/20260617T005232Z/render_review/contact_sheet.png
outputs/jobs/static-room-orbit-001-20260614T100535Z/viewer/viewer-manifest.json
```

Recorded artifact facts:

- PLY size: `22400362` bytes
- PLY SHA256: `ab87ed8ee07bbc6fd6ba30d5d75aa3f2163c7f5ca95ae0d7ced3ab768ffa0707`
- PLY format: `binary_little_endian`
- Vertex count: `400000`
- Sample render: `1280x720`, RGB, `425739` bytes
- Sample target: `1280x720`, RGB, `515412` bytes
- Render review contact sheet: `1008x2212`, RGB, `2494515` bytes
- Training profile: `rtx_reference`
- Training run: `9000` iterations, `42` images, RTX 5090
- Densification: `gsplat DefaultStrategy`, `2423` initial gaussians to `400000` exported gaussians, `165.0846x` growth
- Loss: `0.28722822666168213` initial to `0.07884305715560913` final
- Render review: `pass`, mean MAE `13.0491`, mean RMSE `22.7755`, mean luminance delta `-1.0692`
- Peak PyTorch CUDA allocation: `1557.59 MiB`

Visual inspection of the render-review contact sheet shows that `rtx_reference` is the strongest current technical reference. It uses full capture-frame render resolution and greatly improves the earlier `quality_probe` metrics (`16.3499` mean MAE to `13.0491`). The main camera alignment and object structure are consistent across reviewed views, but foreground occluders are still soft and reflective/high-frequency detail is not product-showcase quality. Two rejected experiment profiles were tested locally: an overly sharp variant collapsed late views, and a balanced variant was stable but softer than `rtx_reference`.

## Viewer Handoff

Packaging writes `viewer/viewer-manifest.json` with artifact hash, byte size, PLY header metadata, sample render path, target path, render-review contact sheet and training/device metadata.

Viewer validation now checks:

- viewer manifest exists and is readable
- artifact exists
- artifact hash matches the manifest
- binary PLY header is readable and includes `x`, `y`, `z`
- sample render exists
- render-review contact sheet exists
- local UI contains WebGL binary PLY viewer hooks
- local UI exposes latest `gsplat` sample render, target image and multi-view render-review sheet for visual comparison

Viewer implementation recorded in the manifest:

```text
local_webgl_binary_ply_point_splats
```

The UI server exposes job artifacts only under `/api/artifacts/...` paths that resolve inside `outputs/jobs`. `/api/state` includes the latest `viewerArtifact`, training profile, densification strategy, gaussian growth metadata, sample render/target URLs and render-review URL. The local frontend reads the exported binary PLY into an interactive WebGL point-debug scene and shows the latest `gsplat` render beside its training target plus a multi-view render/target/diff sheet. The point-debug scene is useful for artifact/orbit inspection, while the render review is the current visual quality reference. This is still not a production-grade covariance/screen-space Gaussian Splat browser renderer.

## HTTP Smoke

Temporary server command:

```bash
.venv/bin/python scripts/lab-ui-server.py --host 127.0.0.1 --port 8766
```

Smoke result:

- `GET /api/state`: returned `viewerArtifact` with `viewerStatus=pass`, `trainingProfile=rtx_reference`, `strategy=default`, `vertexCount=400000`, `renderReview.status=pass` and `renderReview.meanMae=13.0491`
- `GET /api/artifacts/outputs/jobs/static-room-orbit-001-20260614T100535Z/splats/20260617T005232Z/trained_splats.ply`: returned HTTP `200` and `ply` file prefix
- `GET /api/artifacts/outputs/jobs/static-room-orbit-001-20260614T100535Z/splats/20260617T005232Z/render_review/contact_sheet.png`: returned HTTP `200` and PNG file prefix
- `GET /`: returned HTML containing `Artifact Inspect`, `splatCanvas`, `sampleRenderImage`, `sampleTargetImage` and `renderReviewImage`
- `GET /app.js`: returned code containing `initWebGLScene`, `gl_PointSize`, `createSceneLines`, `getContext('webgl')` and `renderSampleComparison`
