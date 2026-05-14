# Gaussian Splat Lab

Status: Stage 0 scaffold

This repository is an isolated lab for local video-to-Gaussian-Splat reconstruction.

It is intentionally separate from `blender-ai-poc`. The first goal is to evaluate whether a local, commercially compatible, RTX 5090-based pipeline can produce browser-viewable Gaussian Splat artifacts from known-good static video inputs.

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

Development currently happens on a Mac. GPU reconstruction runs on a separate Windows machine on the same LAN with an RTX 5090.

Mac development machine:

- documentation and repo scaffolding
- manifests and lightweight scripts
- optional browser viewer development
- no CUDA or NVIDIA GPU assumption

Windows RTX 5090 worker:

- WSL2/Linux-first reconstruction environment
- CUDA, PyTorch, COLMAP and gsplat experiments
- local videos, extracted frames, SfM databases, checkpoints and splat artifacts

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

On the Mac development machine:

```bash
./scripts/smoke-mac.sh
```

On the Windows RTX worker, from PowerShell:

```powershell
.\scripts\smoke-rtx-worker.ps1
```

The RTX smoke script is intentionally lightweight for Stage 0. Later stages will add explicit CUDA, PyTorch and gsplat kernel checks.

## Implementation Phases

The staged implementation plan is maintained in [docs/phases.md](docs/phases.md). Each phase has explicit outputs and exit criteria; later phases should not depend on unvalidated earlier phases.
