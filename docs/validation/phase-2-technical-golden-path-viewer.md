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
.venv/bin/python scripts/lab-pipeline.py run-stage splat_training --job outputs/jobs/static-room-orbit-001-20260614T100535Z/job.json --allow-heavy --training-profile baseline
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
outputs/jobs/static-room-orbit-001-20260614T100535Z/splats/20260616T075257Z/checkpoint.pt
outputs/jobs/static-room-orbit-001-20260614T100535Z/splats/20260616T075257Z/trained_splats.ply
outputs/jobs/static-room-orbit-001-20260614T100535Z/splats/20260616T075257Z/sample_render.png
outputs/jobs/static-room-orbit-001-20260614T100535Z/viewer/viewer-manifest.json
```

Recorded artifact facts:

- PLY size: `1511521` bytes
- PLY SHA256: `9eacfc819fc2d9f57ee5113568ce4b31b5ab455d74bc306da2e53466165aba3d`
- PLY format: `binary_little_endian`
- Vertex count: `26985`
- Sample render: `640x360`, RGB, `101067` bytes
- Training profile: `baseline`
- Training run: `800` iterations, `32` images, RTX 5090
- Densification: `gsplat DefaultStrategy`, `2423` initial gaussians to `26985` exported gaussians, `11.137x` growth
- Loss: `0.20976853370666504` initial to `0.17991331219673157` final

## Viewer Handoff

Packaging writes `viewer/viewer-manifest.json` with artifact hash, byte size, PLY header metadata, sample render path and training/device metadata.

Viewer validation now checks:

- viewer manifest exists and is readable
- artifact exists
- artifact hash matches the manifest
- binary PLY header is readable and includes `x`, `y`, `z`
- sample render exists
- local UI contains WebGL binary PLY viewer hooks

Viewer implementation recorded in the manifest:

```text
local_webgl_binary_ply_point_splats
```

The UI server exposes job artifacts only under `/api/artifacts/...` paths that resolve inside `outputs/jobs`. `/api/state` includes the latest `viewerArtifact`, training profile, densification strategy and gaussian growth metadata. The local frontend reads the exported binary PLY into an interactive WebGL point-splat inspection scene. This is a true browser 3D scene for inspection, but still not a production-grade covariance/screen-space Gaussian Splat renderer.

## HTTP Smoke

Temporary server command:

```bash
.venv/bin/python scripts/lab-ui-server.py --host 127.0.0.1 --port 8766
```

Smoke result:

- `GET /api/state`: returned `viewerArtifact` with `viewerStatus=pass`, `trainingProfile=baseline`, `strategy=default`, `vertexCount=26985`
- `GET /api/artifacts/outputs/jobs/static-room-orbit-001-20260614T100535Z/splats/20260616T075257Z/trained_splats.ply`: returned HTTP `200` and `ply` file prefix
- `GET /`: returned HTML containing `Splat Inspect` and `splatCanvas`
- `GET /app.js`: returned code containing `initWebGLScene`, `gl_PointSize`, `createSceneLines` and `getContext('webgl')`
