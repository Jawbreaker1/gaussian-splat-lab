#!/usr/bin/env python3
"""Convert a TUM RGB-D sequence into a small Nerfstudio transforms dataset."""

from __future__ import annotations

import argparse
import json
import math
import os
from bisect import bisect_left
from pathlib import Path
from typing import Any


FREIBURG1_INTRINSICS = {
    "fl_x": 517.3,
    "fl_y": 516.5,
    "cx": 318.6,
    "cy": 255.3,
    "w": 640,
    "h": 480,
    "camera_model": "OPENCV",
    "k1": 0.2624,
    "k2": -0.9531,
    "p1": -0.0054,
    "p2": 0.0026,
    "k3": 1.1633,
}


def parse_timestamp_file(path: Path) -> list[tuple[float, str]]:
    rows: list[tuple[float, str]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) >= 2:
            rows.append((float(parts[0]), parts[1]))
    return rows


def parse_groundtruth(path: Path) -> list[tuple[float, list[float]]]:
    poses: list[tuple[float, list[float]]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) == 8:
            poses.append((float(parts[0]), [float(value) for value in parts[1:]]))
    return poses


def nearest_by_timestamp[T](items: list[tuple[float, T]], timestamp: float, max_delta: float) -> tuple[float, T] | None:
    if not items:
        return None
    times = [item[0] for item in items]
    index = bisect_left(times, timestamp)
    candidates: list[tuple[float, T]] = []
    if index < len(items):
        candidates.append(items[index])
    if index > 0:
        candidates.append(items[index - 1])
    nearest = min(candidates, key=lambda item: abs(item[0] - timestamp))
    if abs(nearest[0] - timestamp) > max_delta:
        return None
    return nearest


def quaternion_to_matrix(qx: float, qy: float, qz: float, qw: float) -> list[list[float]]:
    norm = math.sqrt(qx * qx + qy * qy + qz * qz + qw * qw)
    if norm == 0:
        raise ValueError("zero-length quaternion")
    qx, qy, qz, qw = qx / norm, qy / norm, qz / norm, qw / norm
    xx, yy, zz = qx * qx, qy * qy, qz * qz
    xy, xz, yz = qx * qy, qx * qz, qy * qz
    wx, wy, wz = qw * qx, qw * qy, qw * qz
    return [
        [1 - 2 * (yy + zz), 2 * (xy - wz), 2 * (xz + wy)],
        [2 * (xy + wz), 1 - 2 * (xx + zz), 2 * (yz - wx)],
        [2 * (xz - wy), 2 * (yz + wx), 1 - 2 * (xx + yy)],
    ]


def tum_pose_to_transform(values: list[float], opencv_to_opengl: bool) -> list[list[float]]:
    tx, ty, tz, qx, qy, qz, qw = values
    rotation = quaternion_to_matrix(qx, qy, qz, qw)
    transform = [
        [rotation[0][0], rotation[0][1], rotation[0][2], tx],
        [rotation[1][0], rotation[1][1], rotation[1][2], ty],
        [rotation[2][0], rotation[2][1], rotation[2][2], tz],
        [0.0, 0.0, 0.0, 1.0],
    ]
    if opencv_to_opengl:
        transform[0][1] *= -1
        transform[0][2] *= -1
        transform[1][1] *= -1
        transform[1][2] *= -1
        transform[2][1] *= -1
        transform[2][2] *= -1
    return transform


