#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
phase1_import_contract_dir="${repo_root}/data/tmp/phase-1-import-contract"
splatfacto_contract_jobs_dir="${repo_root}/data/tmp/phase-1-splatfacto-contract-jobs"
phase1_tmp_dir="$(mktemp -d)"
trap 'rm -rf "${phase1_import_contract_dir}" "${splatfacto_contract_jobs_dir}" "${phase1_tmp_dir}"' EXIT

python3 -m json.tool "${repo_root}/data/manifests/captures.example.json" >/dev/null
python3 -m json.tool "${repo_root}/data/manifests/viewer-assets.example.json" >/dev/null
python3 -m py_compile "${repo_root}/scripts/lab-pipeline.py"

python3 "${repo_root}/scripts/lab-pipeline.py" describe >/dev/null
python3 "${repo_root}/scripts/lab-pipeline.py" list-captures   --capture-manifest data/manifests/captures.example.json   >"${phase1_tmp_dir}"/captures.txt
python3 -m json.tool "${phase1_tmp_dir}"/captures.txt >/dev/null
grep -q "nerfstudio-dozer-reference" "${phase1_tmp_dir}"/captures.txt
grep -q "mipnerf360-flowers-reference" "${phase1_tmp_dir}"/captures.txt
grep -q "record3d-bear-reference" "${phase1_tmp_dir}"/captures.txt
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
python3 "${repo_root}/scripts/lab-pipeline.py" import-video   --capture-manifest "${import_manifest}"   --capture-id phase-1-import-contract   --input "${import_source}"   --overwrite   >"${phase1_tmp_dir}"/import-video.txt
grep -q "import_video_status=pass" "${phase1_tmp_dir}"/import-video.txt
import_report="$(sed -n 's/^import_video_report=//p' "${phase1_tmp_dir}"/import-video.txt)"
python3 -m json.tool "${import_report}" >/dev/null

python3 "${repo_root}/scripts/lab-pipeline.py" import-video   --capture-manifest data/manifests/captures.example.json   --capture-id nerfstudio-dozer-reference   --input "${import_source}"   --dry-run   >"${phase1_tmp_dir}"/import-warning.txt || true
grep -q "import_video_status=blocked_license" "${phase1_tmp_dir}"/import-warning.txt

tmp_jobs_dir="$(mktemp -d)"
python3 "${repo_root}/scripts/lab-pipeline.py" init-job   --capture-manifest data/manifests/captures.example.json   --capture-id static-room-orbit-001   --jobs-dir "${tmp_jobs_dir}"   >"${phase1_tmp_dir}"/contracts.txt

grep -q "job_manifest=" "${phase1_tmp_dir}"/contracts.txt
job_manifest="$(sed -n 's/^job_manifest=//p' "${phase1_tmp_dir}"/contracts.txt)"

python3 "${repo_root}/scripts/lab-pipeline.py" run-stage framework_license   --job "${job_manifest}"   >"${phase1_tmp_dir}"/framework-license.txt || true
grep -Eq "framework_license_status=(pass|warning|fail|setup_gap|blocked_license|blocked_workload)" "${phase1_tmp_dir}"/framework-license.txt
framework_license_report="$(sed -n 's/^framework_license_report=//p' "${phase1_tmp_dir}"/framework-license.txt)"
python3 -m json.tool "${framework_license_report}" >/dev/null

python3 "${repo_root}/scripts/lab-pipeline.py" run-stage environment   --job "${job_manifest}"   >"${phase1_tmp_dir}"/environment.txt

grep -Eq "environment_status=(pass|setup_gap)" "${phase1_tmp_dir}"/environment.txt

python3 "${repo_root}/scripts/lab-pipeline.py" run-stage intake   --job "${job_manifest}"   >"${phase1_tmp_dir}"/intake.txt || true

grep -Eq "intake_status=(pass|warning|fail|setup_gap)" "${phase1_tmp_dir}"/intake.txt
intake_report="$(sed -n 's/^intake_report=//p' "${phase1_tmp_dir}"/intake.txt)"
python3 -m json.tool "${intake_report}" >/dev/null

python3 "${repo_root}/scripts/lab-pipeline.py" run-stage frame_sampling   --job "${job_manifest}"   >"${phase1_tmp_dir}"/frame-sampling.txt || true

