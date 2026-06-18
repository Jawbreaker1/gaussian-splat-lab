# Gaussian Splat Lab

Local video-to-Gaussian-Splat reconstruction lab for an RTX workstation.

Gaussian Splat Lab exists to answer one practical question: can we take ordinary video or structured capture data, run the full reconstruction pipeline locally on a Windows/WSL2 RTX 5090 workstation, and produce an interactive 3D Gaussian Splat environment that can be inspected, exported and eventually embedded in a product experience?

The project is intentionally built as an inspectable lab, not a black-box demo. Every stage writes a report, validates its own boundary, and must be accepted before later stages depend on it. That matters because Gaussian Splat quality is highly sensitive to capture quality, camera solve quality, training profile, licensing posture and viewer correctness.

## Current Status

Status: Phase 1 local pipeline with working browser viewer.

Current reference job:

`outputs/jobs/mipnerf360-flowers-reference-20260617T142004Z`

Current active viewer artifact:

- profile: `rtx_ultra_quality`
- splats: `1,600,000`
- PLY size: `89.6 MB`
- renderer: Spark + Three.js Gaussian Splat viewer
- navigation: Walk, Orbit, mouse-look, wheel zoom, reference cameras and debug point-cloud mode
- export: streamed PLY and viewer-manifest download

The quality report can still be `warning` because the current public reference capture and some commercial-use evidence are not product-ready. That warning is expected; training, packaging and viewer validation pass for the active technical reference.

## GUI Screenshots

Debug point-cloud inspection view:

![Gaussian Splat Lab debug point-cloud GUI](docs/assets/screenshots/gui-debug-pointcloud.png)

Rendered 3DGS view from the active `rtx_ultra_quality` splat:

![Gaussian Splat Lab 3DGS render GUI](docs/assets/screenshots/gui-desktop-ultra.png)

The two views are intentionally shown together: Debug mode exposes the sampled point cloud for inspection, while Render mode shows the interactive Gaussian Splat scene that users navigate.

## Why This Project Exists

The long-term product need is a reliable path from capture media to an interactive 3D environment. In practice that means:

- video-first input, because video is the most likely user capture format
- support for structured datasets, because good reference data is needed for quality ceilings
- local GPU execution, because reconstruction is heavy and we want to test RTX workstation limits
- commercial-aware dependency choices, because the output may later be used in a commercial setting
- a simple end-user interface, because the pipeline should eventually be operated by non-engineers
- exportable scene artifacts, because generated environments need to be embedded, handed off or archived
- an agent-invokable worker boundary, because Swoqer-style integrations may need to wake an AI agent that runs the pipeline through `swoqerd` and returns 3DGS artifacts

The repo is separate from other product code so reconstruction decisions, generated artifacts, licensing checks and heavy GPU experiments stay isolated.

## What It Does

Gaussian Splat Lab can currently:

- track known captures in manifests
- import local videos into controlled capture paths
- extract frames with FFmpeg
- solve camera poses with COLMAP SfM
- train Gaussian Splats locally with PyTorch/CUDA and `gsplat`
- run multiple quality profiles from quick probes to heavy RTX ceiling tests
- package a binary PLY splat plus viewer manifest
- render the result in a browser with a real Gaussian Splat renderer
- switch between production render mode and debug point-cloud mode
- validate viewer navigation controls with headless Chrome
- export the active PLY and manifest from the UI

Large generated files remain outside git. The repo commits scripts, manifests, docs, configuration and screenshots; videos, extracted frames, SfM databases, checkpoints, splats and generated reports stay local.

## Pipeline

The golden path is deliberately stage-gated:

