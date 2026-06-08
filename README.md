# Gaussian Splat Lab

Status: Phase 1 gated local pipeline scaffold

This repository is an isolated lab for local video-to-Gaussian-Splat reconstruction.

It is intentionally separate from `blender-ai-poc`. The first goal is to evaluate whether a local, commercially compatible, RTX 5090-based pipeline can produce browser-viewable Gaussian Splat artifacts from known-good static video inputs.

## MVP Goal

Build a simple local application that can take a video capture through an inspectable pipeline and produce a Gaussian Splat artifact that users can interact with in a browser.

The first app shape is intentionally small:

- create a lab job from a local video capture manifest
- run or resume clear pipeline stages
- preserve stage reports and generated artifacts outside git
- open the packaged result through a narrow viewer asset manifest

The MVP pipeline contract is documented in [docs/mvp-pipeline.md](docs/mvp-pipeline.md).
The immediate golden-path build sequence is documented in [docs/stable-pipeline-build-plan.md](docs/stable-pipeline-build-plan.md).
Framework/license decisions are tracked in [docs/framework-evaluation.md](docs/framework-evaluation.md). Stage-by-stage validation gates are tracked in [docs/pipeline-gates.md](docs/pipeline-gates.md).
Commercial-readiness rules are tracked in [docs/commercial-compliance.md](docs/commercial-compliance.md).
Installation and rollback notes are tracked in [docs/installation-and-revert-ledger.md](docs/installation-and-revert-ledger.md).
RTX workstation setup notes are tracked in [docs/rtx-workstation-setup.md](docs/rtx-workstation-setup.md).
The first post-PSU heavy test sequence is tracked in [docs/psu-replacement-test-runbook.md](docs/psu-replacement-test-runbook.md).

## Boundaries

This repo owns:

- lab manifests and known-good input tracking
- local environment smoke checks
- video intake, frame sampling, SfM, splat training and packaging experiments
- isolated browser viewer experiments
- lab reports and quality reports

This repo must not depend on:

- `blender-ai-poc` backend, frontend or render proxy
- `SceneSpec`, component validation, Blender scene orchestration or render-proxy code
- cloud reconstruction services or external video upload

## Machine Topology

The current primary lab machine is this local Windows workstation with an installed RTX 5090. The goal of moving here from the Mac is to keep the Gaussian Splat pipeline local on one capable machine: video intake, frame sampling, SfM, CUDA/PyTorch/gsplat training, packaging and browser viewing should all be runnable here.

Windows RTX 5090 workstation:

- primary local pipeline host
- WSL2/Linux-first reconstruction runtime where practical
- Windows/PowerShell checks for driver, `nvidia-smi` and WSL status
- CUDA, PyTorch, COLMAP, Nerfstudio/gsplat and viewer experiments
- local videos, extracted frames, SfM databases, checkpoints and splat artifacts

Mac:

- optional secondary documentation or lightweight editing machine
- no longer the assumed primary development/runtime host
- no CUDA or NVIDIA GPU assumption

## Artifact Policy

Large or generated files stay out of git:

- videos
- extracted frames
- COLMAP/SfM databases
- checkpoints
- splat artifacts
- logs and generated reports

Commit only small manifests, docs, scripts and reproducible configuration.

## Initial Smoke Commands

In WSL/Linux on the RTX workstation, run the lightweight local smoke. The script name is historical from the earlier Mac-first setup:

```bash
./scripts/smoke-mac.sh
```

The original Mac-specific Phase 0 validation still exists for the old checkout layout, but this Windows RTX workstation is now the primary host for reconstruction validation:

```bash
./scripts/validate-phase-0.sh
```

On the Windows RTX workstation, from PowerShell:

```powershell
.\scripts\smoke-rtx-worker.ps1
```

Evidence-producing Phase 0 validation on the Windows RTX workstation:

```powershell
.\scripts\validate-phase-0-rtx-worker.ps1
```

The RTX smoke script is intentionally lightweight for Stage 0. Later stages will add explicit CUDA, PyTorch and gsplat kernel checks.


Architecture contract validation for dependency decisions, preflight gates and media pipeline gates:

```bash
./scripts/validate-architecture-contracts.sh
```

Capture readiness and local video import:

```bash
.venv/bin/python scripts/lab-pipeline.py list-captures --capture-manifest data/manifests/captures.example.json
.venv/bin/python scripts/lab-pipeline.py import-video --capture-id <capture-id> --input <local-video> --accept-warning --overwrite
```


Local end-user UI:

```bash
./scripts/lab-ui-server.py
```

UI contract validation:

```bash
./scripts/validate-ui-contracts.sh
```

## Implementation Phases

The staged implementation plan is maintained in [docs/phases.md](docs/phases.md). Each phase has explicit outputs and exit criteria; later phases should not depend on unvalidated earlier phases.
