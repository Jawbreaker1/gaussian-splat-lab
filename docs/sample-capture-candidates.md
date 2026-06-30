# Sample Capture Candidates

Verified: 2026-06-17

The preferred reference input for commercial evaluation is still self-captured footage: 20-40 seconds, slow orbit, static textured scene, no people, no logos, no recognizable third-party artwork and no private documents. That gives the cleanest chain of custody.

For technical quality work, prefer a capture/dataset built for neural rendering over ordinary stock footage. Stock videos often look good to humans while being weak SfM inputs.

## Preferred Technical Candidate: Nerfstudio Dozer

- Capture id: `nerfstudio-dozer-reference`
- Source docs: https://docs.nerf.studio/reference/cli/ns_download_data.html
- Source command: `ns-download-data nerfstudio --capture-name=dozer`
- Local dataset target: `data/datasets/nerfstudio/dozer`
- Derived video target, if needed for video regression only: `data/videos/nerfstudio-dozer-reference.mp4`
- Intended use: high-quality local technical validation only until exact dataset license evidence is attached.

Why it is the preferred technical candidate:

- It comes from a real-world neural-rendering dataset rather than a generic stock clip.
- The scene should be static, textured and outdoor, which is closer to the eventual room/outdoor use case than the hardware close-up.
- A dataset image sequence gives us camera transforms and image provenance without first flattening the source into a compressed stock-style MP4.
- It is a better stress test for the Spark/Three.js splat viewer because the resulting scene should be recognizable from many camera angles.

License posture:

- The Nerfstudio paper states that associated code and data are publicly available with open-source licensing.
- The Nerfstudio repository license is Apache-2.0, but that alone does not prove the exact downloaded capture is commercially cleared.
- Treat this as technical-validation-only until the downloaded dataset archive, license evidence, source command and hashes are stored with the capture.

Manual next step when ready:

1. Download the `dozer` capture through Nerfstudio tooling or a documented manual equivalent.
2. Store the original image sequence and metadata under `data/datasets/nerfstudio/dozer`.
3. Prefer the direct `nerfstudio_dataset` lane when `transforms.json` is present.
4. Derive `data/videos/nerfstudio-dozer-reference.mp4` only when deliberately testing the plain-video regression path.
5. Run preflight plus `intake` and `frame_sampling`; inspect dataset frames before any heavy training run.

Readiness check:

```bash
.venv/bin/python scripts/lab-pipeline.py list-captures --capture-manifest data/manifests/captures.example.json
```

Initial job command after the derived MP4 exists:

```bash
.venv/bin/python scripts/lab-pipeline.py init-job \
  --capture-manifest data/manifests/captures.example.json \
  --capture-id nerfstudio-dozer-reference
```

Known-pose dataset smoke/reference command after `poster` has been downloaded:

```bash
.venv/bin/python scripts/lab-pipeline.py init-job \
  --capture-manifest data/manifests/captures.example.json \
  --capture-id nerfstudio-poster-known-pose-reference
```

## RGB-D / iPhone LiDAR Candidate: Record3D Bear

- Capture id: `record3d-bear-reference`
- Source docs: https://docs.nerf.studio/reference/cli/ns_download_data.html
- Source command: `ns-download-data record3d --capture-name bear`
- Local dataset target: `data/datasets/record3d/bear`
- Intended use: technical validation of the `rgbd_capture_bundle` lane only until exact dataset license evidence is attached.

The current implementation expects a Record3D-style folder with:

```text
<capture>/
  metadata.json
  rgb/
    0.jpg
    1.jpg
    ...
```

The pipeline validates `rgb/`, `metadata.json`, camera poses, intrinsics and image size. It then runs `ns-process-data record3d`, producing a Nerfstudio `transforms.json` dataset used by Splatfacto. Optional depth maps are counted and reported, but not yet used by training.

2026-06-30 note:

- The Nerfstudio `record3d bear` CLI download failed through `gdown`/Google Drive public-link resolution on this workstation.
- Keep the manifest entry as a setup-gap reference until the archive is downloaded manually or a reliable official mirror is found.

For self-capture, use an iPhone or iPad with LiDAR and export Record3D data in the folder layout above. Avoid shiny/transparent scenes, fast motion, people, private documents and large blank walls for the first tests.

## iPhone / LiDAR Known-Pose Reference: ARKitScenes 42444511

- Capture id: `arkitscenes-42444511-reference`
- Source repo: https://github.com/apple/ARKitScenes
- Source assets: https://docs-assets.developer.apple.com/ml-research/datasets/arkitscenes/v1/raw/Training/42444511
- Raw local target: `data/datasets/arkitscenes/raw/Training/42444511`
- Converted dataset target: `data/datasets/arkitscenes/42444511_vga_nerfstudio`
- License posture: Apple-commercial-terms-review-required.
- Intended use: iPhone/LiDAR-style technical validation, not commercial showcase material without review.

