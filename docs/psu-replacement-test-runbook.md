# PSU Replacement Test Runbook

Verified: 2026-06-08

Purpose: provide a controlled sequence for the first heavier local pipeline test after the workstation PSU is replaced.

This runbook separates preflight, light media stages and heavy stages. Do not skip the stop points; they are there to make failures diagnosable and to avoid sustained load surprises.

## Current Readiness

Ready to test after a local video has been imported:

- dependency/license preflight report
- RTX workstation/environment report
- video intake with `ffprobe`
- deterministic frame sampling with `ffmpeg`
- guarded COLMAP SfM wrapper
- quality report summarizing the first blocking boundary

Not yet implemented as real heavy work:

- splat training orchestration
- artifact packaging/conversion
- real browser splat viewer validation

The `splat_training` and `viewer` stages intentionally report guarded/setup states until those implementations are added.

## 0. Confirm Inputs

Use a self-captured clip for the cleanest commercial chain, or the documented Pexels candidate for technical validation only.

```bash
cd /home/engwall/projects/gaussian-splat-lab
.venv/bin/python scripts/lab-pipeline.py list-captures --capture-manifest data/manifests/captures.example.json
```

If the chosen file is not present, import it:

```bash
.venv/bin/python scripts/lab-pipeline.py import-video \
  --capture-id pexels-empty-coffee-shop-interior-14227022 \
  --input /path/to/downloaded-video.mp4 \
  --accept-warning \
  --overwrite
```

Stop if `list-captures` still shows `source_file=setup_gap` for the chosen capture.

## 1. Create A Job

```bash
.venv/bin/python scripts/lab-pipeline.py init-job \
  --capture-id pexels-empty-coffee-shop-interior-14227022
```

Copy the printed `job_manifest=` path into the commands below.

## 2. Run Preflight Checks

```bash
JOB=/home/engwall/projects/gaussian-splat-lab/outputs/jobs/<job_id>/job.json
.venv/bin/python scripts/lab-pipeline.py run-stage framework_license --job "$JOB"
.venv/bin/python scripts/lab-pipeline.py run-stage environment --job "$JOB"
```

Stop if dependency review fails or the environment reports missing critical tools.

## 3. Run Light Media Stages

```bash
.venv/bin/python scripts/lab-pipeline.py run-stage intake --job "$JOB"
.venv/bin/python scripts/lab-pipeline.py run-stage frame_sampling --job "$JOB" --accept-warning
.venv/bin/python scripts/lab-pipeline.py run-stage quality_report --job "$JOB"
```

Inspect the contact sheet before SfM:

```bash
python3 - <<'PY' "$JOB"
import json
import sys
from pathlib import Path
job = Path(sys.argv[1])
report = json.loads((job.parent / 'reports' / 'frame_sampling.json').read_text(encoding='utf-8'))
print(report.get('contactSheetPath'))
print(report.get('frameManifestPath'))
PY
```

Stop if the contact sheet shows motion blur, repeated frames, non-orbit motion, people/logos/private documents, or too little texture.

## 4. Heavy Stage: SfM Only

Run this only after the PSU replacement and an explicit go-ahead.

```bash
.venv/bin/python scripts/lab-pipeline.py run-stage sfm --job "$JOB" --allow-heavy
.venv/bin/python scripts/lab-pipeline.py run-stage quality_report --job "$JOB"
```

Stop after SfM. Record whether COLMAP registers enough frames. Treat 50-70% registered frames as a warning boundary that can be accepted for experimental continuation, not as a clean pass.

## 5. Expected Boundary After SfM

After SfM passes, the next expected boundary is `splat_training`:

```bash
.venv/bin/python scripts/lab-pipeline.py run-stage splat_training --job "$JOB" --allow-heavy
```

After the 2026-06-15 trainer update, this launches the minimal gsplat training wrapper only when `--allow-heavy` is supplied. In the current WSL environment it should still stop at `setup_gap` until `nvcc` or a compatible prebuilt gsplat wheel is available.

## Validation Commands

These are safe, light checks and should pass before any heavy test:

```bash
./scripts/validate-architecture-contracts.sh
./scripts/validate-phase-1-contracts.sh
./scripts/validate-ui-contracts.sh
```
