# Phase 1 Frame Sampling Smoke

Verified: 2026-06-08

Purpose: validate the successful `intake` -> `frame_sampling` CLI path without requiring a real reconstruction capture.

This is a contract smoke only. The generated video is a synthetic FFmpeg test pattern and is not evidence of SfM or Gaussian Splat reconstruction quality.

## Temporary Inputs

- Video: `/tmp/gaussian-splat-lab-frame-sampling-fixture.mp4`
- Capture manifest: `/tmp/gaussian-splat-lab-frame-sampling-captures.json`
- Job: `/tmp/gaussian-splat-lab-frame-sampling-jobs/synthetic-frame-sampling-fixture-20260608T091145Z/job.json`

The temporary capture manifest used `license=generated-test-fixture` and documented that the file was generated locally for pipeline contract validation only.

## Commands

```bash
ffmpeg -hide_banner -loglevel error -y -f lavfi -i testsrc2=duration=12:size=1280x720:rate=30 -c:v mpeg4 -q:v 3 -pix_fmt yuv420p /tmp/gaussian-splat-lab-frame-sampling-fixture.mp4
.venv/bin/python scripts/lab-pipeline.py init-job --capture-manifest /tmp/gaussian-splat-lab-frame-sampling-captures.json --capture-id synthetic-frame-sampling-fixture --jobs-dir /tmp/gaussian-splat-lab-frame-sampling-jobs
.venv/bin/python scripts/lab-pipeline.py run-stage environment --job /tmp/gaussian-splat-lab-frame-sampling-jobs/synthetic-frame-sampling-fixture-20260608T091145Z/job.json
.venv/bin/python scripts/lab-pipeline.py run-stage intake --job /tmp/gaussian-splat-lab-frame-sampling-jobs/synthetic-frame-sampling-fixture-20260608T091145Z/job.json
.venv/bin/python scripts/lab-pipeline.py run-stage frame_sampling --job /tmp/gaussian-splat-lab-frame-sampling-jobs/synthetic-frame-sampling-fixture-20260608T091145Z/job.json
```

## Results

- `environment_status=pass`
- `intake_status=pass`
- `frame_sampling_status=pass`
- `FrameManifest` status: `pass`
- Actual frame count: `60`
- Contact sheet: `/tmp/gaussian-splat-lab-frame-sampling-jobs/synthetic-frame-sampling-fixture-20260608T091145Z/frames/20260608T091602Z/contact_sheet.jpg`
- Contact sheet metadata: `mjpeg`, `800x450`
- First frame SHA256: `7e19c42dbba36ea6e55ca160070aeff84e76401e320bf2617a02bee9299f76f3`
- Last frame SHA256: `b6949c158d02d1cb5c4dcca1b1018d517e26b7bf4dde77f489b845d1145b1f00`

## Current Real Capture Status

The repo placeholder capture still points at `data/videos/static-room-orbit-001.mp4`, which does not exist yet. For the real job, `intake` correctly reports `fail`, and `frame_sampling` correctly refuses to run on top of a failed upstream stage.
