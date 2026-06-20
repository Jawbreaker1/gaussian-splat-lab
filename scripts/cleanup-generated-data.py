#!/usr/bin/env python3
"""Dry-run-first cleanup for generated Gaussian Splat Lab data."""

from __future__ import annotations

import argparse
import json
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUTS_DIR = REPO_ROOT / "outputs"
JOBS_DIR = OUTPUTS_DIR / "jobs"
DELETED_JOBS_DIR = OUTPUTS_DIR / "deleted-jobs"
EXPERIMENTS_DIR = OUTPUTS_DIR / "experiments"


@dataclass(frozen=True)
class Candidate:
    path: Path
    reason: str


def format_bytes(size: int) -> str:
    value = float(size)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024 or unit == "TB":
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
        value /= 1024
    return f"{value:.1f} TB"


def path_size(path: Path) -> int:
    if not path.exists():
        return 0
    if path.is_file() or path.is_symlink():
        return path.stat().st_size
    total = 0
    for child in path.rglob("*"):
        if child.is_file() or child.is_symlink():
            total += child.stat().st_size
    return total


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def iter_repo_relative_strings(value: Any) -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if isinstance(child, str) and (key.endswith("RepoRelativePath") or key == "repoRelativePath"):
                found.append(child)
            else:
                found.extend(iter_repo_relative_strings(child))
    elif isinstance(value, list):
        for child in value:
            found.extend(iter_repo_relative_strings(child))
    return found


def viewer_manifest_path(job_dir: Path) -> Path:
    return job_dir / "viewer" / "viewer-manifest.json"


def gallery_job_dirs() -> list[Path]:
    if not JOBS_DIR.exists():
        return []
    return sorted(path for path in JOBS_DIR.iterdir() if path.is_dir() and viewer_manifest_path(path).exists())


def preserved_gallery_paths(job_dir: Path) -> set[Path]:
    manifest_path = viewer_manifest_path(job_dir)
    manifest = read_json(manifest_path)
    preserved = {
        job_dir / "job.json",
        job_dir / "viewer",
        job_dir / "reports",
        manifest_path,
    }
    for repo_relative in iter_repo_relative_strings(manifest):
        path = (REPO_ROOT / repo_relative).resolve()
        if path.exists() and path.is_relative_to(job_dir.resolve()):
            preserved.add(path)
    return preserved


def contains_preserved_path(candidate: Path, preserved: set[Path]) -> bool:
    resolved = candidate.resolve()
    for keep in preserved:
        keep_resolved = keep.resolve()
        if keep_resolved == resolved or keep_resolved.is_relative_to(resolved):
            return True
    return False


def prune_gallery_candidates() -> list[Candidate]:
    candidates: list[Candidate] = []
    heavy_splat_dirs = {"colmap_txt", "logs", "nerfstudio-data", "nerfstudio-runs"}
    for job_dir in gallery_job_dirs():
        preserved = preserved_gallery_paths(job_dir)
        for child_name in ("frames", "sfm"):
            candidate = job_dir / child_name
            if candidate.exists() and not contains_preserved_path(candidate, preserved):
                candidates.append(Candidate(candidate, "gallery working data"))

        for splat_run in sorted((job_dir / "splats").glob("*")):
            if not splat_run.is_dir():
                continue
            for child in sorted(splat_run.iterdir()):
                if child.name in heavy_splat_dirs and not contains_preserved_path(child, preserved):
                    candidates.append(Candidate(child, "trainer/SfM working data"))

            eval_renders = splat_run / "render_review" / "eval-renders"
            if eval_renders.exists():
                for render in sorted(eval_renders.iterdir()):
                    if render.is_file() and render.resolve() not in {path.resolve() for path in preserved}:
                        candidates.append(Candidate(render, "unreferenced eval render"))
    return candidates


def coalesce_candidates(candidates: list[Candidate]) -> list[Candidate]:
    result: list[Candidate] = []
    for candidate in sorted(candidates, key=lambda item: len(item.path.parts)):
        resolved = candidate.path.resolve()
        if any(resolved == kept.path.resolve() or resolved.is_relative_to(kept.path.resolve()) for kept in result):
            continue
        result.append(candidate)
    return result


def collect_candidates(args: argparse.Namespace) -> list[Candidate]:
    candidates: list[Candidate] = []
    if args.all_safe or args.purge_deleted_jobs:
        if DELETED_JOBS_DIR.exists():
            candidates.append(Candidate(DELETED_JOBS_DIR, "deleted gallery jobs"))
    if args.all_safe or args.purge_experiments:
        if EXPERIMENTS_DIR.exists():
            candidates.append(Candidate(EXPERIMENTS_DIR, "duplicate trainer experiment workspaces"))
    if args.all_safe or args.prune_gallery_workdirs:
        candidates.extend(prune_gallery_candidates())
    return coalesce_candidates(candidates)


def remove_path(path: Path) -> None:
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    else:
        path.unlink(missing_ok=True)


def write_report(candidates: list[tuple[Candidate, int]], applied: bool) -> Path:
    report_dir = OUTPUTS_DIR / "cleanup-reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    report_path = report_dir / f"cleanup-{timestamp}.json"
    report_path.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "applied": applied,
                "totalBytes": sum(size for _, size in candidates),
                "items": [
                    {
                        "path": str(candidate.path.relative_to(REPO_ROOT)),
                        "reason": candidate.reason,
                        "sizeBytes": size,
                    }
                    for candidate, size in candidates
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return report_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Plan or apply cleanup for generated 3DGS data.")
    parser.add_argument("--all-safe", action="store_true", help="Purge deleted jobs, purge duplicate experiments and prune gallery workdirs.")
    parser.add_argument("--purge-deleted-jobs", action="store_true", help="Delete outputs/deleted-jobs.")
    parser.add_argument("--purge-experiments", action="store_true", help="Delete outputs/experiments trainer workspaces.")
    parser.add_argument("--prune-gallery-workdirs", action="store_true", help="Keep gallery viewer/export files but remove frames, SfM data and trainer checkpoints.")
    parser.add_argument("--apply", action="store_true", help="Actually delete the planned files. Omit for dry-run.")
    parser.add_argument("--write-report", action="store_true", help="Write a JSON cleanup report under outputs/cleanup-reports.")
    args = parser.parse_args()

    if not any((args.all_safe, args.purge_deleted_jobs, args.purge_experiments, args.prune_gallery_workdirs)):
        parser.error("choose at least one cleanup target")

    candidates = collect_candidates(args)
    sized = [(candidate, path_size(candidate.path)) for candidate in candidates if candidate.path.exists()]
    total = sum(size for _, size in sized)

    print(f"cleanup_mode={'apply' if args.apply else 'dry-run'}")
    print(f"candidate_count={len(sized)}")
    print(f"reclaimable={format_bytes(total)}")
    for candidate, size in sized:
        print(f"{format_bytes(size):>10}  {candidate.reason:36}  {candidate.path.relative_to(REPO_ROOT)}")

    if args.write_report:
        report_path = write_report(sized, args.apply)
        print(f"report={report_path.relative_to(REPO_ROOT)}")

    if args.apply:
        for candidate, _size in sized:
            remove_path(candidate.path)
        print("cleanup_applied=true")
    else:
        print("cleanup_applied=false")
        print("rerun with --apply to delete these files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
