# Agent Instructions

## Current Goal

Build an isolated, commercially plausible local pipeline that turns a video capture into a browser-interactive Gaussian Splat artifact on this Windows RTX 5090 workstation.

The stable golden path came first and now has a local-test-only technical pass through viewer validation. Input-quality experiments may start from that baseline, but arbitrary-user capture preflight and commercial showcase use still require provenance and compliance hardening.

## Primary Host

The primary lab host is the local Windows workstation with an installed RTX 5090. Use WSL2/Linux-first tooling where practical for reconstruction work, while preserving Windows/PowerShell checks for driver, `nvidia-smi` and WSL status.

Mac is optional for documentation or lightweight editing only. It is not the assumed runtime host.

## Isolation

This repository is separate from `blender-ai-poc`.

Do not import, symlink, vendor or copy runtime code from `blender-ai-poc` unless an explicit promotion decision has been made. Documentation may reference the main project, but executable lab code must remain independent.

Do not add Gaussian Splat dependencies to the main project from this repo.

## Commercial Gate

This project may become commercial, so dependency choices must be conservative and traceable.

Before adding a runtime dependency, tool, training framework or viewer framework:

1. Add it to `data/manifests/framework-evaluation.json`.
2. Record official source URL, license, role, decision and commercial-use status.
3. Mark it `preferred`, `accepted`, `conditional`, `deferred` or `blocked`.
4. Document conditions for every conditional dependency.
5. Run `./scripts/validate-architecture-contracts.sh`.

Blocked by default:

- non-commercial or research-only code
- unknown or missing license
- GPL/AGPL runtime dependencies unless explicitly accepted
- hosted services for the core reconstruction path

Current important decisions:

- original GraphDeco/Inria `gaussian-splatting` runtime code is blocked for product use
- OpenSplat is blocked by policy due to AGPL until explicitly accepted or separately licensed
- Nerfstudio/Splatfacto and `gsplat` are accepted candidates, subject to notices and transitive dependency review
- FFmpeg/ffprobe is conditional as a system external tool until redistribution/build flags are reviewed
- NVIDIA CUDA is conditional for local workstation use; do not redistribute CUDA components without EULA review
- input intake will support multiple lanes side by side: plain video remains first-class, while COLMAP datasets, Nerfstudio datasets and RGB-D capture bundles are added as richer reference/capture paths
- direct Nerfstudio `transforms.json` datasets are implemented through Splatfacto's `nerfstudio-data` parser; do not force these references through derived MP4 unless testing the plain-video regression path

## Installation Discipline

Do not install packages, drivers, toolchains or UI dependencies silently. Record every install or upgrade in `docs/installation-and-revert-ledger.md` with exact command, reason, validation and revert plan.

Environment detection stages must report missing tools as `setup_gap` instead of installing them automatically.

## Artifacts

Do not commit heavy or generated artifacts:

- source videos
- extracted frames
- SfM databases
- model checkpoints
- splat files
- generated logs
- generated job folders
- large rendered outputs

Use manifests and small reports to describe local artifacts instead.

Generated output should live under ignored paths such as `outputs/`, `data/videos/`, `data/frames/`, `data/sfm/`, `data/checkpoints/`, `data/splats/` or `logs/`.

## Documentation Map

Use these documents as the source of truth:

- `INSTALL.md`: workstation setup order, required software, validation and rollback
- `docs/mvp-pipeline.md`: end-to-end MVP shape
- `docs/stable-pipeline-build-plan.md`: immediate build sequence for the golden path
- `docs/framework-evaluation.md`: framework and license decisions
- `docs/commercial-compliance.md`: commercial-readiness checklist
- `docs/installation-and-revert-ledger.md`: install/revert ledger and rollback policy
- `docs/pipeline-gates.md`: stage contracts and stop conditions
- `docs/end-user-ui.md`: local UI scope and viewer runtime
- `docs/reference-video-selection.md`: reference capture criteria and current room-scale candidate
- `docs/input-quality-experiments.md`: post-golden-path degradation experiments
- `docs/input-intake-roadmap.md`: decision record for plain video, COLMAP, Nerfstudio and RGB-D input lanes
- `docs/phases.md`: long-range phase plan
- `docs/validation/`: recorded validation evidence

