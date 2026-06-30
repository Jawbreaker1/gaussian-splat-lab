#!/usr/bin/env python3
"""Convert an ARKitScenes raw sequence into a Nerfstudio transforms dataset."""

from __future__ import annotations

import argparse
import json
import math
import os
from bisect import bisect_left
from pathlib import Path
from typing import Any


ARKITSCENES_URL = "https://github.com/apple/ARKitScenes"
ARKITSCENES_ASSET_URL = "https://docs-assets.developer.apple.com/ml-research/datasets/arkitscenes/v1"


def timestamp_from_stem(path: Path) -> float:
    return float(path.stem.split("_")[-1])


def indexed_files(path: Path, suffix: str) -> list[tuple[float, Path]]:
    rows = [(timestamp_from_stem(item), item) for item in path.glob(f"*{suffix}")]
    return sorted(rows, key=lambda item: item[0])


def parse_intrinsics(path: Path) -> dict[str, float | int]:
    parts = path.read_text(encoding="utf-8").strip().split()
    if len(parts) != 6:
        raise ValueError(f"{path} should contain width height fx fy cx cy")
    width, height = int(parts[0]), int(parts[1])
    fx, fy, cx, cy = (float(value) for value in parts[2:])
    return {"w": width, "h": height, "fl_x": fx, "fl_y": fy, "cx": cx, "cy": cy}


