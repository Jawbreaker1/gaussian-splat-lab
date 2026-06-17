# Framework Evaluation

Verified: 2026-06-16

This project must be able to move from a local video to an interactive browser Gaussian Splat without accidentally depending on non-commercial, strong-copyleft or hosted/proprietary services that would block later product use.

This document is not legal advice. It is an engineering gate: no framework can become a runtime dependency until its license, source, role and constraints are recorded here and in `data/manifests/framework-evaluation.json`.

## Commercial Use Posture

This lab targets possible commercial use. Treat `accepted` as technically/license-compatible for evaluation, not as final production approval. Production use also requires the commercial compliance gate in [commercial-compliance.md](commercial-compliance.md): exact versions, transitive dependency scan, notices, redistribution review and input-media rights.

## License Policy

Preferred licenses for runtime code:

- MIT
- Apache-2.0
- BSD-2-Clause / BSD-3-Clause / BSD-style permissive licenses

Conditional licenses and components:

- LGPL tools can be used as external system binaries in the lab, but must not be bundled into a shipped app without a specific compliance review.
- Proprietary GPU runtimes such as NVIDIA CUDA can be used on the RTX workstation, but we must not redistribute standalone NVIDIA components unless the relevant NVIDIA terms allow it.
- Hosted SaaS features are not acceptable for the core reconstruction path. Self-hosted open-source viewers/tools can be used.

Blocked by default:

- non-commercial or research-only licenses
- AGPL/GPL runtime dependencies for app/server code unless we explicitly decide to accept their copyleft obligations
- unknown or missing license

## Recommended MVP Stack

| Boundary | Recommended first choice | Decision | Why |
| --- | --- | --- | --- |
| App shell | Python stdlib CLI first; FastAPI later if local API is needed | Accepted | Keeps orchestration simple until stages are real. FastAPI is MIT. |
| Video metadata/sampling | System `ffmpeg`/`ffprobe` | Conditional | Practical and mature, but build flags can switch FFmpeg from LGPL to GPL/nonfree. Record build config and do not bundle yet. |
| SfM/camera solve | COLMAP command line | Accepted | Mature SfM/MVS pipeline; COLMAP itself is BSD-style, but third-party dependency licenses must be recorded. |
| Training smoke | Nerfstudio Splatfacto | Accepted for lab | Apache-2.0, already wraps data parsing/training/export; good first end-to-end path. |
| Training core | `gsplat` | Accepted | Apache-2.0 CUDA rasterization library; good target if we need a narrower custom trainer after the MVP. |
| PyTorch companion | TorchVision | Accepted | Installed with the GPU smoke environment; keep notices and avoid bundled datasets/model weights unless separately licensed. |
| Viewer | Spark + Three.js | Preferred current viewer | MIT, active, Three.js-based, supports common splat formats including PLY/SPZ/SPLAT/KSPLAT/SOG. This is the current browser 3DGS viewer path; the older local WebGL PLY renderer is retained as point-debug fallback. |
| Viewer/editor fallback | SuperSplat viewer/editor and `splat-transform` | Accepted | MIT open-source pieces; avoid the hosted PlayCanvas publishing platform for core pipeline. |
| Legacy viewer fallback | `mkkellogg/GaussianSplats3D` | Accepted fallback | MIT and mature, but the maintainer notes it is no longer actively developed. |

## Framework Notes

### Block Original GraphDeco/Inria Gaussian Splatting Code

The original `graphdeco-inria/gaussian-splatting` repository is useful as a paper/reference point, but it is not acceptable as a product runtime dependency. Its license grants use for research/evaluation and states that commercial use requires prior explicit consent from the licensors.

Decision: blocked for runtime/product use.

Official source:

- https://github.com/graphdeco-inria/gaussian-splatting/blob/main/LICENSE.md

### Prefer Nerfstudio/gsplat for Training Experiments

`gsplat` is Apache-2.0 and describes itself as a CUDA-accelerated Gaussian rasterization library with Python bindings. Nerfstudio documents Splatfacto as its Gaussian Splatting implementation and says it uses `gsplat` as the rasterization backend.

Decision: accepted.

Official sources:

- https://github.com/nerfstudio-project/gsplat
- https://docs.nerf.studio/nerfology/methods/splat.html
- https://github.com/nerfstudio-project/nerfstudio

### Use COLMAP Behind a Narrow SfM Boundary

COLMAP is accepted for the SfM stage, but must remain behind a command boundary. The project states that COLMAP itself is under the new BSD license and separately warns that third-party dependencies are independently licensed.

Decision: accepted with dependency review.

Official source:

- https://github.com/colmap/colmap

### Treat FFmpeg as Conditional

FFmpeg is the practical default for video metadata and frame extraction. Its legal page says FFmpeg is LGPL v2.1 or later, but optional GPL components make the whole FFmpeg binary GPL if used. For now we use a system-installed binary only and record `ffmpeg -version` output in the stage report.

Decision: conditional.

Official source:

- https://www.ffmpeg.org/legal.html

### Viewer Direction

The viewer should be isolated and format-driven. Current best first real-renderer spike is Spark on Three.js because Spark is MIT, active, browser-based and supports multiple splat formats. Spark currently describes itself as an advanced 3D Gaussian Splatting renderer for Three.js and the latest checked package version is `2.1.0`. The current dependency-free WebGL canvas in this repo is only a PLY point-debug inspector. SuperSplat is a strong fallback for editing/conversion and self-hosted viewing. The hosted PlayCanvas publishing flow is explicitly outside the core pipeline.

Official sources:

- https://github.com/sparkjsdev/spark
- https://github.com/mrdoob/three.js/blob/dev/LICENSE
- https://developer.playcanvas.com/user-manual/supersplat/
- https://github.com/playcanvas/supersplat
- https://github.com/mkkellogg/GaussianSplats3D

## Open Questions Before Implementation Choices Are Locked

- Which output format is best for our first viewer path: raw Gaussian PLY, SPZ, SOG or KSPLAT?
- Does the RTX 5090 worker currently have a PyTorch/CUDA/gsplat combination that supports its Blackwell compute capability cleanly?
- Do we need a local API server in the MVP, or is a CLI plus static viewer enough for the first successful capture?
- Which known-good input videos have licenses compatible with commercial product evaluation?

## Decision Rule

Before adding a dependency:

1. Add it to `data/manifests/framework-evaluation.json`.
2. Record official source URL, license, role and decision.
3. Mark it `preferred`, `accepted`, `conditional`, `deferred` or `blocked`.
4. If `conditional`, write the exact condition that must be validated.
5. Run `./scripts/validate-architecture-contracts.sh`.

No blocked dependency may be imported, vendored, installed by setup scripts, or required by runtime app code.
