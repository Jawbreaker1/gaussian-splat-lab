#!/usr/bin/env python3
"""Validate a COLMAP binary without replacing the system COLMAP install."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import struct
import subprocess
import tempfile
import time
import zlib
from pathlib import Path
from typing import Any


def png_chunk(kind: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)


def write_texture_png(path: Path, width: int, height: int, shift: int) -> None:
    rows = []
    for y in range(height):
        row = bytearray([0])
        for x in range(width):
            checker = ((x + shift) // 24 + y // 24) % 2
            edge = 220 if checker else 35
            r = (edge + (x * 7 + y * 3 + shift) % 35) & 0xFF
            g = (80 + (x * 5 + y * 11 + shift * 2) % 150) & 0xFF
            b = (210 - edge // 2 + (x * 13 + shift) % 40) & 0xFF
            row.extend([r, g, b])
        rows.append(bytes(row))

    raw = b"".join(rows)
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + png_chunk(b"IDAT", zlib.compress(raw, 9))
        + png_chunk(b"IEND", b"")
    )


def run_command(command: list[str], timeout: int, env: dict[str, str] | None = None) -> dict[str, Any]:
    started = time.monotonic()
    executable = shutil.which(command[0], path=(env or os.environ).get("PATH"))
    if executable is None:
        return {
            "command": command,
            "executable": None,
            "status": "setup_gap",
            "exitCode": None,
            "durationSeconds": 0.0,
            "stdout": "",
            "stderr": f"{command[0]} not found",
        }
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            check=False,
            env=env,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "command": command,
            "executable": executable,
            "status": "fail",
            "exitCode": None,
            "durationSeconds": round(time.monotonic() - started, 3),
            "stdout": exc.stdout or "",
            "stderr": f"timed out after {timeout}s",
        }
    return {
        "command": command,
        "executable": executable,
        "status": "pass" if result.returncode == 0 else "fail",
        "exitCode": result.returncode,
        "durationSeconds": round(time.monotonic() - started, 3),
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }


def text_excerpt(value: str, limit: int = 1200) -> str:
    text = value.strip()
    if len(text) <= limit:
        return text
    return text[:limit] + "\n..."


def compact_command_result(result: dict[str, Any]) -> dict[str, Any]:
    return {
        **result,
        "stdout": text_excerpt(str(result.get("stdout") or "")),
        "stderr": text_excerpt(str(result.get("stderr") or "")),
    }


def command_summary(result: dict[str, Any]) -> str:
    text = str(result.get("stdout") or result.get("stderr") or "")
    return "\n".join(line for line in text.splitlines()[:4] if line.strip())


def colmap_command_help(binary: str, command_name: str, env: dict[str, str]) -> str:
    result = run_command([binary, command_name, "--help"], timeout=20, env=env)
    return "\n".join(str(result.get(key) or "") for key in ("stdout", "stderr"))


def colmap_option(help_text: str, legacy_name: str, current_name: str) -> str:
    if f"--{current_name}" in help_text:
        return f"--{current_name}"
    return f"--{legacy_name}"


def validate_colmap_binary(binary: str, allow_gpu: bool, qt_offscreen: bool, keep_workdir: bool) -> dict[str, Any]:
    workdir = Path(tempfile.mkdtemp(prefix="gsl-colmap-validate-"))
    image_dir = workdir / "images"
    image_dir.mkdir(parents=True, exist_ok=True)
    write_texture_png(image_dir / "frame_000001.png", 640, 480, 0)
    write_texture_png(image_dir / "frame_000002.png", 640, 480, 28)

    env = os.environ.copy()
    if qt_offscreen:
        env["QT_QPA_PLATFORM"] = "offscreen"

    checks: list[dict[str, Any]] = []
    commands: dict[str, Any] = {}

    help_result = run_command([binary, "--help"], timeout=15, env=env)
    commands["help"] = compact_command_result(help_result)
    checks.append(
        {
            "id": "colmap_help",
            "status": help_result["status"],
            "summary": command_summary(help_result) or "COLMAP help failed",
        }
    )

    feature_help = colmap_command_help(binary, "feature_extractor", env)
    matcher_help = colmap_command_help(binary, "exhaustive_matcher", env)
    feature_gpu_option = colmap_option(feature_help, "SiftExtraction.use_gpu", "FeatureExtraction.use_gpu")
    feature_threads_option = colmap_option(feature_help, "SiftExtraction.num_threads", "FeatureExtraction.num_threads")
    feature_max_image_size_option = colmap_option(
        feature_help,
        "SiftExtraction.max_image_size",
        "FeatureExtraction.max_image_size",
    )
    matcher_gpu_option = colmap_option(matcher_help, "SiftMatching.use_gpu", "FeatureMatching.use_gpu")
    matcher_threads_option = colmap_option(matcher_help, "SiftMatching.num_threads", "FeatureMatching.num_threads")

    cpu_db = workdir / "cpu.db"
    cpu_feature = run_command(
        [
            binary,
            "feature_extractor",
            "--database_path",
            str(cpu_db),
            "--image_path",
            str(image_dir),
            "--ImageReader.single_camera",
            "1",
            feature_gpu_option,
            "0",
            feature_threads_option,
            "1",
            feature_max_image_size_option,
            "800",
            "--SiftExtraction.max_num_features",
            "1024",
        ],
        timeout=90,
        env=env,
    )
    commands["cpuFeatureExtractor"] = compact_command_result(cpu_feature)
    checks.append(
        {
            "id": "cpu_feature_extractor",
            "status": cpu_feature["status"],
            "summary": "CPU SIFT feature extraction completed" if cpu_feature["status"] == "pass" else command_summary(cpu_feature),
        }
    )

    if cpu_feature["status"] == "pass":
        cpu_match = run_command(
            [
                binary,
                "exhaustive_matcher",
                "--database_path",
                str(cpu_db),
                matcher_gpu_option,
                "0",
                matcher_threads_option,
                "1",
            ],
            timeout=90,
            env=env,
        )
        commands["cpuMatcher"] = compact_command_result(cpu_match)
        checks.append(
            {
                "id": "cpu_matcher",
                "status": cpu_match["status"],
                "summary": "CPU SIFT matching completed" if cpu_match["status"] == "pass" else command_summary(cpu_match),
            }
        )

    if allow_gpu:
        gpu_db = workdir / "gpu.db"
        gpu_feature = run_command(
            [
                binary,
                "feature_extractor",
                "--database_path",
                str(gpu_db),
                "--image_path",
                str(image_dir),
                "--ImageReader.single_camera",
                "1",
                feature_gpu_option,
                "1",
                feature_threads_option,
                "1",
                feature_max_image_size_option,
                "800",
                "--SiftExtraction.max_num_features",
                "1024",
            ],
            timeout=90,
            env=env,
        )
        commands["gpuFeatureExtractor"] = compact_command_result(gpu_feature)
        checks.append(
            {
                "id": "gpu_feature_extractor",
                "status": gpu_feature["status"],
                "summary": "GPU SIFT feature extraction completed" if gpu_feature["status"] == "pass" else command_summary(gpu_feature),
            }
        )

        if gpu_feature["status"] == "pass":
            gpu_match = run_command(
                [
                    binary,
                    "exhaustive_matcher",
                    "--database_path",
                    str(gpu_db),
                    matcher_gpu_option,
                    "1",
                    matcher_threads_option,
                    "1",
                ],
                timeout=90,
                env=env,
            )
            commands["gpuMatcher"] = compact_command_result(gpu_match)
            checks.append(
                {
                    "id": "gpu_matcher",
                    "status": gpu_match["status"],
                    "summary": "GPU SIFT matching completed" if gpu_match["status"] == "pass" else command_summary(gpu_match),
                }
            )

    status = "pass" if all(check["status"] == "pass" for check in checks) else "fail"
    report = {
        "schemaVersion": 1,
        "status": status,
        "binary": binary,
        "resolvedBinary": help_result.get("executable"),
        "allowGpu": allow_gpu,
        "qtOffscreen": qt_offscreen,
        "workdir": str(workdir),
        "checks": checks,
        "commands": commands,
    }
    if not keep_workdir:
        shutil.rmtree(workdir, ignore_errors=True)
        report["workdir"] = None
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a side-by-side COLMAP binary.")
    parser.add_argument("--binary", default=os.environ.get("GSL_COLMAP_BIN") or "colmap")
    parser.add_argument("--allow-gpu", action="store_true", help="Also run COLMAP SIFT with use_gpu=1.")
    parser.add_argument("--qt-offscreen", action="store_true", help="Set QT_QPA_PLATFORM=offscreen for the test.")
    parser.add_argument("--keep-workdir", action="store_true", help="Keep the temporary image/database directory for inspection.")
    parser.add_argument("--json-out", help="Optional path to write the validation report.")
    args = parser.parse_args()

    report = validate_colmap_binary(
        binary=args.binary,
        allow_gpu=args.allow_gpu,
        qt_offscreen=args.qt_offscreen,
        keep_workdir=args.keep_workdir,
    )
    text = json.dumps(report, indent=2)
    if args.json_out:
        output = Path(args.json_out)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
