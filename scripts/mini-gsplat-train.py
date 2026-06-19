#!/usr/bin/env python3
"""Minimal COLMAP-to-gsplat training smoke for the lab pipeline."""

from __future__ import annotations

import argparse
import json
import math
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import torch
from PIL import Image, ImageChops, ImageDraw, ImageStat


SH_C0 = 0.28209479177387814


@dataclass(frozen=True)
class Camera:
    camera_id: int
    model: str
    width: int
    height: int
    params: list[float]


@dataclass(frozen=True)
class RegisteredImage:
    image_id: int
    qvec: list[float]
    tvec: list[float]
    camera_id: int
    name: str


@dataclass(frozen=True)
class Point3D:
    xyz: list[float]
    rgb: list[float]
    error: float


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2)
        handle.write("\n")


def run_command(command: list[str], timeout_seconds: int) -> dict[str, Any]:
    executable = shutil.which(command[0])
    if executable is None:
        return {
            "command": command,
            "status": "setup_gap",
            "exitCode": None,
            "stdout": "",
            "stderr": f"{command[0]} not found on PATH",
        }
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            check=False,
            text=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "command": command,
            "status": "fail",
            "exitCode": None,
            "stdout": exc.stdout or "",
            "stderr": f"command timed out after {timeout_seconds}s",
        }
    return {
        "command": command,
        "status": "pass" if result.returncode == 0 else "fail",
        "exitCode": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }


def compact_text(value: str, max_chars: int = 2000) -> str:
    normalized = "\n".join(line.rstrip() for line in value.splitlines())
    if len(normalized) <= max_chars:
        return normalized
    return f"{normalized[:max_chars]}... [truncated]"


def model_to_text(sparse_model_path: Path, output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    return run_command(
        [
            "colmap",
            "model_converter",
            "--input_path",
            str(sparse_model_path),
            "--output_path",
            str(output_dir),
            "--output_type",
            "TXT",
        ],
        timeout_seconds=300,
    )


def content_lines(path: Path) -> list[str]:
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]


def parse_cameras(path: Path) -> dict[int, Camera]:
    cameras: dict[int, Camera] = {}
    for line in content_lines(path):
        fields = line.split()
        if len(fields) < 5:
            continue
        camera_id = int(fields[0])
        cameras[camera_id] = Camera(
            camera_id=camera_id,
            model=fields[1],
            width=int(fields[2]),
            height=int(fields[3]),
            params=[float(value) for value in fields[4:]],
        )
    return cameras


def parse_images(path: Path) -> list[RegisteredImage]:
    lines = content_lines(path)
    images: list[RegisteredImage] = []
    index = 0
    while index < len(lines):
        fields = lines[index].split()
        if len(fields) >= 10:
            images.append(
                RegisteredImage(
                    image_id=int(fields[0]),
                    qvec=[float(value) for value in fields[1:5]],
                    tvec=[float(value) for value in fields[5:8]],
                    camera_id=int(fields[8]),
                    name=" ".join(fields[9:]),
                )
            )
        index += 2
    return images


def parse_points3d(path: Path, max_points: int) -> list[Point3D]:
    points: list[Point3D] = []
    for line in content_lines(path):
        fields = line.split()
        if len(fields) < 8:
            continue
        points.append(
            Point3D(
                xyz=[float(value) for value in fields[1:4]],
                rgb=[float(value) / 255.0 for value in fields[4:7]],
                error=float(fields[7]),
            )
        )
    points.sort(key=lambda point: point.error)
    return points[:max_points]


def camera_intrinsics(camera: Camera, scale: float) -> np.ndarray:
    if camera.model in {"SIMPLE_PINHOLE", "SIMPLE_RADIAL"}:
        fx = fy = camera.params[0]
        cx = camera.params[1]
        cy = camera.params[2]
    elif camera.model == "PINHOLE":
        fx, fy, cx, cy = camera.params[:4]
    elif camera.model in {"OPENCV", "OPENCV_FISHEYE", "FULL_OPENCV"}:
        fx, fy, cx, cy = camera.params[:4]
    else:
        raise ValueError(f"unsupported COLMAP camera model: {camera.model}")
    return np.array(
        [
            [fx * scale, 0.0, cx * scale],
            [0.0, fy * scale, cy * scale],
            [0.0, 0.0, 1.0],
        ],
        dtype=np.float32,
    )


def qvec_to_rotmat(qvec: list[float]) -> np.ndarray:
    qw, qx, qy, qz = qvec
    return np.array(
        [
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
        ],
        dtype=np.float32,
    )


