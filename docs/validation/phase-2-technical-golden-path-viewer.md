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
.venv/bin/python scripts/lab-pipeline.py run-stage splat_training --job outputs/jobs/static-room-orbit-001-20260614T100535Z/job.json --allow-heavy --training-profile quality_probe
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
outputs/jobs/static-room-orbit-001-20260614T100535Z/splats/20260616T181446Z/checkpoint.pt
outputs/jobs/static-room-orbit-001-20260614T100535Z/splats/20260616T181446Z/trained_splats.ply
outputs/jobs/static-room-orbit-001-20260614T100535Z/splats/20260616T181446Z/sample_render.png
outputs/jobs/static-room-orbit-001-20260614T100535Z/splats/20260616T181446Z/sample_target.png
outputs/jobs/static-room-orbit-001-20260614T100535Z/splats/20260616T181446Z/render_review/contact_sheet.png
outputs/jobs/static-room-orbit-001-20260614T100535Z/viewer/viewer-manifest.json
```

Recorded artifact facts:

- PLY size: `5562729` bytes
- PLY SHA256: `4f40ff095712290e6c816c37b1f64bd2428b35112ffb71ad61dffffebbde8999`
- PLY format: `binary_little_endian`
- Vertex count: `99328`
- Sample render: `768x432`, RGB, `242117` bytes
- Sample target: `768x432`, RGB, `251780` bytes
- Render review contact sheet: `1008x1332`, RGB, `1556578` bytes
- Training profile: `quality_probe`
- Training run: `2500` iterations, `42` images, RTX 5090
- Densification: `gsplat DefaultStrategy`, `2423` initial gaussians to `99328` exported gaussians, `40.9938x` growth
- Loss: `0.28157898783683777` initial to `0.06988848000764847` final
- Render review: `pass`, mean MAE `16.3499`, mean RMSE `26.1794`, mean luminance delta `5.4782`

Visual inspection of the render-review contact sheet shows that `quality_probe` captures the main geometry and view alignment much better than the earlier baseline. It is still visibly soft and loses sharp reflections/fine detail, with camera index `0` remaining the weakest reviewed view. Treat this as the current technical reference, not final end-user visual quality.

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

- `GET /api/state`: returned `viewerArtifact` with `viewerStatus=pass`, `trainingProfile=quality_probe`, `strategy=default`, `vertexCount=99328`, `renderReview.status=pass` and `renderReview.meanMae=16.3499`
- `GET /api/artifacts/outputs/jobs/static-room-orbit-001-20260614T100535Z/splats/20260616T181446Z/trained_splats.ply`: returned HTTP `200` and `ply` file prefix
- `GET /api/artifacts/outputs/jobs/static-room-orbit-001-20260614T100535Z/splats/20260616T181446Z/render_review/contact_sheet.png`: returned HTTP `200` and PNG file prefix
- `GET /`: returned HTML containing `Artifact Inspect`, `splatCanvas`, `sampleRenderImage`, `sampleTargetImage` and `renderReviewImage`
- `GET /app.js`: returned code containing `initWebGLScene`, `gl_PointSize`, `createSceneLines`, `getContext('webgl')` and `renderSampleComparison`
