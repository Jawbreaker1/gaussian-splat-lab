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

## 2026-06-19 Local Upload Stress Note

Reference job: `outputs/jobs/capture-video-20260619T103507Z-20260619T103515Z`

This was not a clean hardware-limit test because the GPU memory was overclocked during the run. Treat it as a stability warning for the current Windows/WSL/CUDA setup, not as proof that RTX 5090 stock clocks cannot run larger scenes.

| Splat run | Profile | Iterations reached | Images | Gaussians | Render size | Result | Notes |
| --- | --- | ---: | ---: | ---: | --- | --- | --- |
| `20260619T113120Z` | `rtx_ultra_quality` | 24000 / 24000 | 144 | 1600000 | 1600 x 900 | pass | Produced an 89.6 MB PLY in 1140.1 s, mean render-review MAE 12.7041. |
| `20260619T125133Z` | `rtx_max_quality` | 10000 / 30000 | 160 | 2500000 | 1600 x 900 | fail | Hit near-full VRAM and exited with `CUDA error: unknown error`; no PLY artifact. |
| `20260619T132414Z` | `rtx_ceiling_quality` | 16000 / 30000 | 173 | 2000000 | 1600 x 900 | interrupted | Host appeared to crash/restart while near the VRAM limit; GPU-memory overclock may have contributed. |
| `20260619T200405Z` | `rtx_stable_quality` all-views trial | 36000 / 36000 | 184 | 1600000 | 1600 x 900 | pass | Stable, but worse visual/metric result: mean render-review MAE 16.1249. All registered frames included too many weak/occluded views. |
| `20260619T203502Z` | `rtx_stable_quality` Ultra-long | 30000 / 30000 | 144 | 1600000 | 1600 x 900 | pass | Best local upload result so far: 89.6 MB PLY, 1017.4 s, 10079 MiB peak VRAM, mean render-review MAE 11.3772. |

Practical conclusion: keep the GUI's highest normal choice below the VRAM cliff. `rtx_stable_quality` is the current user-facing max profile: it keeps the 1.6M gaussian cap, uses the 1600px training render, and gives the Ultra-style training setup more optimization time without asking ordinary users to run a stress profile. Revisit `rtx_ceiling_quality` and `rtx_max_quality` only with stock-stable GPU memory and active monitoring.

## 2026-06-20 Splatfacto Trainer Comparison

Same local upload job: `outputs/jobs/capture-video-20260619T103507Z-20260619T103515Z`

The main quality lesson changed after testing Nerfstudio Splatfacto. The best result did not come from pushing the mini-trainer to more gaussians. It came from a better trainer/export path with fewer, better-optimized splats.

| Run | Trainer | Iterations | Images | Gaussians | PLY size | Train time | Eval result | Notes |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
| `20260619T203502Z` | repo mini `gsplat` | 30000 | 144 | 1600000 | 89.6 MB | 1017.4 s | mean render-review MAE `11.3772` | Best mini-trainer run so far; usable but still soft in the browser from some angles. |
| `splatfacto-reference-20260620T0120` | Nerfstudio Splatfacto | 30000 | 184 | 246863 | 59 MB | ~506.6 s | PSNR `28.4849`, SSIM `0.9209`, LPIPS `0.0946` | Visually much sharper on held-out/eval views; current best-quality path. |
| `/tmp/gsl-splatfacto-preview/20260620T111933Z` | integrated Splatfacto preview | 1000 | 184 | 96610 | 23.9 MB | 35.0 s | PSNR `22.9227`, SSIM `0.7977`, LPIPS `0.2685` | Pipeline smoke only; validated train, export, eval, packaging and viewer manifest generation. |

Practical conclusion: expose Splatfacto as the GUI's `Best quality` path. Keep the repo-local mini `gsplat` trainer for fast debug, controlled stress testing and experiments where we need tighter ownership of the training code. The next ceiling work should tune Splatfacto settings and capture quality before adding more mini-trainer splats.
