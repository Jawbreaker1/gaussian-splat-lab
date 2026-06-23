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

## Current Read

The change is promising but not magic. It improves the image set and can materially improve COLMAP registration on a weak clip, while preserving behavior on a clean clip. It does not fix captures that lack enough stable overlap, texture or parallax.

Next validation should compare final Splatfacto render reviews on a small set of scenes, using the same training profile before and after keyframe selection.
