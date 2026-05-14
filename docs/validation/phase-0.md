# Phase 0 Validation Report

Status: local validation passed; RTX worker validation pending.

Date: 2026-05-14

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

## Manual RTX Worker Validation

This must be run on the Windows RTX 5090 machine from a clone or copied checkout of this repository:

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

Phase 0 is not fully closed until this Windows RTX worker smoke has been run and the result is recorded here.

## Exit Criteria

- `[x]` repo clones independently
- `[x]` Mac smoke command passes
- `[x]` heavy artifact paths are ignored
- `[x]` no runtime dependency exists on `blender-ai-poc`
- `[ ]` Windows RTX worker smoke command has been run and recorded

## Decision

Do not start Phase 1 as closed work until the Windows RTX worker smoke output is captured. Planning for Phase 1 may continue, but the phase gate remains open.
