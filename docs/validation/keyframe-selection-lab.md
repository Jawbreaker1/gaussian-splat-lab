# Keyframe Selection Lab

Date: 2026-06-23

This note tracks the first validation pass for generic quality-based keyframe selection. The goal is not to tune for one room. The selector uses broad image signals:

- sharpness
- contrast
- exposure balance
- clipped dark/bright pixels
- low-texture risk
- bright low-texture surface risk
- temporal coverage across the full source clip

## Frame Selection Comparison

The frame sampler now compares selected keyframes with a plain temporal baseline from the same candidate buckets. Positive `scoreMedianDelta` means the selected keyframes scored better than taking the middle candidate from each time bucket.

| Clip | Candidates | Selected | Selected median score | Baseline median score | Delta |
| --- | ---: | ---: | ---: | ---: | ---: |
| `capture-wizard-api-e2e-hf-room` | 111 | 37 | `0.9560` | `0.9555` | `+0.0005` |
| `capture-elliots-rum1` | 267 | 89 | `0.9586` | `0.9501` | `+0.0085` |
| `mipnerf360-flowers-reference` | 522 | 174 | `0.9377` | `0.9210` | `+0.0167` |

Interpretation: clean clips barely move, which is good. More varied clips show a larger score lift without changing the frame budget or losing temporal coverage.

## SfM Spot Check

Two small SfM checks were run after the new keyframe selection. This is still not a final render-quality test, but it tells us whether COLMAP sees a better or worse image set.

| Clip | Before | After | Notes |
| --- | --- | --- | --- |
| `capture-wizard-api-e2e-hf-room` | `36/36` registered, `13,014` sparse points, reprojection `0.702852` | `37/37` registered, `13,097` sparse points, reprojection `0.697693` | Already-good clip remained stable and improved slightly. |
| `capture-elliots-rum1` | `21/89` registered, `2,511` sparse points, reprojection `0.835439` | `44/89` registered, `8,322` sparse points, reprojection `1.088691` | Registration and point count improved, but still failed the `70%` registration threshold. More frames registered with a higher mean reprojection error, so this is not a solved capture. |

## 3DGS Render Spot Check

Two real 3DGS training runs were also checked after the keyframe selector. These are not final quality ceilings. They are sanity checks that the pipeline can go from scored video frames to SfM, training, export, render review and viewer packaging.

| Clip | Trainer | Images | Result | Render review |
| --- | --- | ---: | --- | --- |
| `capture-wizard-api-e2e-hf-room` | `quality_probe` / `gsplat`, `2,500` iterations | 37 | `120,000` gaussians, render review passed | MAE `9.0864`, RMSE `13.0668`, preview score `6.9539` |
| `capture-cuda-colmap-smoke-video` | `splatfacto_preview` / Nerfstudio, `1,000` iterations | 148 | `111,911` gaussians, render review passed | PSNR `22.7771`, SSIM `0.7911`, LPIPS `0.2826`, 19 eval images |

Contact sheets:

- `/home/engwall/projects/gaussian-splat-lab/outputs/jobs/capture-wizard-api-e2e-hf-room-20260619T093341Z-20260619T093341Z/splats/20260623T083719Z/render_review/contact_sheet.png`
- `/home/engwall/projects/gaussian-splat-lab/outputs/jobs/capture-cuda-colmap-smoke-video-20260621T114646Z-20260621T114746Z/splats/20260623T084705Z/render_review/contact_sheet.png`

The larger `capture-cuda-colmap-smoke-video` run is the better signal here: frame sampling selected 148 frames from 444 candidates, CUDA COLMAP registered `148/148` frames, and the Splatfacto preview produced a coherent render review. The small E2E room clip stayed valid, but the new keyframes did not improve every final-render metric. That is useful caution: better frame scores help the pipeline, but the final render still depends on trainer choice, scene coverage, camera motion and surface texture.

One operational note: GPU COLMAP must be run from an environment that can see CUDA. In the local sandbox, the CUDA sidecar can fail or fall back. Manual validation should set `GSL_COLMAP_BIN=/home/engwall/projects/gaussian-splat-lab/outputs/tools/colmap-cuda/bin/colmap` and run outside the sandbox when validating GPU behavior.

## Optional AI Review

The simplest AI layer should be an advisory visual review, not a replacement for the deterministic checks. The pipeline already generates the right inputs: selected-frame contact sheets, render/target/diff contact sheets, SfM metrics and trainer metrics.

A first version can ask a vision model for strict JSON:

- `status`: `pass`, `warning` or `fail`
- `riskFlags`: blur, textureless surfaces, exposure issues, coverage gaps, floaters, smeared geometry, missing walls/floors
- `recommendedAction`: continue, capture again, add more coverage, lower frame budget, raise training profile or inspect manually
- `confidence`: low, medium or high
- `evidenceCells`: which contact-sheet cells triggered the judgment

For privacy and commercial use, this should be opt-in if it sends images to a cloud model. Private room captures should not leave the machine by default. A local vision model can be added later, but the first useful version can be a small post-run reviewer that writes `reports/ai_review.json` and displays it as a second opinion in the UI.

## Current Read

The change is promising but not magic. It improves the image set and can materially improve COLMAP registration on a weak clip, while preserving behavior on a clean clip. It does not fix captures that lack enough stable overlap, texture or parallax.

Next validation should compare final Splatfacto render reviews on a small set of scenes, using the same training profile before and after keyframe selection.