| Order | Stage | Responsibility | Output | Self-validation |
| ---: | --- | --- | --- | --- |
| 1 | Framework and license review | Decide which tools are allowed and which are blocked for commercial use. | `framework_license.json` | Flags blocked, conditional and review-required dependencies. |
| 2 | Workstation check | Verify the local RTX workstation, CUDA/PyTorch visibility, COLMAP, FFmpeg and GPU baseline. | `environment.json` | Confirms RTX 5090 visibility and warns if GPU is already busy. |
| 3 | Video intake | Confirm the selected source exists and has acceptable capture/commercial posture for the current purpose. | `intake.json` | Blocks missing files and records source/license warnings. |
| 4 | Frame sampling | Extract frames deterministically from video. | `frames/`, frame manifest, contact sheet | Verifies frame count, hashes and extraction metadata. |
| 5 | SfM camera solve | Run COLMAP feature extraction, matching and mapping. | sparse COLMAP model | Verifies registered images, sparse points and model analyzer output. |
| 6 | Splat training | Train Gaussian Splats with `gsplat` on the RTX GPU. | checkpoint, PLY, sample render, render-review sheet | Verifies CUDA, training completion, exported PLY and render/target review metrics. |
| 7 | Packaging | Build the browser viewer manifest around the active splat artifact. | `viewer-manifest.json` | Verifies PLY hash, size, header and reference camera views. |
| 8 | Viewer validation | Confirm the local browser viewer can load the packaged artifact. | `viewer.json` | Verifies manifest, artifact hash, camera views and viewer hooks. |
| 9 | Quality report | Summarize the whole pipeline boundary. | `quality_report.json` | Classifies the run as usable, weak, incomplete, blocked or failed. |

Each stage can be run independently, and later stages refuse to proceed unless upstream failures are resolved or warnings are explicitly accepted.

## Quality Profiles

The current trainer uses `gsplat` with explicit profiles:

- `smoke`: very fast sanity check
- `baseline`: first densifying profile
- `quality_probe`: faster quality inspection
- `rtx_reference`: stable RTX reference run
- `rtx_high_quality`: balanced 1.0M-splat profile
- `rtx_ultra_quality`: current best active 1.6M-splat profile
- `rtx_ceiling_quality`: controlled 2.0M-splat ceiling test
- `rtx_max_quality`: heavy stress profile for lab-only ceiling exploration

Current quality-ceiling results are tracked in [docs/quality-ceiling-results.md](docs/quality-ceiling-results.md). For the Mip-NeRF 360 flowers reference scene, the current practical ceiling is around 1.6M splats. Larger 2.0M and 2.5M artifacts were worse under the current training settings, so bigger files are not automatically better.

## Browser UI

Start the local UI:

```bash
python3 scripts/lab-ui-server.py --host 127.0.0.1 --port 8765
```

Then open:

```text
http://127.0.0.1:8765/
```

The UI is a local lab console with:

- source/capture selection
- local video import controls
- live pipeline panel on the right
- central 3D scene view
- `Render` mode for Spark Gaussian Splat rendering
- `Debug` mode for point-cloud inspection
- `Walk` and `Orbit` navigation
- reference camera stepping
- collapsible lower-priority metadata
- active PLY and viewer-manifest export buttons

Viewer controls are validated by:

```powershell
.\scripts\validate-viewer-controls.ps1 -Url "http://127.0.0.1:8765/"
```

## Export Model

The primary export today is a viewer environment bundle:

- binary little-endian Gaussian Splat PLY
- viewer manifest
- reference camera views
- preview and render-review images

This is not a triangle mesh or GLB export yet. The current goal is high-quality Gaussian Splat viewing and handoff. Mesh conversion or GLB packaging can be added later as a separate export stage if product needs require it.

## Commercial and Licensing Posture

This repo is commercial-aware but not a legal opinion. The pipeline records license posture for frameworks and captures so we can avoid accidentally building on non-commercial-only code or unclear source material.

Current rules:

- do not use the original GraphDeco/Inria Gaussian Splatting implementation for commercial product work without explicit permission
- prefer permissive components such as `gsplat`, PyTorch, Three.js and Spark where their licenses and notices can be managed
- use FFmpeg and COLMAP as local/system tools until redistribution details are reviewed
- treat benchmark datasets and stock videos as technical validation inputs unless commercial-use evidence is attached
- prefer self-captured or explicitly cleared media for product demos

