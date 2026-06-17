#!/usr/bin/env python3
"""Capture a browser screenshot through Chrome/Edge DevTools Protocol.

This stays dependency-free so visual QA does not require Puppeteer/Playwright.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import shutil
import socket
import struct
import subprocess
import tempfile
import time
import urllib.request
from pathlib import Path
from urllib.parse import urlparse


DEFAULT_CHROME = "/mnt/c/Program Files/Google/Chrome/Application/chrome.exe"
DEFAULT_EDGE = "/mnt/c/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"
DEFAULT_WSL_WINDOWS_TEMP = Path("/mnt/c/Users/engwa/AppData/Local/Temp")


def default_browser() -> str:
    return DEFAULT_CHROME if Path(DEFAULT_CHROME).exists() else DEFAULT_EDGE


def as_browser_path(path: Path, browser: str) -> str:
    value = path.resolve().as_posix()
    if Path(browser).as_posix().startswith("/mnt/c/") and value.startswith("/mnt/c/"):
        return "C:\\" + value.removeprefix("/mnt/c/").replace("/", "\\")
    return value


def read_exact(sock: socket.socket, size: int) -> bytes:
    chunks: list[bytes] = []
    remaining = size
    while remaining:
        chunk = sock.recv(remaining)
        if not chunk:
            raise RuntimeError("websocket closed")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def send_ws(sock: socket.socket, payload: dict) -> None:
    data = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    header = bytearray([0x81])
    if len(data) < 126:
        header.append(0x80 | len(data))
    elif len(data) < 65536:
        header.append(0x80 | 126)
        header.extend(struct.pack("!H", len(data)))
    else:
        header.append(0x80 | 127)
        header.extend(struct.pack("!Q", len(data)))
    mask = os.urandom(4)
    header.extend(mask)
    masked = bytes(byte ^ mask[index % 4] for index, byte in enumerate(data))
    sock.sendall(bytes(header) + masked)


def recv_ws(sock: socket.socket) -> dict:
    payloads: list[bytes] = []
    while True:
        first, second = read_exact(sock, 2)
        fin = bool(first & 0x80)
        opcode = first & 0x0F
        masked = bool(second & 0x80)
        length = second & 0x7F
        if length == 126:
            length = struct.unpack("!H", read_exact(sock, 2))[0]
        elif length == 127:
            length = struct.unpack("!Q", read_exact(sock, 8))[0]
        mask = read_exact(sock, 4) if masked else b""
        data = read_exact(sock, length) if length else b""
        if masked:
            data = bytes(byte ^ mask[index % 4] for index, byte in enumerate(data))
        if opcode == 0x8:
            raise RuntimeError("websocket closed by browser")
        if opcode == 0x9:
            continue
        payloads.append(data)
        if fin:
            return json.loads(b"".join(payloads).decode("utf-8"))


class CdpClient:
    def __init__(self, websocket_url: str, host_override: str | None = None):
        parsed = urlparse(websocket_url)
        if parsed.scheme != "ws":
            raise ValueError(f"unsupported websocket URL: {websocket_url}")
        port = parsed.port or 80
        host = host_override or parsed.hostname or "127.0.0.1"
        self.sock = socket.create_connection((host, port), timeout=10)
        key = base64.b64encode(os.urandom(16)).decode("ascii")
        request = (
            f"GET {parsed.path} HTTP/1.1\r\n"
            f"Host: {parsed.hostname}:{port}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n\r\n"
        )
        self.sock.sendall(request.encode("ascii"))
        response = self.sock.recv(4096)
        if b" 101 " not in response:
            raise RuntimeError(f"websocket upgrade failed: {response[:120]!r}")
        self.next_id = 1

    def command(self, method: str, params: dict | None = None) -> dict:
        message_id = self.next_id
        self.next_id += 1
        send_ws(self.sock, {"id": message_id, "method": method, "params": params or {}})
        while True:
            message = recv_ws(self.sock)
            if message.get("id") == message_id:
                if "error" in message:
                    raise RuntimeError(f"CDP {method} failed: {message['error']}")
                return message.get("result", {})

    def close(self) -> None:
        self.sock.close()


def wait_for_devtools(host: str, port: int, timeout: float) -> list[dict]:
    deadline = time.time() + timeout
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"http://{host}:{port}/json", timeout=2) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception as exc:  # noqa: BLE001 - local browser readiness boundary
            last_error = exc
            time.sleep(0.2)
    raise RuntimeError(f"DevTools endpoint did not become ready: {last_error}")


def evaluate_text(client: CdpClient) -> str:
    expression = """
    (() => {
      const pill = document.querySelector('#viewerStatusPill')?.textContent || '';
      const overlay = document.querySelector('#sparkOverlay')?.textContent || '';
      const mode = document.querySelector('#viewerModeSparkButton')?.classList.contains('active') ? 'spark' : 'debug';
      return `${mode}|${pill}|${overlay}`;
    })()
    """
    result = client.command("Runtime.evaluate", {"expression": expression, "returnByValue": True})
    return result.get("result", {}).get("value", "")


def capture(args: argparse.Namespace) -> None:
    created_user_data_dir = False
    if args.user_data_dir:
        user_data_dir = Path(args.user_data_dir)
        user_data_dir.mkdir(parents=True, exist_ok=True)
    elif Path(args.browser).as_posix().startswith("/mnt/c/") and DEFAULT_WSL_WINDOWS_TEMP.exists():
        user_data_dir = Path(tempfile.mkdtemp(prefix="gslab-browser-", dir=DEFAULT_WSL_WINDOWS_TEMP))
        created_user_data_dir = True
    else:
        user_data_dir = Path(tempfile.mkdtemp(prefix="gslab-browser-"))
        created_user_data_dir = True
    command = [
        args.browser,
        "--headless=new",
        "--enable-gpu-rasterization",
        "--ignore-gpu-blocklist",
        "--hide-scrollbars",
        f"--remote-debugging-port={args.port}",
        "--remote-debugging-address=0.0.0.0",
        f"--user-data-dir={as_browser_path(user_data_dir, args.browser)}",
        f"--window-size={args.width},{args.height}",
        args.url,
    ]
    if args.disable_gpu:
        command.insert(2, "--disable-gpu")
    proc = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    client: CdpClient | None = None
    try:
        try:
            tabs = wait_for_devtools(args.devtools_host, args.port, 20)
        except Exception as exc:  # noqa: BLE001 - include browser diagnostics
            stderr = ""
            if proc.stderr and proc.poll() is not None:
                try:
                    stderr = proc.stderr.read(4000)
                except Exception:
                    stderr = ""
            raise RuntimeError(f"{exc}; browser_returncode={proc.poll()}; stderr={stderr}") from exc
        page = next((tab for tab in tabs if tab.get("type") == "page"), tabs[0])
        client = CdpClient(page["webSocketDebuggerUrl"], host_override=args.devtools_host)
        client.command("Page.enable")
        client.command("Runtime.enable")

        deadline = time.time() + args.wait_timeout
        last_text = ""
        while time.time() < deadline:
            last_text = evaluate_text(client)
            if args.wait_text in last_text or "Spark unavailable" in last_text:
                break
            time.sleep(0.5)
        else:
            raise RuntimeError(f"timed out waiting for {args.wait_text!r}; last UI text: {last_text!r}")

        if args.extra_wait:
            time.sleep(args.extra_wait)
        screenshot = client.command("Page.captureScreenshot", {"format": "png", "captureBeyondViewport": False})
        Path(args.output).write_bytes(base64.b64decode(screenshot["data"]))
        print(f"screenshot={args.output}")
        print(f"ui_text={last_text}")
    finally:
        if client:
            client.close()
        if proc.poll() is None and Path(args.browser).as_posix().startswith("/mnt/c/"):
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
    parser = argparse.ArgumentParser(description="Capture a local UI screenshot after waiting for UI text.")
    parser.add_argument("url")
    parser.add_argument("--output", required=True)
    parser.add_argument("--browser", default=default_browser())
    parser.add_argument("--port", type=int, default=9227)
    parser.add_argument("--devtools-host", default="127.0.0.1")
    parser.add_argument("--width", type=int, default=1440)
    parser.add_argument("--height", type=int, default=1000)
    parser.add_argument("--wait-text", default="reference inspect")
    parser.add_argument("--wait-timeout", type=float, default=120)
    parser.add_argument("--extra-wait", type=float, default=1.0)
    parser.add_argument("--user-data-dir")
    parser.add_argument("--disable-gpu", action="store_true", help="Force software/GPU-disabled screenshot mode for debugging only.")
    args = parser.parse_args()
    capture(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
