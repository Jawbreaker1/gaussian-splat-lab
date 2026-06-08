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