def link_or_copy(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() or target.is_symlink():
        target.unlink()
    try:
        os.symlink(source.resolve(), target)
    except OSError:
        target.write_bytes(source.read_bytes())


def evenly_sample(items: list[Any], max_items: int) -> list[Any]:
    if max_items <= 0 or len(items) <= max_items:
        return items
    if max_items == 1:
        return [items[0]]
    indexes = [round(index * (len(items) - 1) / (max_items - 1)) for index in range(max_items)]
    return [items[index] for index in indexes]


def convert(args: argparse.Namespace) -> dict[str, Any]:
    source = Path(args.input).resolve()
    output = Path(args.output).resolve()
    rgb_rows = parse_timestamp_file(source / "rgb.txt")
    depth_rows = parse_timestamp_file(source / "depth.txt")
    pose_rows = parse_groundtruth(source / "groundtruth.txt")
    if not rgb_rows:
        raise ValueError(f"{source / 'rgb.txt'} has no RGB rows")
    if not depth_rows:
        raise ValueError(f"{source / 'depth.txt'} has no depth rows")
    if not pose_rows:
        raise ValueError(f"{source / 'groundtruth.txt'} has no pose rows")

    candidates: list[dict[str, Any]] = []
    for rgb_timestamp, rgb_rel in rgb_rows:
        depth_match = nearest_by_timestamp(depth_rows, rgb_timestamp, args.max_depth_delta)
        pose_match = nearest_by_timestamp(pose_rows, rgb_timestamp, args.max_pose_delta)
        if depth_match is None or pose_match is None:
            continue
        candidates.append(
            {
                "rgbTimestamp": rgb_timestamp,
                "rgbRelativePath": rgb_rel,
                "depthTimestamp": depth_match[0],
                "depthRelativePath": depth_match[1],
                "poseTimestamp": pose_match[0],
                "poseValues": pose_match[1],
            }
        )

    selected = evenly_sample(candidates, int(args.max_frames))
    image_dir = output / "images"
    depth_dir = output / "depth"
    frames: list[dict[str, Any]] = []
    for index, item in enumerate(selected):
        rgb_source = source / item["rgbRelativePath"]
        depth_source = source / item["depthRelativePath"]
        image_target = image_dir / f"frame_{index:06d}{rgb_source.suffix.lower()}"
        depth_target = depth_dir / f"frame_{index:06d}{depth_source.suffix.lower()}"
        link_or_copy(rgb_source, image_target)
        link_or_copy(depth_source, depth_target)
        frames.append(
            {
                "file_path": image_target.relative_to(output).as_posix(),
                "depth_file_path": depth_target.relative_to(output).as_posix(),
                "transform_matrix": tum_pose_to_transform(item["poseValues"], not args.keep_opencv_camera_axes),
                "timestamp": item["rgbTimestamp"],
                "source_rgb_path": item["rgbRelativePath"],
                "source_depth_path": item["depthRelativePath"],
                "depth_timestamp_delta_seconds": round(abs(item["depthTimestamp"] - item["rgbTimestamp"]), 9),
                "pose_timestamp_delta_seconds": round(abs(item["poseTimestamp"] - item["rgbTimestamp"]), 9),
            }
        )

    output.mkdir(parents=True, exist_ok=True)
    transforms = {
        **FREIBURG1_INTRINSICS,
        "depth_unit_scale_factor": 1.0 / 5000.0,
        "source_dataset": "TUM RGB-D freiburg1_xyz",
        "source_url": "https://cvg.cit.tum.de/rgbd/dataset/freiburg1/rgbd_dataset_freiburg1_xyz.tgz",
        "source_license": "CC BY 4.0 unless stated otherwise by TUM RGB-D benchmark",
        "source_coordinate_convention": "TUM RGB-D camera-to-world, OpenCV camera axes",
        "applied_coordinate_conversion": "opencv_camera_to_opengl_camera_axes"
        if not args.keep_opencv_camera_axes
        else "none",
        "frames": frames,
    }
    (output / "transforms.json").write_text(json.dumps(transforms, indent=2) + "\n", encoding="utf-8")
    report = {
        "source": str(source),
        "output": str(output),
        "rgbRows": len(rgb_rows),
        "depthRows": len(depth_rows),
        "poseRows": len(pose_rows),
        "matchedFrames": len(candidates),
        "selectedFrames": len(frames),
        "maxFrames": int(args.max_frames),
        "transformsPath": str(output / "transforms.json"),
    }
    (output / "conversion-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Path to an unpacked TUM RGB-D sequence.")
    parser.add_argument("--output", required=True, help="Output Nerfstudio dataset directory.")
    parser.add_argument("--max-frames", type=int, default=300, help="Evenly sampled max frame count.")
    parser.add_argument("--max-depth-delta", type=float, default=0.04, help="Maximum RGB/depth timestamp delta in seconds.")
    parser.add_argument("--max-pose-delta", type=float, default=0.04, help="Maximum RGB/pose timestamp delta in seconds.")
    parser.add_argument(
        "--keep-opencv-camera-axes",
        action="store_true",
        help="Do not convert camera axes from OpenCV to the OpenGL-style Nerfstudio transform convention.",
    )
    return parser


def main() -> int:
    report = convert(build_parser().parse_args())
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
