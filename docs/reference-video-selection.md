# Reference Video Selection

Verified: 2026-06-17

The current local video `static-room-orbit-001.mp4` is only a technical baseline. It proves that intake, frame sampling, COLMAP, GPU training, packaging and viewer loading can connect end to end, but it is a poor quality reference for room-scale Gaussian Splat reconstruction because it is a close-up hardware scene with limited spatial extent, glossy surfaces and weak environment geometry.

## Target Reference

The next reference should be a room-scale or outdoor-space capture with:

- stable exposure and focus
- slow camera movement with clear parallax
- mostly static content
- textured walls, floor, furniture, ground or facade features
- enough overlap between neighboring frames
- no identifiable people unless releases and usage rights are recorded
- documented source rights compatible with commercial evaluation

## Preferred Technical Reference

Manifest id: `nerfstudio-dozer-reference`

Reason: use a purpose-built neural-rendering capture instead of a generic stock video. Nerfstudio exposes downloadable real-world captures through `ns-download-data nerfstudio --capture-name=dozer`, and the `dozer` scene is a better match for 3DGS validation because it should have real-world geometry, outdoor texture, strong parallax and no obvious reliance on a close-up glossy subject.

The pipeline now has a direct `nerfstudio_dataset` lane for datasets with `transforms.json`, so reference datasets no longer need to be flattened into video before training. A derived MP4 can still be useful when deliberately testing the ordinary video path, but it is a compatibility artifact. Keep the original downloaded image sequence, metadata and provenance as the source of truth.

License posture: technical validation only until the exact downloaded dataset license evidence is attached. The Nerfstudio paper states that associated code and data are publicly available with open-source licensing, and the Nerfstudio repository is Apache-2.0 licensed, but that is not enough by itself to call a specific downloaded capture commercially cleared. Record the downloaded archive, source page, command, hash and license evidence before using it in a commercial demo.

Stop conditions before using it as reference evidence:

- dataset must be downloaded through a documented command or manually imported with provenance
- derived MP4, if used, must be reproducible from the original image sequence
- intake must validate images, transforms and license posture for dataset input, or duration/resolution/frame-rate/hash for derived video input
- sampled or precomputed frames must show enough coverage and low blur
- SfM must register enough frames with acceptable reprojection error for video input, or explicitly skip with validated known poses for dataset input
- splat training must report RTX 5090 device use
- quality report must compare render review against the previous baseline

## Active Technical Fallback

Manifest id: `mipnerf360-flowers-reference`

Nerfstudio `dozer` remains preferred for a construction/outdoor-object reference, but Google Drive access was not available from the CLI environment during the 2026-06-17 run. The active tested fallback is Mip-NeRF 360 `flowers`, downloaded from the Google Research Cloud Storage archive `360_extra_scenes.zip`.

Run evidence from 2026-06-17:

- derived video: `data/videos/mipnerf360-flowers-reference.mp4`, 57.67 seconds, 1256x828, 173 frames at 3 fps
- source dataset: `data/datasets/mipnerf360/flowers/images_4`
- SfM: 173/173 frames registered, 43,287 sparse points, mean reprojection error 0.477 px
- training: `rtx_reference`, 9,000 iterations, 64 images, 400,000 gaussians, RTX 5090, 67.7 seconds
- artifact: `outputs/jobs/mipnerf360-flowers-reference-20260617T142004Z/splats/20260617T151122Z/trained_splats.ply`
- viewer: Spark mode reached `reference inspect`

Visual posture: this is a strong technical pipeline reference and a clear improvement over the close-up hardware clip. It is still not product-showcase quality because the current mini-trainer render is recognizable but soft in high-frequency grass, leaves and flower detail.

## Benchmark Cross-Check

Mip-NeRF 360 remains the strongest external benchmark family to compare against because it is designed around unbounded 360-degree view synthesis. Scenes such as `garden`, `bicycle` and `stump` are better quality targets than random internet videos. Use them as benchmark references only after the dataset license and source evidence are recorded. They are image-sequence datasets, not normal video clips, so they also argue for adding dataset/image-sequence input to this lab.

## Downgraded Stock Fallback

Manifest id: `pexels-empty-coffee-shop-interior-14227022`

This is now a fallback candidate, not the recommended reference. It can still help test the UI import flow and generic video handling, but it is less suitable for high-quality splats because stock footage is usually optimized for visual composition rather than multi-view reconstruction. It may have insufficient parallax, cuts, exposure shifts or motion that make SfM and training worse.

## Preferred Production Evidence

For commercial demonstrations, prefer self-captured footage from the actual target environment. That gives the clearest provenance and avoids stock-license ambiguity. The dataset candidate is useful for technical quality validation; self-capture is still the cleanest commercial chain of custody.
