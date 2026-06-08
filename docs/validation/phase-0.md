# Phase 0 Validation Report

Status: historical local validation passed; Windows RTX workstation validation pending.

Date: 2026-05-14

## Current Topology Note

As of 2026-06-07, the primary lab host has moved from a Mac-first workflow to this local Windows workstation with an installed RTX 5090. The Mac validation below is historical evidence for the original scaffold. The active reconstruction gate is now the Windows/WSL RTX workstation validation.

## Scope

Phase 0 validates that this repository is isolated, disposable and ready to hold later Gaussian Splat lab work without affecting `blender-ai-poc`.

It does not validate CUDA, PyTorch, COLMAP, gsplat or reconstruction quality. Those belong to later phases.

## Automated Local Validation

Command:

```bash
./scripts/validate-phase-0.sh
```

Checks:

- repo is checked out at `/Users/johanengwall/github_repos/gaussian-splat-lab`
- sibling main project exists at `/Users/johanengwall/github_repos/blender-ai-poc`
- required Stage 0 docs and smoke scripts exist
- heavy artifact paths are ignored by git
- no heavy artifact paths are tracked by git
- runtime scripts do not reference the main project
- Mac smoke command passes
- shell scripts pass `bash -n`

Latest local result:

```text
scripts/smoke-mac.sh syntax: passed
scripts/validate-phase-0.sh syntax: passed
phase0_validation=local_passed
rtx_worker_validation=manual_pending
next_required_command_on_windows=.\scripts\validate-phase-0-rtx-worker.ps1
```

## Manual RTX Workstation Validation

This must be run on the Windows RTX 5090 workstation that is intended to host the local reconstruction pipeline:

```powershell
.\scripts\smoke-rtx-worker.ps1
```

Preferred evidence-producing command:

```powershell
.\scripts\validate-phase-0-rtx-worker.ps1
```

That command writes:

```text
docs\validation\phase-0-rtx-worker-output.md
```

Expected Stage 0 result:

- `git --version` works
- `nvidia-smi` is found or produces a clear missing-driver note
- `wsl --status` is found or produces a clear WSL2 setup note
- script exits successfully

Phase 0 is not fully closed for the current topology until this Windows RTX workstation smoke has been run and the result is recorded here.

## Current WSL RTX Evidence

Current WSL evidence for the local RTX workstation is recorded in [phase-0-rtx-workstation-wsl-output.md](phase-0-rtx-workstation-wsl-output.md). It confirms that the RTX 5090 is visible through `nvidia-smi` from the WSL environment intended for the local pipeline.

## Exit Criteria

- `[x]` repo clones independently
- `[x]` Mac smoke command passes
- `[x]` heavy artifact paths are ignored
- `[x]` no runtime dependency exists on `blender-ai-poc`
- `[ ]` Windows RTX workstation smoke command has been run and recorded

## Decision

Do not start Phase 1 as closed work until the Windows RTX workstation smoke output is captured. Planning for Phase 1 may continue, but the phase gate remains open.
