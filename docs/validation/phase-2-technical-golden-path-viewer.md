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
.venv/bin/python scripts/lab-pipeline.py run-stage splat_training --job outputs/jobs/static-room-orbit-001-20260614T100535Z/job.json --allow-heavy
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
outputs/jobs/static-room-orbit-001-20260614T100535Z/splats/20260615T193148Z/checkpoint.pt
outputs/jobs/static-room-orbit-001-20260614T100535Z/splats/20260615T193148Z/trained_splats.ply
outputs/jobs/static-room-orbit-001-20260614T100535Z/splats/20260615T193148Z/sample_render.png
outputs/jobs/static-room-orbit-001-20260614T100535Z/viewer/viewer-manifest.json
```

Recorded artifact facts:

- PLY size: `136048` bytes
- PLY SHA256: `0f20e784714cb858e4801d54480f8e20f0859c0486b8631f629e6746406eb3fd`
- PLY format: `binary_little_endian`
- Vertex count: `2423`
- Sample render: `384x216`, RGB, `40668` bytes
- Training smoke: `40` iterations, `8` images, RTX 5090

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

The UI server exposes job artifacts only under `/api/artifacts/...` paths that resolve inside `outputs/jobs`. `/api/state` includes the latest `viewerArtifact`, and the local frontend reads the exported binary PLY into an interactive WebGL point-splat scene. This is a true browser 3D scene for inspection, but still not a production-grade covariance/screen-space Gaussian Splat renderer.

## HTTP Smoke

Temporary server command:

```bash
.venv/bin/python scripts/lab-ui-server.py --host 127.0.0.1 --port 8766
```

Smoke result:

- `GET /api/state`: returned `viewerArtifact` with `viewerStatus=pass`
- `GET /api/artifacts/outputs/jobs/static-room-orbit-001-20260614T100535Z/splats/20260615T193148Z/trained_splats.ply`: returned HTTP `200` and `ply` file prefix
- `GET /`: returned HTML containing `splatCanvas` and `viewerStatusPill`
- `GET /app.js`: returned code containing `initWebGLScene`, `gl_PointSize`, `createSceneLines` and `getContext('webgl')`
