#!/usr/bin/env python3
"""Small manifest-driven skeleton for the Gaussian Splat lab pipeline."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import math
import json
import platform
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


HEAVY_STAGES = {"sfm", "splat_training", "viewer"}


STAGES = [
    {
        "id": "framework_license",
        "label": "Framework and license gate",
        "reads": "FrameworkEvaluation",
        "writes": "FrameworkDecisionReport",
    },
    {
        "id": "environment",
        "label": "RTX workstation environment",
        "reads": "MachineRuntime",
        "writes": "EnvironmentReport",
    },
    {
        "id": "intake",
        "label": "Video intake",
        "reads": "CaptureInput",
        "writes": "CaptureMetadata",
    },
    {
        "id": "frame_sampling",
        "label": "Frame sampling",
        "reads": "CaptureMetadata",
        "writes": "FrameManifest",
    },
    {
        "id": "sfm",
        "label": "SfM camera solve",
        "reads": "FrameManifest",
        "writes": "CameraSolveReport",
    },
    {
        "id": "splat_training",
        "label": "Splat training",
        "reads": "CameraSolveReport",
        "writes": "TrainingRunReport",
    },
    {
        "id": "packaging",
        "label": "Artifact packaging",
        "reads": "TrainingRunReport",
        "writes": "SplatArtifact",
    },
    {
        "id": "viewer",
        "label": "Viewer validation",
        "reads": "SplatArtifact",
        "writes": "ViewerValidationReport",
    },
    {
        "id": "quality_report",
        "label": "Quality report",
        "reads": "StageReports",
        "writes": "CaptureQualityReport",
    },
]


@dataclass(frozen=True)
class CaptureSelection:
    manifest_path: Path
    capture: dict[str, Any]


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2)
        handle.write("\n")


def select_capture(manifest_path: Path, capture_id: str) -> CaptureSelection:
    manifest = read_json(manifest_path)
    captures = manifest.get("captures")
    if not isinstance(captures, list):
        raise ValueError(f"{manifest_path} must contain a captures array")

    for capture in captures:
        if isinstance(capture, dict) and capture.get("id") == capture_id:
            return CaptureSelection(manifest_path=manifest_path, capture=capture)

    available = sorted(
        capture.get("id", "<missing-id>")
        for capture in captures
        if isinstance(capture, dict)
    )
    raise ValueError(f"capture id {capture_id!r} not found; available: {available}")


def build_job(selection: CaptureSelection, repo_root: Path) -> dict[str, Any]:
    capture = selection.capture
    capture_id = str(capture["id"])
    now = datetime.now(timezone.utc).replace(microsecond=0)
    created_at = now.isoformat()
    job_id = f"{capture_id}-{now.strftime('%Y%m%dT%H%M%SZ')}"

    return {
        "schemaVersion": 1,
        "job": {
            "id": job_id,
            "createdAt": created_at,
            "repoRoot": str(repo_root),
            "captureManifest": str(selection.manifest_path),
            "captureId": capture_id,
            "status": "planned",
        },
        "capture": capture,
        "stages": [
            {
                "id": stage["id"],
                "label": stage["label"],
                "status": "pending",
                "reads": stage["reads"],
                "writes": stage["writes"],
                "workload": "heavy" if stage["id"] in HEAVY_STAGES else "normal",
                "reportPath": f"reports/{stage['id']}.json",
            }
            for stage in STAGES
        ],
    }


def repo_root_from_script() -> Path:
    return Path(__file__).resolve().parents[1]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def run_command(command: list[str], timeout_seconds: int = 20) -> dict[str, Any]:
    executable = shutil.which(command[0])
    if executable is None:
        return {
            "name": command[0],
            "command": command,
            "status": "setup_gap",
            "exitCode": None,
            "stdout": "",
            "stderr": f"{command[0]} not found on PATH",
        }

    try:
        result = subprocess.run(
            command,
            cwd=repo_root_from_script(),
            capture_output=True,
            check=False,
            text=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "name": command[0],
            "command": command,
            "status": "fail",
            "exitCode": None,
            "stdout": exc.stdout or "",
            "stderr": f"command timed out after {timeout_seconds}s",
        }

    return {
        "name": command[0],
        "command": command,
        "status": "pass" if result.returncode == 0 else "fail",
        "exitCode": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }


def command_summary(command_result: dict[str, Any], max_lines: int = 8) -> str:
    text = command_result.get("stdout") or command_result.get("stderr") or ""
    lines = [line for line in str(text).splitlines() if line.strip()]
    return "\n".join(lines[:max_lines])


def check_torch_cuda() -> dict[str, Any]:
    if importlib.util.find_spec("torch") is None:
        return {
            "status": "setup_gap",
            "package": "torch",
            "message": "PyTorch is not installed in this Python environment.",
            "installNeeded": True,
        }

    try:
        import torch  # type: ignore[import-not-found]

        cuda_available = bool(torch.cuda.is_available())
        result: dict[str, Any] = {
            "status": "pass" if cuda_available else "setup_gap",
            "package": "torch",
            "version": getattr(torch, "__version__", None),
            "cudaAvailable": cuda_available,
            "torchCudaVersion": getattr(torch.version, "cuda", None),
            "deviceCount": int(torch.cuda.device_count()) if cuda_available else 0,
            "installNeeded": False,
        }
        if cuda_available:
            device_index = torch.cuda.current_device()
            tensor = torch.tensor([1.0, 2.0], device="cuda") * 2
            result.update(
                {
                    "deviceName": torch.cuda.get_device_name(device_index),
                    "tensorSmoke": [float(value) for value in tensor.cpu().tolist()],
                }
            )
        else:
            result["message"] = "PyTorch is installed, but CUDA is not available."
        return result
    except Exception as exc:  # noqa: BLE001 - environment boundary should report exact failure
        return {
            "status": "fail",
            "package": "torch",
            "message": str(exc),
            "installNeeded": False,
        }


def check_python_import(module_name: str) -> dict[str, Any]:
    if importlib.util.find_spec(module_name) is None:
        return {
            "status": "setup_gap",
            "package": module_name,
            "message": f"{module_name} is not installed in this Python environment.",
            "installNeeded": True,
        }

    try:
        module = __import__(module_name)
        return {
            "status": "pass",
            "package": module_name,
            "version": getattr(module, "__version__", None),
            "installNeeded": False,
        }
    except Exception as exc:  # noqa: BLE001 - environment boundary should report exact failure
        return {
            "status": "fail",
            "package": module_name,
            "message": str(exc),
            "installNeeded": False,
        }


def report_status(checks: list[dict[str, Any]]) -> str:
    statuses = [check.get("status") for check in checks]
    if any(status == "fail" for status in statuses):
        return "fail"
    if any(status == "setup_gap" for status in statuses):
        return "setup_gap"
    return "pass"


def parse_fraction(value: str | None) -> float | None:
    if not value or value == "0/0":
        return None
    if "/" not in value:
        try:
            return float(value)
        except ValueError:
            return None
    numerator, denominator = value.split("/", 1)
    try:
        denominator_value = float(denominator)
        if denominator_value == 0:
            return None
        return float(numerator) / denominator_value
    except ValueError:
        return None


def stage_report_path(job_path: Path, stage_id: str) -> Path:
    return job_path.parent / "reports" / f"{stage_id}.json"


def stage_status_from_job(job: dict[str, Any], stage_id: str) -> str | None:
    for stage in job.get("stages", []):
        if isinstance(stage, dict) and stage.get("id") == stage_id:
            return stage.get("status")
    return None


def capture_video_path(job: dict[str, Any], repo_root: Path) -> Path:
    source = job.get("capture", {}).get("source", {})
    raw_path = source.get("path")
    if not isinstance(raw_path, str) or not raw_path:
        raise ValueError("capture source.path is required")
    video_path = Path(raw_path)
    if not video_path.is_absolute():
        video_path = repo_root / video_path
    return video_path


def capture_source_path(capture: dict[str, Any], repo_root: Path) -> Path | None:
    source = capture.get("source", {}) if isinstance(capture.get("source"), dict) else {}
    raw_path = source.get("path")
    if not isinstance(raw_path, str) or not raw_path:
        return None
    path = Path(raw_path)
    if not path.is_absolute():
        path = repo_root / path
    return path


def classify_capture_license(source: dict[str, Any]) -> tuple[str, str, str]:
    license_value = str(source.get("license") or "").strip()
    source_url = source.get("sourceUrl")
    if not license_value:
        return "fail", "missing license", "blocked_license"
    if license_value in {"unknown", "placeholder"}:
        return "fail", f"license is {license_value}", "blocked_license"
    if license_value == "local-test-only":
        return "warning", "local test only; replace before product evidence", "technical_validation_only"
    if license_value == "pexels-license":
        verified_at = source.get("licenseVerifiedAt")
        if verified_at:
            return (
                "warning",
                f"Pexels candidate; license/terms verified {verified_at}; avoid commercial showcase use without review",
                "technical_validation_only",
            )
        return "warning", "Pexels candidate; verify current terms and avoid commercial showcase use without review", "technical_validation_only"
    if source_url:
        return "warning", "external source; keep license evidence with the capture", "needs_review_before_showcase"
    return "pass", "license/provenance recorded", "candidate_for_golden_path"


def capture_readiness(capture: dict[str, Any], repo_root: Path) -> dict[str, Any]:
    source = capture.get("source", {}) if isinstance(capture.get("source"), dict) else {}
    source_path = capture_source_path(capture, repo_root)
    license_status, license_summary, commercial_posture = classify_capture_license(source)
    file_exists = bool(source_path and source_path.exists())
    file_status = "pass" if file_exists else "setup_gap"
    checks = [
        {
            "id": "source_file",
            "status": file_status,
            "summary": "source file exists" if file_exists else "source file is not present locally",
            "path": str(source_path) if source_path else None,
            "sizeBytes": source_path.stat().st_size if file_exists and source_path else None,
        },
        {
            "id": "source_license",
            "status": license_status,
            "summary": license_summary,
            "license": source.get("license"),
            "sourceUrl": source.get("sourceUrl"),
            "licenseSourceUrl": source.get("licenseSourceUrl"),
            "termsUrl": source.get("termsUrl"),
            "licenseVerifiedAt": source.get("licenseVerifiedAt"),
        },
    ]
    statuses = [check["status"] for check in checks]
    if any(status == "fail" for status in statuses):
        status = "fail"
    elif any(status == "setup_gap" for status in statuses):
        status = "setup_gap"
    elif any(status == "warning" for status in statuses):
        status = "warning"
    else:
        status = "pass"
    return {
        "id": capture.get("id"),
        "displayName": capture.get("displayName"),
        "status": status,
        "commercialPosture": commercial_posture,
        "sourcePath": str(source_path) if source_path else None,
        "sourceUrl": source.get("sourceUrl"),
        "checks": checks,
    }


def capture_readiness_report(manifest_path: Path, repo_root: Path) -> dict[str, Any]:
    manifest = read_json(manifest_path)
    captures = manifest.get("captures")
    if not isinstance(captures, list):
        raise ValueError(f"{manifest_path} must contain a captures array")
    return {
        "schemaVersion": 1,
        "manifestPath": str(manifest_path),
        "generatedAt": utc_now(),
        "captures": [
            capture_readiness(capture, repo_root)
            for capture in captures
            if isinstance(capture, dict)
        ],
    }


def stage_definition(stage_id: str) -> dict[str, str]:
    for stage in STAGES:
        if stage["id"] == stage_id:
            return stage
    return {"id": stage_id, "label": stage_id, "reads": "Unknown", "writes": "Unknown"}


def derive_job_status(stages: list[dict[str, Any]]) -> str:
    statuses = [stage.get("status") for stage in stages if isinstance(stage, dict)]
    if any(status == "blocked_license" for status in statuses):
        return "blocked_license"
    if any(status == "blocked_workload" for status in statuses):
        return "blocked_workload"
    if any(status == "fail" for status in statuses):
        return "fail"
    if any(status == "setup_gap" for status in statuses):
        return "setup_gap"
    if statuses and all(status in {"pass", "warning"} for status in statuses):
        return "complete"
    return "planned"


def update_job_stage(job_path: Path, stage_id: str, status: str, report_path: Path) -> None:
    job = read_json(job_path)
    rel_report = report_path.relative_to(job_path.parent).as_posix()
    for stage in job.get("stages", []):
        if isinstance(stage, dict) and stage.get("id") == stage_id:
            stage["status"] = status
            stage["reportPath"] = rel_report
            break
    else:
        definition = stage_definition(stage_id)
        job.setdefault("stages", []).append(
            {
                "id": stage_id,
                "label": definition["label"],
                "status": status,
                "reads": definition["reads"],
                "writes": definition["writes"],
                "reportPath": rel_report,
            }
        )
    job["job"]["status"] = derive_job_status(job.get("stages", []))
    write_json(job_path, job)


def build_framework_license_report(job_path: Path) -> dict[str, Any]:
    repo_root = repo_root_from_script()
    frameworks_path = repo_root / "data/manifests/framework-evaluation.json"
    frameworks_manifest = read_json(frameworks_path)
    frameworks = frameworks_manifest.get("frameworks", [])
    checks: list[dict[str, Any]] = []
    if not isinstance(frameworks, list) or not frameworks:
        status = "fail"
        checks.append(
            {
                "id": "framework_manifest",
                "status": "fail",
                "summary": "framework evaluation manifest has no frameworks",
            }
        )
        frameworks = []
    else:
        checks.append(
            {
                "id": "framework_manifest",
                "status": "pass",
                "summary": "framework evaluation manifest loaded",
                "path": str(frameworks_path),
            }
        )

    invalid = []
    decision_counts: dict[str, int] = {}
    for item in frameworks:
        if not isinstance(item, dict):
            invalid.append("framework entry is not an object")
            continue
        decision = item.get("decision")
        decision_counts[str(decision)] = decision_counts.get(str(decision), 0) + 1
        if decision in {"preferred", "accepted"} and item.get("commercialUse") in {"blocked", "blocked_by_policy"}:
            invalid.append(f"{item.get('id')} is accepted/preferred but commercially blocked")
        if decision in {"preferred", "accepted", "conditional"} and not item.get("officialSources"):
            invalid.append(f"{item.get('id')} is missing official source URLs")

    blocked_items = [item.get("id") for item in frameworks if isinstance(item, dict) and item.get("decision") == "blocked"]
    conditional_items = [item.get("id") for item in frameworks if isinstance(item, dict) and item.get("decision") == "conditional"]
    checks.append(
        {
            "id": "blocked_dependencies",
            "status": "pass",
            "summary": f"{len(blocked_items)} blocked decisions are documented",
            "blocked": blocked_items,
        }
    )
    checks.append(
        {
            "id": "conditional_dependencies",
            "status": "warning" if conditional_items else "pass",
            "summary": f"{len(conditional_items)} conditional decisions require review before product packaging",
            "conditional": conditional_items,
        }
    )
    if invalid:
        checks.append(
            {
                "id": "commercial_consistency",
                "status": "fail",
                "summary": "; ".join(invalid),
                "messages": invalid,
            }
        )
        status = "fail"
    elif conditional_items:
        status = "warning"
    else:
        status = "pass"

    return {
        "schemaVersion": 1,
        "stage": {
            "id": "framework_license",
            "status": status,
            "generatedAt": utc_now(),
            "jobPath": str(job_path),
        },
        "frameworkManifestPath": str(frameworks_path),
        "decisionCounts": decision_counts,
        "checks": checks,
    }


def build_environment_report(job_path: Path) -> dict[str, Any]:
    nvidia_query = run_command(
        [
            "nvidia-smi",
            "--query-gpu=name,driver_version,memory.total",
            "--format=csv,noheader",
        ]
    )
    if nvidia_query["status"] == "fail":
        nvidia_query = run_command(["nvidia-smi"])

    colmap = run_command(["colmap", "--help"], timeout_seconds=10)
    ffmpeg = run_command(["ffmpeg", "-version"], timeout_seconds=10)
    ffprobe = run_command(["ffprobe", "-version"], timeout_seconds=10)
    torch_cuda = check_torch_cuda()
    gsplat = check_python_import("gsplat")

    checks = [
        {
            "id": "nvidia_smi",
            "status": nvidia_query["status"],
            "summary": command_summary(nvidia_query),
            "details": nvidia_query,
        },
        {
            "id": "python",
            "status": "pass",
            "summary": sys.version.split()[0],
            "details": {
                "executable": sys.executable,
                "version": sys.version,
                "platform": platform.platform(),
                "uname": platform.uname()._asdict(),
            },
        },
        {
            "id": "pytorch_cuda",
            "status": torch_cuda["status"],
            "summary": torch_cuda.get("deviceName") or torch_cuda.get("message") or torch_cuda.get("version"),
            "details": torch_cuda,
        },
        {
            "id": "colmap",
            "status": "setup_gap" if colmap["status"] == "setup_gap" else colmap["status"],
            "summary": command_summary(colmap, max_lines=4),
            "details": colmap,
        },
        {
            "id": "ffmpeg",
            "status": "setup_gap" if ffmpeg["status"] == "setup_gap" else ffmpeg["status"],
            "summary": command_summary(ffmpeg, max_lines=1),
            "details": ffmpeg,
            "commercialPolicy": "conditional_external_tool_only; do not bundle or redistribute until build flags are reviewed",
        },
        {
            "id": "ffprobe",
            "status": "setup_gap" if ffprobe["status"] == "setup_gap" else ffprobe["status"],
            "summary": command_summary(ffprobe, max_lines=1),
            "details": ffprobe,
            "commercialPolicy": "conditional_external_tool_only; do not bundle or redistribute until build flags are reviewed",
        },
        {
            "id": "gsplat",
            "status": gsplat["status"],
            "summary": gsplat.get("version") or gsplat.get("message"),
            "details": gsplat,
        },
    ]
    status = report_status(checks)
    return {
        "schemaVersion": 1,
        "stage": {
            "id": "environment",
            "status": status,
            "generatedAt": utc_now(),
            "jobPath": str(job_path),
        },
        "policy": {
            "installsPerformed": [],
            "installPolicy": "This stage only detects environment state. Missing tools are reported as setup_gap and must be installed through the installation ledger.",
        },
        "checks": checks,
    }


def ffprobe_metadata(video_path: Path) -> dict[str, Any]:
    ffprobe = run_command(["ffprobe", "-version"], timeout_seconds=10)
    if ffprobe["status"] == "setup_gap":
        return {
            "status": "setup_gap",
            "ffprobe": ffprobe,
            "message": "ffprobe not found on PATH",
        }
    if ffprobe["status"] != "pass":
        return {
            "status": "fail",
            "ffprobe": ffprobe,
            "message": "ffprobe -version failed",
        }

    probe = run_command(
        [
            "ffprobe",
            "-v",
            "error",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            str(video_path),
        ],
        timeout_seconds=60,
    )
    if probe["status"] != "pass":
        return {
            "status": probe["status"],
            "ffprobe": ffprobe,
            "probe": probe,
            "message": "ffprobe metadata extraction failed",
        }

    try:
        metadata = json.loads(probe["stdout"])
    except json.JSONDecodeError as exc:
        return {
            "status": "fail",
            "ffprobe": ffprobe,
            "probe": probe,
            "message": f"ffprobe returned invalid JSON: {exc}",
        }

    return {
        "status": "pass",
        "ffprobe": ffprobe,
        "probe": probe,
        "metadata": metadata,
    }


def summarize_video_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    streams = metadata.get("streams", [])
    video_stream = next(
        (stream for stream in streams if isinstance(stream, dict) and stream.get("codec_type") == "video"),
        None,
    )
    audio_streams = [stream for stream in streams if isinstance(stream, dict) and stream.get("codec_type") == "audio"]
    fmt = metadata.get("format", {}) if isinstance(metadata.get("format"), dict) else {}
    if video_stream is None:
        return {"hasVideo": False}

    duration_raw = fmt.get("duration") or video_stream.get("duration")
    bitrate_raw = fmt.get("bit_rate") or video_stream.get("bit_rate")
    fps = parse_fraction(video_stream.get("avg_frame_rate") or video_stream.get("r_frame_rate"))

    def as_float(value: Any) -> float | None:
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def as_int(value: Any) -> int | None:
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    return {
        "hasVideo": True,
        "container": fmt.get("format_name"),
        "durationSeconds": as_float(duration_raw),
        "bitRate": as_int(bitrate_raw),
        "sizeBytes": as_int(fmt.get("size")),
        "video": {
            "codec": video_stream.get("codec_name"),
            "width": as_int(video_stream.get("width")),
            "height": as_int(video_stream.get("height")),
            "fps": fps,
            "pixelFormat": video_stream.get("pix_fmt"),
            "nbFrames": as_int(video_stream.get("nb_frames")),
        },
        "audioStreamCount": len(audio_streams),
        "streamCount": len(streams),
    }


def validate_intake_summary(summary: dict[str, Any], source: dict[str, Any]) -> tuple[str, list[str]]:
    issues: list[str] = []
    warnings: list[str] = []
    if not summary.get("hasVideo"):
        return "fail", ["no video stream found"]

    license_value = source.get("license")
    if not license_value:
        issues.append("capture source license is missing")
    elif license_value in {"local-test-only", "unknown", "placeholder"}:
        warnings.append(f"capture source license is {license_value}; not product-ready")

    duration = summary.get("durationSeconds")
    if duration is None:
        warnings.append("duration is unknown")
    elif duration < 10:
        warnings.append("duration is below initial MVP threshold of 10 seconds")
    elif duration > 120:
        warnings.append("duration is above initial MVP threshold of 120 seconds")

    video = summary.get("video", {}) if isinstance(summary.get("video"), dict) else {}
    height = video.get("height")
    if height is None:
        warnings.append("video height is unknown")
    elif height < 720:
        warnings.append("video height is below initial MVP threshold of 720p")

    fps = video.get("fps")
    if fps is None:
        warnings.append("frame rate is unknown")
    elif fps < 10:
        warnings.append("frame rate is below initial MVP threshold of 10 fps")

    if issues:
        return "fail", issues + warnings
    if warnings:
        return "warning", warnings
    return "pass", []


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def frame_sampling_settings(job: dict[str, Any]) -> tuple[float, int]:
    settings = job.get("capture", {}).get("pipeline", {}).get("frameSampling", {})
    target_fps = settings.get("targetFps", 2)
    max_frames = settings.get("maxFrames", 180)
    try:
        target_fps_value = float(target_fps)
        max_frames_value = int(max_frames)
    except (TypeError, ValueError) as exc:
        raise ValueError("frameSampling.targetFps and frameSampling.maxFrames must be numeric") from exc
    if target_fps_value <= 0:
        raise ValueError("frameSampling.targetFps must be greater than zero")
    if max_frames_value <= 0:
        raise ValueError("frameSampling.maxFrames must be greater than zero")
    return target_fps_value, max_frames_value


def format_fps(value: float) -> str:
    if value.is_integer():
        return str(int(value))
    return f"{value:.6f}".rstrip("0").rstrip(".")


def frame_run_directory(job_path: Path) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return job_path.parent / "frames" / stamp


def build_frame_manifest(
    job_path: Path,
    intake_report: dict[str, Any],
    frame_dir: Path,
    contact_sheet_path: Path,
    target_fps: float,
    max_frames: int,
) -> dict[str, Any]:
    frames = sorted(frame_dir.glob("frame_*.jpg"))
    frame_entries = []
    for index, frame_path in enumerate(frames):
        frame_entries.append(
            {
                "index": index,
                "path": str(frame_path),
                "timestampSeconds": round(index / target_fps, 6),
                "sizeBytes": frame_path.stat().st_size,
                "sha256": file_sha256(frame_path),
            }
        )

    metadata = intake_report.get("metadata", {}) if isinstance(intake_report.get("metadata"), dict) else {}
    return {
        "schemaVersion": 1,
        "stage": {
            "id": "frame_sampling",
            "status": "pending",
            "generatedAt": utc_now(),
            "jobPath": str(job_path),
        },
        "source": {
            "intakeReportPath": str(stage_report_path(job_path, "intake")),
            "videoPath": intake_report.get("videoPath"),
            "durationSeconds": metadata.get("durationSeconds"),
            "sourceFps": (metadata.get("video") or {}).get("fps") if isinstance(metadata.get("video"), dict) else None,
        },
        "sampling": {
            "targetFps": target_fps,
            "maxFrames": max_frames,
            "actualFrameCount": len(frame_entries),
        },
        "frameDirectory": str(frame_dir),
        "contactSheetPath": str(contact_sheet_path),
        "frames": frame_entries,
    }


def validate_frame_manifest(frame_manifest: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    frames = frame_manifest.get("frames", [])
    checks: list[dict[str, Any]] = []
    if not isinstance(frames, list) or not frames:
        return "fail", [
            {
                "id": "frame_count",
                "status": "fail",
                "summary": "no frames were extracted",
            }
        ]

    missing = [frame for frame in frames if not Path(str(frame.get("path"))).exists()]
    checks.append(
        {
            "id": "frame_files",
            "status": "pass" if not missing else "fail",
            "summary": "all sampled frame files exist" if not missing else f"{len(missing)} sampled frame files are missing",
        }
    )

    timestamps = [frame.get("timestampSeconds") for frame in frames]
    monotonic = all(
        isinstance(current, (int, float)) and isinstance(previous, (int, float)) and current > previous
        for previous, current in zip(timestamps, timestamps[1:])
    ) or len(timestamps) == 1
    checks.append(
        {
            "id": "monotonic_timestamps",
            "status": "pass" if monotonic else "fail",
            "summary": "planned frame timestamps are monotonic" if monotonic else "planned frame timestamps are not monotonic",
        }
    )

    frame_count = len(frames)
    count_status = "pass"
    count_summary = "frame count is inside initial MVP threshold"
    if frame_count < 50:
        count_status = "warning"
        count_summary = "frame count is below initial MVP threshold of 50"
    elif frame_count > 250:
        count_status = "warning"
        count_summary = "frame count is above initial MVP threshold of 250"
    checks.append(
        {
            "id": "frame_count",
            "status": count_status,
            "summary": count_summary,
            "actualFrameCount": frame_count,
        }
    )

    contact_sheet = Path(str(frame_manifest.get("contactSheetPath", "")))
    checks.append(
        {
            "id": "contact_sheet",
            "status": "pass" if contact_sheet.exists() and contact_sheet.stat().st_size > 0 else "fail",
            "summary": "contact sheet generated" if contact_sheet.exists() and contact_sheet.stat().st_size > 0 else "contact sheet missing",
            "path": str(contact_sheet),
        }
    )

    statuses = [check["status"] for check in checks]
    if any(status == "fail" for status in statuses):
        return "fail", checks
    if any(status == "warning" for status in statuses):
        return "warning", checks
    return "pass", checks


def build_frame_sampling_report(job_path: Path, accept_warning: bool = False) -> dict[str, Any]:
    job = read_json(job_path)
    intake_path = stage_report_path(job_path, "intake")
    base = {
        "schemaVersion": 1,
        "stage": {
            "id": "frame_sampling",
            "status": "pending",
            "generatedAt": utc_now(),
            "jobPath": str(job_path),
        },
        "checks": [],
        "acceptedUpstreamWarnings": accept_warning,
    }

    if not intake_path.exists():
        base["stage"]["status"] = "setup_gap"
        base["checks"].append(
            {
                "id": "intake_required",
                "status": "setup_gap",
                "summary": "intake report is missing; run intake before frame_sampling",
            }
        )
        return base

    intake_report = read_json(intake_path)
    intake_status = intake_report.get("stage", {}).get("status")
    if intake_status == "warning" and not accept_warning:
        base["stage"]["status"] = "blocked_license"
        base["checks"].append(
            {
                "id": "intake_warning_acceptance",
                "status": "blocked_license",
                "summary": "intake warning must be explicitly accepted with --accept-warning before sampling frames",
            }
        )
        return base
    if intake_status not in {"pass", "warning"}:
        base["stage"]["status"] = "setup_gap" if intake_status in {None, "pending", "setup_gap"} else "fail"
        base["checks"].append(
            {
                "id": "intake_required",
                "status": base["stage"]["status"],
                "summary": f"intake must pass before frame_sampling; current status is {intake_status}",
            }
        )
        return base

    try:
        target_fps, max_frames = frame_sampling_settings(job)
    except ValueError as exc:
        base["stage"]["status"] = "fail"
        base["checks"].append({"id": "sampling_plan", "status": "fail", "summary": str(exc)})
        return base

    video_path_raw = intake_report.get("videoPath")
    video_path = Path(str(video_path_raw)) if video_path_raw else capture_video_path(job, repo_root_from_script())
    if not video_path.exists():
        base["stage"]["status"] = "fail"
        base["checks"].append(
            {
                "id": "video_file",
                "status": "fail",
                "summary": "source video file no longer exists",
                "path": str(video_path),
            }
        )
        return base

    ffmpeg = run_command(["ffmpeg", "-version"], timeout_seconds=10)
    if ffmpeg["status"] != "pass":
        base["stage"]["status"] = ffmpeg["status"]
        base["checks"].append(
            {
                "id": "ffmpeg",
                "status": ffmpeg["status"],
                "summary": command_summary(ffmpeg, max_lines=1) or "ffmpeg is not available",
                "details": ffmpeg,
            }
        )
        return base

    frame_dir = frame_run_directory(job_path)
    frame_dir.mkdir(parents=True, exist_ok=True)
    output_pattern = frame_dir / "frame_%06d.jpg"
    fps_filter = f"fps={format_fps(target_fps)}"
    extract = run_command(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(video_path),
            "-vf",
            fps_filter,
            "-frames:v",
            str(max_frames),
            "-q:v",
            "2",
            str(output_pattern),
        ],
        timeout_seconds=600,
    )
    base["ffmpeg"] = {
        "versionSummary": command_summary(ffmpeg, max_lines=1),
        "configuration": ffmpeg.get("stdout", ""),
        "commercialPolicy": "conditional_external_tool_only; do not bundle or redistribute until build flags are reviewed",
    }
    base["commands"] = {"extractFrames": extract}
    if extract["status"] != "pass":
        base["stage"]["status"] = extract["status"]
        base["checks"].append(
            {
                "id": "ffmpeg_extract",
                "status": extract["status"],
                "summary": command_summary(extract, max_lines=4) or "ffmpeg frame extraction failed",
                "details": extract,
            }
        )
        return base

    contact_sheet_path = frame_dir / "contact_sheet.jpg"
    contact_sheet = run_command(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-pattern_type",
            "glob",
            "-i",
            str(frame_dir / "frame_*.jpg"),
            "-vf",
            "scale=160:-1,tile=5x5",
            "-frames:v",
            "1",
            str(contact_sheet_path),
        ],
        timeout_seconds=120,
    )
    base["commands"]["contactSheet"] = contact_sheet

    frame_manifest = build_frame_manifest(job_path, intake_report, frame_dir, contact_sheet_path, target_fps, max_frames)
    status, checks = validate_frame_manifest(frame_manifest)
    frame_manifest["stage"]["status"] = status
    frame_manifest_path = frame_dir / "frame_manifest.json"
    write_json(frame_manifest_path, frame_manifest)

    base["stage"]["status"] = status
    base["frameManifestPath"] = str(frame_manifest_path)
    base["frameDirectory"] = str(frame_dir)
    base["contactSheetPath"] = str(contact_sheet_path)
    base["sampling"] = frame_manifest["sampling"]
    base["checks"].append(
        {
            "id": "ffmpeg_extract",
            "status": "pass",
            "summary": "frames extracted",
        }
    )
    base["checks"].extend(checks)
    return base


def sfm_run_directory(job_path: Path) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return job_path.parent / "sfm" / stamp


def parse_colmap_model_analyzer(output: str) -> dict[str, Any]:
    metrics: dict[str, Any] = {}
    for line in output.splitlines():
        if ":" not in line:
            continue
        key, raw_value = line.split(":", 1)
        normalized = re.sub(r"[^a-z0-9]+", "_", key.strip().lower()).strip("_")
        value = raw_value.strip()
        match = re.search(r"-?\d+(?:\.\d+)?", value)
        if match:
            number = float(match.group(0))
            metrics[normalized] = int(number) if number.is_integer() else number
        else:
            metrics[normalized] = value
    return metrics


def first_metric(metrics: dict[str, Any], names: list[str]) -> Any:
    for name in names:
        if name in metrics:
            return metrics[name]
    return None


def validate_sfm_output(
    frame_count: int,
    sparse_model_path: Path | None,
    analyzer: dict[str, Any] | None,
) -> tuple[str, list[dict[str, Any]]]:
    checks: list[dict[str, Any]] = []
    if sparse_model_path is None or not sparse_model_path.exists():
        return "fail", [
            {
                "id": "sparse_model",
                "status": "fail",
                "summary": "COLMAP did not produce a sparse model",
            }
        ]

    checks.append(
        {
            "id": "sparse_model",
            "status": "pass",
            "summary": "sparse model directory exists",
            "path": str(sparse_model_path),
        }
    )

    metrics = analyzer or {}
    registered_images = first_metric(metrics, ["registered_images", "images"])
    points = first_metric(metrics, ["points", "points3d", "points_3d"])
    reprojection_error = first_metric(
        metrics,
        ["mean_reprojection_error", "mean_reprojection_error_px", "reprojection_error"],
    )

    if isinstance(registered_images, int) and frame_count > 0:
        registered_fraction = registered_images / frame_count
        checks.append(
            {
                "id": "registered_frames",
                "status": "pass" if registered_fraction >= 0.70 else "fail",
                "summary": f"{registered_images}/{frame_count} frames registered",
                "registeredImages": registered_images,
                "frameCount": frame_count,
                "registeredFraction": round(registered_fraction, 4),
            }
        )
    else:
        checks.append(
            {
                "id": "registered_frames",
                "status": "warning",
                "summary": "registered image count was not parsed from COLMAP output",
            }
        )

    if isinstance(points, int):
        checks.append(
            {
                "id": "sparse_points",
                "status": "pass" if points > 0 else "fail",
                "summary": f"{points} sparse points",
                "sparsePoints": points,
            }
        )
    else:
        checks.append(
            {
                "id": "sparse_points",
                "status": "warning",
                "summary": "sparse point count was not parsed from COLMAP output",
            }
        )

    checks.append(
        {
            "id": "reprojection_error",
            "status": "pass" if isinstance(reprojection_error, (int, float)) else "warning",
            "summary": "reprojection error recorded" if isinstance(reprojection_error, (int, float)) else "reprojection error was not parsed",
            "meanReprojectionError": reprojection_error,
        }
    )

    statuses = [check["status"] for check in checks]
    if any(status == "fail" for status in statuses):
        return "fail", checks
    if any(status == "warning" for status in statuses):
        return "warning", checks
    return "pass", checks


def build_sfm_report(job_path: Path, accept_warning: bool = False, allow_heavy: bool = False) -> dict[str, Any]:
    frame_sampling_path = stage_report_path(job_path, "frame_sampling")
    base = {
        "schemaVersion": 1,
        "stage": {
            "id": "sfm",
            "status": "pending",
            "generatedAt": utc_now(),
            "jobPath": str(job_path),
        },
        "checks": [],
        "acceptedUpstreamWarnings": accept_warning,
    }

    if not frame_sampling_path.exists():
        base["stage"]["status"] = "setup_gap"
        base["checks"].append(
            {
                "id": "frame_sampling_required",
                "status": "setup_gap",
                "summary": "frame_sampling report is missing; run frame_sampling before sfm",
            }
        )
        return base

    frame_sampling_report = read_json(frame_sampling_path)
    frame_sampling_status = frame_sampling_report.get("stage", {}).get("status")
    if frame_sampling_status == "warning" and not accept_warning:
        base["stage"]["status"] = "fail"
        base["checks"].append(
            {
                "id": "frame_sampling_warning_acceptance",
                "status": "fail",
                "summary": "frame_sampling warning must be explicitly accepted with --accept-warning before SfM",
            }
        )
        return base
    if frame_sampling_status not in {"pass", "warning"}:
        base["stage"]["status"] = "setup_gap" if frame_sampling_status in {None, "pending", "setup_gap"} else "fail"
        base["checks"].append(
            {
                "id": "frame_sampling_required",
                "status": base["stage"]["status"],
                "summary": f"frame_sampling must pass before sfm; current status is {frame_sampling_status}",
            }
        )
        return base

    if not allow_heavy:
        base["stage"]["status"] = "blocked_workload"
        base["checks"].append(
            {
                "id": "heavy_workload_ack_required",
                "status": "blocked_workload",
                "summary": "SfM can be CPU/GPU intensive; rerun with --allow-heavy only after confirming the workstation can take sustained load.",
            }
        )
        base["workload"] = {
            "classification": "heavy",
            "requiresExplicitApproval": True,
            "approvalFlag": "--allow-heavy",
            "reason": "COLMAP feature extraction, matching and mapping can sustain high CPU load.",
        }
        return base

    frame_manifest_path_raw = frame_sampling_report.get("frameManifestPath")
    if not isinstance(frame_manifest_path_raw, str) or not frame_manifest_path_raw:
        base["stage"]["status"] = "fail"
        base["checks"].append(
            {
                "id": "frame_manifest",
                "status": "fail",
                "summary": "frame_sampling report does not declare frameManifestPath",
            }
        )
        return base

    frame_manifest_path = Path(frame_manifest_path_raw)
    if not frame_manifest_path.exists():
        base["stage"]["status"] = "fail"
        base["checks"].append(
            {
                "id": "frame_manifest",
                "status": "fail",
                "summary": "frame manifest file does not exist",
                "path": str(frame_manifest_path),
            }
        )
        return base

    frame_manifest = read_json(frame_manifest_path)
    frames = frame_manifest.get("frames", [])
    if not isinstance(frames, list) or not frames:
        base["stage"]["status"] = "fail"
        base["checks"].append(
            {
                "id": "frame_manifest",
                "status": "fail",
                "summary": "frame manifest has no frames",
            }
        )
        return base

    frame_dir = Path(str(frame_manifest.get("frameDirectory") or frame_sampling_report.get("frameDirectory") or ""))
    if not frame_dir.exists():
        base["stage"]["status"] = "fail"
        base["checks"].append(
            {
                "id": "frame_directory",
                "status": "fail",
                "summary": "frame directory does not exist",
                "path": str(frame_dir),
            }
        )
        return base

    colmap = run_command(["colmap", "--help"], timeout_seconds=10)
    if colmap["status"] != "pass":
        base["stage"]["status"] = colmap["status"]
        base["checks"].append(
            {
                "id": "colmap",
                "status": colmap["status"],
                "summary": command_summary(colmap, max_lines=3) or "COLMAP is not available",
                "details": colmap,
            }
        )
        return base

    sfm_dir = sfm_run_directory(job_path)
    sfm_dir.mkdir(parents=True, exist_ok=True)
    database_path = sfm_dir / "database.db"
    sparse_dir = sfm_dir / "sparse"
    sparse_dir.mkdir(parents=True, exist_ok=True)

    commands: dict[str, Any] = {}
    commands["featureExtractor"] = run_command(
        [
            "colmap",
            "feature_extractor",
            "--database_path",
            str(database_path),
            "--image_path",
            str(frame_dir),
            "--ImageReader.single_camera",
            "1",
            "--SiftExtraction.use_gpu",
            "0",
        ],
        timeout_seconds=3600,
    )
    if commands["featureExtractor"]["status"] != "pass":
        base["stage"]["status"] = commands["featureExtractor"]["status"]
        base["commands"] = commands
        base["checks"].append(
            {
                "id": "colmap_feature_extractor",
                "status": commands["featureExtractor"]["status"],
                "summary": command_summary(commands["featureExtractor"], max_lines=5) or "COLMAP feature extraction failed",
            }
        )
        return base

    commands["sequentialMatcher"] = run_command(
        [
            "colmap",
            "sequential_matcher",
            "--database_path",
            str(database_path),
            "--SiftMatching.use_gpu",
            "0",
        ],
        timeout_seconds=3600,
    )
    if commands["sequentialMatcher"]["status"] != "pass":
        base["stage"]["status"] = commands["sequentialMatcher"]["status"]
        base["commands"] = commands
        base["checks"].append(
            {
                "id": "colmap_matcher",
                "status": commands["sequentialMatcher"]["status"],
                "summary": command_summary(commands["sequentialMatcher"], max_lines=5) or "COLMAP matching failed",
            }
        )
        return base

    commands["mapper"] = run_command(
        [
            "colmap",
            "mapper",
            "--database_path",
            str(database_path),
            "--image_path",
            str(frame_dir),
            "--output_path",
            str(sparse_dir),
        ],
        timeout_seconds=3600,
    )
    base["commands"] = commands
    if commands["mapper"]["status"] != "pass":
        base["stage"]["status"] = commands["mapper"]["status"]
        base["checks"].append(
            {
                "id": "colmap_mapper",
                "status": commands["mapper"]["status"],
                "summary": command_summary(commands["mapper"], max_lines=5) or "COLMAP mapper failed",
            }
        )
        return base

    model_dirs = sorted(path for path in sparse_dir.iterdir() if path.is_dir())
    sparse_model_path = model_dirs[0] if model_dirs else None
    analyzer_result = None
    analyzer_metrics = None
    if sparse_model_path is not None:
        analyzer_result = run_command(["colmap", "model_analyzer", "--path", str(sparse_model_path)], timeout_seconds=300)
        commands["modelAnalyzer"] = analyzer_result
        if analyzer_result["status"] == "pass":
            analyzer_metrics = parse_colmap_model_analyzer(analyzer_result.get("stdout", ""))

    status, checks = validate_sfm_output(len(frames), sparse_model_path, analyzer_metrics)
    base["stage"]["status"] = status
    base["sfmDirectory"] = str(sfm_dir)
    base["databasePath"] = str(database_path)
    base["sparseModelPath"] = str(sparse_model_path) if sparse_model_path else None
    base["frameManifestPath"] = str(frame_manifest_path)
    base["metrics"] = analyzer_metrics or {}
    base["colmap"] = {
        "versionSummary": command_summary(colmap, max_lines=3),
        "matcher": "sequential_matcher",
        "usesGpu": False,
        "note": "Ubuntu COLMAP package reports without CUDA; first SfM validation uses CPU SIFT extraction and matching.",
    }
    base["checks"].extend(checks)
    return base


def upstream_gate_status(upstream_status: str | None) -> str:
    if upstream_status in {None, "pending", "setup_gap"}:
        return "setup_gap"
    if upstream_status == "blocked_workload":
        return "blocked_workload"
    if upstream_status == "blocked_license":
        return "blocked_license"
    return "fail"


def missing_or_blocked_upstream_report(
    job_path: Path,
    stage_id: str,
    upstream_stage_id: str,
    upstream_report_path: Path,
) -> dict[str, Any] | None:
    base = {
        "schemaVersion": 1,
        "stage": {
            "id": stage_id,
            "status": "pending",
            "generatedAt": utc_now(),
            "jobPath": str(job_path),
        },
        "checks": [],
    }
    if not upstream_report_path.exists():
        base["stage"]["status"] = "setup_gap"
        base["checks"].append(
            {
                "id": f"{upstream_stage_id}_required",
                "status": "setup_gap",
                "summary": f"{upstream_stage_id} report is missing; run {upstream_stage_id} before {stage_id}",
            }
        )
        return base

    upstream_report = read_json(upstream_report_path)
    upstream_status = upstream_report.get("stage", {}).get("status")
    if upstream_status not in {"pass", "warning"}:
        status = upstream_gate_status(upstream_status)
        base["stage"]["status"] = status
        base["checks"].append(
            {
                "id": f"{upstream_stage_id}_required",
                "status": status,
                "summary": f"{upstream_stage_id} must pass before {stage_id}; current status is {upstream_status}",
            }
        )
        return base
    return None


def build_splat_training_report(job_path: Path, accept_warning: bool = False, allow_heavy: bool = False) -> dict[str, Any]:
    sfm_path = stage_report_path(job_path, "sfm")
    blocked = missing_or_blocked_upstream_report(job_path, "splat_training", "sfm", sfm_path)
    if blocked is not None:
        return blocked

    sfm_report = read_json(sfm_path)
    sfm_status = sfm_report.get("stage", {}).get("status")
    base = {
        "schemaVersion": 1,
        "stage": {
            "id": "splat_training",
            "status": "pending",
            "generatedAt": utc_now(),
            "jobPath": str(job_path),
        },
        "checks": [],
        "acceptedUpstreamWarnings": accept_warning,
        "training": read_json(job_path).get("capture", {}).get("pipeline", {}).get("training", {}),
        "source": {
            "sfmReportPath": str(sfm_path),
            "sparseModelPath": sfm_report.get("sparseModelPath"),
        },
    }
    if sfm_status == "warning" and not accept_warning:
        base["stage"]["status"] = "fail"
        base["checks"].append(
            {
                "id": "sfm_warning_acceptance",
                "status": "fail",
                "summary": "SfM warning must be explicitly accepted with --accept-warning before training",
            }
        )
        return base
    if not allow_heavy:
        base["stage"]["status"] = "blocked_workload"
        base["checks"].append(
            {
                "id": "heavy_workload_ack_required",
                "status": "blocked_workload",
                "summary": "Splat training can sustain high GPU load; rerun with --allow-heavy only after confirming the workstation can take sustained load.",
            }
        )
        base["workload"] = {
            "classification": "heavy",
            "requiresExplicitApproval": True,
            "approvalFlag": "--allow-heavy",
            "reason": "Gaussian Splat training can sustain high RTX/GPU and CPU load.",
        }
        return base

    base["stage"]["status"] = "setup_gap"
    base["checks"].append(
        {
            "id": "training_implementation",
            "status": "setup_gap",
            "summary": "Training orchestration is not implemented yet; no training command was run.",
        }
    )
    return base


def build_packaging_report(job_path: Path, accept_warning: bool = False) -> dict[str, Any]:
    training_path = stage_report_path(job_path, "splat_training")
    blocked = missing_or_blocked_upstream_report(job_path, "packaging", "splat_training", training_path)
    if blocked is not None:
        return blocked

    training_report = read_json(training_path)
    training_status = training_report.get("stage", {}).get("status")
    base = {
        "schemaVersion": 1,
        "stage": {
            "id": "packaging",
            "status": "pending",
            "generatedAt": utc_now(),
            "jobPath": str(job_path),
        },
        "checks": [],
        "acceptedUpstreamWarnings": accept_warning,
        "source": {"trainingReportPath": str(training_path)},
    }
    if training_status == "warning" and not accept_warning:
        base["stage"]["status"] = "fail"
        base["checks"].append(
            {
                "id": "training_warning_acceptance",
                "status": "fail",
                "summary": "Training warning must be explicitly accepted with --accept-warning before packaging",
            }
        )
        return base

    artifact_path = training_report.get("exportedArtifactPath") or training_report.get("splatArtifactPath")
    if not isinstance(artifact_path, str) or not artifact_path:
        base["stage"]["status"] = "setup_gap"
        base["checks"].append(
            {
                "id": "training_artifact",
                "status": "setup_gap",
                "summary": "Training report does not declare an exported splat artifact path; packaging did not run.",
            }
        )
        return base

    artifact = Path(artifact_path)
    if not artifact.exists():
        base["stage"]["status"] = "fail"
        base["checks"].append(
            {
                "id": "training_artifact",
                "status": "fail",
                "summary": "Declared training artifact does not exist",
                "path": str(artifact),
            }
        )
        return base

    base["stage"]["status"] = "pass"
    base["artifact"] = {
        "path": str(artifact),
        "sizeBytes": artifact.stat().st_size,
        "sha256": file_sha256(artifact),
    }
    base["checks"].append(
        {
            "id": "artifact",
            "status": "pass",
            "summary": "Splat artifact exists and hash/size are recorded",
        }
    )
    return base


def build_viewer_report(job_path: Path, accept_warning: bool = False, allow_heavy: bool = False) -> dict[str, Any]:
    packaging_path = stage_report_path(job_path, "packaging")
    blocked = missing_or_blocked_upstream_report(job_path, "viewer", "packaging", packaging_path)
    if blocked is not None:
        return blocked

    packaging_report = read_json(packaging_path)
    packaging_status = packaging_report.get("stage", {}).get("status")
    base = {
        "schemaVersion": 1,
        "stage": {
            "id": "viewer",
            "status": "pending",
            "generatedAt": utc_now(),
            "jobPath": str(job_path),
        },
        "checks": [],
        "acceptedUpstreamWarnings": accept_warning,
        "source": {"packagingReportPath": str(packaging_path)},
    }
    if packaging_status == "warning" and not accept_warning:
        base["stage"]["status"] = "fail"
        base["checks"].append(
            {
                "id": "packaging_warning_acceptance",
                "status": "fail",
                "summary": "Packaging warning must be explicitly accepted with --accept-warning before viewer validation",
            }
        )
        return base
    if not allow_heavy:
        base["stage"]["status"] = "blocked_workload"
        base["checks"].append(
            {
                "id": "heavy_workload_ack_required",
                "status": "blocked_workload",
                "summary": "Viewer validation may launch browser/rendering work; rerun with --allow-heavy only after confirming workstation load is acceptable.",
            }
        )
        base["workload"] = {
            "classification": "heavy",
            "requiresExplicitApproval": True,
            "approvalFlag": "--allow-heavy",
            "reason": "Browser/canvas validation can exercise GPU rendering paths.",
        }
        return base

    base["stage"]["status"] = "setup_gap"
    base["checks"].append(
        {
            "id": "viewer_implementation",
            "status": "setup_gap",
            "summary": "Viewer validation is not implemented yet; no browser or render command was launched.",
        }
    )
    return base


def build_quality_report(job_path: Path) -> dict[str, Any]:
    stage_summaries = []
    first_boundary = None
    for stage in STAGES:
        stage_id = stage["id"]
        if stage_id == "quality_report":
            continue
        report_path = stage_report_path(job_path, stage_id)
        if report_path.exists():
            report = read_json(report_path)
            status = report.get("stage", {}).get("status", "unknown")
            checks = report.get("checks", []) if isinstance(report.get("checks"), list) else []
            summary = next((check.get("summary") for check in checks if isinstance(check, dict) and check.get("summary")), None)
        else:
            status = "pending"
            summary = "report has not been generated"
        item = {
            "id": stage_id,
            "label": stage["label"],
            "status": status,
            "reportPath": str(report_path) if report_path.exists() else None,
            "summary": summary,
        }
        stage_summaries.append(item)
        if first_boundary is None and status not in {"pass", "warning"}:
            first_boundary = item

    statuses = [item["status"] for item in stage_summaries]
    if any(status == "blocked_license" for status in statuses):
        status = "blocked_license"
        classification = "blocked"
    elif any(status == "blocked_workload" for status in statuses):
        status = "blocked_workload"
        classification = "blocked"
    elif any(status == "fail" for status in statuses):
        status = "fail"
        classification = "failed"
    elif any(status in {"setup_gap", "pending", "unknown"} for status in statuses):
        status = "setup_gap"
        classification = "incomplete"
    elif any(status == "warning" for status in statuses):
        status = "warning"
        classification = "weak"
    else:
        status = "pass"
        classification = "usable"

    return {
        "schemaVersion": 1,
        "stage": {
            "id": "quality_report",
            "status": status,
            "generatedAt": utc_now(),
            "jobPath": str(job_path),
        },
        "classification": classification,
        "firstBoundary": first_boundary,
        "stages": stage_summaries,
        "checks": [
            {
                "id": "pipeline_boundary",
                "status": status,
                "summary": "pipeline summary generated; first blocking boundary recorded" if first_boundary else "all pipeline stages are pass/warning",
            }
        ],
    }


def build_intake_report(job_path: Path) -> dict[str, Any]:
    repo_root = repo_root_from_script()
    job = read_json(job_path)
    environment_status = stage_status_from_job(job, "environment")
    source = job.get("capture", {}).get("source", {})

    base = {
        "schemaVersion": 1,
        "stage": {
            "id": "intake",
            "status": "pending",
            "generatedAt": utc_now(),
            "jobPath": str(job_path),
        },
        "source": source,
        "checks": [],
    }

    if environment_status != "pass":
        base["stage"]["status"] = "setup_gap"
        base["checks"].append(
            {
                "id": "environment_required",
                "status": "setup_gap",
                "summary": f"environment stage must pass before intake; current status is {environment_status}",
            }
        )
        return base

    try:
        video_path = capture_video_path(job, repo_root)
    except ValueError as exc:
        base["stage"]["status"] = "fail"
        base["checks"].append({"id": "source_path", "status": "fail", "summary": str(exc)})
        return base

    base["videoPath"] = str(video_path)
    if not video_path.exists():
        base["stage"]["status"] = "fail"
        base["checks"].append(
            {
                "id": "video_file",
                "status": "fail",
                "summary": "source video file does not exist",
                "path": str(video_path),
            }
        )
        return base

    base["checks"].append(
        {
            "id": "video_file",
            "status": "pass",
            "summary": "source video file exists",
            "path": str(video_path),
            "sizeBytes": video_path.stat().st_size,
        }
    )

    probe_result = ffprobe_metadata(video_path)
    if probe_result["status"] != "pass":
        base["stage"]["status"] = probe_result["status"]
        base["checks"].append(
            {
                "id": "ffprobe",
                "status": probe_result["status"],
                "summary": probe_result.get("message"),
                "details": probe_result,
            }
        )
        return base

    summary = summarize_video_metadata(probe_result["metadata"])
    status, messages = validate_intake_summary(summary, source)
    base["stage"]["status"] = status
    base["ffprobe"] = {
        "versionSummary": command_summary(probe_result["ffprobe"], max_lines=3),
        "configuration": probe_result["ffprobe"].get("stdout", ""),
    }
    base["metadata"] = summary
    base["checks"].append(
        {
            "id": "ffprobe",
            "status": "pass",
            "summary": "metadata extracted",
        }
    )
    base["checks"].append(
        {
            "id": "mvp_thresholds",
            "status": status,
            "summary": "; ".join(messages) if messages else "input satisfies initial MVP intake thresholds",
            "messages": messages,
        }
    )
    return base


def command_run_stage(args: argparse.Namespace) -> int:
    job_path = Path(args.job)
    if not job_path.is_absolute():
        job_path = repo_root_from_script() / job_path
    if not job_path.exists():
        raise FileNotFoundError(f"job manifest not found: {job_path}")

    if args.stage == "framework_license":
        report = build_framework_license_report(job_path)
    elif args.stage == "environment":
        report = build_environment_report(job_path)
    elif args.stage == "intake":
        report = build_intake_report(job_path)
    elif args.stage == "frame_sampling":
        report = build_frame_sampling_report(job_path, accept_warning=args.accept_warning)
    elif args.stage == "sfm":
        report = build_sfm_report(job_path, accept_warning=args.accept_warning, allow_heavy=args.allow_heavy)
    elif args.stage == "splat_training":
        report = build_splat_training_report(job_path, accept_warning=args.accept_warning, allow_heavy=args.allow_heavy)
    elif args.stage == "packaging":
        report = build_packaging_report(job_path, accept_warning=args.accept_warning)
    elif args.stage == "viewer":
        report = build_viewer_report(job_path, accept_warning=args.accept_warning, allow_heavy=args.allow_heavy)
    elif args.stage == "quality_report":
        report = build_quality_report(job_path)
    else:
        raise ValueError(f"unsupported stage {args.stage!r}")

    report_path = stage_report_path(job_path, args.stage)
    write_json(report_path, report)
    update_job_stage(job_path, args.stage, report["stage"]["status"], report_path)
    print(f"{args.stage}_status={report['stage']['status']}")
    print(f"{args.stage}_report={report_path}")
    return 0 if report["stage"]["status"] in {"pass", "warning", "setup_gap"} else 1


def command_list_captures(args: argparse.Namespace) -> int:
    repo_root = repo_root_from_script()
    manifest_path = Path(args.capture_manifest)
    if not manifest_path.is_absolute():
        manifest_path = repo_root / manifest_path
    print(json.dumps(capture_readiness_report(manifest_path, repo_root), indent=2))
    return 0


def command_describe(_args: argparse.Namespace) -> int:
    stages = [
        {**stage, "workload": "heavy" if stage["id"] in HEAVY_STAGES else "normal"}
        for stage in STAGES
    ]
    print(json.dumps({"schemaVersion": 1, "stages": stages}, indent=2))
    return 0


def command_init_job(args: argparse.Namespace) -> int:
    repo_root = repo_root_from_script()
    manifest_path = Path(args.capture_manifest)
    if not manifest_path.is_absolute():
        manifest_path = repo_root / manifest_path

    selection = select_capture(manifest_path, args.capture_id)
    job = build_job(selection, repo_root)

    if args.dry_run:
        print(json.dumps(job, indent=2))
        return 0

    jobs_dir = Path(args.jobs_dir)
    if not jobs_dir.is_absolute():
        jobs_dir = repo_root / jobs_dir
    job_dir = jobs_dir / job["job"]["id"]
    job_path = job_dir / "job.json"
    write_json(job_path, job)
    print(f"job_manifest={job_path}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Manifest-driven skeleton for video-to-Gaussian-Splat jobs."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    describe = subparsers.add_parser("describe", help="Print pipeline stages as JSON.")
    describe.set_defaults(func=command_describe)

    list_captures = subparsers.add_parser("list-captures", help="Print capture readiness as JSON.")
    list_captures.add_argument(
        "--capture-manifest",
        default="data/manifests/captures.example.json",
        help="Path to a capture manifest JSON file.",
    )
    list_captures.set_defaults(func=command_list_captures)

    init_job = subparsers.add_parser(
        "init-job", help="Create a planned job from a capture manifest."
    )
    init_job.add_argument(
        "--capture-manifest",
        default="data/manifests/captures.example.json",
        help="Path to a capture manifest JSON file.",
    )
    init_job.add_argument("--capture-id", required=True, help="Capture id to plan.")
    init_job.add_argument(
        "--jobs-dir",
        default="outputs/jobs",
        help="Directory for generated job folders.",
    )
    init_job.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the job manifest instead of writing it.",
    )
    init_job.set_defaults(func=command_init_job)

    run_stage = subparsers.add_parser(
        "run-stage", help="Run one validated pipeline stage for a job."
    )
    run_stage.add_argument(
        "stage",
        choices=[
            "framework_license",
            "environment",
            "intake",
            "frame_sampling",
            "sfm",
            "splat_training",
            "packaging",
            "viewer",
            "quality_report",
        ],
        help="Stage id to run.",
    )
    run_stage.add_argument("--job", required=True, help="Path to a job.json manifest.")
    run_stage.add_argument(
        "--accept-warning",
        action="store_true",
        help="Explicitly allow downstream work after an upstream warning report.",
    )
    run_stage.add_argument(
        "--allow-heavy",
        action="store_true",
        help="Permit stages that can place sustained load on CPU/GPU. Required for SfM and future training/rendering stages.",
    )
    run_stage.set_defaults(func=command_run_stage)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