def viewmat_from_image(image: RegisteredImage) -> np.ndarray:
    viewmat = np.eye(4, dtype=np.float32)
    viewmat[:3, :3] = qvec_to_rotmat(image.qvec)
    viewmat[:3, 3] = np.array(image.tvec, dtype=np.float32)
    return viewmat


def select_evenly(items: list[RegisteredImage], max_items: int) -> list[RegisteredImage]:
    if len(items) <= max_items:
        return items
    indices = np.linspace(0, len(items) - 1, max_items)
    selected: list[RegisteredImage] = []
    seen: set[int] = set()
    for raw_index in indices:
        index = int(round(float(raw_index)))
        if index not in seen:
            selected.append(items[index])
            seen.add(index)
    return selected


def load_training_views(
    images: list[RegisteredImage],
    cameras: dict[int, Camera],
    image_dir: Path,
    max_images: int,
    max_render_size: int,
    device: torch.device,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, list[dict[str, Any]], int, int]:
    available = [image for image in sorted(images, key=lambda item: item.name) if (image_dir / image.name).exists()]
    selected = select_evenly(available, max_images)
    if not selected:
        raise ValueError("no registered COLMAP images exist in image directory")

    camera = cameras[selected[0].camera_id]
    scale = min(max_render_size / max(camera.width, camera.height), 1.0)
    width = max(1, int(round(camera.width * scale)))
    height = max(1, int(round(camera.height * scale)))

    targets = []
    viewmats = []
    intrinsics = []
    selected_manifest = []
    for image in selected:
        camera = cameras[image.camera_id]
        rgb = Image.open(image_dir / image.name).convert("RGB").resize((width, height), Image.Resampling.BILINEAR)
        target = np.asarray(rgb, dtype=np.float32) / 255.0
        targets.append(torch.from_numpy(target))
        viewmats.append(torch.from_numpy(viewmat_from_image(image)))
        intrinsics.append(torch.from_numpy(camera_intrinsics(camera, scale)))
        selected_manifest.append(
            {
                "imageId": image.image_id,
                "name": image.name,
                "cameraId": image.camera_id,
                "path": str(image_dir / image.name),
            }
        )

    return (
        torch.stack(targets).to(device),
        torch.stack(viewmats).to(device),
        torch.stack(intrinsics).to(device),
        selected_manifest,
        width,
        height,
    )


def scene_extent(points: torch.Tensor) -> float:
    bounds = points.detach().cpu().amax(dim=0) - points.detach().cpu().amin(dim=0)
    return max(float(torch.linalg.norm(bounds).item()), 1.0e-4)


def initial_scale(points: torch.Tensor) -> float:
    if points.shape[0] < 2:
        return 0.01
    sample = points[: min(points.shape[0], 2048)].detach().cpu()
    distances = torch.cdist(sample, sample)
    distances += torch.eye(sample.shape[0]) * 1.0e9
    nearest = distances.min(dim=1).values
    diagonal = scene_extent(points)
    median_nearest = float(torch.median(nearest).item())
    lower = max(diagonal * 0.0005, 1.0e-4)
    upper = max(diagonal * 0.02, lower)
    return min(max(median_nearest * 0.7, lower), upper)


def prune_to_gaussian_cap(
    params: dict[str, torch.nn.Parameter],
    optimizers: dict[str, torch.optim.Optimizer],
    strategy_state: dict[str, Any],
    max_gaussians: int,
    remove_gaussians: Any,
) -> int:
    gaussian_count = int(params["means"].shape[0])
    if gaussian_count <= max_gaussians:
        return 0
    remove_count = gaussian_count - max_gaussians
    scores = torch.sigmoid(params["opacities"].flatten())
    prune_indices = torch.topk(scores, k=remove_count, largest=False).indices
    mask = torch.zeros(gaussian_count, dtype=torch.bool, device=scores.device)
    mask[prune_indices] = True
    remove_gaussians(params=params, optimizers=optimizers, state=strategy_state, mask=mask)
    return int(remove_count)


def tensor_to_image(tensor: torch.Tensor) -> Image.Image:
    image = tensor.detach().clamp(0.0, 1.0).cpu().numpy()
    image_u8 = (image * 255.0).round().astype(np.uint8)
    return Image.fromarray(image_u8)


def save_image(path: Path, tensor: torch.Tensor) -> None:
    tensor_to_image(tensor).save(path)