grep -Eq "frame_sampling_status=(pass|warning|fail|setup_gap|blocked_license|blocked_workload)" "${phase1_tmp_dir}"/frame-sampling.txt
frame_sampling_report="$(sed -n 's/^frame_sampling_report=//p' "${phase1_tmp_dir}"/frame-sampling.txt)"
python3 -m json.tool "${frame_sampling_report}" >/dev/null

python3 "${repo_root}/scripts/lab-pipeline.py" run-stage sfm   --job "${job_manifest}"   >"${phase1_tmp_dir}"/sfm.txt || true

grep -Eq "sfm_status=(pass|warning|fail|setup_gap|blocked_license|blocked_workload)" "${phase1_tmp_dir}"/sfm.txt
sfm_report="$(sed -n 's/^sfm_report=//p' "${phase1_tmp_dir}"/sfm.txt)"
python3 -m json.tool "${sfm_report}" >/dev/null

for stage in splat_training packaging viewer quality_report; do
  python3 "${repo_root}/scripts/lab-pipeline.py" run-stage "${stage}"   --job "${job_manifest}"   >"${phase1_tmp_dir}"/${stage}.txt || true
  grep -Eq "${stage}_status=(pass|warning|fail|setup_gap|blocked_license|blocked_workload)" "${phase1_tmp_dir}"/${stage}.txt
  stage_report="$(sed -n "s/^${stage}_report=//p" "${phase1_tmp_dir}"/${stage}.txt)"
  python3 -m json.tool "${stage_report}" >/dev/null
done

heavy_jobs_dir="$(mktemp -d)"
python3 "${repo_root}/scripts/lab-pipeline.py" init-job   --capture-manifest data/manifests/captures.example.json   --capture-id static-room-orbit-001   --jobs-dir "${heavy_jobs_dir}"   >"${phase1_tmp_dir}"/heavy-contracts.txt
heavy_job_manifest="$(sed -n 's/^job_manifest=//p' "${phase1_tmp_dir}"/heavy-contracts.txt)"
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
python3 "${repo_root}/scripts/lab-pipeline.py" run-stage sfm   --job "${heavy_job_manifest}"   >"${phase1_tmp_dir}"/heavy-sfm.txt || true
grep -q "sfm_status=blocked_workload" "${phase1_tmp_dir}"/heavy-sfm.txt
python3 "${repo_root}/scripts/lab-pipeline.py" run-stage splat_training   --job "${heavy_job_manifest}"   >"${phase1_tmp_dir}"/heavy-training.txt || true
grep -q "splat_training_status=blocked_workload" "${phase1_tmp_dir}"/heavy-training.txt
python3 "${repo_root}/scripts/lab-pipeline.py" run-stage viewer   --job "${heavy_job_manifest}"   >"${phase1_tmp_dir}"/heavy-viewer.txt || true
grep -q "viewer_status=blocked_workload" "${phase1_tmp_dir}"/heavy-viewer.txt

if [[ -x "${repo_root}/.venv-nerfstudio-py312/bin/ns-process-data" ]]; then
  record3d_dir="${phase1_tmp_dir}/record3d-fixture"
  record3d_manifest="${phase1_tmp_dir}/record3d-captures.json"
  record3d_jobs_dir="${phase1_tmp_dir}/record3d-jobs"
  python3 - <<'PYCODE' "${record3d_dir}" "${record3d_manifest}"
from pathlib import Path
import json
import struct
import sys
import zlib

root = Path(sys.argv[1])
manifest_path = Path(sys.argv[2])
rgb = root / "rgb"
rgb.mkdir(parents=True, exist_ok=True)

def write_png(path: Path, width: int, height: int, color: tuple[int, int, int]) -> None:
    rows = []
    for y in range(height):
        row = bytearray([0])
        for x in range(width):
            accent = 90 if 8 < x < width - 8 and 8 < y < height - 8 else 0
            row.extend(((color[0] + accent) % 256, color[1], color[2]))
        rows.append(bytes(row))
    raw = b"".join(rows)
    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )

