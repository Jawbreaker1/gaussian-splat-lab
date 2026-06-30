# ARKitScenes Sample Download

Verified: 2026-06-30

Purpose: find a public iPhone/LiDAR-style sample with RGB, depth, confidence, intrinsics and camera poses after Nerfstudio's Record3D `bear` archive was unavailable.

## Result

Apple ARKitScenes raw video `42444511` was downloaded and converted locally.

```text
Raw sequence: data/datasets/arkitscenes/raw/Training/42444511
Lowres converted dataset: data/datasets/arkitscenes/42444511_nerfstudio
Active VGA converted dataset: data/datasets/arkitscenes/42444511_vga_nerfstudio
```

The Apple license text was stored locally during validation and is linked from the manifest. Treat this as technical validation only until the commercial terms are reviewed for the intended product use.

## Commands

```bash
mkdir -p data/datasets/arkitscenes/raw/Training/42444511
for f in vga_wide.zip vga_wide_intrinsics.zip lowres_depth.zip lowres_wide.traj confidence.zip; do
  curl -L --fail \
    https://docs-assets.developer.apple.com/ml-research/datasets/arkitscenes/v1/raw/Training/42444511/$f \
    -o data/datasets/arkitscenes/raw/Training/42444511/$f
done
python3 scripts/convert-arkitscenes-to-nerfstudio.py \
  --input data/datasets/arkitscenes/raw/Training/42444511 \
  --output data/datasets/arkitscenes/42444511_vga_nerfstudio \
  --video-id 42444511 \
  --image-stream vga_wide \
  --max-frames 600
```

Conversion output for the active VGA dataset:

```text
imageRows: 1583
depthRows: 3165
intrinsicsRows: 1583
confidenceRows: 3165
trajectoryRows: 522
matchedFrames: 1566
selectedFrames: 600
```

## Pipeline Check

The active VGA manifest job passed through the full pipeline:

```text
framework_license: warning
environment: pass
intake: warning
frame_sampling: pass
sfm: pass
splat_training: pass
packaging: pass
viewer: pass
quality_report: warning
```

The warning status is expected because the input is an external Apple dataset with review-required commercial terms.

Best current run:

```text
Job: outputs/jobs/arkitscenes-42444511-reference-20260630T215434Z/job.json
Profile: splatfacto_reference
Iterations: 30000
Images: 600
Training wall time: 342.639 seconds
Training gaussians: 895241
Packaged splats: 790806
PLY size: 222021361 bytes
PSNR: 16.3391
SSIM: 0.6355
LPIPS: 0.6044
```

Visual assessment: usable as a proof that ARKit known-pose input reaches gallery and produces an aligned scene. It is not a showcase-quality scene. The source is a close floor/poster capture with limited geometry, so it validates the lane more than the final visual ceiling.
