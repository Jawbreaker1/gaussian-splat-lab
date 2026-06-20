#!/usr/bin/env python3
"""Local dependency-free web UI for Gaussian Splat Lab."""

from __future__ import annotations

import argparse
import importlib.util
import json
import mimetypes
import re
import shutil
import subprocess
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, quote, unquote, urlparse


REPO_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = REPO_ROOT / "app"
NODE_MODULES_ROOT = REPO_ROOT / "node_modules"
CAPTURE_MANIFEST = REPO_ROOT / "data/manifests/captures.example.json"
LOCAL_CAPTURE_MANIFEST = REPO_ROOT / "data/tmp/ui-captures.json"
EFFECTIVE_CAPTURE_MANIFEST = REPO_ROOT / "data/tmp/ui-effective-captures.json"
FRAMEWORK_MANIFEST = REPO_ROOT / "data/manifests/framework-evaluation.json"
GATES_MANIFEST = REPO_ROOT / "data/manifests/pipeline-gates.json"
JOBS_DIR = REPO_ROOT / "outputs/jobs"
DELETED_JOBS_DIR = REPO_ROOT / "outputs/deleted-jobs"
RTX_EVIDENCE = REPO_ROOT / "docs/validation/phase-0-rtx-workstation-wsl-output.md"
PIPELINE_SCRIPT = REPO_ROOT / "scripts/lab-pipeline.py"
VENV_PYTHON = REPO_ROOT / ".venv/bin/python"
RUNNABLE_STAGES = {"framework_license", "environment", "intake", "frame_sampling", "sfm", "splat_training", "packaging", "viewer", "quality_report"}
TRAINING_STAGE_TIMEOUTS = {
    "smoke": 30 * 60,
    "baseline": 45 * 60,
    "quality_probe": 2 * 60 * 60,
    "rtx_reference": 4 * 60 * 60,
    "rtx_high_quality": 8 * 60 * 60,
    "rtx_ultra_quality": 12 * 60 * 60,
    "rtx_stable_quality": 16 * 60 * 60,
    "rtx_ceiling_quality": 16 * 60 * 60,
    "rtx_max_quality": 20 * 60 * 60,
    "splatfacto_preview": 2 * 60 * 60,
    "splatfacto_reference": 8 * 60 * 60,
    "splatfacto_big_quality": 12 * 60 * 60,
    "splatfacto_ceiling": 20 * 60 * 60,
}
UI_QUALITY_PRESETS = {
    "quality_probe": {
        "label": "Quick preview",
        "targetFps": 2,
        "maxFrames": 180,
        "trainingProfile": "quality_probe",
        "sfm": {
            "matcher": "sequential",
            "featureNumThreads": 4,
            "featureMaxImageSize": 2400,
            "featureMaxNumFeatures": 4096,
            "matcherNumThreads": 4,
            "sequentialOverlap": 12,
            "sequentialQuadraticOverlap": True,
            "guidedMatching": False,
            "useGpu": False,
        },
    },
    "rtx_high_quality": {
        "label": "High quality",
        "targetFps": 3,
        "maxFrames": 300,
        "trainingProfile": "rtx_high_quality",
        "sfm": {
            "matcher": "sequential",
            "featureNumThreads": 4,
            "featureMaxImageSize": 3200,
            "featureMaxNumFeatures": 8192,
            "matcherNumThreads": 4,
            "sequentialOverlap": 20,
            "sequentialQuadraticOverlap": True,
            "guidedMatching": False,
            "useGpu": False,
        },
    },
    "rtx_ultra_quality": {
        "label": "Ultra quality",
        "targetFps": 3,
        "maxFrames": 360,
        "trainingProfile": "rtx_ultra_quality",
        "sfm": {
            "matcher": "sequential",
            "featureNumThreads": 4,
            "featureMaxImageSize": 3200,
            "featureMaxNumFeatures": 8192,
            "matcherNumThreads": 4,
            "sequentialOverlap": 20,
            "sequentialQuadraticOverlap": True,
            "guidedMatching": False,
            "useGpu": False,
        },
    },
    "rtx_stable_quality": {
        "label": "Max stable",
        "targetFps": 3,
        "maxFrames": 360,
        "trainingProfile": "rtx_stable_quality",
        "trainingBackend": "gsplat",
        "sfm": {
            "matcher": "sequential",
            "featureNumThreads": 4,
            "featureMaxImageSize": 3200,
            "featureMaxNumFeatures": 8192,
            "matcherNumThreads": 4,
            "sequentialOverlap": 20,
            "sequentialQuadraticOverlap": True,
            "guidedMatching": False,
            "useGpu": False,
        },
    },
    "splatfacto_reference": {
        "label": "Standard 3DGS",
        "targetFps": 3,
        "maxFrames": 360,
        "trainingProfile": "splatfacto_reference",
        "trainingBackend": "nerfstudio_splatfacto",
        "sfm": {
            "matcher": "sequential",
            "featureNumThreads": 4,
            "featureMaxImageSize": 3200,
            "featureMaxNumFeatures": 8192,
            "matcherNumThreads": 4,
            "sequentialOverlap": 20,
            "sequentialQuadraticOverlap": True,
            "guidedMatching": False,
            "useGpu": False,
        },
    },
    "splatfacto_big_quality": {
        "label": "Best quality",
        "targetFps": 3,
        "maxFrames": 420,
        "trainingProfile": "splatfacto_big_quality",
        "trainingBackend": "nerfstudio_splatfacto",
        "sfm": {
            "matcher": "sequential",
            "featureNumThreads": 4,
            "featureMaxImageSize": 3840,
            "featureMaxNumFeatures": 12288,
            "matcherNumThreads": 4,
            "sequentialOverlap": 28,
            "sequentialQuadraticOverlap": True,
            "guidedMatching": False,
            "useGpu": False,
        },
    },
    "splatfacto_ceiling": {
        "label": "Ceiling test",
        "targetFps": 3,
        "maxFrames": 420,
        "trainingProfile": "splatfacto_ceiling",
        "trainingBackend": "nerfstudio_splatfacto",
        "sfm": {
            "matcher": "sequential",
            "featureNumThreads": 4,
            "featureMaxImageSize": 3840,
            "featureMaxNumFeatures": 12288,
            "matcherNumThreads": 4,
            "sequentialOverlap": 28,
            "sequentialQuadraticOverlap": True,
            "guidedMatching": False,
            "useGpu": False,
        },
    },
    "rtx_max_quality": {
        "label": "Max stress",
        "targetFps": 3,
        "maxFrames": 240,
        "trainingProfile": "rtx_max_quality",
        "trainingBackend": "gsplat",
        "sfm": {
            "matcher": "sequential",
            "featureNumThreads": 4,
            "featureMaxImageSize": 3200,
            "featureMaxNumFeatures": 8192,
            "matcherNumThreads": 4,
            "sequentialOverlap": 24,
            "sequentialQuadraticOverlap": True,
            "guidedMatching": False,
            "useGpu": False,
        },
    },
}


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