## Workload Safety

The workstation PSU has been replaced and the user has approved heavy validation runs, but heavy stages must still stay deliberate. Do not run SfM, splat training, viewer rendering or long GPU/CPU stress tasks without explicit user approval in that turn.

Pipeline stages that can sustain high CPU/GPU load must expose a guard and report `blocked_workload` unless deliberately launched with the documented heavy-workload flag.

## Development Order

Follow the staged plan. Do not build later stages on unvalidated earlier stages.

Golden-path order:

1. framework/license gate
2. RTX workstation environment gate
3. video intake
4. deterministic frame sampling
5. SfM/camera solve
6. splat training
7. artifact packaging
8. browser viewer validation
9. quality report
10. resumable CLI/UI orchestration
11. input-quality experiments
12. capture preflight

Current technical baseline: `outputs/jobs/mipnerf360-flowers-reference-20260617T142004Z` passes frame sampling, SfM, splat training, packaging and viewer validation. The active viewer artifact is `rtx_ultra_quality` with `1600000` exported gaussians, 89.6 MB PLY size and clean GPU-baseline training pass; the first ultra run remains the best observed render-review MAE at `16.4521`, while the active clean rerun measured `16.8005`. Use `quality_probe` for faster quality checks, `rtx_reference` for stable local RTX 5090 reference runs, `rtx_high_quality` for the likely quality/performance sweet spot (`18000` iterations, `112` images, `1000000` gaussians), `rtx_ultra_quality` for upper-ceiling checks (`24000` iterations, `144` images, `1600000` gaussians), `rtx_ceiling_quality` for controlled 2M-splat ceiling checks (`30000` iterations, `173` images, `2000000` gaussians), and `rtx_max_quality` for heavy lab-only ceiling stress tests (`30000` iterations, `160` images, `2500000` gaussians). Current quality-ceiling results are recorded in `docs/quality-ceiling-results.md`; larger artifacts at 2.0M and 2.5M splats were worse for this scene under current settings. The primary browser viewer is now a local Spark + Three.js Gaussian Splat renderer driven by manifest-provided COLMAP/training reference cameras, with Walk navigation as the default render-mode control path and the older WebGL PLY point-debug scene retained as Debug mode. Packaging includes export metadata, and the UI streams active PLY/manifest downloads for environment handoff. The `gsplat` render/target/diff review sheet is the current visual quality reference. The quality report remains `warning` because the capture/framework state is not product-ready.

Avoid big-bang integration. Every stage must be runnable and inspectable before the next stage depends on it.

## Stage Contract Rule

Every stage must have:

- one explicit input manifest/report
- one explicit output manifest/report
- one validation command or validation function
- status values from `docs/pipeline-gates.md`
- clear stop behavior for `fail`, `setup_gap` and `blocked_license`

A downstream stage may only read upstream output after the upstream report is `pass` or an explicitly accepted `warning`.

## UI Rule

The current UI is a local lab console under `app/`, served by `scripts/lab-ui-server.py`.

The approved local viewer dependency set is pinned in `package.json`/`package-lock.json`: `@sparkjsdev/spark 2.1.0`, `three 0.180.0` and transitive `fflate 0.8.3`. Do not introduce React, Vite, new npm packages, CDNs or external UI frameworks until the framework/commercial gate has been updated and validated.

## Testing

Run relevant checks after changes:

```bash
./scripts/validate-architecture-contracts.sh
./scripts/validate-phase-1-contracts.sh
./scripts/validate-ui-contracts.sh
```

Add focused automated tests for application logic. For shell or environment checks, keep smoke tests small and deterministic.

If logic is hard to test, treat that as a boundary problem and simplify before adding more code.

## Complexity Guardrail

Pause before continuing if:

- the lab starts depending on the main project
- setup scripts become machine-specific without documentation
- generated code or artifacts start accumulating in git
- one stage cannot be validated without building multiple later stages
- CUDA/toolchain failures are hidden behind broad fallback logic
- license/commercial status is unclear but implementation continues anyway
- input-quality experiments start before a stable golden path exists