This is the best current public sample for the structured iPhone/LiDAR path. It is not a Record3D export, but it has the pieces we care about: RGB frames, depth maps, confidence maps, per-frame intrinsics and ARKit camera trajectory. The repo converts it to Nerfstudio `transforms.json`, so the normal known-pose pipeline can skip COLMAP and train Splatfacto directly.

The first low-resolution pass used `lowres_wide` at `256x192`. It proved the poses were usable, but the render was too soft. The active manifest now uses `vga_wide` at `640x480`, which is still compact enough for quick lab runs while giving much better visual evidence.

Download and convert the active VGA sample:

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

2026-06-30 validation notes:

- Selected candidate `42444511` because it is Training split, has laser-scanner provenance, is in the upsampling set and has 3DOD metadata.
- Minimal lowres assets were about `289 MB`; `vga_wide` plus intrinsics added about `518 MB`.
- VGA conversion matched `1566` of `1583` RGB/intrinsics frames against depth and trajectory, then selected `600` frames.
- `splatfacto_preview` passed end to end in gallery with about `57k` packaged splats and SSIM around `0.686`.
- `splatfacto_reference` passed end to end in gallery with `790806` packaged splats, about `222 MB` PLY and SSIM `0.635`; visually it was clearly sharper than preview despite the lower SSIM.
- The result proves the ARKit known-pose lane, but it is not a visual ceiling sample. The scene is mostly a flat floor/poster close-up, so it is useful for mechanics, not for impressing users.

## RGB-D / Known-Pose Fallback: TUM Freiburg1 XYZ

- Capture id: `tumrgbd-freiburg1-xyz-reference`
- Source page: https://cvg.cit.tum.de/data/datasets/rgbd-dataset
- Source archive: https://cvg.cit.tum.de/rgbd/dataset/freiburg1/rgbd_dataset_freiburg1_xyz.tgz
- Local archive: `data/datasets/tumrgbd/rgbd_dataset_freiburg1_xyz.tgz`
- Converted dataset target: `data/datasets/tumrgbd/freiburg1_xyz_nerfstudio`
- License: CC BY 4.0 unless otherwise noted by TUM RGB-D.
- Intended use: stable technical RGB-D/kamera-pose validation sample.

This is not an iPhone/Record3D capture, but it is a real RGB-D sequence with RGB images, depth maps and ground-truth camera poses. It is much smaller and more reliable to download than WildRGB-D categories, and it gives us a concrete sample for the known-pose/depth side of the pipeline while the Nerfstudio Record3D `bear` Google Drive link is unavailable.

Download and convert:

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

2026-06-30 validation notes:

- Archive download succeeded; size was about `428 MB`.
- Unpacked raw sequence was about `461 MB`.
- Raw sequence contains `798` RGB frames, `798` depth maps and `3000` pose rows.
- Conversion matched `797` RGB/depth/pose rows and selected `300` frames.
- Pipeline validation passed through `frame_sampling` and `sfm`; `splat_training` correctly stopped at `blocked_workload` without `--allow-heavy`.

## Benchmark Cross-Check: Mip-NeRF 360

- Source page: https://jonbarron.info/mipnerf360/
- Useful scenes: `flowers`, `treehill`, `garden`, `bicycle`, `stump`
- Active tested capture id: `mipnerf360-flowers-reference`
- Active tested archive: `data/datasets/mipnerf360/360_extra_scenes.zip`
- Active derived video: `data/videos/mipnerf360-flowers-reference.mp4`
- Intended use: benchmark comparison only until dataset license evidence is recorded.

Mip-NeRF 360 is highly relevant because it targets 360-degree view synthesis around real scenes. It is not a normal video source, so it should be used once the pipeline supports image-sequence/dataset input or when we intentionally derive a video for compatibility testing.

2026-06-17 validation notes:

- Nerfstudio `dozer` Google Drive download was blocked from CLI automation.
- Mip-NeRF 360 `360_extra_scenes.zip` was downloaded from Google Cloud Storage instead.
- `flowers/images_4` was converted into a 3 fps MP4 to exercise the product's video-first pipeline.
- The run passed frame sampling, SfM, `rtx_reference` training, packaging and Spark viewer validation.
- The resulting splat is recognizable but soft; use it as a baseline for trainer/viewer improvement, not as commercial showcase material.

## Stock Fallback: Pexels Empty Coffee Shop Interior

- Capture id: `pexels-empty-coffee-shop-interior-14227022`
- Source page: https://www.pexels.com/video/an-empty-coffee-shop-interior-14227022/
- License page: https://www.pexels.com/license/
- Terms page: https://www.pexels.com/terms-of-service/
- Local target path: `data/videos/pexels-empty-coffee-shop-interior-14227022.mp4`
- Intended use: UI import and generic video validation only, not high-quality reference generation.

Keep this as a fallback, not the main reference path. It is closer to the intended domain than the CPU-fan clip, but a stock video is not necessarily captured with enough overlap, parallax or reconstruction-friendly motion.
