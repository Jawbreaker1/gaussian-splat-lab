# Phase 1 SfM PSU Replacement Test

Verified: 2026-06-14

Purpose: first post-PSU heavier local reconstruction test on the Windows RTX 5090 workstation.

## Input

- Capture id: `static-room-orbit-001`
- Imported source: `/mnt/c/Users/engwa/Downloads/PXL_20250404_223054837.mp4`
- Lab target: `data/videos/static-room-orbit-001.mp4`
- Job: `/home/engwall/projects/gaussian-splat-lab/outputs/jobs/static-room-orbit-001-20260614T100535Z/job.json`
- Frame sampling: 2 fps, 60 frames

## Result

- SfM status: `pass`
- COLMAP matcher: `exhaustive_matcher`
- Selected sparse model: `/home/engwall/projects/gaussian-splat-lab/outputs/jobs/static-room-orbit-001-20260614T100535Z/sfm/20260614T114234Z/sparse/1`
- Registered images: `42` / 60
- Sparse points: `2423`
- Mean reprojection error: `0.758677` px
- Quality status after training gate: `setup_gap`
- First boundary: `splat_training` / `setup_gap`

## Notes

- PSU-related instability was not observed during this SfM run.
- Installed COLMAP reports without CUDA, so this run primarily exercised CPU/disk rather than sustained GPU load.
- `splat_training` is the next implementation boundary; the current stage reports `setup_gap` and does not launch training yet.
- SfM implementation was updated during this test to use a clean COLMAP image directory and to select the best sparse model when COLMAP emits multiple reconstructions.
