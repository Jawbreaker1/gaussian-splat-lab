#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

python3 -m py_compile "${repo_root}/scripts/lab-ui-server.py"
python3 "${repo_root}/scripts/lab-ui-server.py" --check

python3 - <<'PYCODE' "${repo_root}"
from pathlib import Path
import sys

repo_root = Path(sys.argv[1])
app_files = [repo_root / "app/index.html", repo_root / "app/styles.css", repo_root / "app/app.js"]
for path in app_files:
    text = path.read_text(encoding="utf-8")
    if "https://" in text or "http://" in text:
        raise SystemExit(f"external URL found in {path}")
    if 'script src="http' in text:
        raise SystemExit(f"remote script found in {path}")

print("ui_dependency_check=passed")
PYCODE

python3 - <<'PYCODE' "${repo_root}"
from pathlib import Path
import importlib.util
import io
import json
import shutil
import sys

repo_root = Path(sys.argv[1])
fixture_dir = repo_root / "data/tmp/ui-import-contract"
try:
    fixture_dir.mkdir(parents=True, exist_ok=True)
    manifest = fixture_dir / "manifest.json"
    manifest.write_text(json.dumps({
        "schemaVersion": 1,
        "captures": [
            {
                "id": "ui-import-contract",
                "displayName": "UI import contract",
                "source": {
                    "kind": "local_file",
                    "path": "data/tmp/ui-import-contract/imported.mp4",
                    "sourceUrl": None,
                    "license": "self-captured-test",
                    "licenseNotes": "Synthetic UI import contract fixture; not a real video.",
                },
                "capture": {
                    "subject": "fixture",
                    "motion": "none",
                    "expectedDurationSeconds": None,
                    "expectedResolution": None,
                },
                "pipeline": {
                    "frameSampling": {"targetFps": 1, "maxFrames": 1},
                    "sfm": {"backend": "colmap"},
                    "training": {"backend": "gsplat", "targetWorker": "windows-rtx-5090"},
                    "packaging": {"preferredFormats": ["ply", "ksplat", "splat"]},
                },
                "status": "contract-fixture",
            }
        ],
    }, indent=2) + "\n", encoding="utf-8")

    spec = importlib.util.spec_from_file_location("lab_ui_server_test", repo_root / "scripts/lab-ui-server.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    module.CAPTURE_MANIFEST = manifest
    payload = b"ui import contract fixture\n"
    result = module.save_capture_upload(
        capture_id="ui-import-contract",
        stream=io.BytesIO(payload),
        content_length=len(payload),
        upload_name="fixture.mp4",
        accept_warning=False,
        overwrite=True,
    )
    if result["report"]["status"] != "pass":
        raise SystemExit(f"UI import contract failed: {result['report']['status']}")
    if not (fixture_dir / "imported.mp4").exists():
        raise SystemExit("UI import contract did not write target file")
finally:
    shutil.rmtree(fixture_dir, ignore_errors=True)

print("ui_import_contract=passed")
PYCODE
