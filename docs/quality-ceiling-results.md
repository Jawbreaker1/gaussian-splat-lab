# Quality Ceiling Results

Verified: 2026-06-18

Reference job: `outputs/jobs/mipnerf360-flowers-reference-20260617T142004Z`

The current best active viewer profile is `rtx_ultra_quality`. It is not the absolute largest artifact; it is the best quality/performance point observed so far on the RTX 5090 for the Mip-NeRF 360 flowers reference scene.

| Splat run | Iterations | Images | Gaussians | PLY size | Wall time | Peak VRAM | Render MAE | Notes |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `20260617T150307Z` | 2500 | 48 | 120000 | 6.7 MB | 13.1 s | 370 MiB | 18.8967 | Fast smoke-like quality baseline. |
| `20260617T151122Z` | 9000 | 64 | 400000 | 22.4 MB | 67.7 s | 1225 MiB | 17.1369 | Stable reference profile. |
| `20260617T220127Z` | 18000 | 112 | 1000000 | 56.0 MB | 165.8 s | 2056 MiB | 16.8386 | Good high-quality baseline. |
| `20260618T003649Z` | 24000 | 144 | 1600000 | 89.6 MB | 264.2 s | 2785 MiB | 16.4521 | Best observed MAE, first ultra run. |
| `20260618T014010Z` | 24000 | 144 | 1600000 | 89.6 MB | 264.3 s | 2770 MiB | 16.8005 | Active ultra rerun with clean GPU-baseline report. |
| `20260618T012629Z` | 30000 | 173 | 2000000 | 112.0 MB | 368.4 s | 3605 MiB | 17.5403 | Controlled ceiling test; more splats and images reduced measured quality. |
| `20260617T211053Z` | 30000 | 160 | 2500000 | 140.0 MB | 1406.1 s | 3749 MiB | 20.8938 | Old max stress test; large artifact but visually/quantitatively worse. |

## Interpretation

Increasing splat count helped up to `rtx_ultra_quality`, but quality regressed at 2.0M and 2.5M splats under the current densification and optimization settings. For this scene, the current practical ceiling is therefore around 1.6M gaussians, not the largest file.

The 1.6M ultra profile should remain the active reference until a new tuning path beats it on both render-review metrics and visual inspection. Good next experiments:

- add deterministic seed recording so repeated quality runs are easier to compare
- add a promotion command that can make the best existing splat run active without retraining
- test a 1.8M profile with ultra-like settings before revisiting 2.0M+
- compare Spark browser screenshots against the `gsplat` render-review sheet at reference camera poses