def load_local_capture_manifest() -> dict[str, Any]:
    if not LOCAL_CAPTURE_MANIFEST.exists():
        return {"schemaVersion": 1, "captures": []}
    manifest = read_json(LOCAL_CAPTURE_MANIFEST)
    if not isinstance(manifest.get("captures"), list):
        manifest["captures"] = []
    return manifest


def active_capture_manifest() -> Path:
    base = read_json(CAPTURE_MANIFEST)
    local = load_local_capture_manifest()
    merged: dict[str, Any] = {
        "schemaVersion": base.get("schemaVersion", 1),
        "captures": [],
    }
    seen: set[str] = set()
    for capture in list(base.get("captures", [])) + list(local.get("captures", [])):
        if not isinstance(capture, dict):
            continue
        capture_id = str(capture.get("id") or "")
        if not capture_id:
            continue
        if capture_id in seen:
            merged["captures"] = [
                existing for existing in merged["captures"] if existing.get("id") != capture_id
            ]
        merged["captures"].append(capture)
        seen.add(capture_id)
    write_json(EFFECTIVE_CAPTURE_MANIFEST, merged)
    return EFFECTIVE_CAPTURE_MANIFEST


def slugify(value: str, fallback: str = "scene-capture") -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug[:48] or fallback


def video_extension(upload_name: str | None) -> str:
    suffix = Path(upload_name or "").suffix.lower()
    if suffix in {".mov", ".mp4", ".m4v", ".avi", ".mkv", ".hevc"}:
        return suffix
    return ".mov"


def upsert_local_capture(capture: dict[str, Any]) -> None:
    manifest = load_local_capture_manifest()
    capture_id = capture.get("id")
    manifest["captures"] = [
        item for item in manifest.get("captures", [])
        if isinstance(item, dict) and item.get("id") != capture_id
    ]
    manifest["captures"].append(capture)
    write_json(LOCAL_CAPTURE_MANIFEST, manifest)
    active_capture_manifest()


def remove_local_capture(capture_id: str) -> None:
    manifest = load_local_capture_manifest()
    manifest["captures"] = [
        item for item in manifest.get("captures", [])
        if isinstance(item, dict) and item.get("id") != capture_id
    ]
    write_json(LOCAL_CAPTURE_MANIFEST, manifest)
    active_capture_manifest()