Relevant docs:

- [docs/framework-evaluation.md](docs/framework-evaluation.md)
- [docs/commercial-compliance.md](docs/commercial-compliance.md)
- [docs/installation-and-revert-ledger.md](docs/installation-and-revert-ledger.md)

## Swoqer Integration Possibility

The pipeline is intentionally separated from any product backend so it can later run as a capability behind [swoqer.com](https://swoqer.com/).

Swoqer is expected to act as an identity-based integration platform for distributed agentic applications. In that model, Gaussian Splat Lab is not the user-facing integration layer. It is the local or remote reconstruction worker that can be invoked by an authenticated agent workflow.

Possible flow:

1. An external service or user identity sends large dataset/video payloads through Swoqer.
2. Swoqer authorizes, routes and tracks that integration event.
3. Swoqer wakes or addresses an AI agent with the dataset/video context.
4. The agent talks to `swoqerd` on a capable workstation or worker node.
5. `swoqerd` starts a Gaussian Splat Lab job with the supplied video/dataset.
6. Gaussian Splat Lab runs intake, frame sampling, SfM, splat training, packaging and viewer validation.
7. The generated 3DGS artifacts are returned: PLY splat, viewer manifest, diagnostics and quality reports.
8. The calling service can use those artifacts as an interactive 3D environment or hand them to another agent/application.

In this architecture, Swoqer provides identity, integration routing, large-file handoff and distributed agent activation. Gaussian Splat Lab provides the reconstruction capability and the self-validating pipeline boundary.

That integration is not implemented in this repo yet. The current work is to make the local pipeline robust enough that `swoqerd` or a similar agent runtime can invoke it predictably and return auditable 3DGS results.

## Key Commands

Architecture and phase validation:

```bash
./scripts/validate-architecture-contracts.sh
./scripts/validate-phase-1-contracts.sh
./scripts/validate-ui-contracts.sh
npm run check:js
```

List captures:

```bash
.venv/bin/python scripts/lab-pipeline.py list-captures --capture-manifest data/manifests/captures.example.json
```

Import a local video:

```bash
.venv/bin/python scripts/lab-pipeline.py import-video \
  --capture-id <capture-id> \
  --input <local-video> \
  --accept-warning \
  --overwrite
```

Run a pipeline stage:

```bash
.venv/bin/python scripts/lab-pipeline.py run-stage <stage-id> \
  --job outputs/jobs/<job-id>/job.json \
  --accept-warning
```

Run heavy splat training intentionally:

```bash
.venv/bin/python scripts/lab-pipeline.py run-stage splat_training \
  --job outputs/jobs/<job-id>/job.json \
  --accept-warning \
  --allow-heavy \
  --training-profile rtx_ultra_quality
```

## Machine Topology

Primary lab machine:

- Windows workstation
- WSL2/Linux-first reconstruction runtime where practical
- NVIDIA RTX 5090
- CUDA/PyTorch/gsplat training
- local COLMAP and FFmpeg
- local browser viewer

Mac:

- optional documentation or lightweight editing machine
- not the assumed reconstruction runtime
- no CUDA/NVIDIA assumption

## Documentation Map

- [docs/mvp-pipeline.md](docs/mvp-pipeline.md): MVP pipeline contract
- [docs/stable-pipeline-build-plan.md](docs/stable-pipeline-build-plan.md): golden-path implementation plan
- [docs/pipeline-gates.md](docs/pipeline-gates.md): validation gates
- [docs/end-user-ui.md](docs/end-user-ui.md): UI behavior and responsibilities
- [docs/quality-ceiling-results.md](docs/quality-ceiling-results.md): current quality-ceiling measurements
- [docs/rtx-workstation-setup.md](docs/rtx-workstation-setup.md): workstation setup notes
- [docs/psu-replacement-test-runbook.md](docs/psu-replacement-test-runbook.md): heavy-test runbook
- [AGENTS.md](AGENTS.md): working instructions for coding agents in this repo
