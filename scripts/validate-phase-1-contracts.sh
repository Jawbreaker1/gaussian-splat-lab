#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
phase1_import_contract_dir="${repo_root}/data/tmp/phase-1-import-contract"
trap 'rm -rf "${phase1_import_contract_dir}"' EXIT

python3 -m json.tool "${repo_root}/data/manifests/captures.example.json" >/dev/null
python3 -m json.tool "${repo_root}/data/manifests/viewer-assets.example.json" >/dev/null
python3 -m py_compile "${repo_root}/scripts/lab-pipeline.py"

python3 "${repo_root}/scripts/lab-pipeline.py" describe >/dev/null
python3 "${repo_root}/scripts/lab-pipeline.py" list-captures   --capture-manifest data/manifests/captures.example.json   >/tmp/gaussian-splat-lab-phase-1-captures.txt
python3 -m json.tool /tmp/gaussian-splat-lab-phase-1-captures.txt >/dev/null
grep -q "pexels-empty-coffee-shop-interior-14227022" /tmp/gaussian-splat-lab-phase-1-captures.txt
python3 "${repo_root}/scripts/lab-pipeline.py" init-job   --capture-manifest data/manifests/captures.example.json   --capture-id static-room-orbit-001   --dry-run   >/dev/null

import_manifest="$(mktemp)"
import_source="$(mktemp)"
python3 - <<'PYCODE' "${import_manifest}" "${import_source}"
from pathlib import Path
import json
import sys
manifest_path = Path(sys.argv[1])
source_path = Path(sys.argv[2])
source_path.write_bytes(bytes([103, 97, 117, 115, 115, 105, 97, 110, 45, 115, 112, 108, 97, 116, 45, 108, 97, 98, 32, 105, 109, 112, 111, 114, 116, 32, 99, 111, 110, 116, 114, 97, 99, 116, 32, 102, 105, 120, 116, 117, 114, 101, 10]))
manifest = {
    "schemaVersion": 1,
    "captures": [
        {
            "id": "phase-1-import-contract",
            "displayName": "Phase 1 import contract",
            "source": {
                "kind": "local_file",
                "path": "data/tmp/phase-1-import-contract/imported.mp4",
                "sourceUrl": None,
                "license": "self-captured-test",
                "licenseNotes": "Synthetic contract fixture; not a real video.",
            },
            "capture": {
                "subject": "synthetic import contract fixture",
                "motion": "none",
                "expectedDurationSeconds": None,
                "expectedResolution": None,
            },
            "pipeline": {
                "frameSampling": {"targetFps": 1, "maxFrames": 1},
                "sfm": {"backend": "colmap"},
                "training": {"backend": "gsplat", "targetWorker": "windows-rtx-5090"},
                "packaging": {"preferredFormats": ["ply", "ksplat", "splat"]},
            },
            "status": "contract-fixture",
        }
    ],
}
manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
PYCODE
python3 "${repo_root}/scripts/lab-pipeline.py" import-video   --capture-manifest "${import_manifest}"   --capture-id phase-1-import-contract   --input "${import_source}"   --overwrite   >/tmp/gaussian-splat-lab-phase-1-import-video.txt
grep -q "import_video_status=pass" /tmp/gaussian-splat-lab-phase-1-import-video.txt
import_report="$(sed -n 's/^import_video_report=//p' /tmp/gaussian-splat-lab-phase-1-import-video.txt)"
python3 -m json.tool "${import_report}" >/dev/null

python3 "${repo_root}/scripts/lab-pipeline.py" import-video   --capture-manifest data/manifests/captures.example.json   --capture-id pexels-empty-coffee-shop-interior-14227022   --input "${import_source}"   --dry-run   >/tmp/gaussian-splat-lab-phase-1-import-warning.txt || true
grep -q "import_video_status=blocked_license" /tmp/gaussian-splat-lab-phase-1-import-warning.txt

tmp_jobs_dir="$(mktemp -d)"
python3 "${repo_root}/scripts/lab-pipeline.py" init-job   --capture-manifest data/manifests/captures.example.json   --capture-id static-room-orbit-001   --jobs-dir "${tmp_jobs_dir}"   >/tmp/gaussian-splat-lab-phase-1-contracts.txt

grep -q "job_manifest=" /tmp/gaussian-splat-lab-phase-1-contracts.txt
job_manifest="$(sed -n 's/^job_manifest=//p' /tmp/gaussian-splat-lab-phase-1-contracts.txt)"

python3 "${repo_root}/scripts/lab-pipeline.py" run-stage framework_license   --job "${job_manifest}"   >/tmp/gaussian-splat-lab-phase-1-framework-license.txt || true
grep -Eq "framework_license_status=(pass|warning|fail|setup_gap|blocked_license|blocked_workload)" /tmp/gaussian-splat-lab-phase-1-framework-license.txt
framework_license_report="$(sed -n 's/^framework_license_report=//p' /tmp/gaussian-splat-lab-phase-1-framework-license.txt)"
python3 -m json.tool "${framework_license_report}" >/dev/null

python3 "${repo_root}/scripts/lab-pipeline.py" run-stage environment   --job "${job_manifest}"   >/tmp/gaussian-splat-lab-phase-1-environment.txt

grep -Eq "environment_status=(pass|setup_gap)" /tmp/gaussian-splat-lab-phase-1-environment.txt

