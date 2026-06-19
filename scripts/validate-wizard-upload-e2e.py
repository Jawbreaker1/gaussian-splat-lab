#!/usr/bin/env python3
"""Run the browser wizard from video upload to generated gallery scene."""

from __future__ import annotations

import argparse
import base64
import importlib.util
import json
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
CDP_HELPER = REPO_ROOT / "scripts" / "capture-browser-screenshot.py"
DEFAULT_WSL_WINDOWS_TEMP = Path("/mnt/c/Users/engwa/AppData/Local/Temp")


def load_cdp_helper() -> Any:
    spec = importlib.util.spec_from_file_location("capture_browser_screenshot", CDP_HELPER)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {CDP_HELPER}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def evaluate(client: Any, expression: str, await_promise: bool = False) -> Any:
    result = client.command(
        "Runtime.evaluate",
        {
            "expression": expression,
            "returnByValue": True,
            "awaitPromise": await_promise,
        },
    )
    payload = result.get("result", {})
    if payload.get("subtype") == "error":
        raise RuntimeError(payload.get("description") or payload.get("value") or "browser evaluation failed")
    return payload.get("value")


def wizard_snapshot(client: Any) -> dict[str, Any]:
    value = evaluate(
        client,
        """
        (() => ({
          wizardStatus: document.querySelector('#wizardStatus')?.textContent || '',
          wizardType: document.querySelector('#wizardStatus')?.dataset.type || '',
          progress: document.querySelector('#pipelineProgressText')?.textContent || '',
          currentStage: document.querySelector('#pipelineCurrentStage')?.textContent || '',
          eta: document.querySelector('#pipelineEtaText')?.textContent || '',
          jobText: document.querySelector('#jobBox')?.textContent || '',
          viewerStatus: document.querySelector('#viewerStatusPill')?.textContent || '',
          href: window.location.href,
        }))()
        """,
    )
    return value if isinstance(value, dict) else {}


def set_file_input(client: Any, file_path: Path, browser_path: str, cdp_helper: Any) -> None:
    document = client.command("DOM.getDocument", {"depth": 1})
    root_id = document["root"]["nodeId"]
    node = client.command("DOM.querySelector", {"nodeId": root_id, "selector": "#videoFileInput"})
    node_id = node.get("nodeId")
    if not node_id:
        raise RuntimeError("video file input was not found")
    client.command("DOM.setFileInputFiles", {"nodeId": node_id, "files": [cdp_helper.as_browser_path(file_path, browser_path)]})


def click_generate(client: Any, file_path: Path, browser_path: str, cdp_helper: Any, scene_name: str, quality: str, scene_kind: str) -> None:
    set_file_input(client, file_path, browser_path, cdp_helper)
    script = f"""
    (() => {{
      const setValue = (selector, value) => {{
        const element = document.querySelector(selector);
        if (!element) throw new Error(`missing ${{selector}}`);
        element.value = value;
        element.dispatchEvent(new Event('input', {{ bubbles: true }}));
        element.dispatchEvent(new Event('change', {{ bubbles: true }}));
      }};
      setValue('#wizardCaptureName', {json.dumps(scene_name)});
      setValue('#wizardSceneKind', {json.dumps(scene_kind)});
      setValue('#wizardQualityPreset', {json.dumps(quality)});
      const rights = document.querySelector('#wizardSelfCaptured');
      rights.checked = true;
      rights.dispatchEvent(new Event('change', {{ bubbles: true }}));
      const fileInput = document.querySelector('#videoFileInput');
      fileInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
      fileInput.dispatchEvent(new Event('change', {{ bubbles: true }}));
      const button = document.querySelector('#generatePipelineButton');
      if (!button) throw new Error('generate button missing');
      if (button.disabled) throw new Error(`generate button disabled: ${{document.querySelector('#wizardStatus')?.textContent || ''}}`);
      button.click();
      return true;
    }})()
    """
    evaluate(client, script)


def wait_for_generation(client: Any, timeout_seconds: int, poll_seconds: float) -> dict[str, Any]:
    deadline = time.time() + timeout_seconds
    last_status = ""
    while time.time() < deadline:
        snapshot = wizard_snapshot(client)
        compact = " | ".join(
            str(snapshot.get(key) or "")
            for key in ["wizardStatus", "progress", "currentStage", "eta"]
            if snapshot.get(key)
        )
        if compact != last_status:
            print(f"wizard_status={compact}", flush=True)
            last_status = compact
        if snapshot.get("wizardType") == "fail":
            raise RuntimeError(f"wizard failed: {snapshot}")
        if "Generation complete" in str(snapshot.get("wizardStatus") or ""):
            return snapshot
        time.sleep(poll_seconds)
    raise RuntimeError(f"timed out waiting for generation; last snapshot={wizard_snapshot(client)}")