def parse_trajectory(path: Path) -> list[tuple[float, list[float]]]:
    rows: list[tuple[float, list[float]]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        parts = [float(value) for value in line.split()]
        if len(parts) != 7:
            raise ValueError(f"{path} has a non-ARKitScenes trajectory row: {line}")
        rows.append((parts[0], parts[1:]))
    return sorted(rows, key=lambda item: item[0])


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


def rodrigues_to_matrix(rx: float, ry: float, rz: float) -> list[list[float]]:
    theta = math.sqrt(rx * rx + ry * ry + rz * rz)
    if theta < 1e-12:
        return [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
    x, y, z = rx / theta, ry / theta, rz / theta
    c = math.cos(theta)
    s = math.sin(theta)
    one_c = 1.0 - c
    return [
        [c + x * x * one_c, x * y * one_c - z * s, x * z * one_c + y * s],
        [y * x * one_c + z * s, c + y * y * one_c, y * z * one_c - x * s],
        [z * x * one_c - y * s, z * y * one_c + x * s, c + z * z * one_c],
    ]


def arkit_pose_to_transform(values: list[float], invert_pose: bool, opencv_to_opengl: bool) -> list[list[float]]:
    rx, ry, rz, tx, ty, tz = values
    rotation = rodrigues_to_matrix(rx, ry, rz)
    transform = [
        [rotation[0][0], rotation[0][1], rotation[0][2], tx],
        [rotation[1][0], rotation[1][1], rotation[1][2], ty],
        [rotation[2][0], rotation[2][1], rotation[2][2], tz],
        [0.0, 0.0, 0.0, 1.0],
    ]
    if invert_pose:
        r_t = [[rotation[col][row] for col in range(3)] for row in range(3)]
        translation = [
            -(r_t[0][0] * tx + r_t[0][1] * ty + r_t[0][2] * tz),
            -(r_t[1][0] * tx + r_t[1][1] * ty + r_t[1][2] * tz),
            -(r_t[2][0] * tx + r_t[2][1] * ty + r_t[2][2] * tz),
        ]
        transform = [
            [r_t[0][0], r_t[0][1], r_t[0][2], translation[0]],
            [r_t[1][0], r_t[1][1], r_t[1][2], translation[1]],
            [r_t[2][0], r_t[2][1], r_t[2][2], translation[2]],
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
    intrinsics_stream = args.intrinsics_stream or f"{args.image_stream}_intrinsics"
    image_rows = indexed_files(source / args.image_stream, ".png")
    depth_rows = indexed_files(source / args.depth_stream, ".png")
    intrinsic_rows = indexed_files(source / intrinsics_stream, ".pincam")
    confidence_rows = indexed_files(source / args.confidence_stream, ".png") if (source / args.confidence_stream).exists() else []
    trajectory_rows = parse_trajectory(source / "lowres_wide.traj")
    if not image_rows:
        raise ValueError(f"{source / args.image_stream} has no RGB frames")
    if not depth_rows:
        raise ValueError(f"{source / args.depth_stream} has no depth frames")
    if not intrinsic_rows:
        raise ValueError(f"{source / intrinsics_stream} has no .pincam files")
    if not trajectory_rows:
        raise ValueError(f"{source / 'lowres_wide.traj'} has no trajectory rows")

    candidates: list[dict[str, Any]] = []
    for image_timestamp, image_path in image_rows:
        depth_match = nearest_by_timestamp(depth_rows, image_timestamp, args.max_depth_delta)
        intrinsic_match = nearest_by_timestamp(intrinsic_rows, image_timestamp, args.max_intrinsics_delta)
        trajectory_match = nearest_by_timestamp(trajectory_rows, image_timestamp, args.max_pose_delta)
        confidence_match = nearest_by_timestamp(confidence_rows, image_timestamp, args.max_depth_delta)
        if depth_match is None or intrinsic_match is None or trajectory_match is None:
            continue
        candidates.append(
            {
                "imageTimestamp": image_timestamp,
                "imagePath": image_path,
                "depthTimestamp": depth_match[0],
                "depthPath": depth_match[1],
                "intrinsicsTimestamp": intrinsic_match[0],
                "intrinsicsPath": intrinsic_match[1],
                "poseTimestamp": trajectory_match[0],
                "poseValues": trajectory_match[1],
                "confidenceTimestamp": confidence_match[0] if confidence_match else None,
                "confidencePath": confidence_match[1] if confidence_match else None,
            }
        )

    selected = evenly_sample(candidates, int(args.max_frames))
    image_dir = output / "images"
    depth_dir = output / "depth"
    confidence_dir = output / "confidence"
    frames: list[dict[str, Any]] = []
    first_intrinsics: dict[str, float | int] | None = None
    for index, item in enumerate(selected):
        image_source = item["imagePath"]
        depth_source = item["depthPath"]
        confidence_source = item["confidencePath"]
        intrinsics = parse_intrinsics(item["intrinsicsPath"])
        if first_intrinsics is None:
            first_intrinsics = intrinsics
        image_target = image_dir / f"frame_{index:06d}{image_source.suffix.lower()}"
        depth_target = depth_dir / f"frame_{index:06d}{depth_source.suffix.lower()}"
        link_or_copy(image_source, image_target)
        link_or_copy(depth_source, depth_target)
        frame: dict[str, Any] = {
            **intrinsics,
            "file_path": image_target.relative_to(output).as_posix(),
            "depth_file_path": depth_target.relative_to(output).as_posix(),
            "transform_matrix": arkit_pose_to_transform(
                item["poseValues"],
                invert_pose=args.invert_pose,
                opencv_to_opengl=args.convert_opencv_to_opengl,
            ),
            "timestamp": item["imageTimestamp"],
            "source_rgb_path": str(image_source.relative_to(source)),
            "source_depth_path": str(depth_source.relative_to(source)),
            "source_intrinsics_path": str(item["intrinsicsPath"].relative_to(source)),
            "depth_timestamp_delta_seconds": round(abs(item["depthTimestamp"] - item["imageTimestamp"]), 9),
            "pose_timestamp_delta_seconds": round(abs(item["poseTimestamp"] - item["imageTimestamp"]), 9),
            "intrinsics_timestamp_delta_seconds": round(abs(item["intrinsicsTimestamp"] - item["imageTimestamp"]), 9),
        }
        if confidence_source is not None:
            confidence_target = confidence_dir / f"frame_{index:06d}{confidence_source.suffix.lower()}"
            link_or_copy(confidence_source, confidence_target)
            frame["confidence_file_path"] = confidence_target.relative_to(output).as_posix()
            frame["confidence_timestamp_delta_seconds"] = round(
                abs(float(item["confidenceTimestamp"]) - item["imageTimestamp"]), 9
            )
        frames.append(frame)

    if first_intrinsics is None:
        raise ValueError("no frames matched RGB, depth, intrinsics and pose timestamps")

    output.mkdir(parents=True, exist_ok=True)
    transforms = {
        **first_intrinsics,
        "camera_model": "PINHOLE",
        "depth_unit_scale_factor": 0.001,
        "source_dataset": "Apple ARKitScenes raw",
        "source_url": f"{ARKITSCENES_ASSET_URL}/raw/Training/{args.video_id or source.name}",
        "source_repository": ARKITSCENES_URL,
        "source_license": "Apple ARKitScenes LICENSE; commercial terms depend on Apple's MAU threshold language",
        "source_coordinate_convention": "ARKit camera-to-world axis-angle trajectory",
        "source_image_stream": args.image_stream,
        "source_depth_stream": args.depth_stream,
        "source_intrinsics_stream": intrinsics_stream,
        "source_confidence_stream": args.confidence_stream,
        "applied_coordinate_conversion": "opencv_camera_to_opengl_camera_axes"
        if args.convert_opencv_to_opengl
        else "none",
        "pose_inversion": bool(args.invert_pose),
        "frames": frames,
    }
    (output / "transforms.json").write_text(json.dumps(transforms, indent=2) + "\n", encoding="utf-8")
    report = {
        "source": str(source),
        "output": str(output),
        "videoId": args.video_id or source.name,
        "imageStream": args.image_stream,
        "depthStream": args.depth_stream,
        "intrinsicsStream": intrinsics_stream,
        "confidenceStream": args.confidence_stream,
        "imageRows": len(image_rows),
        "depthRows": len(depth_rows),
        "intrinsicsRows": len(intrinsic_rows),
        "confidenceRows": len(confidence_rows),
        "trajectoryRows": len(trajectory_rows),
        "matchedFrames": len(candidates),
        "selectedFrames": len(frames),
        "maxFrames": int(args.max_frames),
        "maxDepthDeltaSeconds": args.max_depth_delta,
        "maxPoseDeltaSeconds": args.max_pose_delta,
        "maxIntrinsicsDeltaSeconds": args.max_intrinsics_delta,
        "transformsPath": str(output / "transforms.json"),
    }
    (output / "conversion-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Path to an unpacked ARKitScenes raw video directory.")
    parser.add_argument("--output", required=True, help="Output Nerfstudio dataset directory.")
    parser.add_argument("--video-id", help="Optional source video id for provenance.")
    parser.add_argument("--max-frames", type=int, default=600, help="Evenly sampled max frame count.")
    parser.add_argument("--image-stream", default="lowres_wide", help="ARKitScenes RGB stream directory.")
    parser.add_argument("--depth-stream", default="lowres_depth", help="ARKitScenes depth stream directory.")
    parser.add_argument(
        "--intrinsics-stream",
        help="ARKitScenes intrinsics directory. Defaults to '<image-stream>_intrinsics'.",
    )
    parser.add_argument("--confidence-stream", default="confidence", help="ARKitScenes confidence stream directory.")
    parser.add_argument("--max-depth-delta", type=float, default=0.02, help="Maximum RGB/depth timestamp delta.")
    parser.add_argument("--max-pose-delta", type=float, default=0.06, help="Maximum RGB/trajectory timestamp delta.")
    parser.add_argument(
        "--max-intrinsics-delta",
        type=float,
        default=0.02,
        help="Maximum RGB/intrinsics timestamp delta.",
    )
    parser.add_argument(
        "--invert-pose",
        action="store_true",
        help="Treat trajectory rows as world-to-camera and invert to camera-to-world.",
    )
    parser.add_argument(
        "--convert-opencv-to-opengl",
        action="store_true",
        help="Apply OpenCV camera-axis to OpenGL camera-axis conversion. ARKitScenes normally should not need this.",
    )
    return parser


def main() -> int:
    report = convert(build_parser().parse_args())
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