poses = []
for index in range(4):
    write_png(rgb / f"{index}.png", 96, 72, (40 + index * 30, 90, 140))
    poses.append([0.0, 0.0, 0.0, 1.0, index * 0.05, 0.0, 0.0])

(root / "metadata.json").write_text(
    json.dumps(
        {
            "K": [80.0, 0.0, 48.0, 0.0, 80.0, 36.0, 0.0, 0.0, 1.0],
            "h": 72,
            "w": 96,
            "poses": poses,
        },
        indent=2,
    )
    + "\n",
    encoding="utf-8",
)
manifest = {
    "schemaVersion": 1,
    "captures": [
        {
            "id": "record3d-contract-fixture",
            "displayName": "Record3D contract fixture",
            "input": {"kind": "rgbd_capture_bundle", "format": "record3d", "path": str(root)},
            "source": {"kind": "local_dataset", "path": str(root), "license": "generated-test-fixture"},
            "capture": {"subject": "synthetic Record3D contract fixture", "motion": "tiny pose sequence"},
            "pipeline": {
                "frameSampling": {"backend": "record3d_to_nerfstudio_transforms", "maxFrames": 4},
                "record3d": {"numDownscales": 1, "maxDatasetSize": 4, "timeoutSeconds": 300},
                "sfm": {"backend": "record3d_transforms", "requiresExplicitHeavyApproval": False},
                "training": {"backend": "nerfstudio_splatfacto", "profile": "splatfacto_preview"},
                "packaging": {"preferredFormats": ["ply", "viewer-manifest"]},
            },
        }
    ],
}
manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
PYCODE
  python3 "${repo_root}/scripts/lab-pipeline.py" list-captures   --capture-manifest "${record3d_manifest}"   >"${phase1_tmp_dir}"/record3d-list.txt
  grep -q '"status": "pass"' "${phase1_tmp_dir}"/record3d-list.txt
  python3 "${repo_root}/scripts/lab-pipeline.py" init-job   --capture-manifest "${record3d_manifest}"   --capture-id record3d-contract-fixture   --jobs-dir "${record3d_jobs_dir}"   >"${phase1_tmp_dir}"/record3d-init.txt
  record3d_job_manifest="$(sed -n 's/^job_manifest=//p' "${phase1_tmp_dir}"/record3d-init.txt)"
  python3 - <<'PYCODE' "${record3d_job_manifest}"
from pathlib import Path
import json
import sys

job_path = Path(sys.argv[1])
job = json.loads(job_path.read_text(encoding="utf-8"))
for stage in job["stages"]:
    if stage["id"] == "environment":
        stage["status"] = "pass"
        stage["reportPath"] = "reports/environment.json"
job_path.write_text(json.dumps(job, indent=2) + "\n", encoding="utf-8")
PYCODE
  python3 "${repo_root}/scripts/lab-pipeline.py" run-stage intake   --job "${record3d_job_manifest}"   >"${phase1_tmp_dir}"/record3d-intake.txt
  grep -q "intake_status=pass" "${phase1_tmp_dir}"/record3d-intake.txt
  python3 "${repo_root}/scripts/lab-pipeline.py" run-stage frame_sampling   --job "${record3d_job_manifest}"   >"${phase1_tmp_dir}"/record3d-frame-sampling.txt
  grep -q "frame_sampling_status=pass" "${phase1_tmp_dir}"/record3d-frame-sampling.txt
  python3 "${repo_root}/scripts/lab-pipeline.py" run-stage sfm   --job "${record3d_job_manifest}"   >"${phase1_tmp_dir}"/record3d-sfm.txt
  grep -q "sfm_status=pass" "${phase1_tmp_dir}"/record3d-sfm.txt
fi

python3 "${repo_root}/scripts/lab-pipeline.py" init-job   --capture-manifest data/manifests/captures.example.json   --capture-id static-room-orbit-001   --jobs-dir "${splatfacto_contract_jobs_dir}"   >"${phase1_tmp_dir}"/splatfacto-contracts.txt
splatfacto_job_manifest="$(sed -n 's/^job_manifest=//p' "${phase1_tmp_dir}"/splatfacto-contracts.txt)"
python3 - <<'PYCODE' "${splatfacto_job_manifest}"
from pathlib import Path
import json
import struct
import sys

