#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

python3 -m json.tool "${repo_root}/data/manifests/captures.example.json" >/dev/null
python3 -m json.tool "${repo_root}/data/manifests/viewer-assets.example.json" >/dev/null
python3 -m py_compile "${repo_root}/scripts/lab-pipeline.py"

python3 "${repo_root}/scripts/lab-pipeline.py" describe >/dev/null
python3 "${repo_root}/scripts/lab-pipeline.py" init-job   --capture-manifest data/manifests/captures.example.json   --capture-id static-room-orbit-001   --dry-run   >/dev/null

tmp_jobs_dir="$(mktemp -d)"
python3 "${repo_root}/scripts/lab-pipeline.py" init-job   --capture-manifest data/manifests/captures.example.json   --capture-id static-room-orbit-001   --jobs-dir "${tmp_jobs_dir}"   >/tmp/gaussian-splat-lab-phase-1-contracts.txt

grep -q "job_manifest=" /tmp/gaussian-splat-lab-phase-1-contracts.txt
job_manifest="$(sed -n 's/^job_manifest=//p' /tmp/gaussian-splat-lab-phase-1-contracts.txt)"

python3 "${repo_root}/scripts/lab-pipeline.py" run-stage environment   --job "${job_manifest}"   >/tmp/gaussian-splat-lab-phase-1-environment.txt

grep -Eq "environment_status=(pass|setup_gap)" /tmp/gaussian-splat-lab-phase-1-environment.txt

python3 "${repo_root}/scripts/lab-pipeline.py" run-stage intake   --job "${job_manifest}"   >/tmp/gaussian-splat-lab-phase-1-intake.txt || true

grep -Eq "intake_status=(pass|warning|fail|setup_gap)" /tmp/gaussian-splat-lab-phase-1-intake.txt
intake_report="$(sed -n 's/^intake_report=//p' /tmp/gaussian-splat-lab-phase-1-intake.txt)"
python3 -m json.tool "${intake_report}" >/dev/null

python3 "${repo_root}/scripts/lab-pipeline.py" run-stage frame_sampling   --job "${job_manifest}"   >/tmp/gaussian-splat-lab-phase-1-frame-sampling.txt || true

grep -Eq "frame_sampling_status=(pass|warning|fail|setup_gap|blocked_license)" /tmp/gaussian-splat-lab-phase-1-frame-sampling.txt
frame_sampling_report="$(sed -n 's/^frame_sampling_report=//p' /tmp/gaussian-splat-lab-phase-1-frame-sampling.txt)"
python3 -m json.tool "${frame_sampling_report}" >/dev/null

python3 "${repo_root}/scripts/lab-pipeline.py" run-stage sfm   --job "${job_manifest}"   >/tmp/gaussian-splat-lab-phase-1-sfm.txt || true

grep -Eq "sfm_status=(pass|warning|fail|setup_gap|blocked_license)" /tmp/gaussian-splat-lab-phase-1-sfm.txt
sfm_report="$(sed -n 's/^sfm_report=//p' /tmp/gaussian-splat-lab-phase-1-sfm.txt)"
python3 -m json.tool "${sfm_report}" >/dev/null

echo "phase1_contract_validation=passed"