python3 "${repo_root}/scripts/lab-pipeline.py" run-stage intake   --job "${job_manifest}"   >/tmp/gaussian-splat-lab-phase-1-intake.txt || true

grep -Eq "intake_status=(pass|warning|fail|setup_gap)" /tmp/gaussian-splat-lab-phase-1-intake.txt
intake_report="$(sed -n 's/^intake_report=//p' /tmp/gaussian-splat-lab-phase-1-intake.txt)"
python3 -m json.tool "${intake_report}" >/dev/null

python3 "${repo_root}/scripts/lab-pipeline.py" run-stage frame_sampling   --job "${job_manifest}"   >/tmp/gaussian-splat-lab-phase-1-frame-sampling.txt || true

grep -Eq "frame_sampling_status=(pass|warning|fail|setup_gap|blocked_license|blocked_workload)" /tmp/gaussian-splat-lab-phase-1-frame-sampling.txt
frame_sampling_report="$(sed -n 's/^frame_sampling_report=//p' /tmp/gaussian-splat-lab-phase-1-frame-sampling.txt)"
python3 -m json.tool "${frame_sampling_report}" >/dev/null

python3 "${repo_root}/scripts/lab-pipeline.py" run-stage sfm   --job "${job_manifest}"   >/tmp/gaussian-splat-lab-phase-1-sfm.txt || true

grep -Eq "sfm_status=(pass|warning|fail|setup_gap|blocked_license|blocked_workload)" /tmp/gaussian-splat-lab-phase-1-sfm.txt
sfm_report="$(sed -n 's/^sfm_report=//p' /tmp/gaussian-splat-lab-phase-1-sfm.txt)"
python3 -m json.tool "${sfm_report}" >/dev/null

for stage in splat_training packaging viewer quality_report; do
  python3 "${repo_root}/scripts/lab-pipeline.py" run-stage "${stage}"   --job "${job_manifest}"   >/tmp/gaussian-splat-lab-phase-1-${stage}.txt || true
  grep -Eq "${stage}_status=(pass|warning|fail|setup_gap|blocked_license|blocked_workload)" /tmp/gaussian-splat-lab-phase-1-${stage}.txt
  stage_report="$(sed -n "s/^${stage}_report=//p" /tmp/gaussian-splat-lab-phase-1-${stage}.txt)"
  python3 -m json.tool "${stage_report}" >/dev/null
done

heavy_jobs_dir="$(mktemp -d)"
python3 "${repo_root}/scripts/lab-pipeline.py" init-job   --capture-manifest data/manifests/captures.example.json   --capture-id static-room-orbit-001   --jobs-dir "${heavy_jobs_dir}"   >/tmp/gaussian-splat-lab-phase-1-heavy-contracts.txt
heavy_job_manifest="$(sed -n 's/^job_manifest=//p' /tmp/gaussian-splat-lab-phase-1-heavy-contracts.txt)"
python3 - <<'PYCODE' "${heavy_job_manifest}"
from pathlib import Path
import json
import sys
job_path = Path(sys.argv[1])
reports = job_path.parent / "reports"
reports.mkdir(parents=True, exist_ok=True)
synthetic_reports = {
    "frame_sampling": {
        "schemaVersion": 1,
        "stage": {"id": "frame_sampling", "status": "pass"},
        "frameManifestPath": str(job_path.parent / "frames" / "synthetic" / "frame_manifest.json"),
    },
    "sfm": {
        "schemaVersion": 1,
        "stage": {"id": "sfm", "status": "pass"},
        "sparseModelPath": str(job_path.parent / "sfm" / "synthetic" / "sparse" / "0"),
    },
    "packaging": {
        "schemaVersion": 1,
        "stage": {"id": "packaging", "status": "pass"},
        "artifact": {"path": str(job_path.parent / "splats" / "synthetic.ksplat")},
    },
}
for name, report in synthetic_reports.items():
    (reports / f"{name}.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
job = json.loads(job_path.read_text(encoding="utf-8"))
for stage in job["stages"]:
    if stage["id"] in synthetic_reports:
        stage["status"] = "pass"
        stage["reportPath"] = f"reports/{stage['id']}.json"
job_path.write_text(json.dumps(job, indent=2) + "\n", encoding="utf-8")
PYCODE
python3 "${repo_root}/scripts/lab-pipeline.py" run-stage sfm   --job "${heavy_job_manifest}"   >/tmp/gaussian-splat-lab-phase-1-heavy-sfm.txt || true
grep -q "sfm_status=blocked_workload" /tmp/gaussian-splat-lab-phase-1-heavy-sfm.txt
python3 "${repo_root}/scripts/lab-pipeline.py" run-stage splat_training   --job "${heavy_job_manifest}"   >/tmp/gaussian-splat-lab-phase-1-heavy-training.txt || true
grep -q "splat_training_status=blocked_workload" /tmp/gaussian-splat-lab-phase-1-heavy-training.txt
python3 "${repo_root}/scripts/lab-pipeline.py" run-stage viewer   --job "${heavy_job_manifest}"   >/tmp/gaussian-splat-lab-phase-1-heavy-viewer.txt || true
grep -q "viewer_status=blocked_workload" /tmp/gaussian-splat-lab-phase-1-heavy-viewer.txt

echo "phase1_contract_validation=passed"