def image_quality_metrics(rendered: Image.Image, target: Image.Image) -> dict[str, Any]:
    diff = ImageChops.difference(rendered.convert("RGB"), target.convert("RGB"))
    stat = ImageStat.Stat(diff)
    rendered_luma = ImageStat.Stat(rendered.convert("L"))
    target_luma = ImageStat.Stat(target.convert("L"))
    mae = sum(stat.mean) / 3.0
    rmse = math.sqrt(sum(value * value for value in stat.rms) / 3.0)
    return {
        "mae": round(mae, 4),
        "rmse": round(rmse, 4),
        "renderLuminanceMean": round(rendered_luma.mean[0], 4),
        "targetLuminanceMean": round(target_luma.mean[0], 4),
        "luminanceDelta": round(rendered_luma.mean[0] - target_luma.mean[0], 4),
    }


def ssim_index(prediction: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
    pred = prediction.permute(2, 0, 1).unsqueeze(0)
    truth = target.permute(2, 0, 1).unsqueeze(0)
    channels = pred.shape[1]
    window = torch.ones((channels, 1, 11, 11), dtype=pred.dtype, device=pred.device) / 121.0
    mu_pred = torch.nn.functional.conv2d(pred, window, padding=5, groups=channels)
    mu_truth = torch.nn.functional.conv2d(truth, window, padding=5, groups=channels)
    mu_pred_sq = mu_pred * mu_pred
    mu_truth_sq = mu_truth * mu_truth
    mu_pred_truth = mu_pred * mu_truth
    sigma_pred_sq = torch.nn.functional.conv2d(pred * pred, window, padding=5, groups=channels) - mu_pred_sq
    sigma_truth_sq = torch.nn.functional.conv2d(truth * truth, window, padding=5, groups=channels) - mu_truth_sq
    sigma_pred_truth = torch.nn.functional.conv2d(pred * truth, window, padding=5, groups=channels) - mu_pred_truth
    c1 = 0.01**2
    c2 = 0.03**2
    numerator = (2 * mu_pred_truth + c1) * (2 * sigma_pred_truth + c2)
    denominator = (mu_pred_sq + mu_truth_sq + c1) * (sigma_pred_sq + sigma_truth_sq + c2)
    return (numerator / denominator.clamp_min(1.0e-8)).mean()


def render_final_review(
    *,
    rasterization: Any,
    final_means: torch.Tensor,
    final_quats: torch.Tensor,
    final_log_scales: torch.Tensor,
    final_opacity_logits: torch.Tensor,
    final_colors: torch.Tensor,
    viewmats: torch.Tensor,
    Ks: torch.Tensor,
    backgrounds: torch.Tensor,
    targets: torch.Tensor,
    selected_images: list[dict[str, Any]],
    width: int,
    height: int,
    output_dir: Path,
    sample_render_path: Path,
    sample_target_path: Path,
    last_camera_index: int,
    review_samples: int,
) -> dict[str, Any]:
    view_count = int(targets.shape[0])
    sample_count = max(1, min(review_samples, view_count))
    indices = [last_camera_index]
    for raw_index in np.linspace(0, view_count - 1, sample_count):
        index = int(round(float(raw_index)))
        if index not in indices:
            indices.append(index)
    indices = indices[:sample_count]

    review_dir = output_dir / "render_review"
    review_dir.mkdir(parents=True, exist_ok=True)
    samples: list[dict[str, Any]] = []
    sheet_cells: list[tuple[str, Image.Image]] = []
    best_preview: tuple[float, int, Image.Image, Image.Image] | None = None
    scales = torch.exp(final_log_scales).clamp(1.0e-5, 1.0e3)
    opacities = torch.sigmoid(final_opacity_logits)
    with torch.no_grad():
        for order, camera_index in enumerate(indices):
            rendered, _alphas, _info = rasterization(
                means=final_means,
                quats=final_quats,
                scales=scales,
                opacities=opacities,
                colors=final_colors,
                viewmats=viewmats[camera_index : camera_index + 1],
                Ks=Ks[camera_index : camera_index + 1],
                width=width,
                height=height,
                backgrounds=backgrounds[camera_index : camera_index + 1],
                packed=False,
                rasterize_mode="classic",
            )
            render_img = tensor_to_image(rendered[0, :, :, :3])
            target_img = tensor_to_image(targets[camera_index])
            diff_img = ImageChops.difference(render_img, target_img).point(lambda value: min(255, value * 3))
            metrics = image_quality_metrics(render_img, target_img)
            stem = f"view_{order:02d}_camera_{camera_index:03d}"
            render_path = review_dir / f"{stem}_render.png"
            target_path = review_dir / f"{stem}_target.png"
            diff_path = review_dir / f"{stem}_diff_x3.png"
            render_img.save(render_path)
            target_img.save(target_path)
            diff_img.save(diff_path)
            preview_score = metrics["mae"] + abs(metrics["luminanceDelta"]) * 0.25
            if best_preview is None or preview_score < best_preview[0]:
                best_preview = (preview_score, camera_index, render_img.copy(), target_img.copy())
            samples.append(
                {
                    "order": order,
                    "cameraIndex": camera_index,
                    "imageName": selected_images[camera_index].get("name") if camera_index < len(selected_images) else None,
                    "renderPath": str(render_path),
                    "targetPath": str(target_path),
                    "diffPath": str(diff_path),
                    **metrics,
                }
            )
            sheet_cells.extend(
                [
                    (f"Render {camera_index} | MAE {metrics['mae']:.1f}", render_img),
                    (f"Target {camera_index}", target_img),
                    (f"Diff x3 | RMSE {metrics['rmse']:.1f}", diff_img),
                ]
            )

    preview_camera_index = None
    preview_score = None
    if best_preview is not None:
        preview_score, preview_camera_index, preview_render, preview_target = best_preview
        preview_render.save(sample_render_path)
        preview_target.save(sample_target_path)

    thumb_width = 320
    label_height = 28
    pad = 12
    rows = len(samples)
    sheet_width = thumb_width * 3 + pad * 4
    thumb_height = max(1, round(thumb_width * height / width))
    sheet_height = rows * (thumb_height + label_height + pad) + pad
    contact_sheet = Image.new("RGB", (sheet_width, sheet_height), (246, 246, 242))
    draw = ImageDraw.Draw(contact_sheet)
    for index, (label, image) in enumerate(sheet_cells):
        row = index // 3
        col = index % 3
        x = pad + col * (thumb_width + pad)
        y = pad + row * (thumb_height + label_height + pad)
        draw.text((x, y), label, fill=(32, 36, 42))
        thumb = image.resize((thumb_width, thumb_height), Image.Resampling.LANCZOS)
        contact_sheet.paste(thumb, (x, y + label_height))
    contact_sheet_path = review_dir / "contact_sheet.png"
    contact_sheet.save(contact_sheet_path)

    mean_mae = sum(sample["mae"] for sample in samples) / max(len(samples), 1)
    mean_rmse = sum(sample["rmse"] for sample in samples) / max(len(samples), 1)
    mean_luma_delta = sum(sample["luminanceDelta"] for sample in samples) / max(len(samples), 1)
    return {
        "status": "warning" if mean_mae > 35 or abs(mean_luma_delta) > 20 else "pass",
        "summary": "render review indicates visible mismatch" if mean_mae > 35 or abs(mean_luma_delta) > 20 else "render review is within initial visual thresholds",
        "contactSheetPath": str(contact_sheet_path),
        "sampleCount": len(samples),
        "previewCameraIndex": preview_camera_index,
        "previewScore": round(preview_score, 4) if preview_score is not None else None,
        "meanMae": round(mean_mae, 4),
        "meanRmse": round(mean_rmse, 4),
        "meanLuminanceDelta": round(mean_luma_delta, 4),
        "samples": samples,
    }


def train(args: argparse.Namespace) -> dict[str, Any]:
    started = time.perf_counter()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    colmap_text_dir = output_dir / "colmap_txt"
    sparse_model_path = Path(args.sparse_model_path)
    image_dir = Path(args.image_dir)

    converter = model_to_text(sparse_model_path, colmap_text_dir)
    if converter["status"] != "pass":
        return {
            "status": converter["status"],
            "checks": [
                {
                    "id": "colmap_model_converter",
                    "status": converter["status"],
                    "summary": converter.get("stderr") or "COLMAP model conversion failed",
                }
            ],
            "commands": {"modelConverter": converter},
        }

    cameras = parse_cameras(colmap_text_dir / "cameras.txt")
    images = parse_images(colmap_text_dir / "images.txt")
    points = parse_points3d(colmap_text_dir / "points3D.txt", args.max_points)
    if not cameras or not images or not points:
        return {
            "status": "fail",
            "checks": [
                {
                    "id": "colmap_text_model",
                    "status": "fail",
                    "summary": "COLMAP text model did not contain cameras, registered images and sparse points",
                    "cameraCount": len(cameras),
                    "registeredImageCount": len(images),
                    "pointCount": len(points),
                }
            ],
            "commands": {"modelConverter": converter},
        }

    if not torch.cuda.is_available():
        return {
            "status": "setup_gap",
            "checks": [
                {
                    "id": "torch_cuda",
                    "status": "setup_gap",
                    "summary": "PyTorch CUDA is not available for gsplat training",
                }
            ],
            "commands": {"modelConverter": converter},
        }

    try:
        import gsplat as gsplat_module  # type: ignore[import-not-found]
        from gsplat import rasterization  # type: ignore[import-not-found]
        from gsplat.cuda import _backend as gsplat_backend  # type: ignore[import-not-found]
        from gsplat.exporter import export_splats  # type: ignore[import-not-found]
        from gsplat.strategy import DefaultStrategy  # type: ignore[import-not-found]
        from gsplat.strategy.ops import remove as remove_gaussians  # type: ignore[import-not-found]
    except Exception as exc:  # noqa: BLE001 - extension builds fail at this boundary
        diagnostic = compact_text(str(exc))
        summary = "gsplat CUDA extension could not load or build"
        required = "CUDA Toolkit with nvcc and compatible Python development headers"
        if "Python.h" in diagnostic:
            summary = "gsplat CUDA extension build cannot find Python.h; install python3.12-dev"
            required = "python3.12-dev"
        elif "CUDA_HOME" in diagnostic or "nvcc" in diagnostic:
            summary = "gsplat CUDA extension build cannot find CUDA Toolkit/nvcc"
            required = "CUDA Toolkit with nvcc visible to WSL"
        return {
            "status": "setup_gap",
            "checks": [
                {
                    "id": "gsplat_cuda_extension",
                    "status": "setup_gap",
                    "summary": summary,
                    "required": required,
                    "diagnostic": diagnostic,
                }
            ],
            "commands": {"modelConverter": converter},
        }

    if getattr(gsplat_backend, "_C", None) is None:
        return {
            "status": "setup_gap",
            "checks": [
                {
                    "id": "gsplat_cuda_extension",
                    "status": "setup_gap",
                    "summary": "gsplat CUDA extension is unavailable after import",
                    "required": "CUDA Toolkit with nvcc or compatible gsplat prebuilt wheel",
                }
            ],
            "commands": {"modelConverter": converter},
        }

    torch.manual_seed(args.seed)
    device = torch.device("cuda")
    torch.cuda.reset_peak_memory_stats(device)

    targets, viewmats, Ks, selected_images, width, height = load_training_views(
        images=images,
        cameras=cameras,
        image_dir=image_dir,
        max_images=args.max_images,
        max_render_size=args.max_render_size,
        device=device,
    )
    backgrounds = targets.mean(dim=(1, 2)).clamp(0.0, 1.0)

    means_init = torch.tensor([point.xyz for point in points], dtype=torch.float32, device=device)
    rgb_init = torch.tensor([point.rgb for point in points], dtype=torch.float32, device=device).clamp(0.01, 0.99)
    scale_value = initial_scale(means_init) * args.initial_scale_multiplier
    scene_scale = scene_extent(means_init)
    quats_init = torch.zeros((len(points), 4), dtype=torch.float32, device=device)
    quats_init[:, 0] = 1.0
    initial_opacity = min(max(args.initial_opacity, 0.001), 0.999)
    params: dict[str, torch.nn.Parameter] = {
        "means": torch.nn.Parameter(means_init),
        "colors": torch.nn.Parameter(torch.logit(rgb_init)),
        "scales": torch.nn.Parameter(torch.full((len(points), 3), math.log(scale_value), dtype=torch.float32, device=device)),
        "opacities": torch.nn.Parameter(
            torch.full((len(points),), torch.logit(torch.tensor(initial_opacity)).item(), dtype=torch.float32, device=device)
        ),
        "quats": torch.nn.Parameter(quats_init),
    }
    optimizers: dict[str, torch.optim.Optimizer] = {
        "means": torch.optim.Adam([params["means"]], lr=args.mean_lr),
        "colors": torch.optim.Adam([params["colors"]], lr=args.color_lr),
        "scales": torch.optim.Adam([params["scales"]], lr=args.scale_lr),
        "opacities": torch.optim.Adam([params["opacities"]], lr=args.opacity_lr),
        "quats": torch.optim.Adam([params["quats"]], lr=args.quat_lr),
    }

    strategy = None
    strategy_state: dict[str, Any] = {}
    if args.densify_strategy == "default":
        strategy = DefaultStrategy(
            prune_opa=args.prune_opa,
            grow_grad2d=args.grow_grad2d,
            grow_scale3d=args.grow_scale3d,
            refine_start_iter=args.refine_start_iter,
            refine_stop_iter=args.refine_stop_iter,
            refine_every=args.refine_every,
            reset_every=args.reset_every,
            absgrad=args.absgrad,
        )
        strategy.check_sanity(params, optimizers)
        strategy_state = strategy.initialize_state(scene_scale=scene_scale)

    loss_samples: list[dict[str, Any]] = []
    densification_samples: list[dict[str, Any]] = []
    progress_path = output_dir / "training_progress.json"
    cap_pruned_gaussians = 0
    last_render = None
    last_target = None
    last_camera_index = 0

    def write_progress(iteration: int, camera_index: int, loss: torch.Tensor, l1_loss: torch.Tensor, ssim_loss: torch.Tensor) -> None:
        elapsed = time.perf_counter() - started
        write_json(
            progress_path,
            {
                "status": "running",
                "profile": args.profile,
                "iteration": iteration,
                "iterations": args.iterations,
                "percent": round((iteration / max(args.iterations, 1)) * 100.0, 3),
                "elapsedSeconds": round(elapsed, 3),
                "estimatedTotalSeconds": round(elapsed / max(iteration, 1) * args.iterations, 3),
                "cameraIndex": int(camera_index),
                "loss": float(loss.detach().cpu().item()),
                "l1Loss": float(l1_loss.detach().cpu().item()),
                "ssimLoss": float(ssim_loss.detach().cpu().item()),
                "gaussianCount": int(params["means"].shape[0]),
                "selectedImageCount": len(selected_images),
                "renderWidth": width,
                "renderHeight": height,
                "maxGaussians": args.max_gaussians,
                "lossSamples": loss_samples[-12:],
                "densificationSamples": densification_samples[-12:],
            },
        )

    for iteration in range(1, args.iterations + 1):
        camera_index = (iteration - 1) % targets.shape[0]
        colors = torch.sigmoid(params["colors"])
        scales = torch.exp(params["scales"]).clamp(1.0e-5, 1.0e3)
        opacities = torch.sigmoid(params["opacities"])
        quats = torch.nn.functional.normalize(params["quats"], dim=-1)
        rendered, _alphas, info = rasterization(
            means=params["means"],
            quats=quats,
            scales=scales,
            opacities=opacities,
            colors=colors,
            viewmats=viewmats[camera_index : camera_index + 1],
            Ks=Ks[camera_index : camera_index + 1],
            width=width,
            height=height,
            backgrounds=backgrounds[camera_index : camera_index + 1],
            packed=False,
            absgrad=args.absgrad,
            rasterize_mode="classic",
        )
        prediction = rendered[0, :, :, :3]
        target = targets[camera_index]
        l1_loss = torch.nn.functional.l1_loss(prediction, target)
        if args.ssim_weight > 0.0:
            ssim_loss = 1.0 - ssim_index(prediction, target)
            loss = (1.0 - args.ssim_weight) * l1_loss + args.ssim_weight * ssim_loss
        else:
            ssim_loss = torch.zeros((), dtype=l1_loss.dtype, device=l1_loss.device)
            loss = l1_loss

        for optimizer in optimizers.values():
            optimizer.zero_grad(set_to_none=True)
        if strategy is not None:
            strategy.step_pre_backward(params, optimizers, strategy_state, iteration, info)
        loss.backward()
        for optimizer in optimizers.values():
            optimizer.step()

        before_refine_count = int(params["means"].shape[0])
        if strategy is not None:
            strategy.step_post_backward(params, optimizers, strategy_state, iteration, info, packed=False)
            cap_pruned = prune_to_gaussian_cap(params, optimizers, strategy_state, args.max_gaussians, remove_gaussians)
            cap_pruned_gaussians += cap_pruned
            after_refine_count = int(params["means"].shape[0])
            if cap_pruned or after_refine_count != before_refine_count:
                densification_samples.append(
                    {
                        "iteration": iteration,
                        "before": before_refine_count,
                        "after": after_refine_count,
                        "capPruned": cap_pruned,
                    }
                )

        with torch.no_grad():
            params["scales"].clamp_(math.log(1.0e-5), math.log(max(scale_value * 20.0, 1.0e-4)))
            params["opacities"].clamp_(-8.0, 8.0)
            params["colors"].clamp_(-8.0, 8.0)
            params["quats"].div_(params["quats"].norm(dim=-1, keepdim=True).clamp_min(1.0e-8))

        if iteration == 1 or iteration == args.iterations or iteration % args.sample_every == 0:
            loss_samples.append(
                {
                    "iteration": iteration,
                    "cameraIndex": int(camera_index),
                    "loss": float(loss.detach().cpu().item()),
                    "l1Loss": float(l1_loss.detach().cpu().item()),
                    "ssimLoss": float(ssim_loss.detach().cpu().item()),
                    "gaussianCount": int(params["means"].shape[0]),
                }
            )
            write_progress(iteration, camera_index, loss, l1_loss, ssim_loss)
        last_render = prediction.detach()
        last_target = target.detach()
        last_camera_index = int(camera_index)

    torch.cuda.synchronize(device)
    wall_time = time.perf_counter() - started

    checkpoint_path = output_dir / "checkpoint.pt"
    sample_render_path = output_dir / "sample_render.png"
    sample_target_path = output_dir / "sample_target.png"
    exported_ply_path = output_dir / "trained_splats.ply"
    if last_render is not None:
        save_image(sample_render_path, last_render)
    if last_target is not None:
        save_image(sample_target_path, last_target)

    final_colors = torch.sigmoid(params["colors"]).detach()
    final_count = int(params["means"].shape[0])
    sh0 = ((final_colors - 0.5) / SH_C0).unsqueeze(1)
    shN = torch.empty((final_count, 0, 3), dtype=torch.float32, device=device)
    final_log_scales = params["scales"].detach()
    final_opacity_logits = params["opacities"].detach()
    final_quats = torch.nn.functional.normalize(params["quats"].detach(), dim=-1)
    final_means = params["means"].detach()
    render_review = render_final_review(
        rasterization=rasterization,
        final_means=final_means,
        final_quats=final_quats,
        final_log_scales=final_log_scales,
        final_opacity_logits=final_opacity_logits,
        final_colors=final_colors,
        viewmats=viewmats,
        Ks=Ks,
        backgrounds=backgrounds,
        targets=targets,
        selected_images=selected_images,
        width=width,
        height=height,
        output_dir=output_dir,
        sample_render_path=sample_render_path,
        sample_target_path=sample_target_path,
        last_camera_index=last_camera_index,
        review_samples=args.review_samples,
    )

    torch.save(
        {
            "means": final_means.cpu(),
            "log_scales": final_log_scales.cpu(),
            "quats": final_quats.cpu(),
            "opacity_logits": final_opacity_logits.cpu(),
            "sh0": sh0.cpu(),
            "shN": shN.cpu(),
            "source": {
                "sparseModelPath": str(sparse_model_path),
                "imageDirectory": str(image_dir),
                "selectedImages": selected_images,
            },
            "training": {
                "profile": args.profile,
                "densifyStrategy": args.densify_strategy,
                "initialOpacity": initial_opacity,
                "initialScaleMultiplier": args.initial_scale_multiplier,
                "ssimWeight": args.ssim_weight,
                "iterations": args.iterations,
                "lossSamples": loss_samples,
                "densificationSamples": densification_samples,
                "renderReview": render_review,
                "renderWidth": width,
                "renderHeight": height,
            },
        },
        checkpoint_path,
    )
    export_splats(
        means=final_means,
        scales=final_log_scales,
        quats=final_quats,
        opacities=final_opacity_logits,
        sh0=sh0,
        shN=shN,
        format="ply",
        save_to=str(exported_ply_path),
    )

    max_memory_mib = float(torch.cuda.max_memory_allocated(device) / (1024 * 1024))
    if progress_path.exists():
        progress = json.loads(progress_path.read_text(encoding="utf-8"))
        progress["status"] = "pass"
        progress["completedAtSeconds"] = round(wall_time, 3)
        progress["artifactPath"] = str(exported_ply_path)
        write_json(progress_path, progress)
    return {
        "status": "pass",
        "checks": [
            {
                "id": "training_run",
                "status": "pass",
                "summary": "gsplat training completed",
            },
            {
                "id": "exported_splat",
                "status": "pass",
                "summary": "PLY splat artifact exported",
                "path": str(exported_ply_path),
            },
            {
                "id": "sample_render",
                "status": "pass" if sample_render_path.exists() else "fail",
                "summary": "sample render saved" if sample_render_path.exists() else "sample render was not saved",
                "path": str(sample_render_path),
            },
            {
                "id": "render_review",
                "status": render_review["status"],
                "summary": render_review["summary"],
                "path": render_review["contactSheetPath"],
                "meanMae": render_review["meanMae"],
                "meanRmse": render_review["meanRmse"],
                "meanLuminanceDelta": render_review["meanLuminanceDelta"],
            },
        ],
        "commands": {"modelConverter": converter},
        "backend": "gsplat",
        "versions": {
            "torch": torch.__version__,
            "torchCuda": torch.version.cuda,
            "gsplat": getattr(gsplat_module, "__version__", None),
        },
        "device": {
            "name": torch.cuda.get_device_name(device),
            "maxMemoryAllocatedMiB": round(max_memory_mib, 2),
        },
        "source": {
            "sparseModelPath": str(sparse_model_path),
            "imageDirectory": str(image_dir),
            "registeredImageCount": len(images),
            "sparsePointCount": len(points),
        },
        "training": {
            "iterations": args.iterations,
            "imagesUsed": len(selected_images),
            "selectedImages": selected_images,
            "renderWidth": width,
            "renderHeight": height,
            "profile": args.profile,
            "densifyStrategy": args.densify_strategy,
            "initialOpacity": initial_opacity,
            "initialScaleMultiplier": args.initial_scale_multiplier,
            "ssimWeight": args.ssim_weight,
            "initialGaussianCount": len(points),
            "gaussianCount": final_count,
            "gaussianGrowthFactor": round(final_count / max(len(points), 1), 4),
            "maxGaussians": args.max_gaussians,
            "capPrunedGaussianCount": cap_pruned_gaussians,
            "initialScale": scale_value,
            "sceneScale": scene_scale,
            "lossSamples": loss_samples,
            "densificationSamples": densification_samples,
            "renderReview": render_review,
            "initialLoss": loss_samples[0]["loss"] if loss_samples else None,
            "finalLoss": loss_samples[-1]["loss"] if loss_samples else None,
            "lastCameraIndex": last_camera_index,
            "wallTimeSeconds": round(wall_time, 3),
        },
        "checkpointPath": str(checkpoint_path),
        "exportedArtifactPath": str(exported_ply_path),
        "splatArtifactPath": str(exported_ply_path),
        "sampleRenderPath": str(sample_render_path),
        "sampleTargetPath": str(sample_target_path),
        "renderReviewPath": render_review["contactSheetPath"],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run a minimal gsplat training smoke from a COLMAP sparse model.")
    parser.add_argument("--sparse-model-path", required=True)
    parser.add_argument("--image-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--result-json", required=True)
    parser.add_argument("--profile", default="smoke")
    parser.add_argument("--iterations", type=int, default=40)
    parser.add_argument("--max-images", type=int, default=8)
    parser.add_argument("--max-points", type=int, default=6000)
    parser.add_argument("--max-render-size", type=int, default=384)
    parser.add_argument("--max-gaussians", type=int, default=6000)
    parser.add_argument("--sample-every", type=int, default=5)
    parser.add_argument("--review-samples", type=int, default=4)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--initial-opacity", type=float, default=0.55)
    parser.add_argument("--initial-scale-multiplier", type=float, default=1.0)
    parser.add_argument("--ssim-weight", type=float, default=0.0)
    parser.add_argument("--mean-lr", type=float, default=0.0005)
    parser.add_argument("--color-lr", type=float, default=0.02)
    parser.add_argument("--scale-lr", type=float, default=0.001)
    parser.add_argument("--opacity-lr", type=float, default=0.01)
    parser.add_argument("--quat-lr", type=float, default=0.0005)
    parser.add_argument("--densify-strategy", choices=["none", "default"], default="none")
    parser.add_argument("--refine-start-iter", type=int, default=500)
    parser.add_argument("--refine-stop-iter", type=int, default=15000)
    parser.add_argument("--refine-every", type=int, default=100)
    parser.add_argument("--reset-every", type=int, default=3000)
    parser.add_argument("--grow-grad2d", type=float, default=0.0002)
    parser.add_argument("--grow-scale3d", type=float, default=0.01)
    parser.add_argument("--prune-opa", type=float, default=0.005)
    parser.add_argument("--absgrad", action="store_true")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    result_json = Path(args.result_json)
    try:
        result = train(args)
    except Exception as exc:  # noqa: BLE001 - stage report should preserve boundary failure
        result = {
            "status": "fail",
            "checks": [
                {
                    "id": "training_exception",
                    "status": "fail",
                    "summary": str(exc),
                }
            ],
        }
    write_json(result_json, result)
    print(f"training_status={result.get('status')}")
    print(f"training_result={result_json}")
    return 0 if result.get("status") == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
