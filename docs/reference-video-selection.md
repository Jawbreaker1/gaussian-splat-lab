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

## Current Candidate

Manifest id: `pexels-empty-coffee-shop-interior-14227022`

Reason: this is closer to the intended product use than the hardware close-up. It is an empty interior candidate, likely to exercise room-scale structure and viewer navigation more realistically. The manifest records the Pexels source URL, license URL and terms URL. It is still a candidate, not production evidence, because the exact downloaded file and camera motion must be validated locally before SfM/training.

Stop conditions before using it as reference evidence:

- file must be imported locally through the UI or CLI import path
- intake must report duration, resolution, frame rate and hash
- sampled frames must show enough parallax and low blur
- SfM must register enough frames with acceptable reprojection error
- splat training must report RTX 5090 device use
- quality report must compare render review against the previous baseline

## Preferred Production Evidence

For commercial demonstrations, prefer self-captured footage from the actual target environment. That gives the clearest provenance and avoids stock-license ambiguity. The stock candidate is useful for pipeline development, but not a substitute for a controlled capture policy.