job_path = Path(sys.argv[1])
job_dir = job_path.parent
training_dir = job_dir / "splats" / "splatfacto-contract"
colmap_dir = training_dir / "colmap_txt"
reports_dir = job_dir / "reports"
reports_dir.mkdir(parents=True, exist_ok=True)
colmap_dir.mkdir(parents=True, exist_ok=True)

artifact = training_dir / "splatfacto-contract.ply"
header = "\n".join(
    [
        "ply",
        "format binary_little_endian 1.0",
        "element vertex 1200",
        "property float x",
        "property float y",
        "property float z",
        "property float opacity",
        "property float scale_0",
        "property float scale_1",
        "property float scale_2",
        "end_header",
    ]
) + "\n"
with artifact.open("wb") as handle:
    handle.write(header.encode("ascii"))
    for index in range(1200):
        if index >= 1190:
            x, y, z = 80.0 + index, 80.0 + index, 80.0 + index
            opacity = -6.0
            scale = -0.2
        else:
            x = (index % 17) / 16
            y = ((index // 17) % 17) / 16
            z = ((index // 289) % 5) / 4
            opacity = 5.0
            scale = -5.0
        handle.write(struct.pack("<7f", x, y, z, opacity, scale, scale, scale))

(colmap_dir / "cameras.txt").write_text(
    "1 SIMPLE_RADIAL 1600 900 900 800 450 0\n",
    encoding="utf-8",
)
(colmap_dir / "images.txt").write_text(
    "1 1 0 0 0 -2 -4 -6 1 frame_000001.jpg\n",
    encoding="utf-8",
)

report = {
    "schemaVersion": 1,
    "stage": {"id": "splat_training", "status": "pass"},
    "trainingDirectory": str(training_dir),
    "exportedArtifactPath": str(artifact),
    "splatArtifactPath": str(artifact),
    "metrics": {
        "backend": "nerfstudio_splatfacto",
        "profile": "splatfacto_reference",
        "method": "splatfacto",
        "iterations": 30000,
        "imagesUsed": 1,
        "selectedImages": [{"imageId": 1, "name": "frame_000001.jpg"}],
        "gaussianCount": 1200,
        "coordinateTransform": {
            "source": "nerfstudio_dataparser",
            "path": str(training_dir / "dataparser_transforms.json"),
            "matrix": [
                [1, 0, 0, 1],
                [0, 1, 0, 2],
                [0, 0, 1, 3],
            ],
            "scale": 0.5,
        },
    },
}
(reports_dir / "splat_training.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
PYCODE
python3 "${repo_root}/scripts/lab-pipeline.py" run-stage packaging   --job "${splatfacto_job_manifest}"   >"${phase1_tmp_dir}"/splatfacto-packaging.txt
grep -q "packaging_status=pass" "${phase1_tmp_dir}"/splatfacto-packaging.txt
splatfacto_packaging_report="$(sed -n 's/^packaging_report=//p' "${phase1_tmp_dir}"/splatfacto-packaging.txt)"
python3 - <<'PYCODE' "${splatfacto_packaging_report}"
from pathlib import Path
import json
import sys

packaging_report = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
manifest_path = Path(packaging_report["viewerManifestPath"])
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
assert manifest["artifact"]["viewerOptimized"] is True
assert manifest["artifact"]["path"].endswith(".viewer.ply")
assert manifest["originalArtifact"]["path"].endswith("splatfacto-contract.ply")
assert manifest["viewerFilter"]["removedVertexCount"] > 0
assert manifest["viewerFilter"]["vertexCount"] < manifest["viewerFilter"]["originalVertexCount"]
assert manifest["cameraViewSource"]["coordinateSpace"] == "nerfstudio_dataparser"
first_view = manifest["cameraViews"][0]
assert first_view["coordinateSpace"] == "nerfstudio_dataparser"
assert first_view["position"] == [1.5, 3.0, 4.5]
assert manifest["export"]["primaryAssetRepoRelativePath"].endswith("splatfacto-contract.ply")
assert manifest["export"]["viewerAssetRepoRelativePath"].endswith("splatfacto-contract.viewer.ply")
PYCODE

echo "phase1_contract_validation=passed"
