# Input Quality Experiments

Verified: 2026-06-07

Goal: once the video-to-splat golden path is robust, measure how much input video quality can degrade before the pipeline fails or produces unusable Gaussian Splats.

This work must not start as a quality claim until at least one known-good baseline capture runs from video to browser-visible splat.

## Principle

Start from a high-quality baseline video with clear commercial rights. Generate controlled variants from that source, changing one variable at a time. Run every variant through the same pipeline config and compare each stage report against the baseline.

Do not use preflight warnings to hide reconstruction bugs. A known-good baseline must keep passing while experiments run.

## Experiment Axes

| Axis | Example Variants | Main Risk |
| --- | --- | --- |
| Resolution | 4K, 1440p, 1080p, 720p, 540p, 360p | Feature matching and splat detail collapse. |
| Bitrate/compression | visually lossless, medium, low, very low | Compression artifacts hurt SfM and texture/detail quality. |
| Frame rate/sampling | 60, 30, 15, 10, 5 fps | Too few usable viewpoints or motion continuity. |
| Blur | none, mild, moderate, strong | Feature detection and camera solve degrade. |
| Exposure | normal, underexposed, overexposed, flicker | Lost features and inconsistent appearance. |
| Noise | none, mild, moderate, strong | False features and noisy splats. |
| Motion speed | slow orbit, normal orbit, fast orbit | Motion blur and too-large inter-frame baselines. |
| Coverage | full orbit, partial orbit, narrow sweep | Incomplete geometry and weak camera solve. |
| Duration | 60s, 30s, 15s, 8s | Not enough viewpoints. |
| Subject/scene | textured, glossy, transparent, low-texture | Hard surfaces for SfM and splat training. |

## Metrics By Stage

| Stage | Metrics |
| --- | --- |
| Intake | duration, resolution, fps, bitrate, codec, frame count |
| Frame sampling | sampled frame count, missing frames, blur/exposure summary, contact sheet |
| SfM | registered frames %, sparse point count, reprojection error, failed image count |
| Training | export exists, splat count/size, training time, loss trend, sample renders |
| Packaging | artifact format, byte size, hash, parse/load success |
| Viewer | nonblank canvas, load time, memory, FPS, interaction success |
| Quality | `usable`, `weak`, `failed`, failure boundary, notes |

## Experimental Job Shape

A quality experiment should create one parent experiment folder:

```text
outputs/experiments/<experiment_id>/
  experiment.json
  baseline/
  variants/
    resolution-720p/
    bitrate-low/
    blur-moderate/
  summary.json
  summary.md
```

Every variant is a normal pipeline job. The experiment layer only generates variants, runs/resumes jobs and compares reports.

## Stop Conditions

Stop the experiment run if:

- the baseline fails
- framework/license validation fails
- input video rights are missing or unclear
- generated variants are not traceable to the baseline source
- a stage fails without writing enough evidence to classify the failure boundary

## Useful Results

The useful output is not just a yes/no answer. We want thresholds such as:

- minimum resolution where SfM still registers at least 70% of sampled frames
- minimum bitrate before compression artifacts dominate
- maximum motion speed before blur breaks camera solve
- shortest duration that still gives usable splats
- scene types that should be blocked or warned before reconstruction

## Relation To Capture Preflight

After enough experiments, convert the observed thresholds into `CapturePreflightReport` rules:

- `ready`: likely to run successfully
- `warning`: may work but quality risk is known
- `blocked`: expected to fail or produce unusable output

Preflight rules must be calibrated against experiment evidence, not guessed.
