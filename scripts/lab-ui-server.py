#!/usr/bin/env python3
"""Local dependency-free web UI for Gaussian Splat Lab."""

from __future__ import annotations

import argparse
import importlib.util
import json
import mimetypes
import subprocess
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = REPO_ROOT / "app"
CAPTURE_MANIFEST = REPO_ROOT / "data/manifests/captures.example.json"
FRAMEWORK_MANIFEST = REPO_ROOT / "data/manifests/framework-evaluation.json"
GATES_MANIFEST = REPO_ROOT / "data/manifests/pipeline-gates.json"
JOBS_DIR = REPO_ROOT / "outputs/jobs"
RTX_EVIDENCE = REPO_ROOT / "docs/validation/phase-0-rtx-workstation-wsl-output.md"
PIPELINE_SCRIPT = REPO_ROOT / "scripts/lab-pipeline.py"
VENV_PYTHON = REPO_ROOT / ".venv/bin/python"
RUNNABLE_STAGES = {"environment", "intake", "frame_sampling", "sfm"}


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


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


def latest_job() -> dict[str, Any] | None:
    if not JOBS_DIR.exists():
        return None
    candidates = sorted(JOBS_DIR.glob("*/job.json"), key=lambda path: path.stat().st_mtime, reverse=True)
    if not candidates:
        return None
    job = read_json(candidates[0])
    job["jobPath"] = str(candidates[0])
    return job


def build_state() -> dict[str, Any]:
    captures = read_json(CAPTURE_MANIFEST).get("captures", [])
    frameworks = read_json(FRAMEWORK_MANIFEST).get("frameworks", [])
    gates = read_json(GATES_MANIFEST).get("gates", [])
    evidence = RTX_EVIDENCE.read_text(encoding="utf-8") if RTX_EVIDENCE.exists() else ""
    return {
        "schemaVersion": 1,
        "machineLabel": "Windows RTX 5090 workstation / WSL2",
        "captures": captures,
        "frameworks": frameworks,
        "gates": gates,
        "latestJob": latest_job(),
        "validation": {
            "architecture": run_validator("validate-architecture-contracts.sh"),
            "phase1": run_validator("validate-phase-1-contracts.sh"),
            "rtxVisible": "NVIDIA GeForce RTX 5090" in evidence,
        },
    }


def create_job(capture_id: str) -> dict[str, Any]:
    pipeline = load_pipeline_module()
    selection = pipeline.select_capture(CAPTURE_MANIFEST, capture_id)
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


def run_job_stage(job_path: Path, stage: str, accept_warning: bool = False) -> dict[str, Any]:
    if stage not in RUNNABLE_STAGES:
        raise ValueError(f"stage {stage!r} is not runnable from the UI yet")
    command = [pipeline_python(), str(PIPELINE_SCRIPT), "run-stage", stage, "--job", str(job_path)]
    if accept_warning:
        command.append("--accept-warning")
    result = subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
        timeout=900,
    )

    job = read_json(job_path)
    job["jobPath"] = str(job_path)
    return {
        "job": job,
        "stage": stage,
        "returnCode": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }


def validate_ui_contracts() -> None:
    required_files = [
        APP_ROOT / "index.html",
        APP_ROOT / "styles.css",
        APP_ROOT / "app.js",
        CAPTURE_MANIFEST,
        FRAMEWORK_MANIFEST,
        GATES_MANIFEST,
    ]
    for path in required_files:
        if not path.exists():
            raise SystemExit(f"missing required UI file: {path}")

    for path in [APP_ROOT / "index.html", APP_ROOT / "app.js", APP_ROOT / "styles.css"]:
        text = path.read_text(encoding="utf-8")
        blocked_markers = ["https://", "http://", "unpkg.com", "cdn", "importmap"]
        for marker in blocked_markers:
            if marker in text:
                raise SystemExit(f"external UI dependency marker {marker!r} found in {path}")

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
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path == "/api/state":
            try:
                self.send_json(build_state())
            except Exception as exc:  # noqa: BLE001 - user-facing local server boundary
                self.send_json({"error": str(exc)}, HTTPStatus.INTERNAL_SERVER_ERROR)
            return

        route = self.path.split("?", 1)[0]
        if route == "/":
            self.send_static(APP_ROOT / "index.html")
            return

        self.send_static(APP_ROOT / route.lstrip("/"))

    def do_POST(self) -> None:
        route = self.path.split("?", 1)[0]
        if route not in {"/api/jobs", "/api/jobs/run-stage"}:
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
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
            if not isinstance(stage, str) or not stage:
                self.send_json({"error": "stage is required"}, HTTPStatus.BAD_REQUEST)
                return
            result = run_job_stage(job_path, stage, accept_warning=accept_warning)
            self.send_json(result)
        except ValueError as exc:
            self.send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
        except subprocess.TimeoutExpired:
            self.send_json({"error": "stage run timed out"}, HTTPStatus.REQUEST_TIMEOUT)
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
