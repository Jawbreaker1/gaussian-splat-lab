# Stage 0: Isolated Lab Workspace

## Goal

Create a separate, disposable lab workspace for video-to-Gaussian-Splat evaluation without affecting `blender-ai-poc`.

This stage is complete when:

- the repo can be cloned independently
- basic smoke commands run on the Mac and the Windows RTX worker
- artifact locations are ignored by git
- the two-machine topology is documented
- no runtime dependency exists on the main Blender/3D project

## Local Layout

Recommended checkout layout:

```text
~/github_repos/
  blender-ai-poc/
  gaussian-splat-lab/
```

## Machine Roles

Mac:

- docs
- manifests
- lightweight scripting
- optional browser viewer development

Windows RTX 5090 worker:

- WSL2/Linux-first reconstruction runtime
- CUDA/PyTorch/COLMAP/gsplat smoke checks
- reconstruction jobs and generated artifacts

Run this first on the Windows RTX worker:

```powershell
.\scripts\validate-phase-0-rtx-worker.ps1
```

The generated `docs\validation\phase-0-rtx-worker-output.md` file is the evidence needed to close Phase 0.

## Artifact Layout

Ignored local directories:

- `data/videos/`
- `data/frames/`
- `data/sfm/`
- `data/checkpoints/`
- `data/splats/`
- `artifacts/`
- `outputs/`
- `logs/`

Tracked directories:

- `data/manifests/`
- `docs/`
- `scripts/`

## Promotion Rule

Nothing from this repo should be integrated into `blender-ai-poc` until a known-good capture can run from video to browser-visible splat and the result can be represented as a narrow viewer asset manifest.
