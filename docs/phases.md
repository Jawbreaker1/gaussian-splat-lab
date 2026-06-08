# Implementation Phases

This lab must progress through small, validated phases. Do not build a later phase on top of an unvalidated earlier one.

## Phase 0: Repository and Isolation

Status: local validation passed; Windows RTX workstation GPU smoke pending.

Purpose:

- keep the Gaussian Splat lab disposable and separate from `blender-ai-poc`
- define the local Windows RTX 5090 workstation as the primary reconstruction host
- prevent large generated artifacts from entering git

Outputs:

- private `gaussian-splat-lab` repository
- `README.md`, `AGENTS.md`, `.gitignore`
- WSL/Linux and Windows RTX smoke scripts
- `docs/stage-0.md`

Exit criteria:

- repo clones independently
- WSL/Linux smoke command passes on the RTX workstation
- Windows RTX workstation smoke command passes or records clear setup gaps
- heavy artifact paths are ignored
- no runtime dependency exists on `blender-ai-poc`

## Phase 1: Known-Good Inputs and Minimal Contracts

Purpose:

- remove capture quality as an early source of uncertainty
- define the smallest manifest shape needed to pass artifacts between stages

Stages:

1. select and license-check 2-3 known-good static captures
2. create a local capture manifest
3. define minimal `ViewerAsset(assetType=gaussian_splat)` examples

Outputs:

- known-good capture manifest
- license notes for each source
- expected pipeline path per test case
- viewer asset examples
- manifest-driven pipeline job skeleton

Exit criteria:

- every input has a documented source and license status
- at least one input is suitable for full video-to-splat testing
- `ViewerAsset` examples do not depend on `blender-ai-poc` runtime code

## Phase 2: Viewer-First Proof

Purpose:

- prove browser presentation before spending effort on reconstruction
- isolate viewer/runtime problems from camera solve and training problems

Stages:

1. obtain a known-good splat artifact with compatible license for lab use
2. load it in an isolated lab viewer
3. record load time, memory, FPS and camera-control behavior

Outputs:

- isolated viewer prototype
- viewer compatibility notes
- first accepted or rejected splat delivery format candidate

Exit criteria:

- splat is visible in desktop browser
- orbit, pan, zoom and reset work
- viewer failure modes are documented

## Phase 3: RTX Workstation Environment Gate

Purpose:

- prove the local Windows RTX 5090 workstation can run the required GPU stack
- avoid confusing CUDA/toolchain failures with reconstruction quality failures

Stages:

1. verify Windows driver and `nvidia-smi`
2. verify WSL2/Linux environment if used
3. verify Python, CUDA-compatible PyTorch and GPU visibility
4. run a minimal CUDA/gsplat smoke test

Outputs:

- environment report
- successful GPU smoke output
- notes on driver, CUDA, PyTorch and extension versions

Exit criteria:

- RTX 5090 is visible to the chosen runtime
- minimal GPU computation passes
- failures are specific enough to fix or switch stack

## Phase 4: Reconstruction Components

Purpose:

- build the video-to-splat chain as independent, replaceable components

Stages:

1. local video intake and metadata extraction
2. deterministic frame sampling
3. SfM/camera solve boundary
4. local splat training
5. artifact packaging

Outputs:

- `CaptureInput`
- frame manifest and thumbnails/contact sheet
- `CameraSolveReport`
- raw splat/checkpoint and training logs
- browser-loadable `SplatArtifact`

Exit criteria:

- each component can be run and inspected independently
- same input/config produces the same intermediate outputs
- a failed stage can be rerun without starting from zero
- component replacement does not require rewriting the whole chain

## Phase 5: Quality Report and Resumable CLI

Purpose:

- turn the working chain into a repeatable lab workflow
- make failures readable instead of just producing logs

Stages:

1. classify result quality from solve, training, packaging and viewer evidence
2. produce `CaptureQualityReport`
3. build a resumable lab CLI that orchestrates existing stages

Outputs:

- quality report with `usable`, `weak` or `failed`
- failure classification by pipeline boundary
- end-to-end lab command for known-good inputs
- job folder containing all intermediate artifacts

Exit criteria:

- one known-good input runs from video to browser-visible splat
- failed stages preserve enough evidence for diagnosis
- reruns can resume from stable intermediate artifacts

## Phase 6: Input Quality Experiments and Capture Preflight

Purpose:

- only after the known-good chain works, measure how input video degradation affects each pipeline boundary
- convert experiment evidence into early rejection/warning for bad captures

Stages:

1. define a high-quality baseline capture with commercial rights
2. generate controlled degraded variants one axis at a time
3. run each variant through the same pipeline config
4. compare stage reports against the baseline
5. derive preflight thresholds for duration, resolution, frame count, blur, exposure, motion, parallax and coverage
6. return `CapturePreflightReport`

Outputs:

- input quality experiment manifest and summary
- per-variant quality report with failure boundary
- preflight report with `ready`, `warning` or `blocked`
- user-facing capture guidance

Exit criteria:

- baseline known-good input still passes end to end
- each tested degradation has a recorded source, transform and result
- intentionally bad samples produce useful warnings or blocks
- preflight thresholds are backed by experiment evidence
- preflight failures are not used to hide reconstruction bugs

## Phase 7: Isolated Capture UI

Purpose:

- provide a small local UI without integrating into the main product

Stages:

1. local upload/import in the lab repo
2. async lab job status
3. quality report view
4. viewer link for successful splats

Outputs:

- isolated lab UI
- job state model
- local artifact browsing

Exit criteria:

- user can run a capture job without CLI-only steps
- UI remains independent from `blender-ai-poc`
- large or invalid files fail cleanly

## Phase 8: Promotion Evaluation

Purpose:

- decide whether the lab is good enough to integrate or should stay isolated

Promotion requires:

- known-good video to browser-visible splat works
- selected stack is commercially compatible enough for product evaluation
- RTX 5090 workstation setup is reproducible
- failure modes are classified by pipeline boundary
- browser viewer consumes a narrow manifest equivalent to `ViewerAsset(assetType=gaussian_splat)`
- integration can happen through an adapter/viewer boundary without importing reconstruction dependencies into the main app

If these criteria are not met, keep the lab isolated or archive it.
