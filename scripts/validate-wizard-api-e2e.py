#!/usr/bin/env python3
"""Validate the wizard backend contract from upload to packaged 3DGS."""

from __future__ import annotations

import argparse
import json
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


AUTOMATED_STAGE_ORDER = [
    "framework_license",
    "environment",
    "intake",
    "frame_sampling",
    "sfm",
    "splat_training",
    "packaging",
    "viewer",
    "quality_report",
]
HEAVY_STAGES = {"sfm", "splat_training", "viewer"}


def request_json(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    body: bytes | None = None,
    timeout: int | None = None,
) -> dict[str, Any]:
    request = urllib.request.Request(url, data=body, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = response.read().decode("utf-8")
            return json.loads(payload or "{}")
    except urllib.error.HTTPError as exc:
        payload = exc.read().decode("utf-8")
        try:
            parsed = json.loads(payload or "{}")
        except json.JSONDecodeError:
            parsed = {"error": payload}
        raise RuntimeError(f"{method} {url} failed with HTTP {exc.code}: {parsed}") from exc


def upload_capture(base_url: str, video_path: Path, scene_name: str, scene_kind: str, quality: str) -> dict[str, Any]:
    params = urllib.parse.urlencode(
        {
            "displayName": scene_name,
            "sceneKind": scene_kind,
            "qualityPreset": quality,
        }
    )
    return request_json(
        "POST",
        f"{base_url}/api/captures/create-upload?{params}",
        headers={
            "Content-Type": "application/octet-stream",
            "X-Filename": video_path.name,
        },
        body=video_path.read_bytes(),
        timeout=30 * 60,
    )


def create_job(base_url: str, capture_id: str) -> dict[str, Any]:
    return request_json(
        "POST",
        f"{base_url}/api/jobs",
        headers={"Content-Type": "application/json"},
        body=json.dumps({"captureId": capture_id}).encode("utf-8"),
        timeout=5 * 60,
    )


def progress_poller(base_url: str, job_path: str, stop_event: threading.Event, interval: float) -> None:
    last_line = ""
    while not stop_event.wait(interval):
        try:
            params = urllib.parse.urlencode({"jobPath": job_path})
            payload = request_json("GET", f"{base_url}/api/jobs/progress?{params}", timeout=10)
        except Exception as exc:  # noqa: BLE001 - best-effort progress only
            line = f"progress_error={exc}"
        else:
            progress = payload.get("trainingProgress") if isinstance(payload.get("trainingProgress"), dict) else {}
            if progress:
                line = (
                    f"training_progress={progress.get('percent')}% "
                    f"iter={progress.get('iteration')}/{progress.get('iterations')} "
                    f"gaussians={progress.get('gaussianCount')} "
                    f"elapsed={progress.get('elapsedSeconds')}s"
                )
            else:
                reports = payload.get("reports") if isinstance(payload.get("reports"), dict) else {}
                line = "stage_reports=" + ",".join(
                    f"{stage}:{report.get('status')}" for stage, report in sorted(reports.items())
                )
        if line != last_line:
            print(line, flush=True)
            last_line = line


def run_stage(base_url: str, job_path: str, stage: str, quality: str, timeout: int, poll_interval: float) -> dict[str, Any]:
    stop_event = threading.Event()
    poll_thread: threading.Thread | None = None
    if stage == "splat_training":
        poll_thread = threading.Thread(target=progress_poller, args=(base_url, job_path, stop_event, poll_interval), daemon=True)
        poll_thread.start()
    try:
        payload = request_json(
            "POST",
            f"{base_url}/api/jobs/run-stage",
            headers={"Content-Type": "application/json"},
            body=json.dumps(
                {
                    "jobPath": job_path,
                    "stage": stage,
                    "acceptWarning": True,
                    "allowHeavy": stage in HEAVY_STAGES,
                    "trainingProfile": quality if stage == "splat_training" else None,
                }
            ).encode("utf-8"),
            timeout=timeout,
        )
    finally:
        stop_event.set()
        if poll_thread:
            poll_thread.join(timeout=5)

    if payload.get("returnCode") not in {0, None}:
        raise RuntimeError(payload.get("stderr") or payload.get("stdout") or f"{stage} failed")
    status = next(
        (
            item.get("status")
            for item in payload.get("job", {}).get("stages", [])
            if isinstance(item, dict) and item.get("id") == stage
        ),
        None,
    )
    print(f"stage_result={stage}:{status}", flush=True)
    return payload


def gallery_item(base_url: str, job_id: str) -> dict[str, Any]:
    return request_json("GET", f"{base_url}/api/gallery/jobs/{urllib.parse.quote(job_id)}", timeout=60)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the upload wizard backend flow end to end.")
    parser.add_argument("base_url")
    parser.add_argument("--video", required=True)
    parser.add_argument("--scene-name", default="Wizard API E2E room")
    parser.add_argument("--scene-kind", default="room", choices=["room", "outdoor", "object"])
    parser.add_argument("--quality", default="quality_probe")
    parser.add_argument("--stage-timeout-seconds", type=int, default=7200)
    parser.add_argument("--poll-seconds", type=float, default=30.0)
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    video_path = Path(args.video).resolve()
    if not video_path.exists():
        raise FileNotFoundError(video_path)

    upload = upload_capture(base_url, video_path, args.scene_name, args.scene_kind, args.quality)
    capture = upload.get("capture") if isinstance(upload.get("capture"), dict) else {}
    capture_id = str(capture.get("id") or "")
    if not capture_id:
        raise RuntimeError(f"upload response did not include capture id: {upload}")
    print(f"upload_capture={capture_id}", flush=True)

    created = create_job(base_url, capture_id)
    job = created.get("job") if isinstance(created.get("job"), dict) else {}
    job_path = str(job.get("jobPath") or "")
    job_id = str(job.get("job", {}).get("id") or "")
    if not job_path or not job_id:
        raise RuntimeError(f"job response did not include jobPath/job id: {created}")
    print(f"job_created={job_id}", flush=True)

    latest_payload: dict[str, Any] = created
    for stage in AUTOMATED_STAGE_ORDER:
        print(f"stage_start={stage}", flush=True)
        latest_payload = run_stage(
            base_url,
            job_path,
            stage,
            args.quality,
            args.stage_timeout_seconds,
            args.poll_seconds,
        )

    detail = gallery_item(base_url, job_id)
    item = detail.get("item") if isinstance(detail.get("item"), dict) else {}
    artifact = item.get("artifact") if isinstance(item.get("artifact"), dict) else {}
    if not item.get("artifactUrl") or not item.get("viewerManifestUrl"):
        raise RuntimeError(f"gallery item is missing artifact URLs: {detail}")
    if not artifact.get("splatCount"):
        raise RuntimeError(f"gallery item is missing splat count: {detail}")

    print("final_job=" + json.dumps(latest_payload.get("job", {}), sort_keys=True), flush=True)
    print("gallery_item=" + json.dumps(item, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