def build_uploaded_capture(query: dict[str, list[str]], upload_name: str | None) -> dict[str, Any]:
    display_name = (query.get("displayName", [""])[0] or Path(upload_name or "").stem or "Video capture").strip()
    scene_kind = (query.get("sceneKind", ["room"])[0] or "room").strip()
    quality_key = query.get("qualityPreset", ["quality_probe"])[0]
    quality = UI_QUALITY_PRESETS.get(quality_key, UI_QUALITY_PRESETS["quality_probe"])
    sfm_controls = quality.get("sfm", {}) if isinstance(quality.get("sfm"), dict) else {}
    now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    capture_id = f"capture-{slugify(display_name)}-{now}"
    target_path = f"data/videos/uploads/{capture_id}{video_extension(upload_name)}"
    subject = {
        "room": "self-captured indoor room from uploaded video",
        "outdoor": "self-captured outdoor environment from uploaded video",
        "object": "self-captured object/area from uploaded video",
    }.get(scene_kind, "self-captured environment from uploaded video")
    motion = {
        "room": "slow walking loop with clear parallax through the room",
        "outdoor": "slow walking arc/loop with clear parallax through the environment",
        "object": "slow orbit with clear parallax around the subject",
    }.get(scene_kind, "slow capture movement with clear parallax")
    return {
        "id": capture_id,
        "displayName": display_name,
        "source": {
            "kind": "local_file",
            "path": target_path,
            "sourceUrl": None,
            "license": "self-captured",
            "licenseNotes": "Uploaded through the local UI as user-confirmed self-captured media. Review scene content before commercial use.",
        },
        "capture": {
            "subject": subject,
            "motion": motion,
            "expectedDurationSeconds": None,
            "expectedResolution": "source video",
        },
        "pipeline": {
            "frameSampling": {
                "targetFps": quality["targetFps"],
                "maxFrames": quality["maxFrames"],
            },
            "sfm": {
                "backend": "colmap",
                "requiresExplicitHeavyApproval": True,
                **sfm_controls,
            },
            "training": {
                "backend": quality.get("trainingBackend", "gsplat"),
                "targetWorker": "windows-rtx-5090",
                "profile": quality["trainingProfile"],
                "requiresExplicitHeavyApproval": True,
            },
            "packaging": {
                "preferredFormats": ["ply", "viewer-manifest"],
            },
        },
        "status": "self-captured-ui-upload",
        "ui": {
            "sceneKind": scene_kind,
            "qualityPreset": quality_key,
            "uploadedFileName": upload_name,
            "createdAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        },
    }


def load_pipeline_module():
    script_path = REPO_ROOT / "scripts/lab-pipeline.py"
    spec = importlib.util.spec_from_file_location("lab_pipeline", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load lab-pipeline.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def run_validator(script_name: str) -> bool:
    result = subprocess.run(
        [str(REPO_ROOT / "scripts" / script_name)],
        cwd=REPO_ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode == 0


def artifact_url(repo_relative_path: str | None) -> str | None:
    if not repo_relative_path:
        return None
    return f"/api/artifacts/{quote(repo_relative_path, safe='/')}"


def resolve_artifact_path(raw_path: str) -> Path:
    if not raw_path:
        raise ValueError("artifact path is required")
    path = (REPO_ROOT / unquote(raw_path)).resolve()
    path.relative_to(JOBS_DIR.resolve())
    if not path.exists() or not path.is_file():
        raise ValueError("artifact path must point at an existing job artifact")
    return path


def resolve_node_module_path(raw_path: str) -> Path:
    if not raw_path:
        raise ValueError("node module path is required")
    path = (NODE_MODULES_ROOT / unquote(raw_path)).resolve()
    path.relative_to(NODE_MODULES_ROOT.resolve())
    if not path.exists() or not path.is_file():
        raise ValueError("node module path must point at an installed local package file")
    return path


def attach_artifact_urls(viewer_manifest: dict[str, Any]) -> dict[str, Any]:
    manifest = json.loads(json.dumps(viewer_manifest))
    artifact = manifest.get("artifact") if isinstance(manifest.get("artifact"), dict) else {}
    preview = manifest.get("preview") if isinstance(manifest.get("preview"), dict) else {}
    export = manifest.get("export") if isinstance(manifest.get("export"), dict) else {}
    if isinstance(artifact, dict):
        artifact["url"] = artifact_url(artifact.get("repoRelativePath"))
    if isinstance(preview, dict):
        preview["sampleRenderUrl"] = artifact_url(preview.get("sampleRenderRepoRelativePath"))
        preview["sampleTargetUrl"] = artifact_url(preview.get("sampleTargetRepoRelativePath"))
        preview["renderReviewUrl"] = artifact_url(preview.get("renderReviewRepoRelativePath"))
    if isinstance(export, dict):
        export["primaryAssetUrl"] = artifact_url(export.get("primaryAssetRepoRelativePath"))
    return manifest


def latest_job() -> dict[str, Any] | None:
    if not JOBS_DIR.exists():
        return None
    candidates = sorted(JOBS_DIR.glob("*/job.json"), key=lambda path: path.stat().st_mtime, reverse=True)
    if not candidates:
        return None
    job = read_json(candidates[0])
    job["jobPath"] = str(candidates[0])
    job["reportSummaries"] = job_report_summaries(candidates[0])
    return job


def safe_read_report(path: Path) -> dict[str, Any] | None:
    if not path.exists() or not path.is_file():
        return None
    try:
        return read_json(path)
    except Exception:
        return None


def slim_check(check: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(check, dict):
        return None
    slim: dict[str, Any] = {}
    for key in (
        "id",
        "status",
        "summary",
        "registeredImages",
        "frameCount",
        "registeredFraction",
        "passThreshold",
        "warningThreshold",
        "copiedFrameCount",
        "path",
    ):
        if key in check:
            slim[key] = check[key]
    messages = check.get("messages")
    if isinstance(messages, list):
        slim["messages"] = [str(item) for item in messages[:5]]
    return slim


def summarize_stage_report(report: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(report, dict):
        return None
    stage = report.get("stage") if isinstance(report.get("stage"), dict) else {}
    checks = report.get("checks") if isinstance(report.get("checks"), list) else []
    problem_statuses = {"fail", "blocked", "blocked_license", "blocked_workload", "setup_gap"}
    problem = next(
        (
            check for check in checks
            if isinstance(check, dict) and str(check.get("status") or "") in problem_statuses
        ),
        None,
    )
    if problem is None:
        problem = next(
            (
                check for check in checks
                if isinstance(check, dict) and str(check.get("status") or "") == "warning"
            ),
            None,
        )
    return {
        "status": stage.get("status"),
        "generatedAt": stage.get("generatedAt"),
        "problemCheck": slim_check(problem),
    }


def job_report_summaries(job_path: Path) -> dict[str, Any]:
    reports: dict[str, Any] = {}
    reports_dir = job_path.parent / "reports"
    for report_path in sorted(reports_dir.glob("*.json")):
        report = safe_read_report(report_path)
        summary = summarize_stage_report(report)
        if summary is not None:
            reports[report_path.stem] = {
                **summary,
                "path": str(report_path),
            }
    return reports


def latest_training_progress(job_path: Path) -> dict[str, Any] | None:
    splats_dir = job_path.parent / "splats"
    if not splats_dir.exists():
        return None
    candidates = sorted(
        splats_dir.glob("*/training_progress.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    for candidate in candidates:
        progress = safe_read_report(candidate)
        if progress is None:
            continue
        progress["path"] = str(candidate)
        return progress
    return None


def job_progress(job_path: Path) -> dict[str, Any]:
    job = read_json(job_path)
    job["jobPath"] = str(job_path)
    reports = job_report_summaries(job_path)
    job["reportSummaries"] = reports
    return {
        "job": job,
        "reports": reports,
        "trainingProgress": latest_training_progress(job_path),
    }


def latest_viewer_artifact() -> dict[str, Any] | None:
    job = latest_job()
    if not job:
        return None
    job_path = Path(job["jobPath"])
    packaging_path = job_path.parent / "reports" / "packaging.json"
    viewer_path = job_path.parent / "reports" / "viewer.json"
    if not packaging_path.exists():
        return None
    packaging = read_json(packaging_path)
    manifest_raw = packaging.get("viewerManifestPath")
    if not isinstance(manifest_raw, str) or not manifest_raw:
        return None
    manifest_path = Path(manifest_raw)
    if not manifest_path.exists():
        return None
    viewer_report = read_json(viewer_path) if viewer_path.exists() else None
    manifest = attach_artifact_urls(read_json(manifest_path))
    try:
        manifest_repo_relative = manifest_path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        manifest_repo_relative = None
    return {
        "jobId": job.get("job", {}).get("id"),
        "jobPath": str(job_path),
        "packagingStatus": packaging.get("stage", {}).get("status"),
        "viewerStatus": viewer_report.get("stage", {}).get("status") if viewer_report else None,
        "viewerManifestPath": str(manifest_path),
        "viewerManifestUrl": artifact_url(manifest_repo_relative),
        "manifest": manifest,
    }


def capture_display_index() -> dict[str, str]:
    captures = read_json(active_capture_manifest()).get("captures", [])
    index: dict[str, str] = {}
    for capture in captures:
        if not isinstance(capture, dict):
            continue
        capture_id = str(capture.get("id") or "")
        if capture_id:
            index[capture_id] = str(capture.get("displayName") or capture_id)
    return index


def stage_status(job: dict[str, Any], stage_id: str) -> str | None:
    for stage in job.get("stages", []):
        if isinstance(stage, dict) and stage.get("id") == stage_id:
            value = stage.get("status")
            return str(value) if value is not None else None
    return None


def read_optional_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return read_json(path)
    except Exception:
        return {}


def gallery_job_summary(job_path: Path, capture_names: dict[str, str] | None = None) -> dict[str, Any] | None:
    job_dir = job_path.parent
    manifest_path = job_dir / "viewer" / "viewer-manifest.json"
    if not manifest_path.exists():
        return None

    job = read_json(job_path)
    manifest = attach_artifact_urls(read_json(manifest_path))
    artifact = manifest.get("artifact") if isinstance(manifest.get("artifact"), dict) else {}
    preview = manifest.get("preview") if isinstance(manifest.get("preview"), dict) else {}
    export = manifest.get("export") if isinstance(manifest.get("export"), dict) else {}
    training = manifest.get("training") if isinstance(manifest.get("training"), dict) else {}
    run_config = manifest.get("runConfig") if isinstance(manifest.get("runConfig"), dict) else {}
    device = manifest.get("device") if isinstance(manifest.get("device"), dict) else {}
    camera_views = manifest.get("cameraViews") if isinstance(manifest.get("cameraViews"), list) else []
    job_meta = job.get("job") if isinstance(job.get("job"), dict) else {}
    capture_id = str(job_meta.get("captureId") or "")
    job_id = str(job_meta.get("id") or job_dir.name)
    names = capture_names or {}
    training_report = read_optional_json(job_dir / "reports" / "splat_training.json")
    training_result = training_report.get("trainingResult") if isinstance(training_report.get("trainingResult"), dict) else {}
    render_review = training.get("renderReview") if isinstance(training.get("renderReview"), dict) else {}
    if not render_review and isinstance(training_result.get("renderReview"), dict):
        render_review = training_result["renderReview"]

    try:
        manifest_repo_relative = manifest_path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        manifest_repo_relative = None

    thumbnail_url = (
        preview.get("sampleRenderUrl")
        or preview.get("renderReviewUrl")
        or preview.get("sampleTargetUrl")
    )
    return {
        "id": job_id,
        "name": names.get(capture_id, capture_id or job_id),
        "captureId": capture_id,
        "createdAt": job_meta.get("createdAt"),
        "status": job_meta.get("status") or "unknown",
        "sceneUrl": f"/gallery?scene={quote(job_id)}",
        "jobPath": str(job_path),
        "viewerManifestUrl": artifact_url(manifest_repo_relative),
        "thumbnailUrl": thumbnail_url,
        "artifactUrl": artifact.get("url"),
        "artifactFileName": export.get("recommendedSplatFileName") or f"{job_id}.ply",
        "manifestFileName": export.get("recommendedManifestFileName") or f"{job_id}.viewer-manifest.json",
        "artifact": {
            "format": artifact.get("format"),
            "sizeBytes": artifact.get("sizeBytes"),
            "sha256": artifact.get("sha256"),
            "splatCount": (artifact.get("ply") or {}).get("vertexCount") if isinstance(artifact.get("ply"), dict) else None,
        },
        "technical": {
            "profile": training.get("profile") or run_config.get("profile"),
            "iterations": training.get("iterations") or run_config.get("iterations"),
            "imagesUsed": training.get("imagesUsed"),
            "cameraViews": len(camera_views),
            "device": device.get("name"),
            "meanMae": render_review.get("meanMae"),
            "meanRmse": render_review.get("meanRmse"),
        },
        "stages": {
            "frameSampling": stage_status(job, "frame_sampling"),
            "sfm": stage_status(job, "sfm"),
            "splatTraining": stage_status(job, "splat_training"),
            "viewer": stage_status(job, "viewer"),
            "qualityReport": stage_status(job, "quality_report"),
        },
    }


def gallery_jobs() -> list[dict[str, Any]]:
    if not JOBS_DIR.exists():
        return []
    capture_names = capture_display_index()
    items: list[dict[str, Any]] = []
    for job_path in sorted(JOBS_DIR.glob("*/job.json"), key=lambda path: path.stat().st_mtime, reverse=True):
        item = gallery_job_summary(job_path, capture_names)
        if item:
            items.append(item)
    return items


def resolve_gallery_job_dir(job_id: str) -> Path:
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", job_id or ""):
        raise ValueError("invalid job id")
    job_dir = (JOBS_DIR / job_id).resolve()
    job_dir.relative_to(JOBS_DIR.resolve())
    if not (job_dir / "job.json").exists():
        raise ValueError("gallery job does not exist")
    return job_dir


def gallery_job_detail(job_id: str) -> dict[str, Any]:
    job_dir = resolve_gallery_job_dir(job_id)
    item = gallery_job_summary(job_dir / "job.json", capture_display_index())
    if not item:
        raise ValueError("gallery job has no viewer manifest")
    manifest = attach_artifact_urls(read_json(job_dir / "viewer" / "viewer-manifest.json"))
    return {"item": item, "manifest": manifest}


def delete_gallery_job(job_id: str) -> dict[str, Any]:
    job_dir = resolve_gallery_job_dir(job_id)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    target = (DELETED_JOBS_DIR / f"{job_dir.name}-{timestamp}").resolve()
    target.relative_to(DELETED_JOBS_DIR.resolve())
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        raise ValueError("delete target already exists")
    shutil.move(str(job_dir), str(target))
    return {
        "status": "deleted",
        "jobId": job_id,
        "deletedPath": str(target),
    }


def build_state() -> dict[str, Any]:
    manifest_path = active_capture_manifest()
    captures = read_json(manifest_path).get("captures", [])
    frameworks = read_json(FRAMEWORK_MANIFEST).get("frameworks", [])
    gates = read_json(GATES_MANIFEST).get("gates", [])
    pipeline = load_pipeline_module()
    capture_readiness = pipeline.capture_readiness_report(manifest_path, REPO_ROOT).get("captures", [])
    evidence = RTX_EVIDENCE.read_text(encoding="utf-8") if RTX_EVIDENCE.exists() else ""
    return {
        "schemaVersion": 1,
        "machineLabel": "Windows RTX 5090 workstation / WSL2",
        "captures": captures,
        "captureReadiness": capture_readiness,
        "frameworks": frameworks,
        "gates": gates,
        "latestJob": latest_job(),
        "viewerArtifact": latest_viewer_artifact(),
        "qualityPresets": UI_QUALITY_PRESETS,
        "validation": {
            "architecture": run_validator("validate-architecture-contracts.sh"),
            "phase1": run_validator("validate-phase-1-contracts.sh"),
            "rtxVisible": "NVIDIA GeForce RTX 5090" in evidence,
        },
    }


def create_job(capture_id: str) -> dict[str, Any]:
    pipeline = load_pipeline_module()
    selection = pipeline.select_capture(active_capture_manifest(), capture_id)
    job = pipeline.build_job(selection, REPO_ROOT)
    job_dir = JOBS_DIR / job["job"]["id"]
    job_path = job_dir / "job.json"
    pipeline.write_json(job_path, job)
    job["jobPath"] = str(job_path)
    return job


def pipeline_python() -> str:
    return str(VENV_PYTHON if VENV_PYTHON.exists() else Path(sys.executable))


def resolve_job_path(raw_path: Any) -> Path:
    if not isinstance(raw_path, str) or not raw_path:
        raise ValueError("jobPath is required")
    path = Path(raw_path)
    if not path.is_absolute():
        path = REPO_ROOT / path
    resolved = path.resolve()
    resolved.relative_to(JOBS_DIR.resolve())
    if resolved.name != "job.json" or not resolved.exists():
        raise ValueError("jobPath must point at an existing job.json")
    return resolved


def stage_timeout(stage: str, training_profile: str | None = None) -> int:
    if stage == "splat_training":
        return TRAINING_STAGE_TIMEOUTS.get(str(training_profile or ""), 8 * 60 * 60)
    if stage == "sfm":
        return 4 * 60 * 60
    if stage == "viewer":
        return 60 * 60
    return 30 * 60


def run_job_stage(
    job_path: Path,
    stage: str,
    accept_warning: bool = False,
    allow_heavy: bool = False,
    training_profile: str | None = None,
) -> dict[str, Any]:
    if stage not in RUNNABLE_STAGES:
        raise ValueError(f"stage {stage!r} is not runnable from the UI yet")
    command = [pipeline_python(), str(PIPELINE_SCRIPT), "run-stage", stage, "--job", str(job_path)]
    if accept_warning:
        command.append("--accept-warning")
    if allow_heavy:
        command.append("--allow-heavy")
    if stage == "splat_training" and training_profile:
        command.extend(["--training-profile", training_profile])
    result = subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=stage_timeout(stage, training_profile),
    )

    job = read_json(job_path)
    job["jobPath"] = str(job_path)
    report_path = job_path.parent / "reports" / f"{stage}.json"
    report = safe_read_report(report_path)
    job["reportSummaries"] = job_report_summaries(job_path)
    return {
        "job": job,
        "stage": stage,
        "returnCode": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
        "reportSummary": summarize_stage_report(report),
    }


def parse_bool_query(value: str | None) -> bool:
    return str(value or "").lower() in {"1", "true", "yes", "on"}


def save_capture_upload(
    capture_id: str,
    stream: Any,
    content_length: int,
    upload_name: str | None,
    accept_warning: bool,
    overwrite: bool,
    manifest_path: Path | None = None,
) -> dict[str, Any]:
    if content_length <= 0:
        raise ValueError("uploaded video is empty")

    pipeline = load_pipeline_module()
    manifest = manifest_path or active_capture_manifest()
    selection = pipeline.select_capture(manifest, capture_id)
    target_path = pipeline.capture_source_path(selection.capture, REPO_ROOT)
    tmp_path = Path(tempfile.gettempdir()) / f"gaussian-splat-lab-upload-{uuid.uuid4().hex}.video"

    remaining = content_length
    with tmp_path.open("wb") as handle:
        while remaining > 0:
            chunk = stream.read(min(1024 * 1024, remaining))
            if not chunk:
                break
            handle.write(chunk)
            remaining -= len(chunk)

    if remaining != 0:
        tmp_path.unlink(missing_ok=True)
        raise ValueError("uploaded video stream ended before Content-Length bytes were read")

    try:
        report = pipeline.build_video_import_report(
            manifest_path=manifest,
            selection=selection,
            input_path=tmp_path,
            target_path=target_path,
            accept_warning=accept_warning,
            overwrite=overwrite,
            dry_run=False,
            repo_root=REPO_ROOT,
        )
        report["source"]["uploadedFileName"] = upload_name
        if target_path is not None and report["status"] == "pass":
            pipeline.write_json(pipeline.capture_import_report_path(target_path), report)
        readiness = pipeline.capture_readiness_report(manifest, REPO_ROOT).get("captures", [])
        return {"report": report, "captureReadiness": readiness}
    finally:
        tmp_path.unlink(missing_ok=True)


def validate_ui_contracts() -> None:
    required_files = [
        APP_ROOT / "index.html",
        APP_ROOT / "gallery.html",
        APP_ROOT / "styles.css",
        APP_ROOT / "app.js",
        APP_ROOT / "gallery.js",
        CAPTURE_MANIFEST,
        FRAMEWORK_MANIFEST,
        GATES_MANIFEST,
    ]
    for path in required_files:
        if not path.exists():
            raise SystemExit(f"missing required UI file: {path}")

    for path in [
        APP_ROOT / "index.html",
        APP_ROOT / "gallery.html",
        APP_ROOT / "app.js",
        APP_ROOT / "gallery.js",
        APP_ROOT / "styles.css",
    ]:
        text = path.read_text(encoding="utf-8")
        blocked_markers = ["https://", "http://", "unpkg.com", "cdn.jsdelivr", "cdnjs"]
        for marker in blocked_markers:
            if marker in text:
                raise SystemExit(f"external UI dependency marker {marker!r} found in {path}")

    package_manifest = REPO_ROOT / "package.json"
    if package_manifest.exists():
        packages = read_json(package_manifest).get("dependencies", {})
        expected = {
            "@sparkjsdev/spark": "2.1.0",
            "three": "0.180.0",
        }
        for name, version in expected.items():
            if packages.get(name) != version:
                raise SystemExit(f"UI package dependency {name} must be pinned to {version}")

        package_lock = REPO_ROOT / "package-lock.json"
        if package_lock.exists():
            locked_packages = read_json(package_lock).get("packages", {})
            locked_fflate = locked_packages.get("node_modules/fflate", {}).get("version")
            if locked_fflate != "0.8.3":
                raise SystemExit("UI transitive dependency fflate must be locked to 0.8.3")

    state = build_state()
    if not state["captures"]:
        raise SystemExit("UI state has no captures")
    if not state["gates"]:
        raise SystemExit("UI state has no pipeline gates")
    print("ui_contract_validation=passed")


class LabUiHandler(BaseHTTPRequestHandler):
    server_version = "GaussianSplatLabUI/0.1"

    def log_message(self, format: str, *args: Any) -> None:
        return

    def send_json(self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_artifact(self, raw_path: str) -> None:
        try:
            artifact = resolve_artifact_path(raw_path)
        except ValueError:
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        content_type = mimetypes.guess_type(str(artifact))[0] or "application/octet-stream"
        if artifact.suffix == ".ply":
            content_type = "application/octet-stream"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(artifact.stat().st_size))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        with artifact.open("rb") as handle:
            shutil.copyfileobj(handle, self.wfile, length=1024 * 1024)

    def send_node_module(self, raw_path: str) -> None:
        try:
            module_file = resolve_node_module_path(raw_path)
        except ValueError:
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        body = module_file.read_bytes()
        content_type = mimetypes.guess_type(str(module_file))[0] or "application/octet-stream"
        if module_file.suffix in {".js", ".mjs"}:
            content_type = "text/javascript; charset=utf-8"
        elif module_file.suffix == ".map":
            content_type = "application/json; charset=utf-8"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def send_static(self, path: Path) -> None:
        try:
            resolved = path.resolve()
            resolved.relative_to(APP_ROOT.resolve())
        except ValueError:
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        if not resolved.exists() or not resolved.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        body = resolved.read_bytes()
        content_type = mimetypes.guess_type(str(resolved))[0] or "application/octet-stream"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path == "/api/state":
            try:
                self.send_json(build_state())
            except Exception as exc:  # noqa: BLE001 - user-facing local server boundary
                self.send_json({"error": str(exc)}, HTTPStatus.INTERNAL_SERVER_ERROR)
            return

        parsed = urlparse(self.path)
        route = parsed.path
        if route == "/api/jobs/progress":
            try:
                query = parse_qs(parsed.query)
                job_path = resolve_job_path(query.get("jobPath", [""])[0])
                self.send_json(job_progress(job_path))
            except ValueError as exc:
                self.send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
            except Exception as exc:  # noqa: BLE001 - user-facing local server boundary
                self.send_json({"error": str(exc)}, HTTPStatus.INTERNAL_SERVER_ERROR)
            return
        if route == "/api/gallery":
            try:
                self.send_json({"items": gallery_jobs()})
            except Exception as exc:  # noqa: BLE001 - user-facing local server boundary
                self.send_json({"error": str(exc)}, HTTPStatus.INTERNAL_SERVER_ERROR)
            return
        if route.startswith("/api/gallery/jobs/"):
            try:
                self.send_json(gallery_job_detail(route.removeprefix("/api/gallery/jobs/")))
            except ValueError as exc:
                self.send_json({"error": str(exc)}, HTTPStatus.NOT_FOUND)
            except Exception as exc:  # noqa: BLE001 - user-facing local server boundary
                self.send_json({"error": str(exc)}, HTTPStatus.INTERNAL_SERVER_ERROR)
            return
        if route.startswith("/api/artifacts/"):
            self.send_artifact(route.removeprefix("/api/artifacts/"))
            return
        if route.startswith("/node_modules/"):
            self.send_node_module(route.removeprefix("/node_modules/"))
            return
        if route == "/":
            self.send_static(APP_ROOT / "index.html")
            return
        if route == "/gallery":
            self.send_static(APP_ROOT / "gallery.html")
            return

        self.send_static(APP_ROOT / route.lstrip("/"))

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        route = parsed.path
        if route not in {"/api/jobs", "/api/jobs/run-stage", "/api/captures/import-video", "/api/captures/create-upload"}:
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            if route == "/api/captures/create-upload":
                query = parse_qs(parsed.query)
                upload_name = self.headers.get("X-Filename")
                capture = build_uploaded_capture(query, upload_name)
                capture_id = str(capture["id"])
                upsert_local_capture(capture)
                try:
                    result = save_capture_upload(
                        capture_id=capture_id,
                        stream=self.rfile,
                        content_length=length,
                        upload_name=upload_name,
                        accept_warning=True,
                        overwrite=True,
                        manifest_path=active_capture_manifest(),
                    )
                except Exception:
                    remove_local_capture(capture_id)
                    raise
                status = result.get("report", {}).get("status")
                http_status = HTTPStatus.CREATED if status == "pass" else HTTPStatus.CONFLICT
                self.send_json({"capture": capture, **result}, http_status)
                return

            if route == "/api/captures/import-video":
                query = parse_qs(parsed.query)
                capture_id = query.get("captureId", [""])[0]
                if not capture_id:
                    self.send_json({"error": "captureId is required"}, HTTPStatus.BAD_REQUEST)
                    return
                result = save_capture_upload(
                    capture_id=capture_id,
                    stream=self.rfile,
                    content_length=length,
                    upload_name=self.headers.get("X-Filename"),
                    accept_warning=parse_bool_query(query.get("acceptWarning", [""])[0]),
                    overwrite=parse_bool_query(query.get("overwrite", [""])[0]),
                )
                status = result.get("report", {}).get("status")
                http_status = HTTPStatus.CREATED if status == "pass" else HTTPStatus.CONFLICT
                self.send_json(result, http_status)
                return

            payload = json.loads(self.rfile.read(length) or b"{}")
            if route == "/api/jobs":
                capture_id = payload.get("captureId")
                if not isinstance(capture_id, str) or not capture_id:
                    self.send_json({"error": "captureId is required"}, HTTPStatus.BAD_REQUEST)
                    return
                if not run_validator("validate-architecture-contracts.sh"):
                    self.send_json({"error": "architecture validation failed"}, HTTPStatus.CONFLICT)
                    return
                job = create_job(capture_id)
                self.send_json({"job": job}, HTTPStatus.CREATED)
                return

            job_path = resolve_job_path(payload.get("jobPath"))
            stage = payload.get("stage")
            accept_warning = bool(payload.get("acceptWarning", False))
            allow_heavy = bool(payload.get("allowHeavy", False))
            training_profile = payload.get("trainingProfile")
            if not isinstance(training_profile, str):
                training_profile = None
            if not isinstance(stage, str) or not stage:
                self.send_json({"error": "stage is required"}, HTTPStatus.BAD_REQUEST)
                return
            result = run_job_stage(
                job_path,
                stage,
                accept_warning=accept_warning,
                allow_heavy=allow_heavy,
                training_profile=training_profile,
            )
            self.send_json(result)
        except ValueError as exc:
            self.send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
        except subprocess.TimeoutExpired:
            self.send_json({"error": "stage run timed out"}, HTTPStatus.REQUEST_TIMEOUT)
        except Exception as exc:  # noqa: BLE001 - user-facing local server boundary
            self.send_json({"error": str(exc)}, HTTPStatus.INTERNAL_SERVER_ERROR)

    def do_DELETE(self) -> None:
        route = self.path.split("?", 1)[0]
        if not route.startswith("/api/gallery/jobs/"):
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        try:
            result = delete_gallery_job(route.removeprefix("/api/gallery/jobs/"))
            self.send_json(result)
        except ValueError as exc:
            self.send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
        except Exception as exc:  # noqa: BLE001 - user-facing local server boundary
            self.send_json({"error": str(exc)}, HTTPStatus.INTERNAL_SERVER_ERROR)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the local Gaussian Splat Lab UI.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--check", action="store_true", help="Validate UI contracts and exit.")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.check:
        validate_ui_contracts()
        return 0

    server = ThreadingHTTPServer((args.host, args.port), LabUiHandler)
    url = f"http://{args.host}:{server.server_port}"
    print(f"lab_ui_url={url}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
