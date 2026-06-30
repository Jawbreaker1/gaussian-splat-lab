# TUM RGB-D Sample Download

Verified: 2026-06-30

Purpose: find a stable RGB-D/kända-poser sample after Nerfstudio's Record3D `bear` Google Drive link returned 404.

## Result

TUM RGB-D `freiburg1_xyz` was downloaded and converted locally.

```text
Archive: data/datasets/tumrgbd/rgbd_dataset_freiburg1_xyz.tgz
Raw sequence: data/datasets/tumrgbd/rgbd_dataset_freiburg1_xyz
Converted dataset: data/datasets/tumrgbd/freiburg1_xyz_nerfstudio
```

The TUM RGB-D page states that unless otherwise noted, benchmark data is CC BY 4.0. This is usable as a technical validation sample with attribution; keep product/showcase usage under review.

## Commands

```bash
mkdir -p data/datasets/tumrgbd
curl -L https://cvg.cit.tum.de/rgbd/dataset/freiburg1/rgbd_dataset_freiburg1_xyz.tgz \
  -o data/datasets/tumrgbd/rgbd_dataset_freiburg1_xyz.tgz
tar -xzf data/datasets/tumrgbd/rgbd_dataset_freiburg1_xyz.tgz -C data/datasets/tumrgbd
python3 scripts/convert-tum-rgbd-to-nerfstudio.py \
  --input data/datasets/tumrgbd/rgbd_dataset_freiburg1_xyz \
  --output data/datasets/tumrgbd/freiburg1_xyz_nerfstudio \
  --max-frames 300
```

Conversion output:

```text
rgbRows: 798
depthRows: 798
poseRows: 3000
matchedFrames: 797
selectedFrames: 300
```

## Pipeline Check

A temporary manifest job passed:

```text
environment: pass
intake: warning
frame_sampling: pass
sfm: pass
splat_training: blocked_workload
```

The `intake` warning is expected because the source is an external dataset. `splat_training` was intentionally not run during this download check.
