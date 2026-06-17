# End-User Interface

Verified: 2026-06-17

The first user interface is a local, dependency-free lab console. It is intentionally small: it lets a user select a capture, import a local video into the manifest target path, create a planned job, inspect preflight/media pipeline gates and see commercial/compliance status before heavy reconstruction work starts.

As of 2026-06-17, the UI can also show packaged splat artifacts. The central WebGL canvas is a PLY point-debug inspector with pan, orbit, zoom and reset controls; it is not the final production Gaussian Splat renderer. The visual quality reference is the `gsplat` render/target pair and multi-view render-review sheet written by the training stage.

The current visual direction is a dark RTX workstation console: the artifact inspector is the primary workspace, side panels stay secondary, and the palette is restrained graphite/cyan rather than warm placeholder colors. On narrow screens the UI switches to a single-column layout with the artifact inspector first and compact stacked viewer controls.

## Scope

The UI owns:

- capture selection from tracked manifests
- local video import with the same provenance-aware path/hash report as the CLI
- job planning through the existing pipeline contract
- preflight and media pipeline gate visibility
- commercial/compliance visibility
- local RTX workstation status evidence
- central packaged artifact inspection with WebGL PLY point-debug orbit/pan/zoom/reset controls
- latest `gsplat` sample render/target images
- latest `gsplat` multi-view render/target/diff review sheet

The UI does not own:

- video decoding
- SfM
- splat training
- artifact conversion
- production Gaussian Splat rendering; Spark + Three.js is the preferred next viewer spike after dependency install/revert and npm license review are recorded
- viewer runtime validation

Those remain separate stages and must keep their own reports.

## Runtime

The first implementation uses only:

- Python standard library HTTP server
- browser HTML/CSS/JavaScript APIs
- tracked JSON manifests

No npm package, CDN, external UI framework or hosted service is required for this first UI. This keeps the commercial dependency surface small until the framework/compliance gate approves a richer frontend stack.

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

Local video import:

1. Select the capture manifest entry.
2. Choose a local video file.
3. Accept the capture warning when the source is technical-validation-only.
4. Press `Import video`.

The server writes the video under the ignored manifest target path and records a provenance report next to it. It does not download videos automatically.

## Promotion Rule

A future React/Vite or richer app can replace this UI only after:

- dependency licenses are recorded in `framework-evaluation.json`
- npm dependency tree is scanned
- notices are collected
- the app still creates jobs through the pipeline contract
- generated artifacts stay out of git
