# COLMAP Binary Validation

Verified: 2026-06-21

Purpose: keep the working CPU COLMAP install as a known-good fallback while preparing for a side-by-side CUDA COLMAP build.

## CPU Fallback

Command:

```bash
python3 scripts/validate-colmap-binary.py --binary /usr/bin/colmap --json-out /tmp/gsl-colmap-cpu-validation.json
```

Result: pass.

Checks:

- `colmap --help`: pass
- CPU SIFT feature extraction on synthetic PNG frames: pass
- CPU SIFT exhaustive matching on the same synthetic frame set: pass

Resolved binary:

```text
/usr/bin/colmap
```

Version summary:

```text
COLMAP 3.9.1 -- Structure-from-Motion and Multi-View Stereo
(Commit Unknown on Unknown without CUDA)
```

## CUDA Candidate Rule

CUDA COLMAP builds must be installed side-by-side and validated before use:

```bash
python3 scripts/validate-colmap-binary.py \
  --binary "$(pwd)/outputs/tools/colmap-cuda/bin/colmap" \
  --allow-gpu \
  --qt-offscreen
```

Current result: pass.

Validated binary:

```text
outputs/tools/colmap-cuda/bin/colmap
COLMAP 4.0.4 -- Structure-from-Motion and Multi-View Stereo
(Commit 9c23f69 on 2026-04-27 with CUDA)
```

Checks:

- `colmap --help`: pass
- CPU SIFT feature extraction/matching: pass
- GPU SIFT feature extraction/matching: pass
- GPU SIFT feature extraction/matching without `QT_QPA_PLATFORM=offscreen`: pass

The validator supports both COLMAP 3.9's `SiftExtraction.*` / `SiftMatching.*` options and COLMAP 4.0's `FeatureExtraction.*` / `FeatureMatching.*` options.

Start UI or CLI jobs with:

```bash
GSL_COLMAP_BIN="$(pwd)/outputs/tools/colmap-cuda/bin/colmap"
```

Do not replace `/usr/bin/colmap`; it is the rollback path.

## Sidecar Build Script

The repo-local build helper is:

```bash
./scripts/build-colmap-cuda-sidecar.sh
```

It builds under `outputs/build/colmap-cuda/` and installs under `outputs/tools/colmap-cuda/`. Both paths are ignored by git and can be removed without touching the CPU fallback.
