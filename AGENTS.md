# Agent Instructions

## Isolation

This repository is separate from `/Users/johanengwall/github_repos/blender-ai-poc`.

Do not import, symlink, vendor or copy runtime code from `blender-ai-poc` unless an explicit promotion decision has been made. Documentation may reference the main project, but executable lab code must remain independent.

Do not add Gaussian Splat dependencies to the main project from this repo.

## Artifacts

Do not commit heavy or generated artifacts:

- source videos
- extracted frames
- SfM databases
- model checkpoints
- splat files
- generated logs
- large rendered outputs

Use manifests to describe local artifacts instead.

## Development Order

Follow the staged plan in `docs/phases.md`.

Stage summary:

1. isolated workspace and smoke commands
2. known-good input manifest
3. minimal viewer asset examples
4. isolated browser viewer
5. RTX worker environment gate
6. video intake
7. frame sampling
8. SfM/camera solve
9. splat training
10. artifact packaging
11. quality report
12. resumable lab CLI
13. preflight
14. isolated capture UI

Avoid big-bang integration. Every stage must be runnable and inspectable before the next stage depends on it.

## Testing

Add focused automated tests for any application logic introduced here. For shell or environment checks, keep smoke tests small and deterministic.

If logic is hard to test, treat that as a boundary problem and simplify before adding more code.

## Complexity Guardrail

Pause before continuing if:

- the lab starts depending on the main project
- setup scripts become machine-specific without documentation
- generated code or artifacts start accumulating in git
- one stage cannot be validated without building multiple later stages
- CUDA/toolchain failures are hidden behind broad fallback logic
