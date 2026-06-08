# Commercial Compliance Gate

Verified: 2026-06-07

Goal: keep this lab on a path that can become commercial without accidentally violating software licenses, platform terms, media rights or redistribution obligations.

This is not legal advice. It is the engineering compliance gate we must satisfy before calling the pipeline commercially ready.

## Commercial Readiness Rule

A dependency, tool or artifact is not product-ready merely because it runs. It must have:

- official source URL
- exact version or commit
- license and notice obligations
- commercial-use status
- redistribution status
- transitive dependency review
- generated-output/artifact rights status where applicable
- documented approval for any conditional item

Until all are recorded, the component can be used only for lab evaluation.

## Current Position

Commercially plausible path:

- training: Nerfstudio/Splatfacto first, then narrower `gsplat` if needed
- SfM: COLMAP command-line boundary
- viewer: Spark + Three.js first, SuperSplat open-source components as fallback
- app: Python CLI first; React/Vite/FastAPI only when the product surface needs them

Explicitly blocked for this product path:

- original GraphDeco/Inria `gaussian-splatting` runtime code, because the license is non-commercial research/evaluation without explicit commercial consent
- OpenSplat by default, because AGPL obligations are not accepted for this pipeline unless we make a deliberate legal/product decision

Conditional:

- FFmpeg/ffprobe: allowed as a system external tool in the lab; bundling/distribution requires review of LGPL/GPL/nonfree build flags and codec/patent exposure
- NVIDIA CUDA: allowed on the local RTX workstation; redistribution of CUDA/driver/runtime components requires checking the current NVIDIA terms for the exact package
- SuperSplat: use only self-hosted open-source MIT components unless hosted PlayCanvas terms are separately accepted

## Required Checklist Before Product Use

For every runtime dependency:

- `[ ]` record exact package name, version, install source and URL
- `[ ]` store or link license text
- `[ ]` record NOTICE/copyright requirements
- `[ ]` run transitive dependency license scan
- `[ ]` classify as `allowed`, `conditional` or `blocked`
- `[ ]` resolve every conditional item in writing
- `[ ]` ensure no blocked dependency is imported, vendored, installed or required at runtime

For external binaries:

- `[ ]` record `--version` output
- `[ ]` record build/configure flags when available
- `[ ]` decide whether the binary is user-installed, worker-installed, containerized or redistributed
- `[ ]` collect source-offer/notice obligations if redistributed

For input videos:

- `[ ]` record who owns the video
- `[ ]` record capture consent and privacy status
- `[ ]` record whether commercial derivative use is allowed
- `[ ]` record whether generated splats may be stored, displayed, sold, sublicensed or deleted on request
- `[ ]` block public/product demos unless the capture is owned by us or licensed for that use

For generated Gaussian Splat artifacts:

- `[ ]` link artifact to source video manifest
- `[ ]` record generator toolchain and versions
- `[ ]` record output format and viewer license
- `[ ]` record whether the artifact can be commercially displayed or distributed
- `[ ]` hash the artifact and preserve the job reports

## Production Stop Conditions

Stop immediately if:

- a dependency has missing or unknown license
- a dependency has non-commercial/research-only terms
- a GPL/AGPL dependency would become part of app/server runtime without deliberate acceptance
- FFmpeg is bundled without completed LGPL/GPL/nonfree review
- CUDA components are redistributed without current EULA review
- input video rights are missing, unclear or personal/private without consent
- hosted platform terms are required for core reconstruction or viewing

## Notices Bundle

Before shipping any app or packaged worker, create a generated notices bundle under a release artifact, not in source control by default:

```text
THIRD_PARTY_NOTICES/
  software.json
  licenses/
  notices.md
  external-tools.md
```

The notices bundle must include at least MIT/Apache/BSD notices for distributed libraries and any extra notices required by Apache-2.0 NOTICE files, FFmpeg/LGPL terms or binary packages.

## Decision Log

Every promotion from lab to production must add a dated decision entry that includes:

- selected framework/tool
- rejected alternatives
- license/commercial reasoning
- exact unresolved risks
- owner of final legal review
