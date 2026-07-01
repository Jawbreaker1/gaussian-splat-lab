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
| `splatfacto-big-ceiling-20260620T122053` | Nerfstudio Splatfacto-big | 30000 | 184 | 694927 | 165 MB | completed | PSNR `28.6966`, SSIM `0.9252`, LPIPS `0.0862` | Same downscale-2 dataset as the reference run. Viewer package keeps 612058 splats after filtering floaters. Better, but the modest metric gain suggests input resolution/camera coverage is now a bigger bottleneck than raw splat count. |
| `20260620T125300Z` | Nerfstudio Splatfacto-big | 40000 target | 184 | none exported | none | failed at ~3958 s | failed at step `33050` / `40000` | Full-resolution/downscale-1 ceiling attempt. VRAM reached roughly 32 GB and training ended with `torch.AcceleratorError: CUDA error: unknown error` before checkpoint/export. This marks 40k full-resolution Splatfacto-big as above the practical RTX 5090 ceiling for this capture. |
| `20260620T140713Z` | Nerfstudio Splatfacto-big | 30000 | 184 | 813169 | 192 MB | completed | PSNR `28.2316`, SSIM `0.9308`, LPIPS `0.1202` | Full-resolution/downscale-1 practical ceiling attempt. It completed and exported a viewer package with 730205 splats, but LPIPS regressed and browser eval FPS dropped to `0.455`. More input resolution did not improve perceptual quality for this capture. |
| `/tmp/gsl-splatfacto-preview/20260620T111933Z` | integrated Splatfacto preview | 1000 | 184 | 96610 | 23.9 MB | 35.0 s | PSNR `22.9227`, SSIM `0.7977`, LPIPS `0.2685` | Pipeline smoke only; validated train, export, eval, packaging and viewer manifest generation. |

Practical conclusion: expose `splatfacto_big_quality` as the GUI's `Best quality` path: 30k Splatfacto-big at downscale 2 is the current best measured balance. Keep `splatfacto_ceiling` as an explicit lab profile for full-resolution experiments; 30k full-resolution completed but was perceptually worse, while 40k full-resolution hit the VRAM cliff before export. Keep the repo-local mini `gsplat` trainer for fast debug, controlled stress testing and experiments where we need tighter ownership of the training code.

## 2026-06-29 Known-Camera Flowers Dataset

Reference input: `mipnerf360-flowers-colmap-reference`

This uses the local Mip-NeRF 360 `flowers` scene as a direct COLMAP dataset: original images plus `sparse/0`. FFmpeg frame sampling and COLMAP SfM are skipped because the camera model is already supplied. This gives a cleaner trainer/viewer reference than the older MP4-derived flowers path.

| Job | Profile | Method | Images | Viewer splats | Viewer PLY | Splat stage time | Eval result | Notes |
| --- | --- | --- | ---: | ---: | ---: | ---: | --- | --- |
| `mipnerf360-flowers-colmap-reference-20260629T193455Z` | `splatfacto_reference` | Splatfacto | 173 | 1968279 | 488 MB | ~14 min train, ~17 min stage | PSNR `20.1776`, SSIM `0.5418`, LPIPS `0.3750` | Good reference baseline. Much better than preview and visibly cleaner than the older derived-video path. |
| `mipnerf360-flowers-colmap-reference-20260629T200216Z` | `splatfacto_big_quality` | Splatfacto-big | 173 | 2000000 interactive, 4784784 full export | 496 MB interactive, 1.186 GB full export | 1569.8 s | PSNR `20.4715`, SSIM `0.5701`, LPIPS `0.2974` | Better on all eval metrics. Packaging now keeps the full export but defaults the browser to a budgeted interactive artifact. |

Practical conclusion: direct COLMAP datasets are now the best reference lane for measuring trainer quality without conflating it with video sampling or camera-solve failures. `splatfacto_big_quality` gives a real quality gain on Flowers, but the full export is very large. Keep `splatfacto_reference` as the lighter comparison baseline, and use `splatfacto_big_quality` when the goal is to find the current quality ceiling. The eval metrics above come from the full trained model; the web viewer should default to the interactive artifact until we add a real compressed/LOD format, and that interactive artifact should be judged visually in the browser.

## 2026-07-01 Graphdeco/Inria T&T+DB Truck Benchmark

Reference input: `graphdeco-tandt-truck-colmap-reference`

This uses the official Graphdeco/Inria `T&T+DB COLMAP` archive linked from the 3D Gaussian Splatting project page. It is the cleanest technical benchmark lane added so far: images and COLMAP cameras are already present, so the pipeline skips both video frame extraction and SfM. Treat the generated splats as internal benchmark artifacts until the dataset/media terms are reviewed for public or commercial use.

| Job | Profile | Method | Images | Viewer splats | Viewer PLY | Splat stage time | Eval result | Notes |
| --- | --- | --- | ---: | ---: | ---: | ---: | --- | --- |
| `graphdeco-tandt-truck-colmap-reference-20260701T115428Z` | `splatfacto_reference` | Splatfacto | 251 | 516331 | 128 MB | 367.6 s total stage, 305.4 s train | PSNR `25.5914`, SSIM `0.8805`, LPIPS `0.1060` | First run passed training, packaging, viewer validation and visual review. Render-review sheet shows close target/render agreement across held-out views. |

Practical conclusion: this is a much better “known good” reference than the rejected RGB-D samples. It shows that our direct `colmap_dataset` lane can produce a recognizable, navigable 3DGS scene from benchmark-grade inputs quickly. The next useful ceiling test is `splatfacto_big_quality` on the same `truck` scene, then one Deep Blending indoor scene such as `playroom`.

## 2026-06-20 Local 4K Video Samples

These runs used the current default high-quality path, `splatfacto_big_quality`: Splatfacto-big, 30k iterations, downscale factor `2`, 3 fps frame sampling, COLMAP sequential matching and viewer packaging.

Both videos are local test inputs from `C:\Users\engwa\Downloads`, so the pipeline correctly keeps the final quality report at `warning`: technically usable, but not license/provenance-clean for commercial distribution until the source rights are confirmed.

| Job | Source video | Frames | Registered | Sparse points | Viewer splats | Viewer PLY | Eval result | Visual read |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
| `local-vaxthus-ceiling-sample-20260620T125503Z` | `växthus.mp4` | 243 | 243 | 120129 | 1508938 | 357 MB | PSNR `24.1460`, SSIM `0.8192`, LPIPS `0.1445` | Best environment reference so far. Rich parallax, dense foliage and greenhouse structure make it a much better test than the old fan clip. Some leaf clusters and fine plants still smear, which is expected for moving/organic texture and imperfect video coverage. |
| `local-grill-ceiling-sample-20260620T125503Z` | `grill.mp4` | 282 | 281 | 191427 | 788650 | 187 MB | PSNR `27.2697`, SSIM `0.9379`, LPIPS `0.1402` | Strong camera solve despite the repetitive store aisle. Good stress test for shiny metal, signs and textureless floor, but less useful as a target environment. The render review shows smooth/washed floor areas and occasional artifacts on reflective grills. |

Practical conclusion: keep `växthus.mp4` as the better local video reference for environment-quality work. Keep `grill.mp4` as a stress case for SfM, reflective surfaces and repeated retail geometry. These two scenes also show why the UI needs sub-progress inside "SfM camera solve": grill spent most of its time in CPU sequential matching even though training on the RTX 5090 was comparatively quick.