def gallery_latest(client: Any) -> dict[str, Any]:
    value = evaluate(
        client,
        """
        fetch('/api/gallery', { cache: 'no-store' })
          .then((response) => response.json())
          .then((payload) => payload.items?.[0] || null)
        """,
        await_promise=True,
    )
    return value if isinstance(value, dict) else {}


def run(args: argparse.Namespace) -> None:
    cdp_helper = load_cdp_helper()
    browser = args.browser or cdp_helper.default_browser()
    if not Path(browser).exists():
        raise RuntimeError(f"browser not found: {browser}")

    video_path = Path(args.video).resolve()
    if not video_path.exists():
        raise RuntimeError(f"video not found: {video_path}")

    created_user_data_dir = False
    if args.user_data_dir:
        user_data_dir = Path(args.user_data_dir)
        user_data_dir.mkdir(parents=True, exist_ok=True)
    elif Path(browser).as_posix().startswith("/mnt/c/") and DEFAULT_WSL_WINDOWS_TEMP.exists():
        user_data_dir = Path(tempfile.mkdtemp(prefix="gslab-wizard-e2e-", dir=DEFAULT_WSL_WINDOWS_TEMP))
        created_user_data_dir = True
    else:
        user_data_dir = Path(tempfile.mkdtemp(prefix="gslab-wizard-e2e-"))
        created_user_data_dir = True

    command = [
        browser,
        "--headless=new",
        "--enable-gpu-rasterization",
        "--ignore-gpu-blocklist",
        "--hide-scrollbars",
        f"--remote-debugging-port={args.port}",
        "--remote-debugging-address=0.0.0.0",
        f"--user-data-dir={cdp_helper.as_browser_path(user_data_dir, browser)}",
        f"--window-size={args.width},{args.height}",
        args.url,
    ]

    proc = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    client = None
    try:
        try:
            tabs = cdp_helper.wait_for_devtools(args.devtools_host, args.port, 30)
        except Exception as exc:
            stderr = ""
            if proc.stderr and proc.poll() is not None:
                try:
                    stderr = proc.stderr.read(4000)
                except Exception:
                    stderr = ""
            raise RuntimeError(f"{exc}; browser={browser}; browser_returncode={proc.poll()}; stderr={stderr}") from exc
        page = next((tab for tab in tabs if tab.get("type") == "page"), tabs[0])
        client = cdp_helper.CdpClient(page["webSocketDebuggerUrl"], host_override=args.devtools_host)
        client.command("Page.enable")
        client.command("Runtime.enable")
        client.command("DOM.enable")
        client.command("Page.bringToFront")

        deadline = time.time() + 60
        while time.time() < deadline:
            ready = evaluate(client, "document.readyState")
            if ready == "complete":
                break
            time.sleep(0.25)
        else:
            raise RuntimeError("page did not finish loading")

        click_generate(client, video_path, browser, cdp_helper, args.scene_name, args.quality, args.scene_kind)
        final_snapshot = wait_for_generation(client, args.timeout_seconds, args.poll_seconds)
        latest = gallery_latest(client)

        if args.screenshot:
            screenshot = client.command("Page.captureScreenshot", {"format": "png", "captureBeyondViewport": False})
            output = Path(args.screenshot)
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(base64.b64decode(screenshot["data"]))
            print(f"screenshot={output}", flush=True)

        print("final_snapshot=" + json.dumps(final_snapshot, sort_keys=True), flush=True)
        print("gallery_latest=" + json.dumps(latest, sort_keys=True), flush=True)
    finally:
        if client:
            client.close()
        if proc.poll() is None and Path(browser).as_posix().startswith("/mnt/c/"):
            subprocess.run(
                ["/mnt/c/Windows/System32/taskkill.exe", "/PID", str(proc.pid), "/T", "/F"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
        if created_user_data_dir:
            shutil.rmtree(user_data_dir, ignore_errors=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the upload wizard through a real browser session.")
    parser.add_argument("url")
    parser.add_argument("--video", required=True)
    parser.add_argument("--scene-name", default="Wizard E2E room")
    parser.add_argument("--scene-kind", default="room", choices=["room", "outdoor", "object"])
    parser.add_argument("--quality", default="quality_probe")
    parser.add_argument("--browser")
    parser.add_argument("--port", type=int, default=9238)
    parser.add_argument("--devtools-host", default="127.0.0.1")
    parser.add_argument("--width", type=int, default=1440)
    parser.add_argument("--height", type=int, default=1000)
    parser.add_argument("--timeout-seconds", type=int, default=7200)
    parser.add_argument("--poll-seconds", type=float, default=5.0)
    parser.add_argument("--screenshot")
    parser.add_argument("--user-data-dir")
    args = parser.parse_args()
    run(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
