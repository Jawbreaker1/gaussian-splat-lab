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

- `docs/mvp-pipeline.md`: end-to-end MVP shape
- `docs/stable-pipeline-build-plan.md`: immediate build sequence for the golden path
- `docs/framework-evaluation.md`: framework and license decisions
- `docs/commercial-compliance.md`: commercial-readiness checklist
- `docs/installation-and-revert-ledger.md`: install/revert ledger and rollback policy
- `docs/pipeline-gates.md`: stage contracts and stop conditions
- `docs/end-user-ui.md`: dependency-free local UI scope
- `docs/input-quality-experiments.md`: post-golden-path degradation experiments
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

Current technical baseline: `outputs/jobs/static-room-orbit-001-20260614T100535Z` passes environment, frame sampling, SfM, `quality_probe` splat training, packaging and viewer validation. The latest `quality_probe` run uses `gsplat` DefaultStrategy densification and grows the local-test-only capture from `2423` sparse points to `99328` exported gaussians, with render-review mean MAE `16.3499`. The viewer canvas is a dependency-free WebGL PLY point-debug scene, not a production covariance/screen-space Gaussian Splat renderer. The `gsplat` render/target/diff review sheet is the current visual quality reference. The quality report remains `warning` because the capture/framework state is not product-ready.

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

The current UI is a dependency-free local lab console under `app/`, served by `scripts/lab-ui-server.py`.

Do not introduce React, Vite, npm dependencies, CDNs or external UI frameworks until the framework/commercial gate has been updated and validated.

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
