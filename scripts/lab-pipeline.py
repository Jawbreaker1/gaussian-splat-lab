#!/usr/bin/env python3
"""Small manifest-driven skeleton for the Gaussian Splat lab pipeline."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import math
import json
import os
import platform
import re
import shutil
import struct
import subprocess
import sys
import sysconfig
import time
import statistics
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


HEAVY_STAGES = {"sfm", "splat_training", "viewer"}

TRAINING_PROFILE_DEFAULTS: dict[str, dict[str, Any]] = {
    "smoke": {
        "iterations": 40,
        "maxImages": 8,
        "maxPoints": 6000,
        "maxRenderSize": 384,
        "maxGaussians": 6000,
        "sampleEvery": 5,
        "reviewSamples": 2,
        "initialOpacity": 0.55,
        "initialScaleMultiplier": 1.0,
        "ssimWeight": 0.0,
        "meanLr": 0.0005,
        "colorLr": 0.02,
        "scaleLr": 0.001,
        "opacityLr": 0.01,
        "quatLr": 0.0005,
        "densifyStrategy": "none",
        "refineStartIter": 500,
        "refineStopIter": 15000,
        "refineEvery": 100,
        "resetEvery": 3000,
        "growGrad2d": 0.0002,
        "growScale3d": 0.01,
        "pruneOpa": 0.005,
        "absgrad": False,
    },
    "baseline": {
        "iterations": 800,
        "maxImages": 32,
        "maxPoints": 50000,
        "maxRenderSize": 640,
        "maxGaussians": 60000,
        "sampleEvery": 50,
        "reviewSamples": 5,
        "initialOpacity": 0.55,
        "initialScaleMultiplier": 1.0,
        "ssimWeight": 0.0,
        "meanLr": 0.0005,
        "colorLr": 0.02,
        "scaleLr": 0.001,
        "opacityLr": 0.01,
        "quatLr": 0.0005,
        "densifyStrategy": "default",
        "refineStartIter": 100,
        "refineStopIter": 780,
        "refineEvery": 50,
        "resetEvery": 3000,
        "growGrad2d": 0.0002,
        "growScale3d": 0.01,
        "pruneOpa": 0.005,
        "absgrad": False,
    },
    "quality_probe": {
        "iterations": 2500,
        "maxImages": 48,
        "maxPoints": 80000,
        "maxRenderSize": 768,
        "maxGaussians": 120000,
        "sampleEvery": 100,
        "reviewSamples": 6,
        "initialOpacity": 0.12,
        "initialScaleMultiplier": 0.35,
        "ssimWeight": 0.2,
        "meanLr": 0.00035,
        "colorLr": 0.025,
        "scaleLr": 0.004,
        "opacityLr": 0.02,
        "quatLr": 0.0007,
        "densifyStrategy": "default",
        "refineStartIter": 100,
        "refineStopIter": 2400,
        "refineEvery": 100,
        "resetEvery": 3000,
        "growGrad2d": 0.00015,
        "growScale3d": 0.006,
        "pruneOpa": 0.003,
        "absgrad": False,
    },
    "rtx_reference": {
        "iterations": 9000,
        "maxImages": 64,
        "maxPoints": 120000,
        "maxRenderSize": 1280,
        "maxGaussians": 400000,
        "sampleEvery": 250,
        "reviewSamples": 10,
        "initialOpacity": 0.08,
        "initialScaleMultiplier": 0.25,
        "ssimWeight": 0.25,
        "meanLr": 0.00025,
        "colorLr": 0.018,
        "scaleLr": 0.003,
        "opacityLr": 0.015,
        "quatLr": 0.0005,
        "densifyStrategy": "default",
        "refineStartIter": 100,
        "refineStopIter": 7600,
        "refineEvery": 100,
        "resetEvery": 3000,
        "growGrad2d": 0.00008,
        "growScale3d": 0.004,
        "pruneOpa": 0.0015,
        "absgrad": False,
    },
    "rtx_high_quality": {
        "iterations": 18000,
        "maxImages": 112,
        "maxPoints": 220000,
        "maxRenderSize": 1600,
        "maxGaussians": 1000000,
        "sampleEvery": 300,
        "reviewSamples": 14,
        "initialOpacity": 0.07,
        "initialScaleMultiplier": 0.22,
        "ssimWeight": 0.26,
        "meanLr": 0.00022,
        "colorLr": 0.016,
        "scaleLr": 0.0028,
        "opacityLr": 0.013,
        "quatLr": 0.00048,
        "densifyStrategy": "default",
        "refineStartIter": 100,
        "refineStopIter": 15500,
        "refineEvery": 100,
        "resetEvery": 3000,
        "growGrad2d": 0.000065,
        "growScale3d": 0.0035,
        "pruneOpa": 0.0012,
        "absgrad": False,
    },
    "rtx_ultra_quality": {
        "iterations": 24000,
        "maxImages": 144,
        "maxPoints": 280000,
        "maxRenderSize": 1600,
        "maxGaussians": 1600000,
        "sampleEvery": 400,
        "reviewSamples": 16,
        "initialOpacity": 0.065,
        "initialScaleMultiplier": 0.21,
        "ssimWeight": 0.27,
        "meanLr": 0.00021,
        "colorLr": 0.015,
        "scaleLr": 0.0026,
        "opacityLr": 0.0125,
        "quatLr": 0.00046,
        "densifyStrategy": "default",
        "refineStartIter": 100,
        "refineStopIter": 20500,
        "refineEvery": 100,
        "resetEvery": 3000,
        "growGrad2d": 0.000058,
        "growScale3d": 0.0032,
        "pruneOpa": 0.0011,
        "absgrad": False,
    },
    "rtx_stable_quality": {
        "iterations": 30000,
        "maxImages": 144,
        "maxPoints": 280000,
        "maxRenderSize": 1600,
        "maxGaussians": 1600000,
        "sampleEvery": 500,
        "reviewSamples": 24,
        "initialOpacity": 0.065,
        "initialScaleMultiplier": 0.21,
        "ssimWeight": 0.27,
        "meanLr": 0.00021,
        "colorLr": 0.015,
        "scaleLr": 0.0026,
        "opacityLr": 0.0125,
        "quatLr": 0.00046,
        "densifyStrategy": "default",
        "refineStartIter": 100,
        "refineStopIter": 20500,
        "refineEvery": 100,
        "resetEvery": 3000,
        "growGrad2d": 0.000058,
        "growScale3d": 0.0032,
        "pruneOpa": 0.0011,
        "absgrad": False,
    },
    "rtx_ceiling_quality": {
        "iterations": 30000,
        "maxImages": 173,
        "maxPoints": 340000,
        "maxRenderSize": 1600,
        "maxGaussians": 2000000,
        "sampleEvery": 500,
        "reviewSamples": 18,
        "initialOpacity": 0.06,
        "initialScaleMultiplier": 0.19,
        "ssimWeight": 0.28,
        "meanLr": 0.0002,
        "colorLr": 0.014,
        "scaleLr": 0.0024,
        "opacityLr": 0.012,
        "quatLr": 0.00044,
        "densifyStrategy": "default",
        "refineStartIter": 100,
        "refineStopIter": 25500,
        "refineEvery": 100,
        "resetEvery": 3000,
        "growGrad2d": 0.000062,
        "growScale3d": 0.003,
        "pruneOpa": 0.0012,
        "absgrad": False,
    },
    "rtx_max_quality": {
        "iterations": 30000,
        "maxImages": 160,
        "maxPoints": 300000,
        "maxRenderSize": 1600,
        "maxGaussians": 2500000,
        "sampleEvery": 500,
        "reviewSamples": 16,
        "initialOpacity": 0.06,
        "initialScaleMultiplier": 0.2,
        "ssimWeight": 0.28,
        "meanLr": 0.0002,
        "colorLr": 0.014,
        "scaleLr": 0.0025,
        "opacityLr": 0.012,
        "quatLr": 0.00045,
        "densifyStrategy": "default",
        "refineStartIter": 100,
        "refineStopIter": 26000,
        "refineEvery": 100,
        "resetEvery": 3000,
        "growGrad2d": 0.00005,
        "growScale3d": 0.003,
        "pruneOpa": 0.001,
        "absgrad": False,
    },
}
DENSIFY_STRATEGIES = {"none", "default"}

SPLATFACTO_PROFILE_DEFAULTS: dict[str, dict[str, Any]] = {
    "splatfacto_preview": {
        "method": "splatfacto",
        "iterations": 1000,
        "downscaleFactor": 2,
        "cacheImages": "cpu",
        "evalInterval": 8,
        "stepsPerEvalImage": 500,
        "stepsPerEvalAllImages": 1000,
        "stepsPerSave": 1000,
        "estimatedSeconds": 10 * 60,
        "timeoutSeconds": 2 * 60 * 60,
    },
    "splatfacto_reference": {
        "method": "splatfacto",
        "iterations": 30000,
        "downscaleFactor": 2,
        "cacheImages": "cpu",
        "evalInterval": 8,
        "stepsPerEvalImage": 5000,
        "stepsPerEvalAllImages": 30000,
        "stepsPerSave": 30000,
        "estimatedSeconds": 45 * 60,
        "timeoutSeconds": 8 * 60 * 60,
    },
    "splatfacto_big_quality": {
        "method": "splatfacto-big",
        "iterations": 30000,
        "downscaleFactor": 2,
        "cacheImages": "cpu",
        "evalInterval": 8,
        "stepsPerEvalImage": 5000,
        "stepsPerEvalAllImages": 30000,
        "stepsPerSave": 30000,
        "estimatedSeconds": 90 * 60,
        "timeoutSeconds": 12 * 60 * 60,
    },
    "splatfacto_ceiling": {
        "method": "splatfacto-big",
        "iterations": 30000,
        "downscaleFactor": 1,
        "cacheImages": "cpu",
        "evalInterval": 8,
        "stepsPerEvalImage": 5000,
        "stepsPerEvalAllImages": 30000,
        "stepsPerSave": 30000,
        "estimatedSeconds": 2 * 60 * 60,
        "timeoutSeconds": 20 * 60 * 60,
    },
}

TRAINING_TIMEOUT_SECONDS: dict[str, int] = {
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


STAGES = [
    {
        "id": "framework_license",
        "group": "preflight",
        "label": "Dependency review",
        "reads": "FrameworkEvaluation",
        "writes": "FrameworkDecisionReport",
    },
    {
        "id": "environment",
        "group": "preflight",
        "label": "Workstation check",
        "reads": "MachineRuntime",
        "writes": "EnvironmentReport",
    },
    {
        "id": "intake",
        "group": "media_pipeline",
        "label": "Input intake",
        "reads": "CaptureInput",
        "writes": "CaptureMetadata",
    },
    {
        "id": "frame_sampling",
        "group": "media_pipeline",
        "label": "Frame sampling",
        "reads": "CaptureMetadata",
        "writes": "FrameManifest",
    },
    {
        "id": "sfm",
        "group": "media_pipeline",
        "label": "SfM camera solve",
        "reads": "FrameManifest",
        "writes": "CameraSolveReport",
    },
    {
        "id": "splat_training",
        "group": "media_pipeline",
        "label": "Splat training",
        "reads": "CameraSolveReport",
        "writes": "TrainingRunReport",
    },
    {
        "id": "packaging",
        "group": "media_pipeline",
        "label": "Artifact packaging",
        "reads": "TrainingRunReport",
        "writes": "SplatArtifact",
    },
    {
        "id": "viewer",
        "group": "media_pipeline",
        "label": "Viewer validation",
        "reads": "SplatArtifact",
        "writes": "ViewerValidationReport",
    },
    {
        "id": "quality_report",
        "group": "media_pipeline",
        "label": "Quality report",
        "reads": "StageReports",
        "writes": "CaptureQualityReport",
    },
]


@dataclass(frozen=True)
class CaptureSelection:
    manifest_path: Path
    capture: dict[str, Any]


PLAIN_VIDEO_INPUT_KIND = "plain_video"
COLMAP_DATASET_INPUT_KIND = "colmap_dataset"
NERFSTUDIO_DATASET_INPUT_KIND = "nerfstudio_dataset"
RGBD_CAPTURE_BUNDLE_INPUT_KIND = "rgbd_capture_bundle"
SUPPORTED_INPUT_KINDS = {
    PLAIN_VIDEO_INPUT_KIND,
    COLMAP_DATASET_INPUT_KIND,
    NERFSTUDIO_DATASET_INPUT_KIND,
    RGBD_CAPTURE_BUNDLE_INPUT_KIND,
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
                "group": stage.get("group", "media_pipeline"),
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


def external_tool_binary(name: str, env_var: str, env: dict[str, str] | None = None) -> str:
    source = env if env is not None else os.environ
    override = str(source.get(env_var) or "").strip()
    return override or name


def colmap_command(*args: str, env: dict[str, str] | None = None) -> list[str]:
    return [external_tool_binary("colmap", "GSL_COLMAP_BIN", env), *args]


_COLMAP_OPTION_HELP_CACHE: dict[tuple[str, str], str] = {}


def colmap_command_help(command_name: str) -> str:
    binary = external_tool_binary("colmap", "GSL_COLMAP_BIN")
    cache_key = (binary, command_name)
    cached = _COLMAP_OPTION_HELP_CACHE.get(cache_key)
    if cached is not None:
        return cached

    result = run_command(colmap_command(command_name, "--help"), timeout_seconds=15)
    help_text = "\n".join(
        str(result.get(key) or "")
        for key in ("stdout", "stderr")
    )
    _COLMAP_OPTION_HELP_CACHE[cache_key] = help_text
    return help_text


def colmap_option(command_name: str, legacy_name: str, current_name: str) -> str:
    help_text = colmap_command_help(command_name)
    if f"--{current_name}" in help_text:
        return f"--{current_name}"
    return f"--{legacy_name}"


def run_command(command: list[str], timeout_seconds: int = 20, env: dict[str, str] | None = None) -> dict[str, Any]:
    executable = shutil.which(command[0], path=env.get("PATH") if env else None)
    if executable is None:
        return {
            "name": command[0],
            "command": command,
            "executable": None,
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
            env=env,
            text=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "name": command[0],
            "command": command,
            "executable": executable,
            "status": "fail",
            "exitCode": None,
            "stdout": exc.stdout or "",
            "stderr": f"command timed out after {timeout_seconds}s",
        }

    return {
        "name": command[0],
        "command": command,
        "executable": executable,
        "status": "pass" if result.returncode == 0 else "fail",
        "exitCode": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }


def command_summary(command_result: dict[str, Any], max_lines: int = 8) -> str:
    text = command_result.get("stdout") or command_result.get("stderr") or ""
    lines = [line for line in str(text).splitlines() if line.strip()]
    return "\n".join(lines[:max_lines])


def nvidia_smi_status(command_result: dict[str, Any]) -> str:
    if command_result.get("status") != "fail":
        return str(command_result.get("status") or "fail")
    text = f"{command_result.get('stdout') or ''}\n{command_result.get('stderr') or ''}"
    if "GPU access blocked by the operating system" in text:
        return "setup_gap"
    return "fail"


def optional_float(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def parse_nvidia_smi_query_line(line: str) -> dict[str, Any]:
    fields = [field.strip() for field in line.split(",")]
    return {
        "timestamp": fields[0] if len(fields) > 0 else None,
        "name": fields[1] if len(fields) > 1 else None,
        "temperatureGpuC": optional_float(fields[2] if len(fields) > 2 else None),
        "powerDrawW": optional_float(fields[3] if len(fields) > 3 else None),
        "memoryUsedMiB": optional_float(fields[4] if len(fields) > 4 else None),
        "memoryTotalMiB": optional_float(fields[5] if len(fields) > 5 else None),
        "utilizationGpuPercent": optional_float(fields[6] if len(fields) > 6 else None),
    }


def parse_nvidia_smi_process_line(line: str) -> dict[str, Any]:
    fields = [field.strip() for field in line.split(",")]
    return {
        "pid": int(fields[0]) if len(fields) > 0 and fields[0].isdigit() else None,
        "processName": fields[1] if len(fields) > 1 else None,
        "usedMemoryMiB": optional_float(fields[2] if len(fields) > 2 else None),
    }


def gpu_load_snapshot(env: dict[str, str] | None = None) -> dict[str, Any]:
    gpu_query = run_command(
        [
            "nvidia-smi",
            "--query-gpu=timestamp,name,temperature.gpu,power.draw,memory.used,memory.total,utilization.gpu",
            "--format=csv,noheader,nounits",
        ],
        timeout_seconds=10,
        env=env,
    )
    process_query = run_command(
        [
            "nvidia-smi",
            "--query-compute-apps=pid,process_name,used_memory",
            "--format=csv,noheader,nounits",
        ],
        timeout_seconds=10,
        env=env,
    )

    gpus = [
        parse_nvidia_smi_query_line(line)
        for line in str(gpu_query.get("stdout") or "").splitlines()
        if line.strip()
    ]
    processes = [
        parse_nvidia_smi_process_line(line)
        for line in str(process_query.get("stdout") or "").splitlines()
        if line.strip()
    ]
    active_processes = [
        process
        for process in processes
        if process.get("pid") is not None and process.get("usedMemoryMiB") is not None
    ]
    max_util = max((gpu.get("utilizationGpuPercent") or 0.0 for gpu in gpus), default=0.0)
    max_memory_fraction = max(
        (
            (gpu.get("memoryUsedMiB") or 0.0) / max(gpu.get("memoryTotalMiB") or 1.0, 1.0)
            for gpu in gpus
        ),
        default=0.0,
    )
    status = "warning" if active_processes or max_util >= 25.0 or max_memory_fraction >= 0.25 else "pass"
    if gpu_query.get("status") != "pass":
        status = "warning"
    return {
        "status": status,
        "summary": "GPU appears idle enough for a clean training run" if status == "pass" else "GPU baseline is busy or unavailable; training quality/runtime comparisons may be noisy",
        "gpus": gpus,
        "computeProcesses": active_processes,
        "ignoredComputeProcesses": [process for process in processes if process not in active_processes],
        "commands": {
            "gpuQuery": gpu_query,
            "processQuery": process_query,
        },
    }


def check_python_dev_headers() -> dict[str, Any]:
    include_path = sysconfig.get_path("include")
    header_path = Path(include_path) / "Python.h" if include_path else None
    package_hint = f"python{sys.version_info.major}.{sys.version_info.minor}-dev"
    header_exists = bool(header_path and header_path.exists())
    return {
        "id": "python_dev_headers",
        "status": "pass" if header_exists else "setup_gap",
        "summary": "Python development headers are available" if header_exists else f"Python.h is missing; install {package_hint}",
        "path": str(header_path) if header_path else None,
        "required": package_hint,
    }


def check_ninja_available(env: dict[str, str] | None = None) -> dict[str, Any]:
    search_path = (env or os.environ).get("PATH")
    ninja_path = shutil.which("ninja", path=search_path)
    return {
        "id": "ninja",
        "status": "pass" if ninja_path else "setup_gap",
        "summary": "ninja is visible to torch extension builds" if ninja_path else "ninja is missing from PATH; install the ninja Python package or system package",
        "path": ninja_path,
        "required": "ninja",
    }


def cuda_home_candidate() -> Path | None:
    raw_cuda_home = os.environ.get("CUDA_HOME")
    if raw_cuda_home:
        return Path(raw_cuda_home)
    for candidate in (Path("/usr/local/cuda-12.8"), Path("/usr/local/cuda")):
        if (candidate / "bin" / "nvcc").exists():
            return candidate
    return None


def build_training_subprocess_environment(torch_cuda: dict[str, Any]) -> tuple[dict[str, str], dict[str, Any]]:
    env = os.environ.copy()
    path_prepend: list[str] = []

    virtual_env = os.environ.get("VIRTUAL_ENV")
    venv_bin = Path(virtual_env) / "bin" if virtual_env else Path(sys.executable).parent
    if venv_bin.exists():
        path_prepend.append(str(venv_bin))

    cuda_home = cuda_home_candidate()
    if cuda_home is not None:
        env["CUDA_HOME"] = str(cuda_home)
        cuda_bin = cuda_home / "bin"
        if cuda_bin.exists():
            path_prepend.append(str(cuda_bin))

    current_path = env.get("PATH", "")
    env["PATH"] = os.pathsep.join(path_prepend + ([current_path] if current_path else []))

    if not env.get("TORCH_CUDA_ARCH_LIST"):
        capability = torch_cuda.get("deviceCapability")
        if isinstance(capability, (list, tuple)) and len(capability) >= 2:
            env["TORCH_CUDA_ARCH_LIST"] = f"{capability[0]}.{capability[1]}"
        else:
            env["TORCH_CUDA_ARCH_LIST"] = "12.0"
    env.setdefault("MAX_JOBS", "4")

    return env, {
        "CUDA_HOME": env.get("CUDA_HOME"),
        "PATH_PREPEND": path_prepend,
        "TORCH_CUDA_ARCH_LIST": env.get("TORCH_CUDA_ARCH_LIST"),
        "MAX_JOBS": env.get("MAX_JOBS"),
    }


def nerfstudio_venv_paths() -> dict[str, Path]:
    venv = repo_root_from_script() / ".venv-nerfstudio-py312"
    bin_dir = venv / "bin"
    return {
        "venv": venv,
        "bin": bin_dir,
        "python": bin_dir / "python",
        "ns_train": bin_dir / "ns-train",
        "ns_export": bin_dir / "ns-export",
        "ns_eval": bin_dir / "ns-eval",
    }


def build_nerfstudio_environment() -> tuple[dict[str, str], dict[str, Any]]:
    env = os.environ.copy()
    paths = nerfstudio_venv_paths()
    path_prepend: list[str] = []
    if paths["bin"].exists():
        path_prepend.append(str(paths["bin"]))

    cuda_home = cuda_home_candidate()
    if cuda_home is not None:
        env["CUDA_HOME"] = str(cuda_home)
        cuda_bin = cuda_home / "bin"
        if cuda_bin.exists():
            path_prepend.append(str(cuda_bin))
        cuda_lib = cuda_home / "lib64"
        if cuda_lib.exists():
            existing_ld = env.get("LD_LIBRARY_PATH", "")
            env["LD_LIBRARY_PATH"] = os.pathsep.join(
                [str(cuda_lib)] + ([existing_ld] if existing_ld else [])
            )

    current_path = env.get("PATH", "")
    env["PATH"] = os.pathsep.join(path_prepend + ([current_path] if current_path else []))
    env.setdefault("MPLCONFIGDIR", "/tmp/gsl-mpl")
    env.setdefault("WANDB_MODE", "disabled")
    env.setdefault(
        "TORCH_EXTENSIONS_DIR",
        str(repo_root_from_script() / "outputs" / "experiments" / "nerfstudio" / "torch_extensions"),
    )
    env.setdefault("TORCH_CUDA_ARCH_LIST", "12.0")
    env.setdefault("MAX_JOBS", "4")
    # Nerfstudio 1.1.5 checkpoints are produced locally by this pipeline. PyTorch
    # 2.6+ defaults otherwise reject them during export/eval.
    env.setdefault("TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD", "1")
    return env, {
        "venv": str(paths["venv"]),
        "CUDA_HOME": env.get("CUDA_HOME"),
        "PATH_PREPEND": path_prepend,
        "LD_LIBRARY_PATH_PREPEND": [env.get("LD_LIBRARY_PATH", "").split(os.pathsep)[0]]
        if env.get("LD_LIBRARY_PATH")
        else [],
        "TORCH_EXTENSIONS_DIR": env.get("TORCH_EXTENSIONS_DIR"),
        "TORCH_CUDA_ARCH_LIST": env.get("TORCH_CUDA_ARCH_LIST"),
        "MAX_JOBS": env.get("MAX_JOBS"),
    }


def tail_text(path: Path, max_chars: int = 8000) -> str:
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8", errors="replace")
    if len(text) <= max_chars:
        return text
    return f"... [truncated]\n{text[-max_chars:]}"


def write_training_progress(progress_path: Path, payload: dict[str, Any]) -> None:
    try:
        write_json(progress_path, payload)
    except Exception:
        # Progress is best-effort. The stage report is authoritative.
        return


NERFSTUDIO_PROGRESS_PATTERN = re.compile(
    r"(?m)^\s*(\d+)\s+\(([\d.]+)%\)\s+([\d.]+)\s+ms\s+([^\n]+?)\s+([\d.]+\s+[KMG])"
)


def parse_nerfstudio_training_progress(log_path: Path) -> dict[str, Any] | None:
    text = tail_text(log_path, max_chars=200_000)
    if not text:
        return None
    clean = re.sub(r"\x1b\[[0-9;?]*[A-Za-z]", "", text)
    matches = list(NERFSTUDIO_PROGRESS_PATTERN.finditer(clean))
    if not matches:
        return None
    match = matches[-1]
    return {
        "iteration": int(match.group(1)),
        "percent": float(match.group(2)),
        "trainIterationMs": float(match.group(3)),
        "etaText": match.group(4).strip(),
        "trainRaysPerSec": match.group(5).strip(),
    }


def run_logged_command_with_estimated_progress(
    command: list[str],
    *,
    timeout_seconds: int,
    env: dict[str, str],
    log_path: Path,
    progress_path: Path,
    progress_base: dict[str, Any],
    estimated_total_seconds: int,
) -> dict[str, Any]:
    executable = shutil.which(command[0], path=env.get("PATH"))
    if executable is None:
        return {
            "name": command[0],
            "command": command,
            "status": "setup_gap",
            "exitCode": None,
            "stdout": "",
            "stderr": f"{command[0]} not found on PATH",
        }

    log_path.parent.mkdir(parents=True, exist_ok=True)
    start = time.monotonic()
    timed_out = False
    exit_code: int | None = None
    with log_path.open("w", encoding="utf-8", errors="replace") as log_handle:
        process = subprocess.Popen(
            command,
            cwd=repo_root_from_script(),
            env=env,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            text=True,
        )
        while True:
            exit_code = process.poll()
            elapsed = max(time.monotonic() - start, 0.0)
            iterations = int(progress_base.get("iterations") or 0)
            parsed_progress = parse_nerfstudio_training_progress(log_path)
            if parsed_progress is not None:
                percent = min(max(float(parsed_progress["percent"]), 0.0), 99.99)
                iteration = int(parsed_progress["iteration"])
                estimated_from_progress = int(round(elapsed / max(percent / 100.0, 0.001)))
                effective_estimated_total = max(estimated_from_progress, int(elapsed))
                progress_details = {
                    "trainIterationMs": parsed_progress.get("trainIterationMs"),
                    "etaText": parsed_progress.get("etaText"),
                    "trainRaysPerSec": parsed_progress.get("trainRaysPerSec"),
                    "progressSource": "nerfstudio_log",
                }
            else:
                percent = min((elapsed / max(float(estimated_total_seconds), 1.0)) * 100.0, 96.0)
                iteration = int(iterations * percent / 100.0)
                effective_estimated_total = estimated_total_seconds
                progress_details = {"progressSource": "wall_clock_estimate"}
            write_training_progress(
                progress_path,
                {
                    **progress_base,
                    "status": "running" if exit_code is None else "pass",
                    "percent": round(percent, 2) if exit_code is None else 100.0,
                    "iteration": iteration if exit_code is None else iterations,
                    "elapsedSeconds": round(elapsed, 1),
                    "estimatedTotalSeconds": effective_estimated_total,
                    "updatedAt": utc_now(),
                    **progress_details,
                },
            )
            if exit_code is not None:
                break
            if elapsed > timeout_seconds:
                timed_out = True
                process.kill()
                exit_code = process.wait()
                break
            time.sleep(5)

    elapsed = max(time.monotonic() - start, 0.0)
    output_tail = tail_text(log_path)
    final_status = "fail" if timed_out else ("pass" if exit_code == 0 else "fail")
    write_training_progress(
        progress_path,
        {
            **progress_base,
            "status": final_status,
            "percent": 100.0 if final_status == "pass" else min(
                (elapsed / max(float(estimated_total_seconds), 1.0)) * 100.0,
                100.0,
            ),
            "iteration": int(progress_base.get("iterations") or 0) if final_status == "pass" else None,
            "elapsedSeconds": round(elapsed, 1),
            "estimatedTotalSeconds": estimated_total_seconds,
            "updatedAt": utc_now(),
        },
    )
    return {
        "name": command[0],
        "command": command,
        "status": final_status,
        "exitCode": exit_code,
        "stdout": output_tail,
        "stderr": f"command timed out after {timeout_seconds}s" if timed_out else "",
        "logPath": str(log_path),
        "wallTimeSeconds": round(elapsed, 3),
        "timeoutSeconds": timeout_seconds,
    }


def link_or_copytree(source: Path, target: Path) -> None:
    if target.exists() or target.is_symlink():
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.symlink(source.resolve(), target, target_is_directory=True)
    except OSError:
        shutil.copytree(source, target)


def link_or_copyfile(source: Path, target: Path) -> None:
    if target.exists() or target.is_symlink():
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.symlink(source.resolve(), target)
    except OSError:
        shutil.copy2(source, target)


def prepare_downscaled_images(source_dir: Path, output_dir: Path, factor: int) -> int:
    if factor <= 1:
        return 0
    output_dir.mkdir(parents=True, exist_ok=True)
    suffixes = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff"}
    source_images = sorted(path for path in source_dir.iterdir() if path.suffix.lower() in suffixes)
    existing = [path for path in output_dir.iterdir() if path.suffix.lower() in suffixes] if output_dir.exists() else []
    if len(existing) >= len(source_images) and source_images:
        return len(existing)

    from PIL import Image  # type: ignore[import-not-found]

    for source in source_images:
        target = output_dir / source.name
        if target.exists():
            continue
        with Image.open(source) as image:
            width = max(1, image.width // factor)
            height = max(1, image.height // factor)
            resized = image.convert("RGB").resize((width, height), Image.Resampling.LANCZOS)
            save_kwargs: dict[str, Any] = {}
            if target.suffix.lower() in {".jpg", ".jpeg"}:
                save_kwargs = {"quality": 94, "subsampling": 1, "optimize": True}
            resized.save(target, **save_kwargs)
    return len(source_images)


def prepare_colmap_source_images(
    source_dir: Path,
    output_dir: Path,
    expected_size: tuple[int, int] | None,
) -> dict[str, Any]:
    if expected_size is None:
        link_or_copytree(source_dir, output_dir)
        return {
            "mode": "linked_original",
            "sourceDirectory": str(source_dir),
            "imageDirectory": str(output_dir),
            "normalizedImageCount": 0,
        }

    suffixes = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff"}
    source_images = sorted(path for path in source_dir.iterdir() if path.is_file() and path.suffix.lower() in suffixes)
    if not source_images:
        link_or_copytree(source_dir, output_dir)
        return {
            "mode": "linked_original_empty",
            "sourceDirectory": str(source_dir),
            "imageDirectory": str(output_dir),
            "normalizedImageCount": 0,
        }

    first_width, first_height = image_dimensions(source_images[0])
    expected_width, expected_height = expected_size
    if first_width == expected_width and first_height == expected_height:
        link_or_copytree(source_dir, output_dir)
        return {
            "mode": "linked_original_matching_camera",
            "sourceDirectory": str(source_dir),
            "imageDirectory": str(output_dir),
            "expectedSize": {"width": expected_width, "height": expected_height},
            "normalizedImageCount": 0,
        }

    from PIL import Image  # type: ignore[import-not-found]

    output_dir.mkdir(parents=True, exist_ok=True)
    normalized_count = 0
    for source in source_images:
        target = output_dir / source.name
        if target.exists():
            normalized_count += 1
            continue
        with Image.open(source) as image:
            rgb = image.convert("RGB")
            if rgb.width >= expected_width and rgb.height >= expected_height:
                rgb = rgb.crop((0, 0, expected_width, expected_height))
            if rgb.width != expected_width or rgb.height != expected_height:
                rgb = rgb.resize((expected_width, expected_height), Image.Resampling.LANCZOS)
            save_kwargs: dict[str, Any] = {}
            if target.suffix.lower() in {".jpg", ".jpeg"}:
                save_kwargs = {"quality": 96, "subsampling": 1, "optimize": True}
            rgb.save(target, **save_kwargs)
            normalized_count += 1
    return {
        "mode": "normalized_to_colmap_camera_size",
        "sourceDirectory": str(source_dir),
        "imageDirectory": str(output_dir),
        "sourceFirstImageSize": {"width": first_width, "height": first_height},
        "expectedSize": {"width": expected_width, "height": expected_height},
        "normalizedImageCount": normalized_count,
    }


def nerfstudio_image_root_from_transforms(dataset_path: Path, transforms: dict[str, Any]) -> Path:
    frames = transforms.get("frames")
    if not isinstance(frames, list):
        return dataset_path / "images" if (dataset_path / "images").exists() else dataset_path
    image_paths = [
        path
        for frame in frames
        if isinstance(frame, dict)
        for path in [normalize_nerfstudio_frame_path(dataset_path, frame.get("file_path"))]
        if path is not None
    ]
    parents = [path.parent for path in image_paths if path.parent.exists()]
    if not parents:
        return dataset_path / "images" if (dataset_path / "images").exists() else dataset_path
    try:
        common = Path(os.path.commonpath([str(parent.resolve()) for parent in parents]))
    except ValueError:
        return parents[0]
    return common if common.exists() else parents[0]


def prepare_nerfstudio_transforms_data(
    *,
    data_dir: Path,
    dataset_path: Path,
    downscale_factor: int,
) -> dict[str, Any]:
    transforms_path = dataset_path / "transforms.json"
    transforms = read_json(transforms_path)
    data_dir.mkdir(parents=True, exist_ok=True)
    for child in dataset_path.iterdir():
        target = data_dir / child.name
        if child.is_dir():
            link_or_copytree(child, target)
        elif child.is_file():
            link_or_copyfile(child, target)

    image_root = nerfstudio_image_root_from_transforms(dataset_path, transforms)
    downscaled_count = 0
    downscaled_path: Path | None = None
    if downscale_factor > 1 and image_root.exists() and image_root.is_dir():
        try:
            relative_image_root = image_root.resolve().relative_to(dataset_path.resolve())
        except ValueError:
            relative_image_root = Path("images")
        if relative_image_root == Path("."):
            downscaled_path = data_dir / f"images_{downscale_factor}"
        else:
            downscaled_path = data_dir / relative_image_root.with_name(f"{relative_image_root.name}_{downscale_factor}")
        downscaled_count = prepare_downscaled_images(image_root, downscaled_path, downscale_factor)

    return {
        "inputKind": NERFSTUDIO_DATASET_INPUT_KIND,
        "dataDir": str(data_dir),
        "sourceDatasetPath": str(dataset_path),
        "transformsPath": str(data_dir / "transforms.json"),
        "sourceTransformsPath": str(transforms_path),
        "imagesPath": str(data_dir / image_root.name) if image_root.parent == dataset_path else str(image_root),
        "imageRoot": str(image_root),
        "downscaleFactor": downscale_factor,
        "downscaledImages": downscaled_count,
        "downscaledImagesPath": str(downscaled_path) if downscaled_path else None,
        "frameCount": len(transforms.get("frames", [])) if isinstance(transforms.get("frames"), list) else 0,
    }


def prepare_nerfstudio_colmap_data(
    *,
    data_dir: Path,
    sparse_model_path: Path,
    colmap_image_dir: Path,
    downscale_factor: int,
    expected_image_size: tuple[int, int] | None = None,
) -> dict[str, Any]:
    images_link = data_dir / "images"
    sparse_link = data_dir / "colmap" / "sparse" / "0"
    image_prepare_summary = prepare_colmap_source_images(colmap_image_dir, images_link, expected_image_size)
    link_or_copytree(sparse_model_path, sparse_link)
    downscaled_count = 0
    if downscale_factor > 1:
        downscaled_target = data_dir / f"images_{downscale_factor}"
        existing_downscaled = colmap_image_dir.parent / f"{colmap_image_dir.name}_{downscale_factor}"
        if expected_image_size is None and existing_downscaled.exists() and existing_downscaled.is_dir():
            link_or_copytree(existing_downscaled, downscaled_target)
            downscaled_count = count_image_files(existing_downscaled)
        else:
            downscaled_count = prepare_downscaled_images(
                images_link,
                downscaled_target,
                downscale_factor,
            )
    return {
        "dataDir": str(data_dir),
        "imagesPath": str(images_link),
        "sparseModelPath": str(sparse_link),
        "downscaleFactor": downscale_factor,
        "downscaledImages": downscaled_count,
        "imagePreparation": image_prepare_summary,
    }


def selected_images_from_colmap_text(colmap_text_dir: Path, image_dir: Path) -> list[dict[str, Any]]:
    images = parse_colmap_images(colmap_text_dir / "images.txt")
    return [
        {
            "imageId": image["imageId"],
            "name": image["name"],
            "cameraId": image["cameraId"],
            "path": str(image_dir / image["name"]),
        }
        for image in sorted(images.values(), key=lambda item: int(item["imageId"]))
    ]


def image_dimensions(path: Path) -> tuple[int | None, int | None]:
    try:
        from PIL import Image  # type: ignore[import-not-found]

        with Image.open(path) as image:
            return int(image.width), int(image.height)
    except Exception:
        return None, None


def value_from_frame_or_transforms(frame: dict[str, Any], transforms: dict[str, Any], key: str) -> Any:
    value = frame.get(key)
    if value is not None:
        return value
    return transforms.get(key)


def nerfstudio_frame_intrinsics(
    *,
    frame: dict[str, Any],
    transforms: dict[str, Any],
    image_path: Path,
) -> dict[str, Any]:
    width_raw = value_from_frame_or_transforms(frame, transforms, "w")
    height_raw = value_from_frame_or_transforms(frame, transforms, "h")
    try:
        width = int(width_raw)
        height = int(height_raw)
    except (TypeError, ValueError):
        width, height = image_dimensions(image_path)
    width = int(width or 1)
    height = int(height or 1)

    def float_value(key: str, default: float) -> float:
        try:
            return float(value_from_frame_or_transforms(frame, transforms, key))
        except (TypeError, ValueError):
            return default

    fx = float_value("fl_x", max(width, height, 1))
    fy = float_value("fl_y", fx)
    cx = float_value("cx", width / 2)
    cy = float_value("cy", height / 2)
    fov_y = math.degrees(2 * math.atan(height / (2 * max(fy, 1.0e-6))))
    return {
        "model": "NERFSTUDIO_PINHOLE",
        "sourceWidth": width,
        "sourceHeight": height,
        "width": width,
        "height": height,
        "fx": round(fx, 6),
        "fy": round(fy, 6),
        "cx": round(cx, 6),
        "cy": round(cy, 6),
        "fovYDegrees": round(fov_y, 6),
    }


def selected_images_from_nerfstudio_transforms(dataset_path: Path, transforms: dict[str, Any]) -> list[dict[str, Any]]:
    frames = transforms.get("frames")
    if not isinstance(frames, list):
        return []
    selected: list[dict[str, Any]] = []
    for index, frame in enumerate(frames):
        if not isinstance(frame, dict):
            continue
        image_path = normalize_nerfstudio_frame_path(dataset_path, frame.get("file_path"))
        if image_path is None:
            continue
        selected.append(
            {
                "imageId": index + 1,
                "name": Path(str(frame.get("file_path") or image_path.name)).name,
                "cameraId": index + 1,
                "path": str(image_path),
                "filePath": frame.get("file_path"),
                "transformMatrix": frame.get("transform_matrix"),
                "intrinsics": nerfstudio_frame_intrinsics(
                    frame=frame,
                    transforms=transforms,
                    image_path=image_path,
                ),
            }
        )
    return selected


def build_image_contact_sheet(image_paths: list[Path], output_path: Path, max_images: int = 12) -> Path | None:
    existing_images = [path for path in image_paths if path.exists()]
    if not existing_images:
        return None

    from PIL import Image, ImageDraw  # type: ignore[import-not-found]

    thumbs: list[tuple[str, Image.Image]] = []
    for index, path in enumerate(existing_images[:max_images]):
        with Image.open(path) as image:
            thumb = image.convert("RGB")
            thumb.thumbnail((720, 240), Image.Resampling.LANCZOS)
            canvas = Image.new("RGB", (720, 270), (18, 22, 28))
            canvas.paste(thumb, ((720 - thumb.width) // 2, 26))
            draw = ImageDraw.Draw(canvas)
            draw.text((12, 8), f"eval {index:02d}", fill=(226, 232, 240))
            thumbs.append((path.name, canvas))

    columns = 2
    rows = math.ceil(len(thumbs) / columns)
    padding = 12
    sheet = Image.new(
        "RGB",
        (
            columns * 720 + (columns + 1) * padding,
            rows * 270 + (rows + 1) * padding,
        ),
        (8, 12, 18),
    )
    for index, (_, thumb) in enumerate(thumbs):
        x = padding + (index % columns) * (720 + padding)
        y = padding + (index // columns) * (270 + padding)
        sheet.paste(thumb, (x, y))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output_path, quality=92)
    return output_path


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
            capability = torch.cuda.get_device_capability(device_index)
            result.update(
                {
                    "deviceName": torch.cuda.get_device_name(device_index),
                    "deviceCapability": [int(capability[0]), int(capability[1])],
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


def resolve_repo_path(raw_path: str, repo_root: Path) -> Path:
    path = Path(raw_path).expanduser()
    if not path.is_absolute():
        path = repo_root / path
    return path


def capture_input_descriptor(capture: dict[str, Any]) -> dict[str, Any]:
    explicit = capture.get("input")
    if isinstance(explicit, dict):
        descriptor = dict(explicit)
    else:
        source = capture.get("source", {}) if isinstance(capture.get("source"), dict) else {}
        descriptor = {
            "kind": PLAIN_VIDEO_INPUT_KIND,
            "path": source.get("path"),
            "source": "legacy_source_path",
        }
    kind = str(descriptor.get("kind") or PLAIN_VIDEO_INPUT_KIND).strip()
    aliases = {
        "video": PLAIN_VIDEO_INPUT_KIND,
        "local_file": PLAIN_VIDEO_INPUT_KIND,
        "colmap": COLMAP_DATASET_INPUT_KIND,
        "colmap_scene": COLMAP_DATASET_INPUT_KIND,
        "nerfstudio_capture": NERFSTUDIO_DATASET_INPUT_KIND,
    }
    descriptor["kind"] = aliases.get(kind, kind)
    return descriptor


def capture_record_from(value: dict[str, Any]) -> dict[str, Any]:
    if isinstance(value.get("job"), dict) and isinstance(value.get("capture"), dict):
        return value["capture"]
    return value


def capture_input_kind(capture_or_job: dict[str, Any]) -> str:
    capture = capture_record_from(capture_or_job)
    if not isinstance(capture, dict):
        return PLAIN_VIDEO_INPUT_KIND
    return str(capture_input_descriptor(capture).get("kind") or PLAIN_VIDEO_INPUT_KIND)


def capture_video_path(job: dict[str, Any], repo_root: Path) -> Path:
    input_descriptor = capture_input_descriptor(job.get("capture", {}))
    if input_descriptor.get("kind") == PLAIN_VIDEO_INPUT_KIND and isinstance(input_descriptor.get("path"), str):
        return resolve_repo_path(str(input_descriptor["path"]), repo_root)
    source = job.get("capture", {}).get("source", {})
    raw_path = source.get("path")
    if not isinstance(raw_path, str) or not raw_path:
        raise ValueError("capture source.path is required")
    return resolve_repo_path(raw_path, repo_root)


def capture_source_path(capture: dict[str, Any], repo_root: Path) -> Path | None:
    descriptor = capture_input_descriptor(capture)
    raw_input_path = descriptor.get("path")
    if isinstance(raw_input_path, str) and raw_input_path:
        return resolve_repo_path(raw_input_path, repo_root)
    source = capture.get("source", {}) if isinstance(capture.get("source"), dict) else {}
    raw_path = source.get("path")
    if not isinstance(raw_path, str) or not raw_path:
        return None
    return resolve_repo_path(raw_path, repo_root)


def nerfstudio_dataset_path(capture_or_job: dict[str, Any], repo_root: Path) -> Path | None:
    capture = capture_record_from(capture_or_job)
    if not isinstance(capture, dict):
        return None
    descriptor = capture_input_descriptor(capture)
    raw_path = descriptor.get("path")
    if not isinstance(raw_path, str) or not raw_path:
        dataset = capture.get("dataset", {}) if isinstance(capture.get("dataset"), dict) else {}
        raw_path = dataset.get("path") or dataset.get("expectedLocalDatasetPath")
    if not isinstance(raw_path, str) or not raw_path:
        return None
    return resolve_repo_path(raw_path, repo_root)


def colmap_dataset_paths(capture_or_job: dict[str, Any], repo_root: Path) -> dict[str, Path | None]:
    capture = capture_record_from(capture_or_job)
    if not isinstance(capture, dict):
        return {"datasetPath": None, "imageDirectory": None, "sparseModelPath": None}
    descriptor = capture_input_descriptor(capture)
    dataset = capture.get("dataset", {}) if isinstance(capture.get("dataset"), dict) else {}

    raw_dataset_path = descriptor.get("path") or dataset.get("scenePath") or dataset.get("expectedLocalDatasetPath")
    dataset_path = resolve_repo_path(str(raw_dataset_path), repo_root) if isinstance(raw_dataset_path, str) and raw_dataset_path else None

    raw_image_dir = descriptor.get("imageDirectory") or dataset.get("imageSequencePath")
    if isinstance(raw_image_dir, str) and raw_image_dir:
        image_dir = resolve_repo_path(raw_image_dir, repo_root)
    elif dataset_path is not None and (dataset_path / "images").exists():
        image_dir = dataset_path / "images"
    elif dataset_path is not None and (dataset_path / "images_2").exists():
        image_dir = dataset_path / "images_2"
    else:
        image_dir = None

    raw_sparse_path = descriptor.get("sparseModelPath") or dataset.get("sparseModelPath")
    if isinstance(raw_sparse_path, str) and raw_sparse_path:
        sparse_model_path = resolve_repo_path(raw_sparse_path, repo_root)
    elif dataset_path is not None and (dataset_path / "sparse" / "0").exists():
        sparse_model_path = dataset_path / "sparse" / "0"
    else:
        sparse_model_path = None

    return {
        "datasetPath": dataset_path,
        "imageDirectory": image_dir,
        "sparseModelPath": sparse_model_path,
    }


def count_image_files(image_dir: Path) -> int:
    suffixes = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff"}
    return sum(1 for path in image_dir.iterdir() if path.is_file() and path.suffix.lower() in suffixes)


def validate_colmap_dataset(capture_or_job: dict[str, Any], repo_root: Path) -> dict[str, Any]:
    paths = colmap_dataset_paths(capture_or_job, repo_root)
    dataset_path = paths["datasetPath"]
    image_dir = paths["imageDirectory"]
    sparse_model_path = paths["sparseModelPath"]
    checks: list[dict[str, Any]] = [
        {
            "id": "dataset_directory",
            "status": "pass" if dataset_path and dataset_path.exists() and dataset_path.is_dir() else "setup_gap",
            "summary": "dataset directory exists" if dataset_path and dataset_path.exists() and dataset_path.is_dir() else "dataset directory is missing",
            "path": str(dataset_path) if dataset_path else None,
        },
        {
            "id": "image_directory",
            "status": "pass" if image_dir and image_dir.exists() and image_dir.is_dir() else "setup_gap",
            "summary": "image directory exists" if image_dir and image_dir.exists() and image_dir.is_dir() else "image directory is missing",
            "path": str(image_dir) if image_dir else None,
        },
        {
            "id": "sparse_model",
            "status": "pass" if sparse_model_path and sparse_model_path.exists() and sparse_model_path.is_dir() else "setup_gap",
            "summary": "COLMAP sparse model exists" if sparse_model_path and sparse_model_path.exists() and sparse_model_path.is_dir() else "COLMAP sparse model is missing",
            "path": str(sparse_model_path) if sparse_model_path else None,
        },
    ]
    image_count = count_image_files(image_dir) if image_dir and image_dir.exists() and image_dir.is_dir() else 0
    checks.append(
        {
            "id": "image_files",
            "status": "pass" if image_count > 0 else "fail",
            "summary": f"{image_count} input images found" if image_count > 0 else "no supported input images found",
            "imageCount": image_count,
        }
    )
    sparse_files = []
    if sparse_model_path and sparse_model_path.exists() and sparse_model_path.is_dir():
        sparse_files = [path.name for path in sparse_model_path.iterdir() if path.is_file()]
    has_binary_model = {"cameras.bin", "images.bin", "points3D.bin"}.issubset(set(sparse_files))
    has_text_model = {"cameras.txt", "images.txt", "points3D.txt"}.issubset(set(sparse_files))
    checks.append(
        {
            "id": "sparse_model_files",
            "status": "pass" if has_binary_model or has_text_model else "fail",
            "summary": "COLMAP sparse model files are present" if has_binary_model or has_text_model else "COLMAP sparse model is missing cameras/images/points3D files",
            "files": sparse_files,
        }
    )
    statuses = [check["status"] for check in checks]
    status = "fail" if "fail" in statuses else "setup_gap" if "setup_gap" in statuses else "pass"
    return {
        "status": status,
        "summary": "COLMAP dataset is ready" if status == "pass" else "COLMAP dataset is incomplete",
        "datasetPath": str(dataset_path) if dataset_path else None,
        "imageDirectory": str(image_dir) if image_dir else None,
        "sparseModelPath": str(sparse_model_path) if sparse_model_path else None,
        "imageCount": image_count,
        "checks": checks,
    }


def normalize_nerfstudio_frame_path(dataset_path: Path, file_path: Any) -> Path | None:
    if not isinstance(file_path, str) or not file_path:
        return None
    path = Path(file_path)
    if not path.is_absolute():
        path = dataset_path / path
    if path.suffix:
        return path
    for suffix in (".jpg", ".jpeg", ".png"):
        candidate = path.with_suffix(suffix)
        if candidate.exists():
            return candidate
    return path


def validate_nerfstudio_dataset(dataset_path: Path) -> dict[str, Any]:
    transforms_path = dataset_path / "transforms.json"
    checks: list[dict[str, Any]] = [
        {
            "id": "dataset_directory",
            "status": "pass" if dataset_path.exists() and dataset_path.is_dir() else "setup_gap",
            "summary": "dataset directory exists" if dataset_path.exists() and dataset_path.is_dir() else "dataset directory is missing",
            "path": str(dataset_path),
        },
        {
            "id": "transforms_json",
            "status": "pass" if transforms_path.exists() else "setup_gap",
            "summary": "transforms.json exists" if transforms_path.exists() else "transforms.json is missing",
            "path": str(transforms_path),
        },
    ]
    if not dataset_path.exists() or not dataset_path.is_dir() or not transforms_path.exists():
        return {
            "status": "setup_gap",
            "summary": "Nerfstudio dataset is not present locally",
            "datasetPath": str(dataset_path),
            "transformsPath": str(transforms_path),
            "checks": checks,
        }

    try:
        transforms = read_json(transforms_path)
    except Exception as exc:  # noqa: BLE001 - report invalid user/reference data directly
        checks.append({"id": "transforms_parse", "status": "fail", "summary": f"transforms.json is not readable: {exc}"})
        return {
            "status": "fail",
            "summary": "Nerfstudio transforms.json is invalid",
            "datasetPath": str(dataset_path),
            "transformsPath": str(transforms_path),
            "checks": checks,
        }

    frames = transforms.get("frames")
    if not isinstance(frames, list) or not frames:
        checks.append({"id": "frame_entries", "status": "fail", "summary": "transforms.json has no frames"})
        return {
            "status": "fail",
            "summary": "Nerfstudio dataset has no frame entries",
            "datasetPath": str(dataset_path),
            "transformsPath": str(transforms_path),
            "frameCount": 0,
            "readableFrameCount": 0,
            "depthFrameCount": 0,
            "checks": checks,
        }

    readable_count = 0
    missing: list[str] = []
    pose_count = 0
    depth_count = 0
    for frame in frames:
        if not isinstance(frame, dict):
            continue
        image_path = normalize_nerfstudio_frame_path(dataset_path, frame.get("file_path"))
        if image_path and image_path.exists() and image_path.is_file():
            readable_count += 1
        elif image_path:
            missing.append(str(image_path))
        matrix = frame.get("transform_matrix")
        if isinstance(matrix, list) and len(matrix) == 4 and all(isinstance(row, list) and len(row) == 4 for row in matrix):
            pose_count += 1
        depth_path = normalize_nerfstudio_frame_path(dataset_path, frame.get("depth_file_path"))
        if depth_path and depth_path.exists():
            depth_count += 1

    checks.append(
        {
            "id": "frame_images",
            "status": "pass" if readable_count == len(frames) else "fail",
            "summary": "all transform frame images exist" if readable_count == len(frames) else f"{len(frames) - readable_count} transform frame images are missing",
            "frameCount": len(frames),
            "readableFrameCount": readable_count,
            "missingExamples": missing[:5],
        }
    )
    checks.append(
        {
            "id": "frame_poses",
            "status": "pass" if pose_count == len(frames) else "fail",
            "summary": "all frames contain transform matrices" if pose_count == len(frames) else f"{len(frames) - pose_count} frames are missing transform matrices",
            "poseCount": pose_count,
        }
    )
    if depth_count:
        checks.append(
            {
                "id": "depth_maps",
                "status": "pass",
                "summary": f"{depth_count} frames reference readable depth maps",
                "depthFrameCount": depth_count,
            }
        )

    status = "pass" if readable_count == len(frames) and pose_count == len(frames) else "fail"
    image_root = dataset_path / "images"
    if not image_root.exists():
        image_root = dataset_path
    return {
        "status": status,
        "summary": "Nerfstudio dataset is ready" if status == "pass" else "Nerfstudio dataset is incomplete",
        "datasetPath": str(dataset_path),
        "transformsPath": str(transforms_path),
        "imageRoot": str(image_root),
        "frameCount": len(frames),
        "readableFrameCount": readable_count,
        "depthFrameCount": depth_count,
        "checks": checks,
    }


def nerfstudio_frame_entries(dataset_path: Path, transforms: dict[str, Any]) -> list[dict[str, Any]]:
    frames = transforms.get("frames")
    if not isinstance(frames, list):
        return []
    entries: list[dict[str, Any]] = []
    for index, frame in enumerate(frames):
        if not isinstance(frame, dict):
            continue
        image_path = normalize_nerfstudio_frame_path(dataset_path, frame.get("file_path"))
        if image_path is None:
            continue
        depth_path = normalize_nerfstudio_frame_path(dataset_path, frame.get("depth_file_path"))
        entry = {
            "index": index,
            "path": str(image_path),
            "filePath": frame.get("file_path"),
            "timestampSeconds": frame.get("timestampSeconds", index),
            "sizeBytes": image_path.stat().st_size if image_path.exists() else None,
            "sha256": file_sha256(image_path) if image_path.exists() and image_path.is_file() else None,
            "transformMatrix": frame.get("transform_matrix"),
        }
        if depth_path is not None:
            entry["depthPath"] = str(depth_path)
            entry["depthExists"] = depth_path.exists()
        entries.append(entry)
    return entries


def colmap_dataset_frame_entries(image_dir: Path) -> list[dict[str, Any]]:
    suffixes = {".jpg", ".jpeg", ".png", ".webp", ".tif", ".tiff"}
    entries: list[dict[str, Any]] = []
    for index, image_path in enumerate(sorted(path for path in image_dir.iterdir() if path.is_file() and path.suffix.lower() in suffixes)):
        entries.append(
            {
                "index": index,
                "path": str(image_path),
                "filePath": image_path.name,
                "timestampSeconds": index,
                "sizeBytes": image_path.stat().st_size,
                "sha256": file_sha256(image_path),
            }
        )
    return entries


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
    input_kind = capture_input_kind(capture)
    license_status, license_summary, commercial_posture = classify_capture_license(source)
    source_path = capture_source_path(capture, repo_root)
    if input_kind == COLMAP_DATASET_INPUT_KIND:
        dataset_report = validate_colmap_dataset(capture, repo_root)
        source_check = {
            "id": "source_dataset",
            "status": dataset_report["status"],
            "summary": dataset_report["summary"],
            "path": dataset_report.get("datasetPath"),
            "frameCount": dataset_report.get("imageCount"),
            "sparseModelPath": dataset_report.get("sparseModelPath"),
        }
    elif input_kind == NERFSTUDIO_DATASET_INPUT_KIND:
        dataset_path = nerfstudio_dataset_path(capture, repo_root)
        dataset_report = validate_nerfstudio_dataset(dataset_path) if dataset_path else {
            "status": "setup_gap",
            "summary": "Nerfstudio dataset path is missing",
            "datasetPath": None,
            "checks": [{"id": "dataset_path", "status": "setup_gap", "summary": "input.path or dataset.expectedLocalDatasetPath is required"}],
        }
        source_check = {
            "id": "source_dataset",
            "status": dataset_report["status"],
            "summary": dataset_report["summary"],
            "path": dataset_report.get("datasetPath"),
            "frameCount": dataset_report.get("frameCount"),
            "depthFrameCount": dataset_report.get("depthFrameCount"),
        }
    else:
        file_exists = bool(source_path and source_path.exists())
        source_check = {
            "id": "source_file",
            "status": "pass" if file_exists else "setup_gap",
            "summary": "source file exists" if file_exists else "source file is not present locally",
            "path": str(source_path) if source_path else None,
            "sizeBytes": source_path.stat().st_size if file_exists and source_path else None,
        }
    checks = [
        source_check,
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
        "inputKind": input_kind,
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


def resolve_input_path(raw_path: str, repo_root: Path) -> Path:
    path = Path(raw_path).expanduser()
    if not path.is_absolute():
        path = repo_root / path
    return path


def ensure_repo_target(path: Path, repo_root: Path) -> Path:
    resolved = path.resolve()
    resolved.relative_to(repo_root.resolve())
    return resolved


def capture_import_report_path(target_path: Path) -> Path:
    return target_path.parent / ".provenance" / f"{target_path.name}.import.json"


def build_video_import_report(
    manifest_path: Path,
    selection: CaptureSelection,
    input_path: Path,
    target_path: Path | None,
    accept_warning: bool,
    overwrite: bool,
    dry_run: bool,
    repo_root: Path,
) -> dict[str, Any]:
    source = selection.capture.get("source", {}) if isinstance(selection.capture.get("source"), dict) else {}
    license_status, license_summary, commercial_posture = classify_capture_license(source)
    checks: list[dict[str, Any]] = []
    report: dict[str, Any] = {
        "schemaVersion": 1,
        "command": "import-video",
        "status": "pending",
        "generatedAt": utc_now(),
        "captureManifestPath": str(manifest_path),
        "captureId": selection.capture.get("id"),
        "dryRun": dry_run,
        "acceptedLicenseWarning": accept_warning,
        "overwrite": overwrite,
        "commercialPosture": commercial_posture,
        "source": {
            "path": str(input_path),
            "exists": input_path.exists(),
            "sizeBytes": input_path.stat().st_size if input_path.exists() and input_path.is_file() else None,
            "sha256": file_sha256(input_path) if input_path.exists() and input_path.is_file() else None,
        },
        "target": {
            "path": str(target_path) if target_path else None,
            "existsBefore": target_path.exists() if target_path else False,
        },
        "license": {
            "status": license_status,
            "summary": license_summary,
            "value": source.get("license"),
            "sourceUrl": source.get("sourceUrl"),
            "licenseSourceUrl": source.get("licenseSourceUrl"),
            "termsUrl": source.get("termsUrl"),
            "licenseVerifiedAt": source.get("licenseVerifiedAt"),
        },
        "checks": checks,
    }

    if target_path is None:
        checks.append({"id": "target_path", "status": "fail", "summary": "capture source.path is missing"})
        report["status"] = "fail"
        return report

    try:
        ensure_repo_target(target_path, repo_root)
        checks.append({"id": "target_path", "status": "pass", "summary": "target path is inside repository", "path": str(target_path)})
    except ValueError:
        checks.append({"id": "target_path", "status": "fail", "summary": "target path must stay inside repository", "path": str(target_path)})
        report["status"] = "fail"
        return report

    if not input_path.exists() or not input_path.is_file():
        checks.append({"id": "source_file", "status": "fail", "summary": "input video file does not exist", "path": str(input_path)})
        report["status"] = "fail"
        return report
    checks.append({"id": "source_file", "status": "pass", "summary": "input file exists", "path": str(input_path)})

    if license_status == "fail":
        checks.append({"id": "source_license", "status": "blocked_license", "summary": license_summary})
        report["status"] = "blocked_license"
        return report
    if license_status == "warning" and not accept_warning:
        checks.append(
            {
                "id": "source_license",
                "status": "blocked_license",
                "summary": "license warning must be explicitly accepted with --accept-warning before importing this capture",
                "licenseSummary": license_summary,
            }
        )
        report["status"] = "blocked_license"
        return report
    checks.append({"id": "source_license", "status": license_status, "summary": license_summary})

    if target_path.exists() and not overwrite:
        checks.append(
            {
                "id": "overwrite_policy",
                "status": "setup_gap",
                "summary": "target file already exists; rerun with --overwrite to replace it intentionally",
                "path": str(target_path),
            }
        )
        report["status"] = "setup_gap"
        return report
    checks.append({"id": "overwrite_policy", "status": "pass", "summary": "target can be written"})

    if dry_run:
        report["status"] = "pass"
        report["target"].update({"wouldWrite": True, "reportPath": str(capture_import_report_path(target_path))})
        checks.append({"id": "dry_run", "status": "pass", "summary": "import plan validated without copying"})
        return report

    target_path.parent.mkdir(parents=True, exist_ok=True)
    if input_path.resolve() != target_path.resolve():
        shutil.copy2(input_path, target_path)
    report_path = capture_import_report_path(target_path)
    report["status"] = "pass"
    report["target"].update(
        {
            "existsAfter": target_path.exists(),
            "sizeBytes": target_path.stat().st_size,
            "sha256": file_sha256(target_path),
            "reportPath": str(report_path),
        }
    )
    checks.append({"id": "copy", "status": "pass", "summary": "input file copied to capture target path"})
    return report


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
                "group": definition.get("group", "media_pipeline"),
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

    colmap = run_command(colmap_command("--help"), timeout_seconds=10)
    ffmpeg = run_command(["ffmpeg", "-version"], timeout_seconds=10)
    ffprobe = run_command(["ffprobe", "-version"], timeout_seconds=10)
    torch_cuda = check_torch_cuda()
    gsplat = check_python_import("gsplat")
    trainer_env, trainer_env_summary = build_training_subprocess_environment(torch_cuda)
    ninja = check_ninja_available(trainer_env)
    gpu_baseline = gpu_load_snapshot(trainer_env)

    checks = [
        {
            "id": "nvidia_smi",
            "status": nvidia_smi_status(nvidia_query),
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
        ninja,
        {
            "id": "gpu_load_baseline",
            "status": gpu_baseline["status"],
            "summary": gpu_baseline["summary"],
            "details": {
                "gpus": gpu_baseline["gpus"],
                "computeProcesses": gpu_baseline["computeProcesses"],
                "ignoredComputeProcesses": gpu_baseline["ignoredComputeProcesses"],
            },
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
        "trainingSubprocessEnvironment": trainer_env_summary,
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


def frame_sampling_plan(target_fps: float, max_frames: int, duration_seconds: Any) -> dict[str, Any]:
    try:
        duration = float(duration_seconds)
    except (TypeError, ValueError):
        duration = 0.0
    if duration <= 0:
        return {
            "strategy": "fixed_fps",
            "targetFps": target_fps,
            "effectiveFps": target_fps,
            "maxFrames": max_frames,
            "durationSeconds": None,
            "cappedByMaxFrames": False,
        }

    requested_frame_count = duration * target_fps
    if requested_frame_count <= max_frames:
        return {
            "strategy": "fixed_fps",
            "targetFps": target_fps,
            "effectiveFps": target_fps,
            "maxFrames": max_frames,
            "durationSeconds": duration,
            "cappedByMaxFrames": False,
            "expectedUncappedFrameCount": int(math.ceil(requested_frame_count)),
        }

    effective_fps = max(0.001, max_frames / duration)
    return {
        "strategy": "full_duration_even",
        "targetFps": target_fps,
        "effectiveFps": effective_fps,
        "maxFrames": max_frames,
        "durationSeconds": duration,
        "cappedByMaxFrames": True,
        "expectedUncappedFrameCount": int(math.ceil(requested_frame_count)),
    }


def planned_frame_count(target_fps: float, max_frames: int, duration_seconds: Any) -> int:
    try:
        duration = float(duration_seconds)
    except (TypeError, ValueError):
        duration = 0.0
    if duration <= 0:
        return max_frames
    return max(1, min(max_frames, int(math.ceil(duration * target_fps))))


def candidate_sampling_plan(target_fps: float, max_frames: int, duration_seconds: Any) -> dict[str, Any]:
    target_count = planned_frame_count(target_fps, max_frames, duration_seconds)
    try:
        duration = float(duration_seconds)
    except (TypeError, ValueError):
        duration = 0.0
    requested_candidates = min(max_frames * 3, max(target_count, target_count * 3))
    if duration > 0:
        candidate_fps = min(10.0, max(0.001, requested_candidates / duration))
        requested_candidates = max(target_count, int(math.ceil(duration * candidate_fps)))
    else:
        candidate_fps = target_fps
    return {
        "strategy": "quality_keyframes",
        "candidateFps": candidate_fps,
        "candidateMaxFrames": max(1, requested_candidates),
        "targetFrameCount": target_count,
    }


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def frame_quality_score(metrics: dict[str, Any]) -> float:
    sharpness = float(metrics.get("sharpness") or 0.0)
    contrast = float(metrics.get("contrast") or 0.0)
    luma = float(metrics.get("luma") or 0.0)
    clipped_dark = float(metrics.get("clippedDarkFraction") or 0.0)
    clipped_bright = float(metrics.get("clippedBrightFraction") or 0.0)

    sharpness_score = clamp01((sharpness - 5.0) / 24.0)
    contrast_score = clamp01((contrast - 12.0) / 48.0)
    exposure_score = 1.0 - clamp01((abs(luma - 128.0) - 68.0) / 70.0)
    clipping_score = 1.0 - clamp01((clipped_dark + clipped_bright) * 4.0)
    texture_penalty = 0.18 if metrics.get("texturelessRisk") else 0.0
    bright_low_texture_penalty = 0.16 if metrics.get("lowTextureBrightSurfaceRisk") else 0.0
    score = (
        0.38 * sharpness_score
        + 0.30 * contrast_score
        + 0.20 * exposure_score
        + 0.12 * clipping_score
        - texture_penalty
        - bright_low_texture_penalty
    )
    return round(clamp01(score), 6)


def analyze_candidate_frames(
    candidate_frames: list[Path],
    candidate_fps: float,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    try:
        from PIL import Image, ImageChops, ImageFilter, ImageStat  # type: ignore[import-not-found]
    except Exception as exc:  # noqa: BLE001 - optional local diagnostic dependency
        candidates = [
            {
                "sourcePath": str(path),
                "sourceIndex": index,
                "timestampSeconds": round((index - 1) / candidate_fps, 6) if candidate_fps > 0 else index - 1,
                "score": 0.5,
            }
            for index, path in enumerate(candidate_frames, start=1)
        ]
        return candidates, {
            "status": "warning",
            "summary": "quality keyframe scoring skipped because Pillow is unavailable",
            "error": str(exc),
        }

    candidates: list[dict[str, Any]] = []
    previous_gray = None
    for index, path in enumerate(candidate_frames, start=1):
        entry: dict[str, Any] = {
            "sourcePath": str(path),
            "sourceIndex": index,
            "timestampSeconds": round((index - 1) / candidate_fps, 6) if candidate_fps > 0 else index - 1,
        }
        try:
            with Image.open(path) as image:
                gray = image.convert("L")
                gray.thumbnail((320, 320), Image.Resampling.BILINEAR)
                stat = ImageStat.Stat(gray)
                luma = float(stat.mean[0])
                contrast = float(stat.stddev[0])
                edge_stat = ImageStat.Stat(gray.filter(ImageFilter.FIND_EDGES))
                sharpness = float(edge_stat.stddev[0])
                histogram = gray.histogram()
                pixel_count = max(1, sum(histogram))
                clipped_dark = sum(histogram[:8]) / pixel_count
                clipped_bright = sum(histogram[248:]) / pixel_count
                delta = None
                if previous_gray is not None and previous_gray.size == gray.size:
                    delta = float(ImageStat.Stat(ImageChops.difference(previous_gray, gray)).mean[0])
                previous_gray = gray.copy()
        except Exception as exc:  # noqa: BLE001 - keep one bad frame from killing the run
            entry.update(
                {
                    "status": "warning",
                    "error": str(exc),
                    "luma": None,
                    "contrast": None,
                    "sharpness": None,
                    "interFrameDelta": None,
                    "score": 0.0,
                }
            )
            candidates.append(entry)
            continue

        textureless = contrast < 18.0 and sharpness < 8.0
        bright_low_texture_surface = luma > 185.0 and contrast < 24.0 and sharpness < 9.5
        entry.update(
            {
                "status": "pass",
                "luma": round(luma, 3),
                "contrast": round(contrast, 3),
                "sharpness": round(sharpness, 3),
                "clippedDarkFraction": round(clipped_dark, 5),
                "clippedBrightFraction": round(clipped_bright, 5),
                "interFrameDelta": round(delta, 3) if delta is not None else None,
                "texturelessRisk": textureless,
                "lowTextureBrightSurfaceRisk": bright_low_texture_surface,
            }
        )
        entry["score"] = frame_quality_score(entry)
        candidates.append(entry)

    readable = [item for item in candidates if item.get("status") == "pass"]
    if not readable:
        return candidates, {"status": "fail", "summary": "no candidate frames could be scored"}

    def fraction(predicate: Any) -> float:
        return sum(1 for item in readable if predicate(item)) / max(1, len(readable))

    score_values = [float(item.get("score") or 0.0) for item in readable]
    report = {
        "status": "pass",
        "summary": "candidate frames scored for keyframe selection",
        "candidateFrameCount": len(candidates),
        "scoredFrameCount": len(readable),
        "scoreMedian": round(float(statistics.median(score_values)), 4),
        "lowScoreCandidateFraction": round(fraction(lambda item: float(item.get("score") or 0.0) < 0.35), 4),
        "texturelessCandidateFraction": round(fraction(lambda item: bool(item.get("texturelessRisk"))), 4),
        "brightLowTextureCandidateFraction": round(
            fraction(lambda item: bool(item.get("lowTextureBrightSurfaceRisk"))),
            4,
        ),
    }
    return candidates, report


def keyframe_metric_summary(items: list[dict[str, Any]]) -> dict[str, Any]:
    readable = [item for item in items if item.get("status") == "pass"]
    if not readable:
        return {
            "frameCount": len(items),
            "scoredFrameCount": 0,
            "scoreMedian": None,
            "lowScoreFraction": None,
            "texturelessFraction": None,
            "brightLowTextureFraction": None,
        }

    def fraction(predicate: Any) -> float:
        return sum(1 for item in readable if predicate(item)) / max(1, len(readable))

    return {
        "frameCount": len(items),
        "scoredFrameCount": len(readable),
        "scoreMedian": round(float(statistics.median([float(item.get("score") or 0.0) for item in readable])), 4),
        "lowScoreFraction": round(fraction(lambda item: float(item.get("score") or 0.0) < 0.35), 4),
        "texturelessFraction": round(fraction(lambda item: bool(item.get("texturelessRisk"))), 4),
        "brightLowTextureFraction": round(
            fraction(lambda item: bool(item.get("lowTextureBrightSurfaceRisk"))),
            4,
        ),
    }


def select_keyframes_from_candidates(
    candidates: list[dict[str, Any]],
    target_count: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if not candidates:
        return [], {"status": "fail", "summary": "no candidate frames were extracted"}

    target = max(1, min(target_count, len(candidates)))
    selected: list[dict[str, Any]] = []
    temporal_baseline: list[dict[str, Any]] = []
    for bucket_index in range(target):
        start = math.floor(bucket_index * len(candidates) / target)
        end = math.floor((bucket_index + 1) * len(candidates) / target)
        bucket = candidates[start:max(start + 1, end)]
        best = max(bucket, key=lambda item: float(item.get("score") or 0.0))
        middle = bucket[len(bucket) // 2]
        selected.append(dict(best))
        temporal_baseline.append(dict(middle))

    selected.sort(key=lambda item: int(item.get("sourceIndex") or 0))
    deduped: list[dict[str, Any]] = []
    last_source_index: int | None = None
    for item in selected:
        source_index = int(item.get("sourceIndex") or 0)
        if last_source_index is not None and source_index == last_source_index:
            continue
        deduped.append(item)
        last_source_index = source_index

    readable = [item for item in candidates if item.get("status") == "pass"]
    selected_summary = keyframe_metric_summary(deduped)
    baseline_summary = keyframe_metric_summary(temporal_baseline)
    selected_score = selected_summary.get("scoreMedian")
    baseline_score = baseline_summary.get("scoreMedian")
    score_delta = (
        round(float(selected_score) - float(baseline_score), 4)
        if isinstance(selected_score, (int, float)) and isinstance(baseline_score, (int, float))
        else None
    )

    report = {
        "status": "pass",
        "summary": f"selected {len(deduped)} quality keyframes from {len(candidates)} candidates",
        "strategy": "quality_keyframes_temporal_buckets",
        "candidateFrameCount": len(candidates),
        "selectedFrameCount": len(deduped),
        "targetFrameCount": target_count,
        "droppedCandidateCount": max(0, len(candidates) - len(deduped)),
        "scoredCandidateCount": len(readable),
        "selectedQuality": selected_summary,
        "temporalBaselineQuality": baseline_summary,
        "qualityComparison": {
            "scoreMedianDelta": score_delta,
            "baseline": "middle candidate from each temporal bucket",
        },
    }
    selected_bright_low_texture = selected_summary.get("brightLowTextureFraction")
    selected_textureless = selected_summary.get("texturelessFraction")
    if isinstance(selected_bright_low_texture, (int, float)) and selected_bright_low_texture > 0.18:
        report["status"] = "warning"
        report["summary"] += "; many selected frames still contain bright low-texture regions"
        report["recommendation"] = "film large plain bright surfaces with slower movement and keep edges, corners, surface detail or nearby objects in view"
    elif isinstance(selected_textureless, (int, float)) and selected_textureless > 0.25:
        report["status"] = "warning"
        report["summary"] += "; many selected frames are low texture"
        report["recommendation"] = "add more parallax and keep edges, surface detail or nearby objects visible around plain surfaces"
    return deduped, report


def materialize_selected_frames(selected: list[dict[str, Any]], frame_dir: Path) -> list[dict[str, Any]]:
    materialized: list[dict[str, Any]] = []
    for output_index, item in enumerate(selected, start=1):
        source_path = Path(str(item.get("sourcePath") or ""))
        output_path = frame_dir / f"frame_{output_index:06d}.jpg"
        shutil.copy2(source_path, output_path)
        materialized.append(
            {
                **item,
                "index": output_index - 1,
                "path": str(output_path),
            }
        )
    return materialized


def frame_run_directory(job_path: Path) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return job_path.parent / "frames" / stamp


def build_frame_manifest(
    job_path: Path,
    intake_report: dict[str, Any],
    frame_dir: Path,
    contact_sheet_path: Path,
    target_fps: float,
    effective_fps: float,
    max_frames: int,
    sampling_strategy: str,
    contact_sheet_stride: int,
    selected_frames: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    frames = sorted(frame_dir.glob("frame_*.jpg"))
    frame_entries = []
    metadata = intake_report.get("metadata", {}) if isinstance(intake_report.get("metadata"), dict) else {}
    duration_seconds = metadata.get("durationSeconds")
    try:
        duration_value = float(duration_seconds)
    except (TypeError, ValueError):
        duration_value = 0.0
    if selected_frames is not None:
        iterable_frames = [(index, Path(str(frame.get("path"))), frame) for index, frame in enumerate(selected_frames)]
    else:
        iterable_frames = [(index, frame_path, {}) for index, frame_path in enumerate(frames)]

    for index, frame_path, selected_frame in iterable_frames:
        timestamp_seconds = selected_frame.get("timestampSeconds")
        if not isinstance(timestamp_seconds, (int, float)):
            timestamp_seconds = index / effective_fps if effective_fps > 0 else index / target_fps
            if duration_value > 0:
                timestamp_seconds = min(timestamp_seconds, duration_value)
        quality = {
            key: selected_frame.get(key)
            for key in (
                "score",
                "luma",
                "contrast",
                "sharpness",
                "clippedDarkFraction",
                "clippedBrightFraction",
                "interFrameDelta",
                "texturelessRisk",
                "lowTextureBrightSurfaceRisk",
            )
            if key in selected_frame
        }
        frame_entries.append(
            {
                "index": index,
                "path": str(frame_path),
                "timestampSeconds": round(timestamp_seconds, 6),
                "sizeBytes": frame_path.stat().st_size,
                "sha256": file_sha256(frame_path),
                **(
                    {
                        "selection": {
                            "sourceIndex": selected_frame.get("sourceIndex"),
                            "sourcePath": selected_frame.get("sourcePath"),
                            "quality": quality,
                        }
                    }
                    if selected_frame
                    else {}
                ),
            }
        )

    coverage_end = frame_entries[-1]["timestampSeconds"] if frame_entries else 0
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
            "effectiveFps": round(effective_fps, 6),
            "maxFrames": max_frames,
            "actualFrameCount": len(frame_entries),
            "strategy": sampling_strategy,
            "cappedByMaxFrames": sampling_strategy == "full_duration_even",
            "coverageStartSeconds": frame_entries[0]["timestampSeconds"] if frame_entries else None,
            "coverageEndSeconds": coverage_end,
            "sourceDurationSeconds": duration_seconds,
            "contactSheetStride": contact_sheet_stride,
        },
        "frameDirectory": str(frame_dir),
        "contactSheetPath": str(contact_sheet_path),
        "frames": frame_entries,
    }


def analyze_capture_frame_quality(frames: list[Any], max_samples: int = 90) -> dict[str, Any]:
    try:
        from PIL import Image, ImageChops, ImageFilter, ImageStat  # type: ignore[import-not-found]
    except Exception as exc:  # noqa: BLE001 - optional local diagnostic dependency
        return {
            "status": "warning",
            "summary": "frame quality diagnostics skipped because Pillow is unavailable",
            "error": str(exc),
        }

    usable = [frame for frame in frames if isinstance(frame, dict) and Path(str(frame.get("path") or "")).exists()]
    if not usable:
        return {
            "status": "fail",
            "summary": "no readable frames available for quality diagnostics",
        }

    stride = max(1, math.ceil(len(usable) / max_samples))
    selected = usable[::stride][:max_samples]
    sharpness_values: list[float] = []
    contrast_values: list[float] = []
    luma_values: list[float] = []
    inter_frame_deltas: list[float] = []
    previous_gray = None
    analyzed = 0

    for frame in selected:
        path = Path(str(frame.get("path") or ""))
        try:
            with Image.open(path) as image:
                gray = image.convert("L")
                gray.thumbnail((320, 320), Image.Resampling.BILINEAR)
                stat = ImageStat.Stat(gray)
                luma = float(stat.mean[0])
                contrast = float(stat.stddev[0])
                edge_stat = ImageStat.Stat(gray.filter(ImageFilter.FIND_EDGES))
                sharpness = float(edge_stat.stddev[0])
                if previous_gray is not None and previous_gray.size == gray.size:
                    delta = float(ImageStat.Stat(ImageChops.difference(previous_gray, gray)).mean[0])
                    inter_frame_deltas.append(delta)
                previous_gray = gray.copy()
        except Exception:
            continue
        analyzed += 1
        luma_values.append(luma)
        contrast_values.append(contrast)
        sharpness_values.append(sharpness)

    if analyzed == 0:
        return {
            "status": "fail",
            "summary": "frame quality diagnostics could not read sampled frames",
            "sampledFrameCount": len(selected),
        }

    sharpness_median = float(statistics.median(sharpness_values))
    contrast_median = float(statistics.median(contrast_values))
    luma_median = float(statistics.median(luma_values))
    motion_delta_median = float(statistics.median(inter_frame_deltas)) if inter_frame_deltas else None
    blurry_fraction = sum(1 for value in sharpness_values if value < 8.0) / analyzed
    low_contrast_fraction = sum(1 for value in contrast_values if value < 24.0) / analyzed
    exposure_risk_fraction = sum(1 for value in luma_values if value < 35.0 or value > 220.0) / analyzed
    large_motion_fraction = (
        sum(1 for value in inter_frame_deltas if value > 38.0) / len(inter_frame_deltas)
        if inter_frame_deltas
        else 0.0
    )

    recommendations: list[str] = []
    if blurry_fraction > 0.30:
        recommendations.append("reduce motion blur: move slower, add light, avoid quick sweeps")
    if low_contrast_fraction > 0.35:
        recommendations.append("add textured surfaces or include more detailed objects in view")
    if exposure_risk_fraction > 0.20:
        recommendations.append("avoid very dark/bright regions and lock exposure if needed")
    if large_motion_fraction > 0.45:
        recommendations.append("increase overlap: walk in a smooth arc and avoid large jumps between frames")

    status = "warning" if recommendations else "pass"
    summary = "frame quality looks usable for SfM"
    if recommendations:
        summary = "capture may be hard for SfM: " + "; ".join(recommendations[:2])

    return {
        "status": status,
        "summary": summary,
        "sampledFrameCount": len(selected),
        "analyzedFrameCount": analyzed,
        "sharpnessMedian": round(sharpness_median, 3),
        "contrastMedian": round(contrast_median, 3),
        "lumaMedian": round(luma_median, 3),
        "motionDeltaMedian": round(motion_delta_median, 3) if motion_delta_median is not None else None,
        "blurryFrameFraction": round(blurry_fraction, 4),
        "lowContrastFrameFraction": round(low_contrast_fraction, 4),
        "exposureRiskFrameFraction": round(exposure_risk_fraction, 4),
        "largeMotionFrameFraction": round(large_motion_fraction, 4),
        "recommendations": recommendations,
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

    sampling = frame_manifest.get("sampling", {}) if isinstance(frame_manifest.get("sampling"), dict) else {}
    duration = sampling.get("sourceDurationSeconds")
    coverage_end = sampling.get("coverageEndSeconds")
    try:
        duration_value = float(duration)
        coverage_end_value = float(coverage_end)
    except (TypeError, ValueError):
        duration_value = 0.0
        coverage_end_value = 0.0
    if duration_value > 0 and coverage_end_value > 0:
        coverage_ratio = min(1.0, coverage_end_value / duration_value)
        checks.append(
            {
                "id": "video_coverage",
                "status": "pass" if coverage_ratio >= 0.92 else "warning",
                "summary": (
                    "sampled frames span the source video"
                    if coverage_ratio >= 0.92
                    else f"sampled frames cover only {coverage_ratio:.1%} of the source video"
                ),
                "coverageRatio": round(coverage_ratio, 4),
                "coverageEndSeconds": round(coverage_end_value, 3),
                "sourceDurationSeconds": round(duration_value, 3),
                "strategy": sampling.get("strategy"),
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

    candidate_quality = frame_manifest.get("candidateQuality")
    if isinstance(candidate_quality, dict):
        checks.append(
            {
                "id": "candidate_quality",
                "status": candidate_quality.get("status", "warning"),
                "summary": candidate_quality.get("summary", "candidate frame quality scored"),
                **{key: value for key, value in candidate_quality.items() if key not in {"status", "summary"}},
            }
        )

    keyframe_selection = frame_manifest.get("keyframeSelection")
    if isinstance(keyframe_selection, dict):
        checks.append(
            {
                "id": "keyframe_selection",
                "status": keyframe_selection.get("status", "warning"),
                "summary": keyframe_selection.get("summary", "quality keyframes selected"),
                **{key: value for key, value in keyframe_selection.items() if key not in {"status", "summary"}},
            }
        )

    quality = analyze_capture_frame_quality(frames)
    frame_manifest["captureQuality"] = quality
    checks.append(
        {
            "id": "capture_quality",
            "status": quality.get("status", "warning"),
            "summary": quality.get("summary", "capture quality diagnostics completed"),
            **{key: value for key, value in quality.items() if key not in {"status", "summary"}},
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

    input_kind = str(intake_report.get("inputKind") or capture_input_kind(job))
    if input_kind == COLMAP_DATASET_INPUT_KIND:
        image_dir_raw = intake_report.get("imageDirectory")
        sparse_model_raw = intake_report.get("sparseModelPath")
        image_dir = Path(str(image_dir_raw)) if image_dir_raw else None
        sparse_model_path = Path(str(sparse_model_raw)) if sparse_model_raw else None
        if image_dir is None or not image_dir.exists() or sparse_model_path is None or not sparse_model_path.exists():
            base["stage"]["status"] = "setup_gap"
            base["checks"].append(
                {
                    "id": "precomputed_colmap_dataset",
                    "status": "setup_gap",
                    "summary": "intake did not provide a readable COLMAP dataset",
                    "imageDirectory": str(image_dir) if image_dir else None,
                    "sparseModelPath": str(sparse_model_path) if sparse_model_path else None,
                }
            )
            return base
        frames = colmap_dataset_frame_entries(image_dir)
        frame_dir = frame_run_directory(job_path)
        frame_dir.mkdir(parents=True, exist_ok=True)
        frame_manifest = {
            "schemaVersion": 1,
            "stage": {
                "id": "frame_sampling",
                "status": "pass",
                "generatedAt": utc_now(),
                "jobPath": str(job_path),
            },
            "inputKind": input_kind,
            "source": {
                "intakeReportPath": str(intake_path),
                "datasetPath": intake_report.get("datasetPath"),
                "imageDirectory": str(image_dir),
                "sparseModelPath": str(sparse_model_path),
            },
            "sampling": {
                "strategy": "precomputed_colmap_images",
                "targetFps": None,
                "effectiveFps": None,
                "maxFrames": len(frames),
                "actualFrameCount": len(frames),
                "cappedByMaxFrames": False,
            },
            "frameDirectory": str(image_dir),
            "frames": frames,
            "sparseModelPath": str(sparse_model_path),
        }
        frame_manifest_path = frame_dir / "frame_manifest.json"
        write_json(frame_manifest_path, frame_manifest)
        base["stage"]["status"] = "pass"
        base["inputKind"] = input_kind
        base["frameManifestPath"] = str(frame_manifest_path)
        base["frameDirectory"] = str(image_dir)
        base["sparseModelPath"] = str(sparse_model_path)
        base["sampling"] = frame_manifest["sampling"]
        base["checks"].append(
            {
                "id": "precomputed_frames",
                "status": "pass",
                "summary": f"skipped FFmpeg sampling; using {len(frames)} images from COLMAP dataset",
                "frameCount": len(frames),
                "imageDirectory": str(image_dir),
            }
        )
        return base

    if input_kind == NERFSTUDIO_DATASET_INPUT_KIND:
        dataset_path_raw = intake_report.get("datasetPath")
        transforms_path_raw = intake_report.get("transformsPath")
        dataset_path = Path(str(dataset_path_raw)) if dataset_path_raw else None
        transforms_path = Path(str(transforms_path_raw)) if transforms_path_raw else None
        if dataset_path is None or transforms_path is None or not transforms_path.exists():
            base["stage"]["status"] = "setup_gap"
            base["checks"].append(
                {
                    "id": "precomputed_dataset",
                    "status": "setup_gap",
                    "summary": "intake did not provide a readable Nerfstudio dataset",
                    "datasetPath": str(dataset_path) if dataset_path else None,
                    "transformsPath": str(transforms_path) if transforms_path else None,
                }
            )
            return base
        transforms = read_json(transforms_path)
        frames = nerfstudio_frame_entries(dataset_path, transforms)
        frame_dir = frame_run_directory(job_path)
        frame_dir.mkdir(parents=True, exist_ok=True)
        frame_manifest = {
            "schemaVersion": 1,
            "stage": {
                "id": "frame_sampling",
                "status": "pass",
                "generatedAt": utc_now(),
                "jobPath": str(job_path),
            },
            "inputKind": input_kind,
            "source": {
                "intakeReportPath": str(intake_path),
                "datasetPath": str(dataset_path),
                "transformsPath": str(transforms_path),
            },
            "sampling": {
                "strategy": "precomputed_nerfstudio_frames",
                "targetFps": None,
                "effectiveFps": None,
                "maxFrames": len(frames),
                "actualFrameCount": len(frames),
                "cappedByMaxFrames": False,
            },
            "frameDirectory": str(dataset_path),
            "frames": frames,
            "transformsPath": str(transforms_path),
        }
        frame_manifest_path = frame_dir / "frame_manifest.json"
        write_json(frame_manifest_path, frame_manifest)
        base["stage"]["status"] = "pass"
        base["inputKind"] = input_kind
        base["frameManifestPath"] = str(frame_manifest_path)
        base["frameDirectory"] = str(dataset_path)
        base["sampling"] = frame_manifest["sampling"]
        base["checks"].append(
            {
                "id": "precomputed_frames",
                "status": "pass",
                "summary": f"skipped FFmpeg sampling; using {len(frames)} frames from Nerfstudio transforms.json",
                "frameCount": len(frames),
                "transformsPath": str(transforms_path),
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

    metadata = intake_report.get("metadata", {}) if isinstance(intake_report.get("metadata"), dict) else {}
    sampling_plan = frame_sampling_plan(target_fps, max_frames, metadata.get("durationSeconds"))
    selection_plan = candidate_sampling_plan(target_fps, max_frames, metadata.get("durationSeconds"))
    effective_fps = float(sampling_plan["effectiveFps"])
    candidate_fps = float(selection_plan["candidateFps"])
    candidate_max_frames = int(selection_plan["candidateMaxFrames"])
    target_frame_count = int(selection_plan["targetFrameCount"])

    frame_dir = frame_run_directory(job_path)
    frame_dir.mkdir(parents=True, exist_ok=True)
    candidate_dir = frame_dir / "candidates"
    candidate_dir.mkdir(parents=True, exist_ok=True)
    output_pattern = candidate_dir / "candidate_%06d.jpg"
    fps_filter = f"fps={format_fps(candidate_fps)}"
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
            str(candidate_max_frames),
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

    candidate_frames = sorted(candidate_dir.glob("candidate_*.jpg"))
    candidates, candidate_quality_report = analyze_candidate_frames(candidate_frames, candidate_fps)
    selected_candidates, selection_report = select_keyframes_from_candidates(candidates, target_frame_count)
    selected_frames = materialize_selected_frames(selected_candidates, frame_dir)
    extracted_frames = sorted(frame_dir.glob("frame_*.jpg"))
    contact_sheet_stride = max(1, math.ceil(len(extracted_frames) / 25)) if extracted_frames else 1
    contact_sheet_filter = f"select='not(mod(n\\,{contact_sheet_stride}))',scale=160:-1,tile=5x5"
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
            contact_sheet_filter,
            "-frames:v",
            "1",
            str(contact_sheet_path),
        ],
        timeout_seconds=120,
    )
    base["commands"]["contactSheet"] = contact_sheet

    frame_manifest = build_frame_manifest(
        job_path,
        intake_report,
        frame_dir,
        contact_sheet_path,
        target_fps,
        effective_fps,
        max_frames,
        str(selection_plan["strategy"]),
        contact_sheet_stride,
        selected_frames=selected_frames,
    )
    frame_manifest["sampling"]["expectedUncappedFrameCount"] = sampling_plan.get("expectedUncappedFrameCount")
    frame_manifest["sampling"]["sourceStrategy"] = sampling_plan.get("strategy")
    frame_manifest["sampling"]["candidateFps"] = round(candidate_fps, 6)
    frame_manifest["sampling"]["candidateMaxFrames"] = candidate_max_frames
    frame_manifest["sampling"]["candidateFrameCount"] = len(candidate_frames)
    frame_manifest["sampling"]["targetFrameCount"] = target_frame_count
    frame_manifest["sampling"]["selectionStrategy"] = selection_report.get("strategy")
    frame_manifest["sampling"]["cappedByMaxFrames"] = bool(sampling_plan.get("cappedByMaxFrames"))
    frame_manifest["candidateFrameDirectory"] = str(candidate_dir)
    frame_manifest["candidateQuality"] = candidate_quality_report
    frame_manifest["keyframeSelection"] = selection_report
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
            "summary": (
                "quality keyframes selected across full video"
                if frame_manifest["sampling"].get("sourceStrategy") == "full_duration_even"
                else "quality keyframes selected"
            ),
        }
    )
    base["checks"].extend(checks)
    return base


def sfm_run_directory(job_path: Path) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return job_path.parent / "sfm" / stamp


def splat_training_run_directory(job_path: Path) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return job_path.parent / "splats" / stamp


def positive_int_setting(config: dict[str, Any], key: str, default: int, minimum: int, maximum: int) -> int:
    raw_value = config.get(key, default)
    try:
        value = int(raw_value)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, value))


def positive_float_setting(config: dict[str, Any], key: str, default: float, minimum: float, maximum: float) -> float:
    raw_value = config.get(key, default)
    try:
        value = float(raw_value)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, value))


def bool_setting(config: dict[str, Any], key: str, default: bool) -> bool:
    raw_value = config.get(key, default)
    if isinstance(raw_value, bool):
        return raw_value
    if isinstance(raw_value, str):
        return raw_value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(raw_value) if raw_value is not None else default


def optional_path(value: Any) -> Path | None:
    return Path(value) if isinstance(value, str) and value else None


def build_splatfacto_training_report(
    *,
    job_path: Path,
    base: dict[str, Any],
    sparse_model_path: Path | None,
    colmap_image_dir: Path | None,
    training_config: dict[str, Any],
    requested_profile: str,
    nerfstudio_data_path: Path | None = None,
    source_input_kind: str | None = None,
) -> dict[str, Any]:
    paths = nerfstudio_venv_paths()
    trainer_env, trainer_env_summary = build_nerfstudio_environment()
    base["commandEnvironment"] = trainer_env_summary
    base["training"] = {
        **training_config,
        "backend": "nerfstudio_splatfacto",
        "profile": requested_profile,
    }
    base["trainingDirectory"] = str(splat_training_run_directory(job_path))
    training_dir = Path(base["trainingDirectory"])
    progress_path = training_dir / "training_progress.json"
    commands: dict[str, Any] = {}
    base["commands"] = commands

    binary_checks = [
        {
            "id": "nerfstudio_virtualenv",
            "status": "pass" if paths["venv"].exists() else "setup_gap",
            "summary": "isolated Nerfstudio environment exists"
            if paths["venv"].exists()
            else "isolated Nerfstudio environment is missing",
            "path": str(paths["venv"]),
        },
        {
            "id": "ns_train",
            "status": "pass" if paths["ns_train"].exists() else "setup_gap",
            "summary": "ns-train is available" if paths["ns_train"].exists() else "ns-train is missing",
            "path": str(paths["ns_train"]),
        },
        {
            "id": "ns_export",
            "status": "pass" if paths["ns_export"].exists() else "setup_gap",
            "summary": "ns-export is available" if paths["ns_export"].exists() else "ns-export is missing",
            "path": str(paths["ns_export"]),
        },
        {
            "id": "ns_eval",
            "status": "pass" if paths["ns_eval"].exists() else "setup_gap",
            "summary": "ns-eval is available" if paths["ns_eval"].exists() else "ns-eval is missing",
            "path": str(paths["ns_eval"]),
        },
    ]
    base["checks"].extend(binary_checks)
    if any(check["status"] == "setup_gap" for check in binary_checks):
        base["stage"]["status"] = "setup_gap"
        return base

    import_check = run_command(
        [
            str(paths["python"]),
            "-c",
            (
                "import nerfstudio, torch, gsplat; "
                "device=torch.cuda.get_device_name(0) if torch.cuda.is_available() else None; "
                "print('nerfstudio=%s torch=%s cuda=%s device=%s gsplat=%s' % "
                "(getattr(nerfstudio, '__version__', None), torch.__version__, torch.cuda.is_available(), device, getattr(gsplat, '__version__', None)))"
            ),
        ],
        timeout_seconds=60,
        env=trainer_env,
    )
    commands["nerfstudioImportCheck"] = import_check
    import_stdout = str(import_check.get("stdout") or "")
    import_text = f"{import_stdout}\n{import_check.get('stderr') or ''}"
    import_status = "pass" if import_check["status"] == "pass" and "cuda=True" in import_stdout else "setup_gap"
    if "Found no NVIDIA driver" in import_text:
        import_status = "setup_gap"
    base["checks"].append(
        {
            "id": "nerfstudio_cuda",
            "status": import_status,
            "summary": import_stdout or command_summary(import_check) or "Nerfstudio CUDA check did not pass",
            "details": import_check,
        }
    )
    if import_status != "pass":
        base["stage"]["status"] = import_status
        return base

    profile = requested_profile if requested_profile in SPLATFACTO_PROFILE_DEFAULTS else "splatfacto_reference"
    defaults = SPLATFACTO_PROFILE_DEFAULTS[profile]
    method = str(training_config.get("method", defaults["method"]))
    if method not in {"splatfacto", "splatfacto-big"}:
        method = str(defaults["method"])
    cache_images = str(training_config.get("cacheImages", defaults["cacheImages"]))
    if cache_images not in {"cpu", "gpu"}:
        cache_images = str(defaults["cacheImages"])
    run_config = {
        "backend": "nerfstudio_splatfacto",
        "profile": profile,
        "requestedProfile": requested_profile,
        "method": method,
        "iterations": positive_int_setting(training_config, "iterations", int(defaults["iterations"]), 1, 150000),
        "downscaleFactor": positive_int_setting(training_config, "downscaleFactor", int(defaults["downscaleFactor"]), 1, 8),
        "cacheImages": cache_images,
        "evalInterval": positive_int_setting(training_config, "evalInterval", int(defaults["evalInterval"]), 1, 512),
        "stepsPerEvalImage": positive_int_setting(
            training_config,
            "stepsPerEvalImage",
            int(defaults["stepsPerEvalImage"]),
            1,
            150000,
        ),
        "stepsPerEvalAllImages": positive_int_setting(
            training_config,
            "stepsPerEvalAllImages",
            int(defaults["stepsPerEvalAllImages"]),
            1,
            150000,
        ),
        "stepsPerSave": positive_int_setting(training_config, "stepsPerSave", int(defaults["stepsPerSave"]), 1, 150000),
        "estimatedSeconds": positive_int_setting(
            training_config,
            "estimatedSeconds",
            int(defaults["estimatedSeconds"]),
            60,
            24 * 60 * 60,
        ),
        "timeoutSeconds": positive_int_setting(
            training_config,
            "timeoutSeconds",
            int(defaults["timeoutSeconds"]),
            60,
            24 * 60 * 60,
        ),
    }
    base["runConfig"] = run_config

    input_kind = source_input_kind or (NERFSTUDIO_DATASET_INPUT_KIND if nerfstudio_data_path is not None else PLAIN_VIDEO_INPUT_KIND)
    if nerfstudio_data_path is not None:
        try:
            data_summary = prepare_nerfstudio_transforms_data(
                data_dir=training_dir / "nerfstudio-data",
                dataset_path=nerfstudio_data_path,
                downscale_factor=int(run_config["downscaleFactor"]),
            )
        except Exception as exc:  # noqa: BLE001 - report dataset setup failures directly
            base["stage"]["status"] = "fail"
            base["checks"].append(
                {
                    "id": "nerfstudio_dataset_layout",
                    "status": "fail",
                    "summary": str(exc),
                }
            )
            return base
    else:
        if sparse_model_path is None or colmap_image_dir is None:
            base["stage"]["status"] = "fail"
            base["checks"].append(
                {
                    "id": "colmap_training_input",
                    "status": "fail",
                    "summary": "COLMAP Splatfacto training requires both sparseModelPath and colmapImageDirectory",
                }
            )
            return base
        colmap_text_dir = training_dir / "colmap_txt"
        colmap_text_dir.mkdir(parents=True, exist_ok=True)
        model_converter = run_command(
            [
                *colmap_command("model_converter", env=trainer_env),
                "--input_path",
                str(sparse_model_path),
                "--output_path",
                str(colmap_text_dir),
                "--output_type",
                "TXT",
            ],
            timeout_seconds=300,
            env=trainer_env,
        )
        commands["colmapModelConverter"] = model_converter
        base["checks"].append(
            {
                "id": "colmap_text_export",
                "status": model_converter["status"],
                "summary": "COLMAP text model exported"
                if model_converter["status"] == "pass"
                else command_summary(model_converter) or "COLMAP text export failed",
            }
        )
        if model_converter["status"] != "pass":
            base["stage"]["status"] = model_converter["status"]
            return base
        cameras = parse_colmap_cameras(colmap_text_dir / "cameras.txt")
        first_camera = next(iter(cameras.values()), None)
        expected_image_size = (
            int(first_camera["width"]),
            int(first_camera["height"]),
        ) if isinstance(first_camera, dict) and first_camera.get("width") and first_camera.get("height") else None
        selected_images = selected_images_from_colmap_text(colmap_text_dir, colmap_image_dir)
        try:
            data_summary = prepare_nerfstudio_colmap_data(
                data_dir=training_dir / "nerfstudio-data",
                sparse_model_path=sparse_model_path,
                colmap_image_dir=colmap_image_dir,
                downscale_factor=int(run_config["downscaleFactor"]),
                expected_image_size=expected_image_size,
            )
        except Exception as exc:  # noqa: BLE001 - report dataset setup failures directly
            base["stage"]["status"] = "fail"
            base["checks"].append(
                {
                    "id": "nerfstudio_dataset_layout",
                    "status": "fail",
                    "summary": str(exc),
                }
            )
            return base

    base["nerfstudioData"] = data_summary
    base["checks"].append(
        {
            "id": "nerfstudio_dataset_layout",
            "status": "pass",
            "summary": "Nerfstudio dataset layout prepared",
            "details": data_summary,
        }
    )

    if nerfstudio_data_path is not None:
        transforms = read_json(nerfstudio_data_path / "transforms.json")
        selected_images = selected_images_from_nerfstudio_transforms(nerfstudio_data_path, transforms)
        base["checks"].append(
            {
                "id": "nerfstudio_transform_cameras",
                "status": "pass" if selected_images else "fail",
                "summary": f"{len(selected_images)} camera poses loaded from transforms.json"
                if selected_images
                else "no camera poses could be loaded from transforms.json",
            }
        )
        if not selected_images:
            base["stage"]["status"] = "fail"
            return base
    else:
        pass
    timestamp = training_dir.name
    runs_dir = training_dir / "nerfstudio-runs"
    experiment_name = profile
    train_log_path = training_dir / "logs" / "ns-train.log"
    dataparser_name = "nerfstudio-data" if nerfstudio_data_path is not None else "colmap"
    dataparser_data_dir = Path(str(data_summary["dataDir"]))
    train_command = [
        str(paths["ns_train"]),
        method,
        "--output-dir",
        str(runs_dir),
        "--experiment-name",
        experiment_name,
        "--timestamp",
        timestamp,
        "--vis",
        "tensorboard",
        "--max-num-iterations",
        str(run_config["iterations"]),
        "--steps-per-save",
        str(run_config["stepsPerSave"]),
        "--steps-per-eval-image",
        str(run_config["stepsPerEvalImage"]),
        "--steps-per-eval-all-images",
        str(run_config["stepsPerEvalAllImages"]),
        "--viewer.quit-on-train-completion",
        "True",
        "--pipeline.datamanager.cache-images",
        str(run_config["cacheImages"]),
        dataparser_name,
        "--data",
        str(dataparser_data_dir),
        "--downscale-factor",
        str(run_config["downscaleFactor"]),
        "--eval-mode",
        "interval",
        "--eval-interval",
        str(run_config["evalInterval"]),
    ]
    progress_base = {
        "backend": "nerfstudio_splatfacto",
        "profile": profile,
        "method": method,
        "inputKind": input_kind,
        "dataparser": dataparser_name,
        "iterations": int(run_config["iterations"]),
        "startedAt": utc_now(),
    }
    trainer = run_logged_command_with_estimated_progress(
        train_command,
        timeout_seconds=int(run_config["timeoutSeconds"]),
        env=trainer_env,
        log_path=train_log_path,
        progress_path=progress_path,
        progress_base=progress_base,
        estimated_total_seconds=int(run_config["estimatedSeconds"]),
    )
    commands["splatfactoTrainer"] = trainer
    if trainer["status"] != "pass":
        base["stage"]["status"] = trainer["status"]
        base["checks"].append(
            {
                "id": "splatfacto_trainer",
                "status": trainer["status"],
                "summary": command_summary(trainer) or "Nerfstudio Splatfacto training failed",
                "logPath": str(train_log_path),
            }
        )
        return base

    config_path = runs_dir / experiment_name / method / timestamp / "config.yml"
    if not config_path.exists():
        candidates = sorted(runs_dir.glob(f"{experiment_name}/*/{timestamp}/config.yml"))
        if candidates:
            config_path = candidates[-1]
    checkpoint_dir = config_path.parent / "nerfstudio_models"
    checkpoint_candidates = sorted(checkpoint_dir.glob("*.ckpt")) if checkpoint_dir.exists() else []
    checkpoint_path = checkpoint_candidates[-1] if checkpoint_candidates else None
    dataparser_transform_path = config_path.parent / "dataparser_transforms.json"
    dataparser_transform = read_json(dataparser_transform_path) if dataparser_transform_path.exists() else {}

    export_dir = training_dir / "exports"
    export_filename = f"{profile}.ply"
    export_command = [
        str(paths["ns_export"]),
        "gaussian-splat",
        "--load-config",
        str(config_path),
        "--output-dir",
        str(export_dir),
        "--output-filename",
        export_filename,
    ]
    export_result = run_command(export_command, timeout_seconds=2 * 60 * 60, env=trainer_env)
    commands["splatfactoExport"] = export_result
    exported_artifact_path = export_dir / export_filename

    eval_dir = training_dir / "render_review"
    eval_json = eval_dir / "eval.json"
    eval_renders = eval_dir / "eval-renders"
    eval_command = [
        str(paths["ns_eval"]),
        "--load-config",
        str(config_path),
        "--output-path",
        str(eval_json),
        "--render-output-path",
        str(eval_renders),
    ]
    eval_result = run_command(eval_command, timeout_seconds=2 * 60 * 60, env=trainer_env)
    commands["splatfactoEval"] = eval_result

    eval_payload = read_json(eval_json) if eval_json.exists() else {}
    eval_metrics = eval_payload.get("results") if isinstance(eval_payload.get("results"), dict) else {}
    eval_images = sorted(eval_renders.glob("*.png")) if eval_renders.exists() else []
    contact_sheet_path = build_image_contact_sheet(eval_images, eval_dir / "contact_sheet.png")
    sample_render_path = eval_images[0] if eval_images else None

    ply_header = parse_ply_header(exported_artifact_path) if exported_artifact_path.exists() else {}
    gaussian_count = ply_header.get("vertexCount")
    render_review = {
        "status": "pass" if eval_result["status"] == "pass" and eval_json.exists() else "warning",
        "psnr": eval_metrics.get("psnr"),
        "ssim": eval_metrics.get("ssim"),
        "lpips": eval_metrics.get("lpips"),
        "fps": eval_metrics.get("fps"),
        "evalImageCount": len(eval_images),
        "evalJsonPath": str(eval_json) if eval_json.exists() else None,
        "contactSheetPath": str(contact_sheet_path) if contact_sheet_path else None,
    }
    training_metrics = {
        "backend": "nerfstudio_splatfacto",
        "inputKind": input_kind,
        "dataparser": dataparser_name,
        "profile": profile,
        "method": method,
        "iterations": int(run_config["iterations"]),
        "imagesUsed": len(selected_images),
        "selectedImages": selected_images,
        "gaussianCount": gaussian_count,
        "initialGaussianCount": None,
        "gaussianGrowthFactor": None,
        "wallTimeSeconds": trainer.get("wallTimeSeconds"),
        "downscaleFactor": run_config["downscaleFactor"],
        "renderReview": render_review,
    }
    if isinstance(dataparser_transform.get("transform"), list) and isinstance(dataparser_transform.get("scale"), (int, float)):
        training_metrics["coordinateTransform"] = {
            "source": "nerfstudio_dataparser",
            "path": str(dataparser_transform_path),
            "matrix": dataparser_transform["transform"],
            "scale": dataparser_transform["scale"],
        }
    artifact_ok = (
        export_result["status"] == "pass"
        and exported_artifact_path.exists()
        and exported_artifact_path.stat().st_size > 0
    )
    checkpoint_exists = checkpoint_path is not None and checkpoint_path.exists()
    result_status = "pass" if config_path.exists() and checkpoint_exists and artifact_ok else "fail"
    result = {
        "schemaVersion": 1,
        "status": result_status,
        "backend": "nerfstudio_splatfacto",
        "checkpointPath": str(checkpoint_path) if checkpoint_path is not None else None,
        "configPath": str(config_path) if config_path.exists() else None,
        "exportedArtifactPath": str(exported_artifact_path),
        "splatArtifactPath": str(exported_artifact_path),
        "sampleRenderPath": str(sample_render_path) if sample_render_path else None,
        "sampleTargetPath": None,
        "renderReviewPath": str(contact_sheet_path) if contact_sheet_path else None,
        "training": training_metrics,
        "versions": {"nerfstudio": import_stdout},
    }
    result_path = training_dir / "training_result.json"
    write_json(result_path, result)

    artifact_checks = [
        {
            "id": "splatfacto_trainer",
            "status": trainer["status"],
            "summary": "Nerfstudio Splatfacto training completed",
            "logPath": str(train_log_path),
        },
        {
            "id": "splatfacto_config",
            "status": "pass" if config_path.exists() else "fail",
            "summary": "Nerfstudio config exists" if config_path.exists() else "Nerfstudio config was not found",
            "path": str(config_path),
        },
        {
            "id": "checkpoint",
            "status": "pass" if checkpoint_exists else "fail",
            "summary": "checkpoint exists" if checkpoint_exists else "checkpoint was not found",
            "path": str(checkpoint_path) if checkpoint_path is not None else None,
        },
        {
            "id": "splatfacto_export",
            "status": export_result["status"],
            "summary": "Splatfacto PLY exported"
            if export_result["status"] == "pass"
            else command_summary(export_result) or "Splatfacto export failed",
        },
        {
            "id": "exported_artifact",
            "status": "pass"
            if exported_artifact_path.exists() and exported_artifact_path.stat().st_size > 0
            else "fail",
            "summary": "exported splat artifact exists"
            if exported_artifact_path.exists()
            else "exported splat artifact was not written",
            "path": str(exported_artifact_path),
        },
        {
            "id": "splatfacto_eval",
            "status": eval_result["status"] if eval_result["status"] == "pass" else "warning",
            "summary": "Nerfstudio eval metrics and review renders written"
            if eval_result["status"] == "pass"
            else command_summary(eval_result) or "Nerfstudio eval did not complete",
            "path": str(eval_json),
        },
        {
            "id": "render_review_artifact",
            "status": "pass" if contact_sheet_path and contact_sheet_path.exists() else "warning",
            "summary": "render review contact sheet exists"
            if contact_sheet_path and contact_sheet_path.exists()
            else "render review contact sheet was not written",
            "path": str(contact_sheet_path) if contact_sheet_path else None,
        },
    ]
    base["checks"].extend(artifact_checks)
    base["trainingResultPath"] = str(result_path)
    base["trainingResult"] = result
    base["checkpointPath"] = str(checkpoint_path) if checkpoint_path is not None else None
    base["configPath"] = str(config_path) if config_path.exists() else None
    base["exportedArtifactPath"] = str(exported_artifact_path)
    base["splatArtifactPath"] = str(exported_artifact_path)
    base["sampleRenderPath"] = str(sample_render_path) if sample_render_path else None
    base["sampleTargetPath"] = None
    base["renderReviewPath"] = str(contact_sheet_path) if contact_sheet_path else None
    base["metrics"] = training_metrics
    base["device"] = {"targetWorker": training_config.get("targetWorker", "windows-rtx-5090")}
    base["versions"] = {"nerfstudioImport": import_stdout}
    base["artifact"] = {
        "path": str(exported_artifact_path),
        "format": "ply",
        "sizeBytes": exported_artifact_path.stat().st_size if exported_artifact_path.exists() else 0,
        "sha256": file_sha256(exported_artifact_path) if exported_artifact_path.exists() else None,
    }

    check_statuses = [check.get("status") for check in base["checks"] if isinstance(check, dict)]
    if any(status == "fail" for status in check_statuses):
        base["stage"]["status"] = "fail"
    elif any(status == "warning" for status in check_statuses):
        base["stage"]["status"] = "warning"
    else:
        base["stage"]["status"] = "pass"
    return base


def prepare_colmap_image_directory(frames: list[Any], image_dir: Path) -> tuple[list[dict[str, str]], list[str]]:
    image_dir.mkdir(parents=True, exist_ok=True)
    copied: list[dict[str, str]] = []
    errors: list[str] = []
    for frame in frames:
        if not isinstance(frame, dict):
            errors.append("frame entry is not an object")
            continue
        source = Path(str(frame.get("path") or ""))
        if not source.exists() or not source.is_file():
            errors.append(f"frame file is missing: {source}")
            continue
        if source.suffix.lower() not in {".jpg", ".jpeg", ".png"}:
            errors.append(f"frame file is not a supported image: {source}")
            continue
        target = image_dir / source.name
        shutil.copy2(source, target)
        copied.append({"source": str(source), "path": str(target)})
    return copied, errors


def parse_colmap_model_analyzer(output: str) -> dict[str, Any]:
    metrics: dict[str, Any] = {}
    for line in output.splitlines():
        if "] " in line:
            line = line.split("] ", 1)[1]
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
        if registered_fraction >= 0.70:
            registered_status = "pass"
        elif registered_fraction >= 0.50:
            registered_status = "warning"
        else:
            registered_status = "fail"
        checks.append(
            {
                "id": "registered_frames",
                "status": registered_status,
                "summary": f"{registered_images}/{frame_count} frames registered",
                "registeredImages": registered_images,
                "frameCount": frame_count,
                "registeredFraction": round(registered_fraction, 4),
                "passThreshold": 0.70,
                "warningThreshold": 0.50,
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


def colmap_model_score(model: dict[str, Any]) -> tuple[int, int]:
    metrics = model.get("metrics", {}) if isinstance(model.get("metrics"), dict) else {}
    registered = metrics.get("registered_images")
    images = metrics.get("images")
    points = metrics.get("points")
    image_score = registered if isinstance(registered, int) else images if isinstance(images, int) else -1
    point_score = points if isinstance(points, int) else -1
    return image_score, point_score


def sfm_attempt_registered_fraction(attempt: dict[str, Any]) -> float:
    best_model = attempt.get("bestModel") if isinstance(attempt.get("bestModel"), dict) else {}
    metrics = best_model.get("metrics", {}) if isinstance(best_model.get("metrics"), dict) else {}
    registered = metrics.get("registered_images")
    if not isinstance(registered, int):
        registered = metrics.get("images")
    frame_count = attempt.get("frameCount")
    if isinstance(registered, int) and isinstance(frame_count, int) and frame_count > 0:
        return registered / frame_count
    return 0.0


def colmap_attempt_profiles(
    sfm_config: dict[str, Any],
    frame_count: int,
) -> list[dict[str, Any]]:
    feature_num_threads = positive_int_setting(sfm_config, "featureNumThreads", 4, 1, 64)
    feature_max_image_size = positive_int_setting(sfm_config, "featureMaxImageSize", 3200, 256, 8192)
    feature_max_num_features = positive_int_setting(sfm_config, "featureMaxNumFeatures", 8192, 512, 65536)
    matcher_num_threads = positive_int_setting(sfm_config, "matcherNumThreads", feature_num_threads, 1, 64)
    matcher_block_size = positive_int_setting(sfm_config, "exhaustiveBlockSize", 20, 1, 100)
    matcher_kind = str(sfm_config.get("matcher") or "exhaustive").strip().lower()
    if matcher_kind not in {"exhaustive", "sequential"}:
        matcher_kind = "exhaustive"
    sequential_overlap = positive_int_setting(sfm_config, "sequentialOverlap", 10, 1, 200)
    sequential_quadratic_overlap = bool_setting(sfm_config, "sequentialQuadraticOverlap", True)
    guided_matching = bool_setting(sfm_config, "guidedMatching", False)
    use_gpu = bool_setting(sfm_config, "useGpu", False)

    primary = {
        "name": "primary",
        "matcherKind": matcher_kind,
        "featureNumThreads": feature_num_threads,
        "featureMaxImageSize": feature_max_image_size,
        "featureMaxNumFeatures": feature_max_num_features,
        "matcherNumThreads": matcher_num_threads,
        "exhaustiveBlockSize": matcher_block_size,
        "sequentialOverlap": sequential_overlap,
        "sequentialQuadraticOverlap": sequential_quadratic_overlap,
        "guidedMatching": guided_matching,
        "useGpu": use_gpu,
    }
    profiles = [primary]
    if bool_setting(sfm_config, "autoRetry", True):
        profiles.append(
            {
                **primary,
                "name": "guided-sequential-rescue",
                "matcherKind": "sequential",
                "featureMaxImageSize": min(max(feature_max_image_size, 3840), 8192),
                "featureMaxNumFeatures": min(max(feature_max_num_features * 2, 16384), 65536),
                "sequentialOverlap": min(max(sequential_overlap * 2, 48), 200),
                "sequentialQuadraticOverlap": True,
                "guidedMatching": True,
            }
        )
        if frame_count <= 260:
            profiles.append(
                {
                    **primary,
                    "name": "exhaustive-guided-rescue",
                    "matcherKind": "exhaustive",
                    "featureMaxImageSize": min(max(feature_max_image_size, 3840), 8192),
                    "featureMaxNumFeatures": min(max(feature_max_num_features * 2, 16384), 65536),
                    "exhaustiveBlockSize": max(matcher_block_size, 30),
                    "guidedMatching": True,
                }
            )
    return profiles


def run_colmap_sfm_attempt(
    attempt_dir: Path,
    frame_count: int,
    colmap_image_dir: Path,
    profile: dict[str, Any],
) -> dict[str, Any]:
    attempt_dir.mkdir(parents=True, exist_ok=True)
    database_path = attempt_dir / "database.db"
    sparse_dir = attempt_dir / "sparse"
    sparse_dir.mkdir(parents=True, exist_ok=True)
    sift_use_gpu = "1" if profile.get("useGpu") else "0"
    matcher_kind = str(profile["matcherKind"])
    feature_gpu_option = colmap_option("feature_extractor", "SiftExtraction.use_gpu", "FeatureExtraction.use_gpu")
    feature_threads_option = colmap_option("feature_extractor", "SiftExtraction.num_threads", "FeatureExtraction.num_threads")
    feature_max_image_size_option = colmap_option(
        "feature_extractor",
        "SiftExtraction.max_image_size",
        "FeatureExtraction.max_image_size",
    )
    matcher_gpu_option = colmap_option(
        "exhaustive_matcher" if matcher_kind == "exhaustive" else "sequential_matcher",
        "SiftMatching.use_gpu",
        "FeatureMatching.use_gpu",
    )
    matcher_threads_option = colmap_option(
        "exhaustive_matcher" if matcher_kind == "exhaustive" else "sequential_matcher",
        "SiftMatching.num_threads",
        "FeatureMatching.num_threads",
    )
    matcher_guided_option = colmap_option(
        "exhaustive_matcher" if matcher_kind == "exhaustive" else "sequential_matcher",
        "SiftMatching.guided_matching",
        "FeatureMatching.guided_matching",
    )
    commands: dict[str, Any] = {}
    commands["featureExtractor"] = run_command(
        [
            *colmap_command("feature_extractor"),
            "--database_path",
            str(database_path),
            "--image_path",
            str(colmap_image_dir),
            "--ImageReader.single_camera",
            "1",
            feature_gpu_option,
            sift_use_gpu,
            feature_threads_option,
            str(profile["featureNumThreads"]),
            feature_max_image_size_option,
            str(profile["featureMaxImageSize"]),
            "--SiftExtraction.max_num_features",
            str(profile["featureMaxNumFeatures"]),
        ],
        timeout_seconds=3600,
    )
    if commands["featureExtractor"]["status"] != "pass":
        status, checks = validate_sfm_output(frame_count, None, None)
        checks.append(
            {
                "id": "colmap_feature_extractor",
                "status": commands["featureExtractor"]["status"],
                "summary": command_summary(commands["featureExtractor"], max_lines=5) or "COLMAP feature extraction failed",
            }
        )
        return {
            "name": profile["name"],
            "status": commands["featureExtractor"]["status"],
            "profile": profile,
            "databasePath": str(database_path),
            "sparseDirectory": str(sparse_dir),
            "commands": commands,
            "checks": checks,
            "sparseModels": [],
            "bestModel": None,
            "frameCount": frame_count,
        }

    matcher_command = [
        *colmap_command("exhaustive_matcher" if matcher_kind == "exhaustive" else "sequential_matcher"),
        "--database_path",
        str(database_path),
        matcher_gpu_option,
        sift_use_gpu,
        matcher_threads_option,
        str(profile["matcherNumThreads"]),
        matcher_guided_option,
        "1" if profile.get("guidedMatching") else "0",
    ]
    if matcher_kind == "exhaustive":
        matcher_command.extend(
            [
                "--ExhaustiveMatching.block_size",
                str(profile["exhaustiveBlockSize"]),
            ]
        )
    else:
        matcher_command.extend(
            [
                "--SequentialMatching.overlap",
                str(profile["sequentialOverlap"]),
                "--SequentialMatching.quadratic_overlap",
                "1" if profile.get("sequentialQuadraticOverlap") else "0",
            ]
        )

    matcher_command_name = f"{matcher_kind}Matcher"
    commands[matcher_command_name] = run_command(matcher_command, timeout_seconds=3600)
    matcher_result = commands[matcher_command_name]
    if matcher_result["status"] != "pass":
        status, checks = validate_sfm_output(frame_count, None, None)
        checks.append(
            {
                "id": "colmap_matcher",
                "status": matcher_result["status"],
                "summary": command_summary(matcher_result, max_lines=5) or "COLMAP matching failed",
            }
        )
        return {
            "name": profile["name"],
            "status": matcher_result["status"],
            "profile": profile,
            "databasePath": str(database_path),
            "sparseDirectory": str(sparse_dir),
            "commands": commands,
            "checks": checks,
            "sparseModels": [],
            "bestModel": None,
            "frameCount": frame_count,
        }

    commands["mapper"] = run_command(
        [
            *colmap_command("mapper"),
            "--database_path",
            str(database_path),
            "--image_path",
            str(colmap_image_dir),
            "--output_path",
            str(sparse_dir),
        ],
        timeout_seconds=3600,
    )
    if commands["mapper"]["status"] != "pass":
        status, checks = validate_sfm_output(frame_count, None, None)
        checks.append(
            {
                "id": "colmap_mapper",
                "status": commands["mapper"]["status"],
                "summary": command_summary(commands["mapper"], max_lines=5) or "COLMAP mapper failed",
            }
        )
        return {
            "name": profile["name"],
            "status": commands["mapper"]["status"],
            "profile": profile,
            "databasePath": str(database_path),
            "sparseDirectory": str(sparse_dir),
            "commands": commands,
            "checks": checks,
            "sparseModels": [],
            "bestModel": None,
            "frameCount": frame_count,
        }

    model_dirs = sorted(path for path in sparse_dir.iterdir() if path.is_dir())
    sparse_models: list[dict[str, Any]] = []
    for model_path in model_dirs:
        analyzer_result = run_command(colmap_command("model_analyzer", "--path", str(model_path)), timeout_seconds=300)
        commands[f"modelAnalyzer_{model_path.name}"] = analyzer_result
        analyzer_metrics = None
        if analyzer_result["status"] == "pass":
            analyzer_text = analyzer_result.get("stdout") or analyzer_result.get("stderr") or ""
            analyzer_metrics = parse_colmap_model_analyzer(analyzer_text)
        sparse_models.append(
            {
                "path": str(model_path),
                "name": model_path.name,
                "status": analyzer_result["status"],
                "metrics": analyzer_metrics or {},
            }
        )

    best_model = max(sparse_models, key=colmap_model_score) if sparse_models else None
    sparse_model_path = Path(best_model["path"]) if best_model else None
    analyzer_metrics = best_model.get("metrics", {}) if best_model else None
    status, checks = validate_sfm_output(frame_count, sparse_model_path, analyzer_metrics)
    return {
        "name": profile["name"],
        "status": status,
        "profile": profile,
        "databasePath": str(database_path),
        "sparseDirectory": str(sparse_dir),
        "sparseModelPath": str(sparse_model_path) if sparse_model_path else None,
        "commands": commands,
        "checks": checks,
        "sparseModels": sparse_models,
        "bestModel": best_model,
        "frameCount": frame_count,
    }


def build_sfm_report(job_path: Path, accept_warning: bool = False, allow_heavy: bool = False) -> dict[str, Any]:
    job = read_json(job_path)
    sfm_config = job.get("capture", {}).get("pipeline", {}).get("sfm", {})
    if not isinstance(sfm_config, dict):
        sfm_config = {}
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

    input_kind = str(frame_sampling_report.get("inputKind") or capture_input_kind(job))
    if input_kind == COLMAP_DATASET_INPUT_KIND:
        frame_manifest_path_raw = frame_sampling_report.get("frameManifestPath")
        frame_manifest_path = Path(str(frame_manifest_path_raw)) if frame_manifest_path_raw else None
        if frame_manifest_path is None or not frame_manifest_path.exists():
            base["stage"]["status"] = "setup_gap"
            base["checks"].append(
                {
                    "id": "frame_manifest",
                    "status": "setup_gap",
                    "summary": "precomputed frame manifest is missing",
                    "path": str(frame_manifest_path) if frame_manifest_path else None,
                }
            )
            return base
        frame_manifest = read_json(frame_manifest_path)
        source = frame_manifest.get("source") if isinstance(frame_manifest.get("source"), dict) else {}
        image_dir = source.get("imageDirectory") or frame_manifest.get("frameDirectory")
        sparse_model_path = source.get("sparseModelPath") or frame_manifest.get("sparseModelPath")
        frames = frame_manifest.get("frames", [])
        base["stage"]["status"] = "pass"
        base["inputKind"] = input_kind
        base["frameManifestPath"] = str(frame_manifest_path)
        base["datasetPath"] = source.get("datasetPath")
        base["colmapImageDirectory"] = image_dir
        base["sparseModelPath"] = sparse_model_path
        base["metrics"] = {
            "registeredImages": len(frames) if isinstance(frames, list) else 0,
            "sparsePoints": None,
            "precomputedImageCount": len(frames) if isinstance(frames, list) else 0,
        }
        base["checks"].append(
            {
                "id": "precomputed_colmap_model",
                "status": "pass",
                "summary": f"skipped COLMAP SfM; using existing sparse model with {len(frames) if isinstance(frames, list) else 0} images",
                "imageDirectory": image_dir,
                "sparseModelPath": sparse_model_path,
            }
        )
        base["sfm"] = {
            "backend": "precomputed_colmap",
            "note": "COLMAP was not run because the input dataset already contains a sparse model.",
        }
        return base

    if input_kind == NERFSTUDIO_DATASET_INPUT_KIND:
        frame_manifest_path_raw = frame_sampling_report.get("frameManifestPath")
        frame_manifest_path = Path(str(frame_manifest_path_raw)) if frame_manifest_path_raw else None
        if frame_manifest_path is None or not frame_manifest_path.exists():
            base["stage"]["status"] = "setup_gap"
            base["checks"].append(
                {
                    "id": "frame_manifest",
                    "status": "setup_gap",
                    "summary": "precomputed frame manifest is missing",
                    "path": str(frame_manifest_path) if frame_manifest_path else None,
                }
            )
            return base
        frame_manifest = read_json(frame_manifest_path)
        transforms_path = frame_manifest.get("transformsPath") or frame_sampling_report.get("transformsPath")
        dataset_path = (frame_manifest.get("source") or {}).get("datasetPath") if isinstance(frame_manifest.get("source"), dict) else None
        frames = frame_manifest.get("frames", [])
        base["stage"]["status"] = "pass"
        base["inputKind"] = input_kind
        base["frameManifestPath"] = str(frame_manifest_path)
        base["nerfstudioDataPath"] = dataset_path
        base["transformsPath"] = transforms_path
        base["colmapImageDirectory"] = frame_manifest.get("frameDirectory")
        base["sparseModelPath"] = None
        base["metrics"] = {
            "registeredImages": len(frames) if isinstance(frames, list) else 0,
            "sparsePoints": None,
            "precomputedCameraCount": len(frames) if isinstance(frames, list) else 0,
        }
        base["checks"].append(
            {
                "id": "precomputed_cameras",
                "status": "pass",
                "summary": f"skipped COLMAP SfM; using {len(frames) if isinstance(frames, list) else 0} Nerfstudio transform cameras",
                "transformsPath": transforms_path,
                "datasetPath": dataset_path,
            }
        )
        base["sfm"] = {
            "backend": "nerfstudio_transforms",
            "note": "COLMAP was not run because the input dataset already contains camera poses and intrinsics.",
        }
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

    colmap = run_command(colmap_command("--help"), timeout_seconds=10)
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
    colmap_image_dir = sfm_dir / "images"
    sparse_dir.mkdir(parents=True, exist_ok=True)
    colmap_images, colmap_image_errors = prepare_colmap_image_directory(frames, colmap_image_dir)
    if colmap_image_errors or len(colmap_images) != len(frames):
        base["stage"]["status"] = "fail"
        base["colmapImageDirectory"] = str(colmap_image_dir)
        base["checks"].append(
            {
                "id": "colmap_images",
                "status": "fail",
                "summary": "failed to prepare clean COLMAP image directory",
                "errors": colmap_image_errors,
                "copiedFrameCount": len(colmap_images),
                "expectedFrameCount": len(frames),
            }
        )
        return base

    base["colmapImageDirectory"] = str(colmap_image_dir)
    base["checks"].append(
        {
            "id": "colmap_images",
            "status": "pass",
            "summary": "prepared clean COLMAP image directory from frame manifest",
            "copiedFrameCount": len(colmap_images),
            "path": str(colmap_image_dir),
        }
    )

    attempt_profiles = colmap_attempt_profiles(sfm_config, len(frames))
    attempts: list[dict[str, Any]] = []
    for profile in attempt_profiles:
        attempt = run_colmap_sfm_attempt(
            sfm_dir / f"attempt-{profile['name']}",
            len(frames),
            colmap_image_dir,
            profile,
        )
        attempts.append(attempt)
        if attempt["status"] == "pass":
            break

    selected_attempt = max(
        attempts,
        key=lambda item: (
            2 if item.get("status") == "pass" else 1 if item.get("status") == "warning" else 0,
            sfm_attempt_registered_fraction(item),
            colmap_model_score(item["bestModel"]) if isinstance(item.get("bestModel"), dict) else (-1, -1),
        ),
    ) if attempts else None
    sparse_model_path = Path(str(selected_attempt.get("sparseModelPath"))) if selected_attempt and selected_attempt.get("sparseModelPath") else None
    best_model = selected_attempt.get("bestModel") if selected_attempt else None
    analyzer_metrics = best_model.get("metrics", {}) if isinstance(best_model, dict) else None

    status, checks = validate_sfm_output(len(frames), sparse_model_path, analyzer_metrics)
    base["stage"]["status"] = status
    base["sfmDirectory"] = str(sfm_dir)
    base["colmapImageDirectory"] = str(colmap_image_dir)
    base["databasePath"] = str(selected_attempt.get("databasePath")) if selected_attempt else str(database_path)
    base["sparseModelPath"] = str(sparse_model_path) if sparse_model_path else None
    base["sparseModels"] = selected_attempt.get("sparseModels", []) if selected_attempt else []
    base["sfmAttempts"] = attempts
    base["selectedAttempt"] = selected_attempt.get("name") if selected_attempt else None
    base["frameManifestPath"] = str(frame_manifest_path)
    base["metrics"] = analyzer_metrics or {}
    base["commands"] = {
        f"attempt_{attempt['name']}": attempt.get("commands", {})
        for attempt in attempts
    }
    base["colmap"] = {
        "versionSummary": command_summary(colmap, max_lines=3),
        "binary": colmap.get("executable"),
        "binaryOverrideEnv": os.environ.get("GSL_COLMAP_BIN"),
        "matcher": selected_attempt.get("profile", {}).get("matcherKind") if selected_attempt else None,
        "usesGpu": bool(selected_attempt.get("profile", {}).get("useGpu")) if selected_attempt else False,
        "resourceControls": selected_attempt.get("profile", {}) if selected_attempt else {},
        "note": "SfM uses the resolved COLMAP binary. The default remains the apt CPU COLMAP on PATH; set GSL_COLMAP_BIN to test a side-by-side CUDA build without replacing /usr/bin/colmap.",
    }
    if attempts:
        attempt_summaries = [
            f"{attempt['name']}={attempt['status']} ({sfm_attempt_registered_fraction(attempt):.1%})"
            for attempt in attempts
        ]
        base["checks"].append(
            {
                "id": "sfm_auto_retry",
                "status": "pass" if status == "pass" else "warning" if len(attempts) > 1 else "pass",
                "summary": f"COLMAP attempts: {', '.join(attempt_summaries)}; selected {base['selectedAttempt']}",
                "attemptCount": len(attempts),
                "selectedAttempt": base["selectedAttempt"],
            }
        )
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


def build_splat_training_report(
    job_path: Path,
    accept_warning: bool = False,
    allow_heavy: bool = False,
    training_profile_override: str | None = None,
) -> dict[str, Any]:
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

    job = read_json(job_path)
    training_config = base["training"] if isinstance(base.get("training"), dict) else {}
    requested_profile = str(training_profile_override or training_config.get("profile") or "smoke")
    requested_backend = str(training_config.get("backend") or "").strip().lower()
    input_kind = str(sfm_report.get("inputKind") or capture_input_kind(job))
    if input_kind == NERFSTUDIO_DATASET_INPUT_KIND:
        dataset_raw = sfm_report.get("nerfstudioDataPath")
        dataset_path = Path(str(dataset_raw)) if isinstance(dataset_raw, str) and dataset_raw else None
        transforms_raw = sfm_report.get("transformsPath")
        base["source"].update(
            {
                "inputKind": input_kind,
                "nerfstudioDataPath": str(dataset_path) if dataset_path else None,
                "transformsPath": transforms_raw,
            }
        )
        if dataset_path is None or not dataset_path.exists():
            base["stage"]["status"] = "setup_gap"
            base["checks"].append(
                {
                    "id": "nerfstudio_dataset",
                    "status": "setup_gap",
                    "summary": "Nerfstudio dataset path is missing from the SfM report",
                    "datasetPath": str(dataset_path) if dataset_path else None,
                }
            )
            return base
        if requested_backend in {"gsplat", "mini_gsplat", "mini-gsplat"}:
            base["stage"]["status"] = "setup_gap"
            base["checks"].append(
                {
                    "id": "nerfstudio_dataset_training_backend",
                    "status": "setup_gap",
                    "summary": "known-pose Nerfstudio datasets currently train through Nerfstudio Splatfacto, not the repo-local mini gsplat trainer",
                    "requestedBackend": requested_backend,
                }
            )
            return base
        return build_splatfacto_training_report(
            job_path=job_path,
            base=base,
            sparse_model_path=None,
            colmap_image_dir=None,
            training_config=training_config,
            requested_profile=requested_profile,
            nerfstudio_data_path=dataset_path,
            source_input_kind=input_kind,
        )

    sparse_model_raw = sfm_report.get("sparseModelPath")
    if not isinstance(sparse_model_raw, str) or not sparse_model_raw:
        base["stage"]["status"] = "fail"
        base["checks"].append(
            {
                "id": "sparse_model",
                "status": "fail",
                "summary": "SfM report does not declare sparseModelPath",
            }
        )
        return base

    sparse_model_path = Path(sparse_model_raw)
    if not sparse_model_path.exists():
        base["stage"]["status"] = "fail"
        base["checks"].append(
            {
                "id": "sparse_model",
                "status": "fail",
                "summary": "SfM sparse model path does not exist",
                "path": str(sparse_model_path),
            }
        )
        return base

    colmap_image_dir_raw = sfm_report.get("colmapImageDirectory")
    if not isinstance(colmap_image_dir_raw, str) or not colmap_image_dir_raw:
        base["stage"]["status"] = "fail"
        base["checks"].append(
            {
                "id": "colmap_image_directory",
                "status": "fail",
                "summary": "SfM report does not declare colmapImageDirectory",
            }
        )
        return base

    colmap_image_dir = Path(colmap_image_dir_raw)
    if not colmap_image_dir.exists():
        base["stage"]["status"] = "fail"
        base["checks"].append(
            {
                "id": "colmap_image_directory",
                "status": "fail",
                "summary": "COLMAP image directory does not exist",
                "path": str(colmap_image_dir),
            }
        )
        return base

    if requested_backend in {"nerfstudio_splatfacto", "splatfacto", "nerfstudio"} or requested_profile in SPLATFACTO_PROFILE_DEFAULTS:
        return build_splatfacto_training_report(
            job_path=job_path,
            base=base,
            sparse_model_path=sparse_model_path,
            colmap_image_dir=colmap_image_dir,
            training_config=training_config,
            requested_profile=requested_profile,
            source_input_kind=input_kind,
        )

    torch_cuda = check_torch_cuda()
    gsplat = check_python_import("gsplat")
    env_checks = [
        {
            "id": "pytorch_cuda",
            "status": torch_cuda["status"],
            "summary": torch_cuda.get("deviceName") or torch_cuda.get("message") or torch_cuda.get("version"),
            "details": torch_cuda,
        },
        {
            "id": "gsplat",
            "status": gsplat["status"],
            "summary": gsplat.get("version") or gsplat.get("message"),
            "details": gsplat,
        },
    ]
    base["checks"].extend(env_checks)
    if any(check["status"] == "fail" for check in env_checks):
        base["stage"]["status"] = "fail"
        return base
    if any(check["status"] == "setup_gap" for check in env_checks):
        base["stage"]["status"] = "setup_gap"
        return base

    trainer_env, trainer_env_summary = build_training_subprocess_environment(torch_cuda)
    base["commandEnvironment"] = trainer_env_summary
    gpu_baseline = gpu_load_snapshot(trainer_env)
    base["gpuLoadBaseline"] = {
        "status": gpu_baseline["status"],
        "summary": gpu_baseline["summary"],
        "gpus": gpu_baseline["gpus"],
        "computeProcesses": gpu_baseline["computeProcesses"],
        "ignoredComputeProcesses": gpu_baseline["ignoredComputeProcesses"],
    }
    base["checks"].append(
        {
            "id": "gpu_load_baseline",
            "status": gpu_baseline["status"],
            "summary": gpu_baseline["summary"],
            "details": base["gpuLoadBaseline"],
        }
    )
    nvcc_path = shutil.which("nvcc", path=trainer_env.get("PATH"))
    setup_checks = [
        {
            "id": "cuda_toolkit_nvcc",
            "status": "pass" if nvcc_path else "setup_gap",
            "summary": "nvcc is visible to the trainer" if nvcc_path else "nvcc is not visible to the trainer",
            "path": nvcc_path,
            "CUDA_HOME": trainer_env_summary.get("CUDA_HOME"),
        },
        check_python_dev_headers(),
        check_ninja_available(trainer_env),
    ]
    base["checks"].extend(setup_checks)
    if any(check["status"] == "setup_gap" for check in setup_checks):
        base["stage"]["status"] = "setup_gap"
        return base

    training_config = base["training"] if isinstance(base.get("training"), dict) else {}
    requested_profile = str(training_profile_override or training_config.get("profile") or "smoke")
    profile = requested_profile if requested_profile in TRAINING_PROFILE_DEFAULTS else "smoke"
    profile_defaults = TRAINING_PROFILE_DEFAULTS[profile]
    densify_strategy = str(training_config.get("densifyStrategy", profile_defaults["densifyStrategy"]))
    if densify_strategy not in DENSIFY_STRATEGIES:
        densify_strategy = str(profile_defaults["densifyStrategy"])
    run_config = {
        "profile": profile,
        "requestedProfile": requested_profile,
        "iterations": positive_int_setting(training_config, "iterations", int(profile_defaults["iterations"]), 1, 150000),
        "maxImages": positive_int_setting(training_config, "maxImages", int(profile_defaults["maxImages"]), 1, 512),
        "maxPoints": positive_int_setting(training_config, "maxPoints", int(profile_defaults["maxPoints"]), 100, 1000000),
        "maxRenderSize": positive_int_setting(training_config, "maxRenderSize", int(profile_defaults["maxRenderSize"]), 64, 4096),
        "maxGaussians": positive_int_setting(training_config, "maxGaussians", int(profile_defaults["maxGaussians"]), 100, 10000000),
        "sampleEvery": positive_int_setting(training_config, "sampleEvery", int(profile_defaults["sampleEvery"]), 1, 5000),
        "reviewSamples": positive_int_setting(training_config, "reviewSamples", int(profile_defaults["reviewSamples"]), 1, 32),
        "initialOpacity": positive_float_setting(training_config, "initialOpacity", float(profile_defaults["initialOpacity"]), 0.001, 0.999),
        "initialScaleMultiplier": positive_float_setting(training_config, "initialScaleMultiplier", float(profile_defaults["initialScaleMultiplier"]), 0.01, 10.0),
        "ssimWeight": positive_float_setting(training_config, "ssimWeight", float(profile_defaults["ssimWeight"]), 0.0, 1.0),
        "meanLr": positive_float_setting(training_config, "meanLr", float(profile_defaults["meanLr"]), 0.0, 1.0),
        "colorLr": positive_float_setting(training_config, "colorLr", float(profile_defaults["colorLr"]), 0.0, 1.0),
        "scaleLr": positive_float_setting(training_config, "scaleLr", float(profile_defaults["scaleLr"]), 0.0, 1.0),
        "opacityLr": positive_float_setting(training_config, "opacityLr", float(profile_defaults["opacityLr"]), 0.0, 1.0),
        "quatLr": positive_float_setting(training_config, "quatLr", float(profile_defaults["quatLr"]), 0.0, 1.0),
        "densifyStrategy": densify_strategy,
        "refineStartIter": positive_int_setting(training_config, "refineStartIter", int(profile_defaults["refineStartIter"]), 0, 50000),
        "refineStopIter": positive_int_setting(training_config, "refineStopIter", int(profile_defaults["refineStopIter"]), 0, 50000),
        "refineEvery": positive_int_setting(training_config, "refineEvery", int(profile_defaults["refineEvery"]), 1, 5000),
        "resetEvery": positive_int_setting(training_config, "resetEvery", int(profile_defaults["resetEvery"]), 1, 50000),
        "growGrad2d": positive_float_setting(training_config, "growGrad2d", float(profile_defaults["growGrad2d"]), 0.0, 10.0),
        "growScale3d": positive_float_setting(training_config, "growScale3d", float(profile_defaults["growScale3d"]), 0.0, 10.0),
        "pruneOpa": positive_float_setting(training_config, "pruneOpa", float(profile_defaults["pruneOpa"]), 0.0, 1.0),
        "absgrad": bool_setting(training_config, "absgrad", bool(profile_defaults["absgrad"])),
        "timeoutSeconds": positive_int_setting(
            training_config,
            "timeoutSeconds",
            TRAINING_TIMEOUT_SECONDS.get(profile, 2 * 60 * 60),
            60,
            24 * 60 * 60,
        ),
    }
    training_dir = splat_training_run_directory(job_path)
    result_path = training_dir / "training_result.json"
    trainer_script = repo_root_from_script() / "scripts" / "mini-gsplat-train.py"
    command = [
        sys.executable,
        str(trainer_script),
        "--sparse-model-path",
        str(sparse_model_path),
        "--image-dir",
        str(colmap_image_dir),
        "--output-dir",
        str(training_dir),
        "--result-json",
        str(result_path),
        "--profile",
        str(run_config["profile"]),
        "--iterations",
        str(run_config["iterations"]),
        "--max-images",
        str(run_config["maxImages"]),
        "--max-points",
        str(run_config["maxPoints"]),
        "--max-render-size",
        str(run_config["maxRenderSize"]),
        "--max-gaussians",
        str(run_config["maxGaussians"]),
        "--sample-every",
        str(run_config["sampleEvery"]),
        "--review-samples",
        str(run_config["reviewSamples"]),
        "--initial-opacity",
        str(run_config["initialOpacity"]),
        "--initial-scale-multiplier",
        str(run_config["initialScaleMultiplier"]),
        "--ssim-weight",
        str(run_config["ssimWeight"]),
        "--mean-lr",
        str(run_config["meanLr"]),
        "--color-lr",
        str(run_config["colorLr"]),
        "--scale-lr",
        str(run_config["scaleLr"]),
        "--opacity-lr",
        str(run_config["opacityLr"]),
        "--quat-lr",
        str(run_config["quatLr"]),
        "--densify-strategy",
        str(run_config["densifyStrategy"]),
        "--refine-start-iter",
        str(run_config["refineStartIter"]),
        "--refine-stop-iter",
        str(run_config["refineStopIter"]),
        "--refine-every",
        str(run_config["refineEvery"]),
        "--reset-every",
        str(run_config["resetEvery"]),
        "--grow-grad2d",
        str(run_config["growGrad2d"]),
        "--grow-scale3d",
        str(run_config["growScale3d"]),
        "--prune-opa",
        str(run_config["pruneOpa"]),
    ]
    if run_config["absgrad"]:
        command.append("--absgrad")
    trainer = run_command(command, timeout_seconds=int(run_config["timeoutSeconds"]), env=trainer_env)
    base["trainingDirectory"] = str(training_dir)
    base["runConfig"] = run_config
    base["commands"] = {"miniGsplatTrainer": trainer}

    if trainer["status"] != "pass":
        result_status = trainer["status"]
        result_summary = command_summary(trainer, max_lines=8) or "mini gsplat trainer failed"
        if result_path.exists():
            result = read_json(result_path)
            base["trainingResultPath"] = str(result_path)
            base["trainingResult"] = result
            if isinstance(result.get("status"), str):
                result_status = result["status"]
            result_checks = result.get("checks", []) if isinstance(result.get("checks"), list) else []
            base["checks"].extend(check for check in result_checks if isinstance(check, dict))
            for check in result_checks:
                if isinstance(check, dict) and check.get("summary"):
                    result_summary = str(check["summary"])
                    break
        base["stage"]["status"] = result_status if result_status in {"setup_gap", "blocked_license", "blocked_workload", "fail"} else trainer["status"]
        base["checks"].append(
            {
                "id": "mini_gsplat_trainer",
                "status": base["stage"]["status"],
                "summary": result_summary,
            }
        )
        return base

    if not result_path.exists():
        base["stage"]["status"] = "fail"
        base["checks"].append(
            {
                "id": "training_result",
                "status": "fail",
                "summary": "trainer completed without writing training_result.json",
                "path": str(result_path),
            }
        )
        return base

    result = read_json(result_path)
    base["trainingResultPath"] = str(result_path)
    base["trainingResult"] = result
    result_checks = result.get("checks", []) if isinstance(result.get("checks"), list) else []
    base["checks"].extend(check for check in result_checks if isinstance(check, dict))

    checkpoint_path = optional_path(result.get("checkpointPath"))
    exported_artifact_path = optional_path(result.get("exportedArtifactPath")) or optional_path(result.get("splatArtifactPath"))
    sample_render_path = optional_path(result.get("sampleRenderPath"))
    render_review_path = optional_path(result.get("renderReviewPath"))
    checkpoint_exists = checkpoint_path is not None and checkpoint_path.exists()
    exported_artifact_exists = (
        exported_artifact_path is not None
        and exported_artifact_path.exists()
        and exported_artifact_path.stat().st_size > 0
    )
    sample_render_exists = (
        sample_render_path is not None
        and sample_render_path.exists()
        and sample_render_path.stat().st_size > 0
    )
    render_review_exists = (
        render_review_path is not None
        and render_review_path.exists()
        and render_review_path.stat().st_size > 0
    )
    loss_samples = result.get("training", {}).get("lossSamples") if isinstance(result.get("training"), dict) else None
    artifact_checks = [
        {
            "id": "checkpoint",
            "status": "pass" if checkpoint_exists else "fail",
            "summary": "checkpoint exists" if checkpoint_exists else "checkpoint was not written",
            "path": str(checkpoint_path) if checkpoint_path is not None else None,
        },
        {
            "id": "exported_artifact",
            "status": "pass" if exported_artifact_exists else "fail",
            "summary": "exported splat artifact exists" if exported_artifact_exists else "exported splat artifact was not written",
            "path": str(exported_artifact_path) if exported_artifact_path is not None else None,
        },
        {
            "id": "loss_samples",
            "status": "pass" if isinstance(loss_samples, list) and len(loss_samples) >= 2 else "fail",
            "summary": "loss samples recorded" if isinstance(loss_samples, list) and len(loss_samples) >= 2 else "loss samples were not recorded",
        },
        {
            "id": "sample_render",
            "status": "pass" if sample_render_exists else "fail",
            "summary": "sample render exists" if sample_render_exists else "sample render was not written",
            "path": str(sample_render_path) if sample_render_path is not None else None,
        },
        {
            "id": "render_review_artifact",
            "status": "pass" if render_review_exists else "fail",
            "summary": "render review contact sheet exists" if render_review_exists else "render review contact sheet was not written",
            "path": str(render_review_path) if render_review_path is not None else None,
        },
    ]
    base["checks"].extend(artifact_checks)
    base["checkpointPath"] = str(checkpoint_path) if checkpoint_path is not None else None
    base["exportedArtifactPath"] = str(exported_artifact_path) if exported_artifact_path is not None else None
    base["splatArtifactPath"] = str(exported_artifact_path) if exported_artifact_path is not None else None
    base["sampleRenderPath"] = str(sample_render_path) if sample_render_path is not None else None
    base["sampleTargetPath"] = result.get("sampleTargetPath")
    base["renderReviewPath"] = str(render_review_path) if render_review_path is not None else None
    base["metrics"] = result.get("training", {})
    base["device"] = result.get("device", {})
    base["versions"] = result.get("versions", {})
    base["artifact"] = {
        "path": str(exported_artifact_path) if exported_artifact_path is not None else None,
        "format": "ply",
        "sizeBytes": exported_artifact_path.stat().st_size if exported_artifact_exists and exported_artifact_path is not None else 0,
        "sha256": file_sha256(exported_artifact_path) if exported_artifact_exists and exported_artifact_path is not None else None,
    }

    check_statuses = [check.get("status") for check in base["checks"] if isinstance(check, dict)]
    if result.get("status") != "pass" or any(status == "fail" for status in check_statuses):
        base["stage"]["status"] = "fail"
    elif any(status == "warning" for status in check_statuses):
        base["stage"]["status"] = "warning"
    else:
        base["stage"]["status"] = "pass"
    return base


def repo_relative_path(path: Path) -> str | None:
    try:
        return path.resolve().relative_to(repo_root_from_script().resolve()).as_posix()
    except ValueError:
        return None


def parse_ply_header(path: Path) -> dict[str, Any]:
    with path.open("rb") as handle:
        prefix = handle.read(65536)
    marker = b"end_header"
    index = prefix.find(marker)
    if index < 0:
        return {
            "status": "fail",
            "summary": "PLY header does not contain end_header",
        }
    line_end = prefix.find(b"\n", index)
    header_bytes = prefix[: line_end + 1 if line_end >= 0 else index + len(marker)]
    header = header_bytes.decode("ascii", errors="replace")
    lines = [line.strip() for line in header.splitlines() if line.strip()]
    ply_format = None
    vertex_count = None
    properties: list[str] = []
    in_vertex = False
    for line in lines:
        fields = line.split()
        if len(fields) >= 2 and fields[0] == "format":
            ply_format = fields[1]
        elif len(fields) >= 3 and fields[0] == "element":
            in_vertex = fields[1] == "vertex"
            if in_vertex:
                try:
                    vertex_count = int(fields[2])
                except ValueError:
                    vertex_count = None
        elif in_vertex and len(fields) >= 3 and fields[0] == "property":
            properties.append(fields[-1])
    required = {"x", "y", "z"}
    missing = sorted(required.difference(properties))
    return {
        "status": "pass" if ply_format and vertex_count is not None and not missing else "fail",
        "summary": "PLY header is readable" if ply_format and vertex_count is not None and not missing else "PLY header is missing required vertex fields",
        "format": ply_format,
        "vertexCount": vertex_count,
        "properties": properties,
        "headerBytes": len(header_bytes),
        "missingProperties": missing,
    }


PLY_PROPERTY_SIZES = {
    "char": 1,
    "int8": 1,
    "uchar": 1,
    "uint8": 1,
    "short": 2,
    "int16": 2,
    "ushort": 2,
    "uint16": 2,
    "int": 4,
    "int32": 4,
    "uint": 4,
    "uint32": 4,
    "float": 4,
    "float32": 4,
    "double": 8,
    "float64": 8,
}

PLY_PROPERTY_FORMATS = {
    "char": "b",
    "int8": "b",
    "uchar": "B",
    "uint8": "B",
    "short": "h",
    "int16": "h",
    "ushort": "H",
    "uint16": "H",
    "int": "i",
    "int32": "i",
    "uint": "I",
    "uint32": "I",
    "float": "f",
    "float32": "f",
    "double": "d",
    "float64": "d",
}

VIEWER_FILTER_PROFILE = {
    "name": "balanced_no_crop",
    "minOpacity": 0.03,
    "scalePercentile": 0.995,
    "coordinateCrop": False,
}

VIEWER_INTERACTIVE_BUDGET = {
    "name": "interactive_balanced_budget",
    "maxVertexCount": 2_000_000,
    "maxSizeBytes": 512 * 1024 * 1024,
    "minimumVertexCount": 750_000,
    "importanceTopRatio": 0.72,
}


def sigmoid(value: float) -> float:
    if value >= 0:
        exponent = math.exp(-value)
        return 1 / (1 + exponent)
    exponent = math.exp(value)
    return exponent / (1 + exponent)


def percentile(values: list[float], fraction: float) -> float:
    if not values:
        raise ValueError("cannot calculate percentile for an empty value list")
    ordered = sorted(values)
    index = round((len(ordered) - 1) * min(1.0, max(0.0, fraction)))
    return ordered[index]


def parse_binary_ply_layout(data: bytes) -> dict[str, Any]:
    marker = b"end_header"
    marker_index = data.find(marker)
    if marker_index < 0:
        raise ValueError("PLY header does not contain end_header")
    header_end = marker_index + len(marker)
    while header_end < len(data) and data[header_end] in (10, 13):
        header_end += 1

    header = data[:header_end].decode("ascii", errors="replace")
    lines = header.splitlines()
    ply_format = None
    vertex_count = None
    in_vertex = False
    properties: list[dict[str, Any]] = []
    for line in lines:
        fields = line.strip().split()
        if len(fields) >= 2 and fields[0] == "format":
            ply_format = fields[1]
        elif len(fields) >= 3 and fields[0] == "element":
            in_vertex = fields[1] == "vertex"
            if in_vertex:
                vertex_count = int(fields[2])
        elif in_vertex and len(fields) >= 3 and fields[0] == "property":
            property_type = fields[1]
            if property_type == "list":
                raise ValueError("PLY vertex list properties are not supported for viewer filtering")
            property_size = PLY_PROPERTY_SIZES.get(property_type)
            property_format = PLY_PROPERTY_FORMATS.get(property_type)
            if property_size is None or property_format is None:
                raise ValueError(f"unsupported PLY property type {property_type}")
            properties.append(
                {
                    "name": fields[2],
                    "type": property_type,
                    "size": property_size,
                    "format": property_format,
                    "offset": 0,
                }
            )

    if ply_format != "binary_little_endian":
        raise ValueError(f"unsupported PLY format {ply_format or 'unknown'}")
    if vertex_count is None or vertex_count <= 0:
        raise ValueError("PLY vertex count is empty")

    stride = 0
    for prop in properties:
        prop["offset"] = stride
        stride += prop["size"]
    properties_by_name = {prop["name"]: prop for prop in properties}
    for required in ("x", "y", "z"):
        if required not in properties_by_name:
            raise ValueError(f"PLY missing {required}")

    vertex_bytes_end = header_end + vertex_count * stride
    if vertex_bytes_end > len(data):
        raise ValueError("PLY vertex data is shorter than the declared vertex count")

    return {
        "header": header,
        "headerEnd": header_end,
        "vertexCount": vertex_count,
        "properties": properties,
        "propertiesByName": properties_by_name,
        "stride": stride,
        "vertexBytesEnd": vertex_bytes_end,
    }


def read_ply_property(view: memoryview, base: int, prop: dict[str, Any]) -> float:
    return float(struct.unpack_from("<" + prop["format"], view, base + int(prop["offset"]))[0])


def replace_ply_vertex_count(header: str, vertex_count: int) -> bytes:
    lines = []
    replaced = False
    for line in header.splitlines():
        fields = line.strip().split()
        if len(fields) >= 3 and fields[0] == "element" and fields[1] == "vertex":
            lines.append(f"element vertex {vertex_count}")
            replaced = True
        else:
            lines.append(line)
    if not replaced:
        raise ValueError("PLY header has no vertex element")
    return ("\n".join(lines) + "\n").encode("ascii")


def build_viewer_filtered_ply(source: Path, target: Path) -> dict[str, Any]:
    data = source.read_bytes()
    layout = parse_binary_ply_layout(data)
    props = layout["propertiesByName"]
    stride = int(layout["stride"])
    header_end = int(layout["headerEnd"])
    vertex_count = int(layout["vertexCount"])
    view = memoryview(data)

    has_opacity = "opacity" in props
    has_scale = all(name in props for name in ("scale_0", "scale_1", "scale_2"))
    records: list[dict[str, float]] = []
    scale_values: list[float] = []
    for index in range(vertex_count):
        base = header_end + index * stride
        opacity = sigmoid(read_ply_property(view, base, props["opacity"])) if has_opacity else 1.0
        if has_scale:
            average_log_scale = (
                read_ply_property(view, base, props["scale_0"])
                + read_ply_property(view, base, props["scale_1"])
                + read_ply_property(view, base, props["scale_2"])
            ) / 3
            average_scale = math.exp(average_log_scale)
        else:
            average_scale = 0.0
        records.append(
            {
                "index": float(index),
                "x": read_ply_property(view, base, props["x"]),
                "y": read_ply_property(view, base, props["y"]),
                "z": read_ply_property(view, base, props["z"]),
                "opacity": opacity,
                "averageScale": average_scale,
            }
        )
        scale_values.append(average_scale)

    max_scale = percentile(scale_values, float(VIEWER_FILTER_PROFILE["scalePercentile"])) if has_scale else float("inf")
    initial = [
        item
        for item in records
        if item["opacity"] >= float(VIEWER_FILTER_PROFILE["minOpacity"]) and item["averageScale"] <= max_scale
    ]
    if len(initial) < max(1000, int(vertex_count * 0.4)):
        initial = records

    bounds: dict[str, tuple[float, float]] = {}
    if VIEWER_FILTER_PROFILE.get("coordinateCrop"):
        for axis in ("x", "y", "z"):
            values = [item[axis] for item in initial]
            low = percentile(values, float(VIEWER_FILTER_PROFILE["boundsLowPercentile"]))
            high = percentile(values, float(VIEWER_FILTER_PROFILE["boundsHighPercentile"]))
            padding = max((high - low) * float(VIEWER_FILTER_PROFILE["boundsPaddingRatio"]), 1.0e-6)
            bounds[axis] = (low - padding, high + padding)

    filtered_indices = [
        int(item["index"])
        for item in initial
        if not bounds or all(bounds[axis][0] <= item[axis] <= bounds[axis][1] for axis in ("x", "y", "z"))
    ]
    if len(filtered_indices) < max(1000, int(vertex_count * 0.35)):
        filtered_indices = [int(item["index"]) for item in records]
        initial = records
        bounds = {}

    max_by_size = max(
        int(VIEWER_INTERACTIVE_BUDGET["minimumVertexCount"]),
        int((int(VIEWER_INTERACTIVE_BUDGET["maxSizeBytes"]) - header_end) / max(stride, 1)),
    )
    budget_count = min(int(VIEWER_INTERACTIVE_BUDGET["maxVertexCount"]), max_by_size)
    budget_count = max(int(VIEWER_INTERACTIVE_BUDGET["minimumVertexCount"]), budget_count)
    downsampled = len(filtered_indices) > budget_count

    if downsampled:
        filtered_set = set(filtered_indices)
        candidates = [item for item in initial if int(item["index"]) in filtered_set]
        top_count = max(1, min(budget_count, int(round(budget_count * float(VIEWER_INTERACTIVE_BUDGET["importanceTopRatio"])))))
        fill_count = max(0, budget_count - top_count)

        def importance(item: dict[str, float]) -> float:
            scale_penalty = math.sqrt(max(item["averageScale"], 1.0e-8))
            return item["opacity"] / max(scale_penalty, 1.0e-4)

        ranked = sorted(candidates, key=importance, reverse=True)
        selected = {int(item["index"]) for item in ranked[:top_count]}
        if fill_count:
            remainder = [item for item in candidates if int(item["index"]) not in selected]
            if remainder:
                step = len(remainder) / fill_count
                for offset in range(fill_count):
                    selected.add(int(remainder[min(len(remainder) - 1, int(offset * step))]["index"]))
        kept_indices = sorted(selected)
    else:
        kept_indices = filtered_indices

    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("wb") as handle:
        handle.write(replace_ply_vertex_count(str(layout["header"]), len(kept_indices)))
        for index in kept_indices:
            base = header_end + index * stride
            handle.write(data[base : base + stride])
        tail_start = int(layout["vertexBytesEnd"])
        if tail_start < len(data):
            handle.write(data[tail_start:])

    return {
        "status": "pass",
        "summary": f"viewer PLY filtered from {vertex_count} to {len(kept_indices)} splats",
        "path": str(target),
        "repoRelativePath": repo_relative_path(target),
        "originalVertexCount": vertex_count,
        "filteredVertexCount": len(filtered_indices),
        "vertexCount": len(kept_indices),
        "removedVertexCount": vertex_count - len(kept_indices),
        "keptRatio": round(len(kept_indices) / max(vertex_count, 1), 6),
        "downsampledForInteractiveViewer": downsampled,
        "filterProfile": dict(VIEWER_FILTER_PROFILE),
        "interactiveBudget": dict(VIEWER_INTERACTIVE_BUDGET),
        "maxAverageScale": max_scale if math.isfinite(max_scale) else None,
        "bounds": {axis: [round(pair[0], 6), round(pair[1], 6)] for axis, pair in bounds.items()},
    }


def colmap_content_lines(path: Path) -> list[str]:
    if not path.exists():
        return []
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]


def parse_colmap_cameras(path: Path) -> dict[int, dict[str, Any]]:
    cameras: dict[int, dict[str, Any]] = {}
    for line in colmap_content_lines(path):
        fields = line.split()
        if len(fields) < 5:
            continue
        camera_id = int(fields[0])
        cameras[camera_id] = {
            "cameraId": camera_id,
            "model": fields[1],
            "width": int(fields[2]),
            "height": int(fields[3]),
            "params": [float(value) for value in fields[4:]],
        }
    return cameras


def parse_colmap_images(path: Path) -> dict[int, dict[str, Any]]:
    lines = colmap_content_lines(path)
    images: dict[int, dict[str, Any]] = {}
    index = 0
    while index < len(lines):
        fields = lines[index].split()
        if len(fields) >= 10:
            image_id = int(fields[0])
            images[image_id] = {
                "imageId": image_id,
                "qvec": [float(value) for value in fields[1:5]],
                "tvec": [float(value) for value in fields[5:8]],
                "cameraId": int(fields[8]),
                "name": " ".join(fields[9:]),
            }
        index += 2
    return images


def qvec_to_rotmat(qvec: list[float]) -> list[list[float]]:
    qw, qx, qy, qz = qvec
    return [
        [
            1 - 2 * qy * qy - 2 * qz * qz,
            2 * qx * qy - 2 * qw * qz,
            2 * qz * qx + 2 * qw * qy,
        ],
        [
            2 * qx * qy + 2 * qw * qz,
            1 - 2 * qz * qz - 2 * qx * qx,
            2 * qy * qz - 2 * qw * qx,
        ],
        [
            2 * qz * qx - 2 * qw * qy,
            2 * qy * qz + 2 * qw * qx,
            1 - 2 * qx * qx - 2 * qy * qy,
        ],
    ]


def transpose3(matrix: list[list[float]]) -> list[list[float]]:
    return [[matrix[row][column] for row in range(3)] for column in range(3)]


def mat3_vec(matrix: list[list[float]], vector: list[float]) -> list[float]:
    return [
        matrix[0][0] * vector[0] + matrix[0][1] * vector[1] + matrix[0][2] * vector[2],
        matrix[1][0] * vector[0] + matrix[1][1] * vector[1] + matrix[1][2] * vector[2],
        matrix[2][0] * vector[0] + matrix[2][1] * vector[1] + matrix[2][2] * vector[2],
    ]


def normalize3(vector: list[float]) -> list[float]:
    length = math.sqrt(sum(value * value for value in vector))
    if length <= 1.0e-12:
        return [0.0, 0.0, 0.0]
    return [value / length for value in vector]


def rounded3(vector: list[float]) -> list[float]:
    return [round(value, 8) for value in vector]


def nerfstudio_camera_transform(training_metrics: dict[str, Any]) -> dict[str, Any] | None:
    transform = training_metrics.get("coordinateTransform")
    if not isinstance(transform, dict):
        return None
    matrix = transform.get("matrix")
    scale = transform.get("scale")
    if (
        not isinstance(matrix, list)
        or len(matrix) != 3
        or not all(isinstance(row, list) and len(row) == 4 for row in matrix)
        or not isinstance(scale, (int, float))
    ):
        return None
    return {"matrix": matrix, "scale": float(scale)}


def apply_nerfstudio_transform_to_view(view: dict[str, Any], transform: dict[str, Any]) -> dict[str, Any]:
    matrix = transform["matrix"]
    scale = transform["scale"]

    def transform_point(point: list[float]) -> list[float]:
        return [
            scale * (float(row[0]) * point[0] + float(row[1]) * point[1] + float(row[2]) * point[2] + float(row[3]))
            for row in matrix
        ]

    def transform_direction(vector: list[float]) -> list[float]:
        return normalize3(
            [
                float(row[0]) * vector[0] + float(row[1]) * vector[1] + float(row[2]) * vector[2]
                for row in matrix
            ]
        )

    adjusted = dict(view)
    adjusted["position"] = rounded3(transform_point([float(value) for value in view["position"]]))
    adjusted["forward"] = rounded3(transform_direction([float(value) for value in view["forward"]]))
    adjusted["up"] = rounded3(transform_direction([float(value) for value in view["up"]]))
    adjusted["coordinateSpace"] = "nerfstudio_dataparser"
    return adjusted


def camera_intrinsics_for_manifest(
    camera: dict[str, Any],
    render_width: int | None,
    render_height: int | None,
) -> dict[str, Any]:
    model = camera.get("model")
    params = camera.get("params", [])
    width = int(camera.get("width") or 0)
    height = int(camera.get("height") or 0)
    if model in {"SIMPLE_PINHOLE", "SIMPLE_RADIAL"} and len(params) >= 3:
        fx = fy = float(params[0])
        cx = float(params[1])
        cy = float(params[2])
    elif model in {"PINHOLE", "OPENCV", "OPENCV_FISHEYE", "FULL_OPENCV"} and len(params) >= 4:
        fx = float(params[0])
        fy = float(params[1])
        cx = float(params[2])
        cy = float(params[3])
    else:
        fx = fy = max(width, height, 1)
        cx = width / 2
        cy = height / 2

    scaled_width = int(render_width or width or 1)
    scaled_height = int(render_height or height or 1)
    scale_x = scaled_width / width if width else 1.0
    scale_y = scaled_height / height if height else 1.0
    fy_scaled = max(fy * scale_y, 1.0e-6)
    fov_y = math.degrees(2 * math.atan(scaled_height / (2 * fy_scaled)))
    return {
        "model": model,
        "sourceWidth": width,
        "sourceHeight": height,
        "width": scaled_width,
        "height": scaled_height,
        "fx": round(fx * scale_x, 6),
        "fy": round(fy * scale_y, 6),
        "cx": round(cx * scale_x, 6),
        "cy": round(cy * scale_y, 6),
        "fovYDegrees": round(fov_y, 6),
    }


def camera_view_from_colmap(
    *,
    image: dict[str, Any],
    camera: dict[str, Any],
    selected_index: int,
    render_width: int | None,
    render_height: int | None,
    review_sample: dict[str, Any] | None = None,
) -> dict[str, Any]:
    rotation = qvec_to_rotmat(image["qvec"])
    camera_to_world = transpose3(rotation)
    tvec = image["tvec"]
    center = mat3_vec(camera_to_world, [-tvec[0], -tvec[1], -tvec[2]])
    down = mat3_vec(camera_to_world, [0.0, 1.0, 0.0])
    forward = mat3_vec(camera_to_world, [0.0, 0.0, 1.0])
    up = [-down[0], -down[1], -down[2]]
    intrinsics = camera_intrinsics_for_manifest(camera, render_width, render_height)
    view = {
        "selectedIndex": selected_index,
        "imageId": image["imageId"],
        "imageName": image["name"],
        "cameraId": image["cameraId"],
        "position": rounded3(center),
        "forward": rounded3(normalize3(forward)),
        "up": rounded3(normalize3(up)),
        "intrinsics": intrinsics,
        "fovYDegrees": intrinsics["fovYDegrees"],
    }
    if review_sample is not None:
        view["referenceKind"] = "render_review"
        view["reviewOrder"] = review_sample.get("order")
        view["reviewMae"] = review_sample.get("mae")
        view["renderPath"] = review_sample.get("renderPath")
        view["targetPath"] = review_sample.get("targetPath")
    else:
        view["referenceKind"] = "training_selected"
    return view


def valid_nerfstudio_transform_matrix(matrix: Any) -> bool:
    return (
        isinstance(matrix, list)
        and len(matrix) >= 3
        and all(isinstance(row, list) and len(row) >= 4 for row in matrix[:3])
    )


def camera_view_from_nerfstudio_selected(
    *,
    selected: dict[str, Any],
    selected_index: int,
    review_sample: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    matrix = selected.get("transformMatrix")
    if not valid_nerfstudio_transform_matrix(matrix):
        return None
    rows = matrix[:3]
    position = [float(rows[0][3]), float(rows[1][3]), float(rows[2][3])]
    up = [float(rows[0][1]), float(rows[1][1]), float(rows[2][1])]
    forward = [-float(rows[0][2]), -float(rows[1][2]), -float(rows[2][2])]
    intrinsics = selected.get("intrinsics") if isinstance(selected.get("intrinsics"), dict) else {}
    fov_y = intrinsics.get("fovYDegrees") if isinstance(intrinsics.get("fovYDegrees"), (int, float)) else 60.0
    view = {
        "selectedIndex": selected_index,
        "imageId": selected.get("imageId"),
        "imageName": selected.get("name") or selected.get("filePath"),
        "cameraId": selected.get("cameraId"),
        "position": rounded3(position),
        "forward": rounded3(normalize3(forward)),
        "up": rounded3(normalize3(up)),
        "intrinsics": intrinsics,
        "fovYDegrees": round(float(fov_y), 6),
        "coordinateSpace": "nerfstudio_input",
    }
    if review_sample is not None:
        view["referenceKind"] = "render_review"
        view["reviewOrder"] = review_sample.get("order")
        view["reviewMae"] = review_sample.get("mae")
        view["renderPath"] = review_sample.get("renderPath")
        view["targetPath"] = review_sample.get("targetPath")
    else:
        view["referenceKind"] = "training_selected"
    return view


def build_camera_views(training_report: dict[str, Any]) -> dict[str, Any]:
    metrics = training_report.get("metrics", {})
    if not isinstance(metrics, dict):
        return {"status": "warning", "summary": "training metrics missing", "views": []}

    training_dir_raw = training_report.get("trainingDirectory")
    training_dir = Path(training_dir_raw) if isinstance(training_dir_raw, str) and training_dir_raw else None
    if training_dir is None:
        result_path_raw = training_report.get("trainingResultPath")
        if isinstance(result_path_raw, str) and result_path_raw:
            training_dir = Path(result_path_raw).parent
    if training_dir is None:
        return {"status": "warning", "summary": "training directory missing", "views": []}

    selected_images = metrics.get("selectedImages", [])
    if not isinstance(selected_images, list) or not selected_images:
        return {"status": "warning", "summary": "selected training images missing", "views": []}

    render_width = metrics.get("renderWidth")
    render_height = metrics.get("renderHeight")
    render_width = int(render_width) if isinstance(render_width, (int, float)) else None
    render_height = int(render_height) if isinstance(render_height, (int, float)) else None
    review = metrics.get("renderReview", {}) if isinstance(metrics.get("renderReview"), dict) else {}
    review_samples = review.get("samples", []) if isinstance(review.get("samples"), list) else []
    camera_transform = nerfstudio_camera_transform(metrics)

    ordered_items: list[tuple[int, dict[str, Any] | None]] = []
    seen_indices: set[int] = set()
    for sample in review_samples:
        if not isinstance(sample, dict):
            continue
        camera_index = sample.get("cameraIndex")
        if isinstance(camera_index, int) and 0 <= camera_index < len(selected_images) and camera_index not in seen_indices:
            ordered_items.append((camera_index, sample))
            seen_indices.add(camera_index)
    for selected_index in range(len(selected_images)):
        if selected_index not in seen_indices:
            ordered_items.append((selected_index, None))
            seen_indices.add(selected_index)

    if any(isinstance(item, dict) and valid_nerfstudio_transform_matrix(item.get("transformMatrix")) for item in selected_images):
        views: list[dict[str, Any]] = []
        for selected_index, review_sample in ordered_items:
            selected = selected_images[selected_index]
            if not isinstance(selected, dict):
                continue
            view = camera_view_from_nerfstudio_selected(
                selected=selected,
                selected_index=selected_index,
                review_sample=review_sample,
            )
            if view is None:
                continue
            if camera_transform is not None:
                view = apply_nerfstudio_transform_to_view(view, camera_transform)
            views.append(view)
        return {
            "status": "pass" if views else "warning",
            "summary": f"{len(views)} Nerfstudio camera views exported" if views else "no Nerfstudio camera views could be exported",
            "views": views,
            "source": {
                "selectedImageCount": len(selected_images),
                "renderReviewSampleCount": len(review_samples),
                "coordinateSpace": "nerfstudio_dataparser" if camera_transform is not None else "nerfstudio_input",
            },
        }

    colmap_text_dir = training_dir / "colmap_txt"
    cameras = parse_colmap_cameras(colmap_text_dir / "cameras.txt")
    images_by_id = parse_colmap_images(colmap_text_dir / "images.txt")
    images_by_name = {image["name"]: image for image in images_by_id.values()}

    views: list[dict[str, Any]] = []
    for selected_index, review_sample in ordered_items:
        selected = selected_images[selected_index]
        if not isinstance(selected, dict):
            continue
        image_id = selected.get("imageId")
        image_name = selected.get("name")
        image = images_by_id.get(image_id) if isinstance(image_id, int) else None
        if image is None and isinstance(image_name, str):
            image = images_by_name.get(image_name)
        if image is None:
            continue
        camera = cameras.get(image["cameraId"])
        if camera is None:
            continue
        view = camera_view_from_colmap(
            image=image,
            camera=camera,
            selected_index=selected_index,
            render_width=render_width,
            render_height=render_height,
            review_sample=review_sample,
        )
        if camera_transform is not None:
            view = apply_nerfstudio_transform_to_view(view, camera_transform)
        views.append(view)

    return {
        "status": "pass" if views else "warning",
        "summary": f"{len(views)} COLMAP camera views exported" if views else "no COLMAP camera views could be exported",
        "views": views,
        "source": {
            "colmapTextPath": str(colmap_text_dir),
            "selectedImageCount": len(selected_images),
            "renderReviewSampleCount": len(review_samples),
            "coordinateSpace": "nerfstudio_dataparser" if camera_transform is not None else "colmap_world",
        },
    }


def build_viewer_manifest(
    job_path: Path,
    training_report: dict[str, Any],
    packaging_report: dict[str, Any],
    artifact: Path,
) -> dict[str, Any]:
    sample_render_raw = training_report.get("sampleRenderPath")
    sample_target_raw = training_report.get("sampleTargetPath")
    render_review_raw = training_report.get("renderReviewPath")
    sample_render_path = Path(sample_render_raw) if isinstance(sample_render_raw, str) and sample_render_raw else None
    sample_target_path = Path(sample_target_raw) if isinstance(sample_target_raw, str) and sample_target_raw else None
    render_review_path = Path(render_review_raw) if isinstance(render_review_raw, str) and render_review_raw else None
    training_metrics = training_report.get("metrics", {}) if isinstance(training_report.get("metrics"), dict) else {}
    profile = training_metrics.get("profile") or training_report.get("runConfig", {}).get("profile") or "splat"
    viewer_artifact = artifact
    viewer_filter: dict[str, Any] | None = None
    if training_metrics.get("backend") == "nerfstudio_splatfacto":
        viewer_candidate = artifact.with_name(f"{artifact.stem}.viewer.ply")
        try:
            viewer_filter = build_viewer_filtered_ply(artifact, viewer_candidate)
            if viewer_candidate.exists() and viewer_candidate.stat().st_size > 0:
                viewer_artifact = viewer_candidate
        except Exception as exc:
            viewer_filter = {
                "status": "warning",
                "summary": f"viewer PLY filtering failed; using original artifact: {exc}",
                "path": str(viewer_candidate),
            }
    ply_header = parse_ply_header(viewer_artifact)
    original_ply_header = parse_ply_header(artifact)
    camera_views = build_camera_views(training_report)
    export_file_stem = f"gaussian-splat-lab-{profile}-{artifact.stem}"
    artifact_variants = [
        {
            "id": "viewer_default",
            "label": "Interactive",
            "role": "browser_viewer",
            "path": str(viewer_artifact),
            "repoRelativePath": repo_relative_path(viewer_artifact),
            "sizeBytes": viewer_artifact.stat().st_size,
            "sha256": file_sha256(viewer_artifact),
            "ply": ply_header,
            "default": True,
        }
    ]
    if viewer_artifact != artifact:
        artifact_variants.append(
            {
                "id": "full_export",
                "label": "Full export",
                "role": "archive_export",
                "path": str(artifact),
                "repoRelativePath": repo_relative_path(artifact),
                "sizeBytes": artifact.stat().st_size,
                "sha256": file_sha256(artifact),
                "ply": original_ply_header,
                "default": False,
            }
        )
    return {
        "schemaVersion": 1,
        "generatedAt": utc_now(),
        "jobPath": str(job_path),
        "source": {
            "trainingReportPath": packaging_report.get("source", {}).get("trainingReportPath"),
            "packagingStage": packaging_report.get("stage", {}).get("id"),
        },
        "artifact": {
            "kind": "gaussian_splat_ply",
            "format": "ply",
            "path": str(viewer_artifact),
            "repoRelativePath": repo_relative_path(viewer_artifact),
            "sizeBytes": viewer_artifact.stat().st_size,
            "sha256": file_sha256(viewer_artifact),
            "ply": ply_header,
            "viewerOptimized": viewer_artifact != artifact,
        },
        "originalArtifact": {
            "kind": "gaussian_splat_ply",
            "format": "ply",
            "path": str(artifact),
            "repoRelativePath": repo_relative_path(artifact),
            "sizeBytes": artifact.stat().st_size,
            "sha256": file_sha256(artifact),
            "ply": original_ply_header,
        },
        "artifactVariants": artifact_variants,
        "viewerFilter": viewer_filter,
        "preview": {
            "sampleRenderPath": str(sample_render_path) if sample_render_path else None,
            "sampleRenderRepoRelativePath": repo_relative_path(sample_render_path) if sample_render_path else None,
            "sampleRenderSizeBytes": sample_render_path.stat().st_size if sample_render_path and sample_render_path.exists() else None,
            "sampleTargetPath": str(sample_target_path) if sample_target_path else None,
            "sampleTargetRepoRelativePath": repo_relative_path(sample_target_path) if sample_target_path else None,
            "renderReviewPath": str(render_review_path) if render_review_path else None,
            "renderReviewRepoRelativePath": repo_relative_path(render_review_path) if render_review_path else None,
            "renderReviewSizeBytes": render_review_path.stat().st_size if render_review_path and render_review_path.exists() else None,
        },
        "cameraViews": camera_views["views"],
        "cameraViewSource": {
            "status": camera_views["status"],
            "summary": camera_views["summary"],
            **camera_views.get("source", {}),
        },
        "export": {
            "kind": "viewer_environment_bundle",
            "recommendedManifestFileName": f"{export_file_stem}.viewer-manifest.json",
            "recommendedSplatFileName": f"{export_file_stem}.ply",
            "primaryAssetRepoRelativePath": repo_relative_path(artifact),
            "viewerAssetRepoRelativePath": repo_relative_path(viewer_artifact),
            "includes": ["gaussian_splat_ply", "viewer_manifest", "reference_camera_views", "preview_images", "original_gaussian_splat_ply"],
            "coordinateSpace": "viewer artifact and reference cameras share the packaged splat coordinate space",
            "note": "This is a Gaussian Splat environment export, not a triangle mesh/GLB export.",
        },
        "training": training_metrics,
        "runConfig": training_report.get("runConfig", {}),
        "device": training_report.get("device", {}),
        "versions": training_report.get("versions", {}),
        "viewer": {
            "implementation": "spark_webgl_gaussian_splat_renderer",
            "supports": ["gaussian_splat_render", "reference_camera_views", "walk", "mouse_look", "orbit", "pan", "zoom", "reset_view", "debug_point_cloud", "viewer_environment_export"],
            "loads": "binary_little_endian PLY Gaussian splats into Spark for 3DGS rendering and exposes a point-cloud debug fallback",
        },
    }


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

    viewer_manifest_path = job_path.parent / "viewer" / "viewer-manifest.json"
    viewer_manifest = build_viewer_manifest(job_path, training_report, base, artifact)
    write_json(viewer_manifest_path, viewer_manifest)
    ply_header = viewer_manifest["artifact"].get("ply", {})
    camera_view_source = viewer_manifest.get("cameraViewSource", {})

    base["artifact"] = {
        "path": str(artifact),
        "repoRelativePath": repo_relative_path(artifact),
        "sizeBytes": artifact.stat().st_size,
        "sha256": file_sha256(artifact),
        "ply": ply_header,
    }
    base["viewerManifestPath"] = str(viewer_manifest_path)
    base["viewerManifestRepoRelativePath"] = repo_relative_path(viewer_manifest_path)
    base["checks"].extend(
        [
            {
                "id": "artifact",
                "status": "pass",
                "summary": "Splat artifact exists and hash/size are recorded",
            },
            {
                "id": "ply_header",
                "status": ply_header.get("status", "fail"),
                "summary": ply_header.get("summary", "PLY header could not be validated"),
                "format": ply_header.get("format"),
                "vertexCount": ply_header.get("vertexCount"),
            },
            {
                "id": "viewer_manifest",
                "status": "pass" if viewer_manifest_path.exists() else "fail",
                "summary": "viewer manifest written" if viewer_manifest_path.exists() else "viewer manifest was not written",
                "path": str(viewer_manifest_path),
            },
            {
                "id": "camera_views",
                "status": camera_view_source.get("status", "warning"),
                "summary": camera_view_source.get("summary", "COLMAP camera views were not exported"),
                "count": len(viewer_manifest.get("cameraViews", [])),
            },
        ]
    )
    check_statuses = [check.get("status") for check in base["checks"] if isinstance(check, dict)]
    base["stage"]["status"] = "fail" if any(status == "fail" for status in check_statuses) else "pass"
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

    manifest_raw = packaging_report.get("viewerManifestPath")
    if not isinstance(manifest_raw, str) or not manifest_raw:
        base["stage"]["status"] = "setup_gap"
        base["checks"].append(
            {
                "id": "viewer_manifest",
                "status": "setup_gap",
                "summary": "Packaging report does not declare viewerManifestPath; rerun packaging before viewer validation.",
            }
        )
        return base

    viewer_manifest_path = Path(manifest_raw)
    if not viewer_manifest_path.exists():
        base["stage"]["status"] = "fail"
        base["checks"].append(
            {
                "id": "viewer_manifest",
                "status": "fail",
                "summary": "Declared viewer manifest does not exist",
                "path": str(viewer_manifest_path),
            }
        )
        return base

    viewer_manifest = read_json(viewer_manifest_path)
    artifact_info = viewer_manifest.get("artifact", {}) if isinstance(viewer_manifest.get("artifact"), dict) else {}
    artifact_raw = artifact_info.get("path")
    artifact_path = Path(artifact_raw) if isinstance(artifact_raw, str) and artifact_raw else None
    artifact_exists = bool(artifact_path and artifact_path.exists() and artifact_path.is_file())
    expected_sha = artifact_info.get("sha256")
    actual_sha = file_sha256(artifact_path) if artifact_exists and artifact_path else None
    ply_header = parse_ply_header(artifact_path) if artifact_exists and artifact_path else {"status": "fail", "summary": "artifact missing"}
    preview_info = viewer_manifest.get("preview", {}) if isinstance(viewer_manifest.get("preview"), dict) else {}
    camera_views = viewer_manifest.get("cameraViews", []) if isinstance(viewer_manifest.get("cameraViews"), list) else []
    sample_render_raw = preview_info.get("sampleRenderPath")
    sample_render_path = Path(sample_render_raw) if isinstance(sample_render_raw, str) and sample_render_raw else None
    app_js = repo_root_from_script() / "app" / "app.js"
    app_html = repo_root_from_script() / "app" / "index.html"
    app_css = repo_root_from_script() / "app" / "styles.css"
    app_text = app_js.read_text(encoding="utf-8") if app_js.exists() else ""
    checks = [
        {
            "id": "viewer_manifest",
            "status": "pass",
            "summary": "viewer manifest exists and is readable",
            "path": str(viewer_manifest_path),
        },
        {
            "id": "viewer_artifact",
            "status": "pass" if artifact_exists and artifact_path and artifact_path.stat().st_size > 0 else "fail",
            "summary": "viewer artifact exists" if artifact_exists else "viewer artifact is missing",
            "path": str(artifact_path) if artifact_path else None,
            "sizeBytes": artifact_path.stat().st_size if artifact_exists and artifact_path else None,
        },
        {
            "id": "viewer_artifact_hash",
            "status": "pass" if expected_sha and actual_sha == expected_sha else "fail",
            "summary": "viewer artifact hash matches manifest" if expected_sha and actual_sha == expected_sha else "viewer artifact hash does not match manifest",
            "expectedSha256": expected_sha,
            "actualSha256": actual_sha,
        },
        {
            "id": "viewer_ply_header",
            "status": ply_header.get("status", "fail"),
            "summary": ply_header.get("summary", "PLY header could not be validated"),
            "format": ply_header.get("format"),
            "vertexCount": ply_header.get("vertexCount"),
        },
        {
            "id": "viewer_camera_views",
            "status": "pass" if camera_views else "warning",
            "summary": f"{len(camera_views)} reference camera views available" if camera_views else "viewer manifest has no reference camera views",
        },
        {
            "id": "sample_render",
            "status": "pass" if sample_render_path and sample_render_path.exists() and sample_render_path.stat().st_size > 0 else "warning",
            "summary": "sample render exists" if sample_render_path and sample_render_path.exists() else "sample render is not available for preview fallback",
            "path": str(sample_render_path) if sample_render_path else None,
        },
        {
            "id": "local_viewer_app",
            "status": "pass" if app_html.exists() and app_css.exists() and "parseBinaryPly" in app_text and "initWebGLScene" in app_text and "gl_PointSize" in app_text and "viewerArtifact" in app_text else "fail",
            "summary": "local UI contains WebGL binary PLY viewer hooks" if app_html.exists() and app_css.exists() and "parseBinaryPly" in app_text and "initWebGLScene" in app_text and "gl_PointSize" in app_text and "viewerArtifact" in app_text else "local UI is missing WebGL viewer hooks",
        },
    ]
    base["checks"].extend(checks)
    base["viewerManifestPath"] = str(viewer_manifest_path)
    base["viewerManifest"] = viewer_manifest
    base["artifact"] = artifact_info
    base["preview"] = preview_info
    base["viewerUrl"] = "/"
    check_statuses = [check.get("status") for check in checks]
    if any(status == "fail" for status in check_statuses):
        base["stage"]["status"] = "fail"
    elif any(status == "warning" for status in check_statuses):
        base["stage"]["status"] = "warning"
    else:
        base["stage"]["status"] = "pass"
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
    input_kind = capture_input_kind(job)

    base = {
        "schemaVersion": 1,
        "stage": {
            "id": "intake",
            "status": "pending",
            "generatedAt": utc_now(),
            "jobPath": str(job_path),
        },
        "input": capture_input_descriptor(job.get("capture", {})),
        "inputKind": input_kind,
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

    if input_kind == COLMAP_DATASET_INPUT_KIND:
        dataset_report = validate_colmap_dataset(job, repo_root)
        base["datasetPath"] = dataset_report.get("datasetPath")
        base["imageDirectory"] = dataset_report.get("imageDirectory")
        base["sparseModelPath"] = dataset_report.get("sparseModelPath")
        base["metadata"] = {
            "hasVideo": False,
            "inputKind": input_kind,
            "dataset": {
                "kind": "colmap_dataset",
                "path": dataset_report.get("datasetPath"),
                "imageDirectory": dataset_report.get("imageDirectory"),
                "sparseModelPath": dataset_report.get("sparseModelPath"),
                "imageCount": dataset_report.get("imageCount"),
            },
        }
        base["checks"].extend(dataset_report.get("checks", []))
        source_license_status, source_license_summary, commercial_posture = classify_capture_license(source)
        base["commercialPosture"] = commercial_posture
        base["checks"].append(
            {
                "id": "source_license",
                "status": source_license_status,
                "summary": source_license_summary,
                "license": source.get("license"),
                "sourceUrl": source.get("sourceUrl"),
                "licenseSourceUrl": source.get("licenseSourceUrl"),
                "termsUrl": source.get("termsUrl"),
                "licenseVerifiedAt": source.get("licenseVerifiedAt"),
            }
        )
        statuses = [check.get("status") for check in base["checks"] if isinstance(check, dict)]
        if any(status == "fail" for status in statuses):
            base["stage"]["status"] = "fail"
        elif any(status == "setup_gap" for status in statuses):
            base["stage"]["status"] = "setup_gap"
        elif any(status == "warning" for status in statuses):
            base["stage"]["status"] = "warning"
        else:
            base["stage"]["status"] = "pass"
        return base

    if input_kind == NERFSTUDIO_DATASET_INPUT_KIND:
        dataset_path = nerfstudio_dataset_path(job, repo_root)
        if dataset_path is None:
            base["stage"]["status"] = "setup_gap"
            base["checks"].append(
                {
                    "id": "dataset_path",
                    "status": "setup_gap",
                    "summary": "Nerfstudio dataset input requires input.path or dataset.expectedLocalDatasetPath",
                }
            )
            return base
        dataset_report = validate_nerfstudio_dataset(dataset_path)
        base["datasetPath"] = dataset_report.get("datasetPath")
        base["transformsPath"] = dataset_report.get("transformsPath")
        base["imageRoot"] = dataset_report.get("imageRoot")
        base["metadata"] = {
            "hasVideo": False,
            "inputKind": input_kind,
            "dataset": {
                "kind": "nerfstudio_dataset",
                "path": dataset_report.get("datasetPath"),
                "frameCount": dataset_report.get("frameCount"),
                "readableFrameCount": dataset_report.get("readableFrameCount"),
                "depthFrameCount": dataset_report.get("depthFrameCount"),
            },
        }
        base["checks"].extend(dataset_report.get("checks", []))
        source_license_status, source_license_summary, commercial_posture = classify_capture_license(source)
        base["commercialPosture"] = commercial_posture
        base["checks"].append(
            {
                "id": "source_license",
                "status": source_license_status,
                "summary": source_license_summary,
                "license": source.get("license"),
                "sourceUrl": source.get("sourceUrl"),
                "licenseSourceUrl": source.get("licenseSourceUrl"),
                "termsUrl": source.get("termsUrl"),
                "licenseVerifiedAt": source.get("licenseVerifiedAt"),
            }
        )
        statuses = [check.get("status") for check in base["checks"] if isinstance(check, dict)]
        if any(status == "fail" for status in statuses):
            base["stage"]["status"] = "fail"
        elif any(status == "setup_gap" for status in statuses):
            base["stage"]["status"] = "setup_gap"
        elif any(status == "warning" for status in statuses):
            base["stage"]["status"] = "warning"
        else:
            base["stage"]["status"] = "pass"
        return base

    if input_kind != PLAIN_VIDEO_INPUT_KIND:
        base["stage"]["status"] = "setup_gap"
        base["checks"].append(
            {
                "id": "input_kind",
                "status": "setup_gap",
                "summary": f"input kind {input_kind!r} is documented but not implemented in intake yet",
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
        report = build_splat_training_report(
            job_path,
            accept_warning=args.accept_warning,
            allow_heavy=args.allow_heavy,
            training_profile_override=args.training_profile,
        )
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


def command_import_video(args: argparse.Namespace) -> int:
    repo_root = repo_root_from_script()
    manifest_path = Path(args.capture_manifest)
    if not manifest_path.is_absolute():
        manifest_path = repo_root / manifest_path

    selection = select_capture(manifest_path, args.capture_id)
    input_path = resolve_input_path(args.input, repo_root)
    target_path = capture_source_path(selection.capture, repo_root)
    report = build_video_import_report(
        manifest_path=manifest_path,
        selection=selection,
        input_path=input_path,
        target_path=target_path,
        accept_warning=args.accept_warning,
        overwrite=args.overwrite,
        dry_run=args.dry_run,
        repo_root=repo_root,
    )

    report_path = None
    if target_path is not None:
        report_path = capture_import_report_path(target_path)
        if not args.dry_run and report["status"] == "pass":
            write_json(report_path, report)

    print(f"import_video_status={report['status']}")
    print(f"import_video_target={target_path}")
    if report_path is not None:
        print(f"import_video_report={report_path}")
    if args.dry_run or report["status"] != "pass":
        print(json.dumps(report, indent=2))
    return 0 if report["status"] in {"pass", "warning", "setup_gap"} else 1


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

    import_video = subparsers.add_parser(
        "import-video",
        help="Copy a manually obtained capture video into the manifest target path and record provenance.",
    )
    import_video.add_argument(
        "--capture-manifest",
        default="data/manifests/captures.example.json",
        help="Path to a capture manifest JSON file.",
    )
    import_video.add_argument("--capture-id", required=True, help="Capture id to import video for.")
    import_video.add_argument("--input", required=True, help="Path to the manually obtained local video file.")
    import_video.add_argument(
        "--accept-warning",
        action="store_true",
        help="Explicitly allow import when the capture license posture is warning/technical-validation-only.",
    )
    import_video.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace an existing target video intentionally.",
    )
    import_video.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate the import plan without copying the input file.",
    )
    import_video.set_defaults(func=command_import_video)

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
    run_stage.add_argument(
        "--training-profile",
        choices=sorted({*TRAINING_PROFILE_DEFAULTS, *SPLATFACTO_PROFILE_DEFAULTS}),
        help="Override the configured splat_training profile for this run.",
    )
    run_stage.set_defaults(func=command_run_stage)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
