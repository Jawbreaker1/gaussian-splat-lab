# End-User Interface

Verified: 2026-06-21

The first user interface is a local lab console. Its primary path is now a guided scene capture wizard: choose a video, name the scene, select a capture profile and generation strategy, then add the work to the local render queue. The queue worker uploads, plans and runs the pipeline stages in order. Manual capture selection, import and per-stage run controls remain available for debugging.

As of 2026-06-20, the UI can show packaged splat artifacts from both the repo-local gsplat path and Nerfstudio Splatfacto. The central scene is a Spark + Three.js Gaussian Splat viewer loaded from local npm packages, with Walk and Orbit navigation modes, pan, orbit, zoom, reset, reference-camera step controls and export controls for the active PLY plus viewer manifest. Walk mode supports keyboard movement and mouse-look inside the splat scene; double-clicking the canvas can enter pointer-lock look mode in browsers that allow it. Packaging exports camera poses into the same coordinate space as the packaged viewer artifact, so the first render starts from a real training/review camera instead of a generic object-fit view. For Splatfacto, packaging keeps the original PLY as the export/download artifact and can create a viewer-optimized PLY that removes extreme floaters before browser loading. The older PLY WebGL point renderer remains available as `Debug` mode because it is useful for diagnosing malformed exports, sparse geometry and scale problems. The visual quality reference remains the render/target pair and multi-view render-review sheet written by the training stage.

The current visual direction is a dark RTX workstation console: the 3D scene is the primary workspace, the pipeline panel sits on the right as the live operator flow, and lower-priority capture/compliance/artifact metadata is collapsible. On narrow screens the UI switches to a single-column layout with the 3D scene first and compact stacked viewer controls.

The separate `/gallery` page lists previously packaged 3DGS environments with thumbnails, names, artifact size, splat count, quality profile and reference-view counts. Selecting an item loads the same Spark browser renderer with Walk/Orbit navigation. The gallery exposes direct PLY and viewer-manifest downloads. Delete is intentionally conservative: the job output folder is moved from `outputs/jobs` into ignored `outputs/deleted-jobs` so accidental deletes can be recovered locally.

## Scope

The UI owns:

- capture selection from tracked manifests
- local user capture creation from direct video upload
- automatic job planning and queued stage-by-stage generation
- editable queued jobs, including reorder, edit, cancel and remove actions
- active-render feedback through a modal with current stage, elapsed time, ETA and cancel controls
- capture profile selection that changes frame sampling and COLMAP matching defaults
- quality profile selection for the training stage
- generation progress and estimated remaining time
- local video import with the same provenance-aware path/hash report as the CLI
- job planning through the existing pipeline contract
- preflight and media pipeline gate visibility
- commercial/compliance visibility
- local RTX workstation status evidence
- central packaged artifact inspection with Spark + Three.js Gaussian Splat Walk/Orbit navigation, orbit/pan/zoom/reset controls and manifest-provided reference camera views
- gallery inspection of prior packaged 3DGS environments with thumbnail cards, browser navigation, downloads and recoverable local delete
- debug packaged artifact inspection with the older WebGL PLY point renderer
- active environment export through streamed PLY and viewer-manifest downloads
- latest `gsplat` sample render/target images
- latest `gsplat` multi-view render/target/diff review sheet

The UI does not own:

- video decoding
- SfM
- splat training
- artifact conversion
- viewer runtime validation

Those remain separate stages and must keep their own reports.

## Runtime

The current implementation uses:

- Python standard library HTTP server
- browser HTML/CSS/JavaScript APIs
- tracked JSON manifests
- project-local npm packages served from `node_modules/`: `@sparkjsdev/spark 2.1.0`, `three 0.180.0` and transitive `fflate 0.8.3`

No CDN, external UI framework or hosted service is required. The UI server only exposes files from the repository app folder, generated job artifacts and the local `node_modules` paths needed by the import map. Generated artifacts are streamed from disk rather than read entirely into server memory, which keeps larger splat exports practical. The package versions and license posture are recorded in `data/manifests/framework-evaluation.json` and `docs/installation-and-revert-ledger.md`.

## Commands

Start the local UI:

```bash
./scripts/lab-ui-server.py
```

Validate the UI contract:

```bash
./scripts/validate-ui-contracts.sh
```

Default local URL:

```text
http://127.0.0.1:8765
```

Queued video generation:

1. Enter a scene name.
2. Choose a capture profile and generation strategy.
3. Choose a local video file.
4. Confirm that you have rights to process the video.
5. Press `Add to Queue`.

The server creates a local user capture under ignored `data/tmp` manifest state, stores the uploaded video under ignored `data/videos/uploads`, records provenance and places the job in `data/tmp/render-queue.json`. The queue worker runs one job at a time through packaging/viewer validation. While a job is running, the progress panel and rendering modal show the current stage, elapsed time and estimated remaining time. Queued jobs can be reordered, edited or removed before they start; running jobs can be cancelled immediately or after the current stage finishes.

Manual video import:

1. Select the capture manifest entry.
2. Choose a local video file.
3. Accept the capture warning when the source is technical-validation-only.
4. Press `Import video`.

The server writes the video under the ignored manifest target path and records a provenance report next to it. It does not download videos automatically.

## Promotion Rule

A future React/Vite or richer app can replace this UI only after:

- dependency licenses are recorded in `framework-evaluation.json`
- npm dependency tree is scanned and locked
- notices are collected
- the app still creates jobs through the pipeline contract
- generated artifacts stay out of git
